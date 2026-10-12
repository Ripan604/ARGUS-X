from __future__ import annotations

from dataclasses import dataclass
import numpy as np
from scipy.signal import resample_poly

from backend.app.models.domain import Experiment, physical_distance
from backend.app.replay.datasets import CounterfactualDataset, _validate_action, _validate_metadata, _validate_rate
from backend.app.replay.safe_io import MAX_ARTIFACT_BYTES, MAX_BANK_ACTIONS, MAX_SIGNAL_SAMPLES, validate_signal
from backend.app.services.engine import ArgusEngine


@dataclass
class AdaptiveReplayRunner:
    """Execute adaptive selection against a finite, truth-sealed response bank."""

    engine: ArgusEngine
    dataset: CounterfactualDataset

    def run(self, maximum: int | None = None, *, reveal_at_end: bool = True) -> dict:
        if not self.dataset.truth_is_sealed:
            raise PermissionError("Blind replay cannot reuse a dataset whose truth has been revealed")
        if maximum is not None and (isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 1):
            raise ValueError("Replay maximum must be a positive integer")
        action_payloads = self.dataset.list_available_actions()
        if not isinstance(action_payloads, list) or not 1 <= len(action_payloads) <= MAX_BANK_ACTIONS:
            raise ValueError("Response-bank action count must be between 1 and 1000")
        actions = [Experiment(**_validate_action(item)) for item in action_payloads]
        remaining = {self.engine.neo_planner._key(item): item for item in actions}
        if len(remaining) != len(actions):
            raise ValueError("Duplicate actions cannot be used as independent replay evidence")
        metadata = _validate_metadata(self.dataset.get_metadata())
        maximum = min(maximum if maximum is not None else self.engine.config.max_experiments, len(actions))
        # Validate and window every recorded response before changing the engine.
        # A short acquisition cannot become evidence through implicit zero padding.
        observations, provenance = {}, {}
        total_bytes = 0
        for key, action in remaining.items():
            signal = validate_signal(self.dataset.get_observation(action))
            source_rate = _validate_rate(metadata.get("sample_rates", {}).get(key,
                                         metadata.get("sample_rate", self.engine.config.sample_rate)))
            if action.frequency_end_hz >= source_rate / 2:
                raise ValueError("Replay excitation band must be below the original recording Nyquist frequency")
            target_samples = max(32, int(round(self.engine.config.sample_rate * action.duration_s)))
            if not 8 <= target_samples <= MAX_SIGNAL_SAMPLES:
                raise ValueError("Replay acquisition window exceeds supported bounds")
            if signal.size < max(32, int(round(source_rate * action.duration_s))):
                raise ValueError("Replay recording is shorter than the experiment acquisition window")
            original_samples = int(signal.size)
            # Crop at source rate before resampling, avoiding a large expansion
            # when a low-rate recording contains many unused samples.
            source_window_samples = int(np.ceil(source_rate * action.duration_s))
            signal = signal[:source_window_samples]
            if source_rate != self.engine.config.sample_rate:
                divisor = int(np.gcd(source_rate, self.engine.config.sample_rate))
                signal = resample_poly(signal, self.engine.config.sample_rate // divisor, source_rate // divisor).astype(np.float32)
            if signal.size < target_samples:
                raise ValueError("Resampled replay recording is shorter than the acquisition window")
            signal = validate_signal(signal[:target_samples])
            total_bytes += signal.nbytes
            if total_bytes > MAX_ARTIFACT_BYTES:
                raise ValueError("Resampled replay bank exceeds the 100 MB limit")
            observations[key] = signal
            provenance[key] = {"source_sample_rate": source_rate, "source_samples": original_samples,
                               "source_window_samples": source_window_samples,
                               "target_sample_rate": self.engine.config.sample_rate,
                               "target_window_samples": target_samples, "padding_applied": False}
        trace = []
        for _ in range(maximum):
            if not remaining or self.engine.status()["should_stop"]:
                break
            kinds = metadata.get("action_types", {})
            diagnostics = [a for key, a in remaining.items() if kinds.get(key, "diagnostic") == "diagnostic"]
            calibrations = [a for key, a in remaining.items() if kinds.get(key) == "calibration"]
            if not diagnostics:
                break
            if self.engine.config.enable_risk_calibration_design:
                plan = self.engine.risk_planner.recommend(self.engine.joint_state, self.engine.experiments,
                    candidate_override=diagnostics, calibration_override=calibrations)
            else:
                plan = self.engine.neo_planner.recommend(
                    self.engine.joint_state, self.engine.experiments,
                    action_type="diagnostic", objective=self.engine.config.planner_objective,
                    candidate_override=diagnostics,
                )
            experiment = plan.selected.experiment
            key = self.engine.neo_planner._key(experiment)
            if key not in remaining or not self.dataset.truth_is_sealed:
                raise ValueError("Replay selection is unavailable or ground truth was unsealed during execution")
            signal = observations[key]
            synthetic = metadata.get("evidence_source") in {"simulated", "physics_simulation", "synthetic"}
            result = self.engine.process_signal(signal, experiment, plan, plan_next=False,
                                                physical_acquisition=not synthetic)
            self.engine.current_recommendation = plan
            remaining.pop(self.engine.neo_planner._key(experiment))
            trace.append({
                "experiment_index": result.index, "experiment": experiment.to_dict(),
                "recommendation": plan.to_dict(), "status": self.engine.status(),
                "acquisition_provenance": provenance[key],
                "evidence_source_declaration": "simulated" if synthetic else "imported_measurement",
            })
        report = {
            "metadata": self.dataset.get_metadata(), "trace": trace,
            "final_status": self.engine.status(), "available_action_count": len(actions),
            "selected_action_count": len(trace), "truth_was_sealed_during_execution": self.dataset.truth_is_sealed,
            "blinding_scope": "operational_API_contract; not an adversarial process isolation boundary",
        }
        if reveal_at_end:
            truth = self.dataset.end_blind_evaluation()
            report["revealed_truth"] = truth
            if "center_x" in truth and "center_y" in truth:
                estimate = self.engine.belief.estimate()
                report["localization_error_mm"] = float(
                    physical_distance(estimate["map_x"], estimate["map_y"], truth["center_x"], truth["center_y"], self.engine.panel) * 1_000
                )
        return report
