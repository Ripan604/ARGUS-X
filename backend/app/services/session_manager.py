from __future__ import annotations

from dataclasses import dataclass, field
import io
import json
import secrets
from threading import RLock

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

from backend.app.core.config import ArgusConfig, config_for_profile
from backend.app.core.materials import get_material_profile
from backend.app.database.repository import SessionRepository
from backend.app.evidence.ledger import EvidenceLedger
from backend.app.inference.diagnostics import estimate_measurement_quality
from backend.app.inference.joint_state import JointInferenceState
from backend.app.inference.structural_posterior import StructuralPosterior
from backend.app.models.domain import Defect, Experiment, Material, Panel
from backend.app.schemas.api import CreateSessionRequest
from backend.app.services.engine import ArgusEngine
from backend.app.safety.constraints import NoGoRegion


@dataclass
class SessionRuntime:
    id: str
    mode: str
    preset: str
    engine: ArgusEngine
    revealed: bool = False
    calibration: dict | None = None
    no_go_regions: list[NoGoRegion] = field(default_factory=list)
    unavailable_action_keys: set[str] = field(default_factory=set)
    human_decisions: list[dict] = field(default_factory=list)


class SessionManager:
    def __init__(self, repository: SessionRepository) -> None:
        self.repository = repository
        self._sessions: dict[str, SessionRuntime] = {}
        self._lock = RLock()
        self.ledger = EvidenceLedger(repository)

    def create(self, request: CreateSessionRequest) -> SessionRuntime:
        seed = request.seed if request.seed is not None else secrets.randbelow(2**31 - 1)
        config = config_for_profile(
            request.config_profile, grid_size=request.grid_size,
            max_experiments=request.max_experiments, seed=seed,
        )
        profile = get_material_profile(request.material_profile)
        panel = Panel(request.panel_width_mm / 1_000, request.panel_height_mm / 1_000, request.material_profile)
        engine = ArgusEngine(config=config, panel=panel, material=profile.material, seed=seed, preset=request.preset)
        runtime = SessionRuntime(secrets.token_urlsafe(12), request.mode, request.preset, engine)
        with self._lock:
            self._sessions[runtime.id] = runtime
            self.repository.create_session(runtime.id, runtime.mode, runtime.preset, self._serialize(runtime))
        return runtime

    def get(self, session_id: str) -> SessionRuntime:
        with self._lock:
            if session_id in self._sessions:
                return self._sessions[session_id]
            record = self.repository.get_session(session_id)
            if record is None:
                raise KeyError(session_id)
            runtime = self._hydrate(session_id, record["mode"], record["preset"], record["state"])
            self._sessions[session_id] = runtime
            return runtime

    def run(self, session_id: str, experiment: Experiment | None = None):
        with self._lock:
            runtime = self.get(session_id)
            if runtime.mode == "physical":
                raise RuntimeError("Physical sessions require an acquired microphone, WAV, or serial signal")
            if runtime.engine.status()["should_stop"] and experiment is None:
                # Manual custom experiments remain possible after automatic termination.
                raise RuntimeError("Automatic stop condition reached; submit a custom experiment to continue")
            result = runtime.engine.run_experiment(experiment) if experiment else runtime.engine.run_recommended()
            self._persist_result(runtime, result, "simulation")
            return result

    def process_wav(self, session_id: str, payload: bytes, experiment: Experiment | None = None):
        if len(payload) > 10 * 1024 * 1024:
            raise ValueError("WAV upload exceeds the 10 MB limit")
        try:
            source_rate, samples = wavfile.read(io.BytesIO(payload))
        except Exception as exc:
            raise ValueError("Invalid or unsupported WAV file") from exc
        if samples.ndim == 2:
            samples = np.mean(samples.astype(np.float64), axis=1)
        if np.issubdtype(samples.dtype, np.integer):
            samples = samples.astype(np.float64) / max(abs(np.iinfo(samples.dtype).min), np.iinfo(samples.dtype).max)
        else:
            samples = samples.astype(np.float64)
        return self.process_samples(session_id, samples, int(source_rate), experiment, acquisition_source="wav_upload")

    def process_samples(
        self,
        session_id: str,
        samples: np.ndarray,
        source_rate: int,
        experiment: Experiment | None = None,
        acquisition_source: str = "external_samples",
        sensor_metadata: dict | None = None,
    ):
        runtime = self.get(session_id)
        target_rate = runtime.engine.config.sample_rate
        values = np.asarray(samples, dtype=np.float64).reshape(-1)
        if values.size < 8 or not np.all(np.isfinite(values)):
            raise ValueError("Acquired signal is empty or contains invalid samples")
        if source_rate != target_rate:
            divisor = int(np.gcd(source_rate, target_rate))
            values = resample_poly(values, target_rate // divisor, source_rate // divisor)
        target_length = int(runtime.engine.config.signal_duration * target_rate)
        normalized = np.zeros(target_length, dtype=np.float32)
        normalized[: min(target_length, len(values))] = values[:target_length]
        selected = experiment or runtime.engine.current_recommendation.selected.experiment
        with self._lock:
            result = runtime.engine.process_signal(normalized, selected, quality_context=sensor_metadata)
            self._persist_result(runtime, result, acquisition_source)
        return result

    def _persist_result(self, runtime: SessionRuntime, result, acquisition_source: str) -> None:
        self.repository.add_experiment(runtime.id, result)
        self.ledger.append(runtime.id, result, runtime.engine, acquisition_source)
        self.refresh_recommendation(runtime)
        self.repository.update_session(runtime.id, self._serialize(runtime))

    def refresh_recommendation(self, runtime: SessionRuntime) -> None:
        runtime.engine.current_recommendation = runtime.engine._recommend(runtime.no_go_regions, runtime.unavailable_action_keys)

    def set_no_go_regions(self, session_id: str, regions: list[dict]) -> dict:
        runtime = self.get(session_id)
        runtime.no_go_regions = [NoGoRegion(**region) for region in regions]
        self.refresh_recommendation(runtime)
        self.repository.add_event(session_id, "no_go_regions_updated", {"regions": regions})
        self.repository.update_session(session_id, self._serialize(runtime))
        return self.public_state(runtime)

    def human_decision(self, session_id: str, decision: str, reason: str | None = None, experiment: dict | None = None) -> dict:
        runtime = self.get(session_id)
        current = runtime.engine.current_recommendation.selected.experiment
        selected = Experiment(**experiment) if experiment else current
        record = {"decision": decision, "reason": reason, "experiment": selected.to_dict(), "recommendation": current.to_dict()}
        runtime.human_decisions.append(record)
        if decision == "reject":
            runtime.unavailable_action_keys.add(json.dumps(selected.to_dict(), sort_keys=True, separators=(",", ":")))
            self.refresh_recommendation(runtime)
        self.repository.add_event(session_id, "human_decision", record)
        self.repository.update_session(session_id, self._serialize(runtime))
        return {"recorded": True, "decision": record, "state": self.public_state(runtime)}

    def calibrate(self, session_id: str) -> dict:
        runtime = self.get(session_id)
        simulator = runtime.engine.acquisition_simulator
        references = [
            Experiment(0.05, 0.08, 0.95, 0.08, 1_200, 3_000, 0.38, 0.12, "chirp"),
            Experiment(0.05, 0.92, 0.95, 0.92, 2_200, 4_400, 0.38, 0.12, "chirp"),
            Experiment(0.08, 0.05, 0.08, 0.95, 3_400, 6_200, 0.38, 0.12, "chirp"),
        ]
        baselines = [simulator.simulate_baseline(item) for item in references]
        updates = []
        for experiment, baseline in zip(references, baselines):
            measured = (baseline + simulator.rng.normal(0.0, simulator.material.noise_std, len(baseline))).astype(np.float32)
            quality = estimate_measurement_quality(measured)
            diagnostics = runtime.engine._direct_path_diagnostics(measured, experiment)
            updates.append(
                runtime.engine.calibration_engine.update(
                    runtime.engine.joint_state.nuisance,
                    experiment,
                    runtime.engine.panel,
                    diagnostics,
                    quality,
                    "healthy_reference",
                ).to_dict()
            )
        runtime.engine.joint_state.last_calibration = updates[-1]
        runtime.engine.synchronize_inference_material()
        self.refresh_recommendation(runtime)
        runtime.calibration = {
            "status": "calibrated",
            "reference_count": len(references),
            "estimated_noise_std": simulator.material.noise_std,
            "estimated_wave_velocity_m_s": simulator.material.wave_velocity,
            "baseline_rms": [float(np.sqrt(np.mean(values**2))) for values in baselines],
            "resonance_hz": simulator.material.resonance_hz,
            "updates": updates,
            "nuisance_posterior": runtime.engine.joint_state.nuisance.to_dict(),
        }
        self.repository.update_session(session_id, self._serialize(runtime))
        return runtime.calibration

    def public_state(self, runtime: SessionRuntime) -> dict:
        engine = runtime.engine
        status = engine.status()
        return {
            "id": runtime.id, "mode": runtime.mode, "preset": runtime.preset,
            "revealed": runtime.revealed, "panel": engine.panel.to_dict(), "material": engine.material.to_dict(),
            "config": engine.config.to_dict(), "status": status, "posterior": engine.belief.to_list(),
            "recommendation": engine.current_recommendation.to_dict(), "calibration": runtime.calibration,
            "joint_inference": engine.joint_state.to_dict(),
            "uncertainty": engine.joint_state.uncertainty_summary(),
            "ground_truth": engine.truth.to_dict() if runtime.revealed else None,
            "localization_error_mm": engine.localization_error() * 1_000 if runtime.revealed else None,
            "no_go_regions": [region.to_dict() for region in runtime.no_go_regions],
            "human_decisions": runtime.human_decisions,
        }

    def reveal(self, session_id: str) -> dict:
        runtime = self.get(session_id)
        if runtime.mode != "simulation":
            raise RuntimeError("Ground truth is available only for simulation sessions")
        runtime.revealed = True
        self.repository.update_session(session_id, self._serialize(runtime))
        return self.public_state(runtime)

    def _serialize(self, runtime: SessionRuntime) -> dict:
        engine = runtime.engine
        return {
            "seed": engine.seed, "config": engine.config.to_dict(), "panel": engine.panel.to_dict(),
            "material": engine.material.to_dict(), "truth": engine.truth.to_dict(),
            "posterior": engine.belief.to_list(), "revealed": runtime.revealed, "calibration": runtime.calibration,
            "experiments": [item.to_dict() for item in engine.experiments],
            "rng_state": engine.simulator.rng.bit_generator.state,
            "joint_inference": engine.joint_state.to_dict(),
            "discrepancy_model": engine.discrepancy_model.to_dict(),
            "ood_detector": engine.ood_detector.to_dict(),
            "acquisition_material": engine.acquisition_material.to_dict() if engine.acquisition_material else None,
            "acquisition_rng_state": engine.acquisition_simulator.rng.bit_generator.state if engine.acquisition_material else None,
            "no_go_regions": [region.to_dict() for region in runtime.no_go_regions],
            "unavailable_action_keys": sorted(runtime.unavailable_action_keys),
            "human_decisions": runtime.human_decisions,
        }

    def _hydrate(self, session_id: str, mode: str, preset: str, state: dict) -> SessionRuntime:
        engine = ArgusEngine(
            config=ArgusConfig(**state["config"]), panel=Panel(**state["panel"]), material=Material(**state["material"]),
            seed=state["seed"], preset=preset, truth=Defect(**state["truth"]),
            acquisition_material=Material(**state["acquisition_material"]) if state.get("acquisition_material") else None,
        )
        if state.get("joint_inference"):
            engine.joint_state = JointInferenceState.from_dict(state["joint_inference"], engine.material)
            engine.belief = engine.joint_state.structural
        else:
            engine.belief = StructuralPosterior(engine.config.grid_size, np.asarray(state["posterior"]))
            engine.joint_state = JointInferenceState.nominal(engine.belief, engine.material)
        engine.experiments = [Experiment(**item) for item in state.get("experiments", [])]
        if "rng_state" in state:
            engine.simulator.rng.bit_generator.state = state["rng_state"]
        if state.get("acquisition_rng_state") and engine.acquisition_material:
            engine.acquisition_simulator.rng.bit_generator.state = state["acquisition_rng_state"]
        if state.get("discrepancy_model"):
            from backend.app.digital_twin.discrepancy import OnlineDiscrepancyModel

            engine.discrepancy_model = OnlineDiscrepancyModel.from_dict(state["discrepancy_model"])
            engine.neo_planner.discrepancy = engine.discrepancy_model
        if state.get("ood_detector"):
            from backend.app.ood.detection import OODDetector

            engine.ood_detector = OODDetector.from_dict(state["ood_detector"])
        engine.current_recommendation = engine._recommend()
        runtime = SessionRuntime(
            session_id, mode, preset, engine, state.get("revealed", False), state.get("calibration"),
            [NoGoRegion(**item) for item in state.get("no_go_regions", [])],
            set(state.get("unavailable_action_keys", [])),
            state.get("human_decisions", []),
        )
        self.refresh_recommendation(runtime)
        return runtime
