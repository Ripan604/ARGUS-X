from __future__ import annotations

from dataclasses import dataclass
import io
import secrets
from threading import RLock

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

from backend.app.core.config import ArgusConfig
from backend.app.database.repository import SessionRepository
from backend.app.inference.belief import BeliefState
from backend.app.models.domain import Defect, Experiment, Material, Panel
from backend.app.schemas.api import CreateSessionRequest
from backend.app.services.engine import ArgusEngine


@dataclass
class SessionRuntime:
    id: str
    mode: str
    preset: str
    engine: ArgusEngine
    revealed: bool = False
    calibration: dict | None = None


class SessionManager:
    def __init__(self, repository: SessionRepository) -> None:
        self.repository = repository
        self._sessions: dict[str, SessionRuntime] = {}
        self._lock = RLock()

    def create(self, request: CreateSessionRequest) -> SessionRuntime:
        seed = request.seed if request.seed is not None else secrets.randbelow(2**31 - 1)
        config = ArgusConfig(grid_size=request.grid_size, max_experiments=request.max_experiments, seed=seed)
        panel = Panel(request.panel_width_mm / 1_000, request.panel_height_mm / 1_000)
        engine = ArgusEngine(config=config, panel=panel, seed=seed, preset=request.preset)
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
            self.repository.add_experiment(session_id, result)
            self.repository.update_session(session_id, self._serialize(runtime))
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
        return self.process_samples(session_id, samples, int(source_rate), experiment)

    def process_samples(
        self,
        session_id: str,
        samples: np.ndarray,
        source_rate: int,
        experiment: Experiment | None = None,
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
            result = runtime.engine.process_signal(normalized, selected)
            self.repository.add_experiment(session_id, result)
            self.repository.update_session(session_id, self._serialize(runtime))
        return result

    def calibrate(self, session_id: str) -> dict:
        runtime = self.get(session_id)
        simulator = runtime.engine.simulator
        references = [
            Experiment(0.05, 0.08, 0.95, 0.08, 1_200, 3_000, 0.38, 0.12, "chirp"),
            Experiment(0.05, 0.92, 0.95, 0.92, 2_200, 4_400, 0.38, 0.12, "chirp"),
            Experiment(0.08, 0.05, 0.08, 0.95, 3_400, 6_200, 0.38, 0.12, "chirp"),
        ]
        baselines = [simulator.simulate_baseline(item) for item in references]
        runtime.calibration = {
            "status": "calibrated",
            "reference_count": len(references),
            "estimated_noise_std": simulator.material.noise_std,
            "estimated_wave_velocity_m_s": simulator.material.wave_velocity,
            "baseline_rms": [float(np.sqrt(np.mean(values**2))) for values in baselines],
            "resonance_hz": simulator.material.resonance_hz,
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
            "ground_truth": engine.truth.to_dict() if runtime.revealed else None,
            "localization_error_mm": engine.localization_error() * 1_000 if runtime.revealed else None,
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
        }

    def _hydrate(self, session_id: str, mode: str, preset: str, state: dict) -> SessionRuntime:
        engine = ArgusEngine(
            config=ArgusConfig(**state["config"]), panel=Panel(**state["panel"]), material=Material(**state["material"]),
            seed=state["seed"], preset=preset, truth=Defect(**state["truth"]),
        )
        engine.belief = BeliefState(engine.config.grid_size, np.asarray(state["posterior"]))
        engine.experiments = [Experiment(**item) for item in state.get("experiments", [])]
        if "rng_state" in state:
            engine.simulator.rng.bit_generator.state = state["rng_state"]
        engine.current_recommendation = engine.planner.recommend(engine.belief.posterior, engine.experiments)
        return SessionRuntime(session_id, mode, preset, engine, state.get("revealed", False), state.get("calibration"))
