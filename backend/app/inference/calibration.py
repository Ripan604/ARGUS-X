from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.app.inference.diagnostics import QualityEstimate
from backend.app.inference.nuisance_posterior import NuisancePosterior
from backend.app.models.domain import Experiment, Panel, physical_distance


@dataclass
class CalibrationResult:
    calibration_type: str
    updated_parameters: tuple[str, ...]
    uncertainty_before: float
    uncertainty_after: float
    observation: dict[str, float]
    explanation: str
    accepted: bool = True

    def to_dict(self) -> dict:
        return {
            "calibration_type": self.calibration_type,
            "updated_parameters": list(self.updated_parameters),
            "uncertainty_before": self.uncertainty_before,
            "uncertainty_after": self.uncertainty_after,
            "observation": self.observation,
            "explanation": self.explanation,
            "accepted": self.accepted,
        }


class CalibrationEngine:
    def update(
        self,
        posterior: NuisancePosterior,
        experiment: Experiment,
        panel: Panel,
        diagnostics: dict[str, float],
        quality: QualityEstimate,
        calibration_type: str = "direct_path",
    ) -> CalibrationResult:
        before = posterior.uncertainty_summary()["combined"]
        if not quality.accepted:
            return CalibrationResult(
                calibration_type,
                (),
                before,
                before,
                {},
                "Calibration was rejected because the reference acquisition failed signal-quality checks.",
                accepted=False,
            )
        if any(not isinstance(value, (int, float, np.number)) or not np.isfinite(value) for value in diagnostics.values()):
            return CalibrationResult(calibration_type, (), before, before, {},
                                     "Calibration diagnostics must be finite measured values.", accepted=False)
        supported = {"direct_path", "timing_calibration", "healthy_reference", "frequency_sweep",
                     "phone_pose_recalibration", "coupling_repeat", "microphone_level_check"}
        if calibration_type not in supported:
            return CalibrationResult(calibration_type, (), before, before, {},
                                     "Unsupported calibration type; no nuisance state was changed.", accepted=False)
        if calibration_type in {"direct_path", "timing_calibration", "healthy_reference", "frequency_sweep"} and "peak_delay_s" not in diagnostics:
            return CalibrationResult(calibration_type, (), before, before, {},
                                     "Propagation calibration requires a measured direct-path delay.", accepted=False)
        if calibration_type in {"coupling_repeat", "microphone_level_check", "healthy_reference"} and (
            "baseline_rms" not in diagnostics or "signal_rms" not in diagnostics or diagnostics["baseline_rms"] <= 0
            or diagnostics["signal_rms"] < 0
        ):
            return CalibrationResult(calibration_type, (), before, before, {},
                                     "Gain calibration requires a positive reference RMS and measured signal RMS.", accepted=False)
        if "noise_floor" not in diagnostics and "noise_estimate" not in diagnostics:
            return CalibrationResult(calibration_type, (), before, before, {},
                                     "Calibration requires a measured noise estimate.", accepted=False)
        if diagnostics.get("noise_floor", diagnostics.get("noise_estimate", 0)) < 0:
            return CalibrationResult(calibration_type, (), before, before, {},
                                     "Measured noise cannot be negative.", accepted=False)
        if calibration_type == "phone_pose_recalibration" and "pose_observation_std" in diagnostics and diagnostics["pose_observation_std"] <= 0:
            return CalibrationResult(calibration_type, (), before, before, {},
                                     "Pose measurement uncertainty must be positive.", accepted=False)
        if calibration_type == "phone_pose_recalibration":
            for name in ("source_pose_error", "receiver_pose_error"):
                if name + "_observed" in diagnostics:
                    parameter = posterior.parameter(name)
                    if not parameter.lower <= diagnostics[name + "_observed"] <= parameter.upper:
                        return CalibrationResult(calibration_type, (), before, before, {},
                            "Measured pose error is outside the supported calibration model.", accepted=False)
        strength = float(np.clip(quality.evidence_weight, 0, 1))
        updated: list[str] = []
        observation: dict[str, float] = {}
        if calibration_type in {"direct_path", "timing_calibration", "healthy_reference", "frequency_sweep"}:
            distance = float(physical_distance(experiment.source_x, experiment.source_y, experiment.receiver_x, experiment.receiver_y, panel))
            observed_delay = float(diagnostics.get("peak_delay_s", 0.0))
            observation_std = float(diagnostics.get("delay_std_s", 0.00020))
            try:
                observation.update(posterior.update_direct_path(distance, observed_delay, observation_std, strength))
            except ValueError as exc:
                return CalibrationResult(calibration_type, (), before, before, {}, str(exc), accepted=False)
            updated.extend(["wave_velocity", "timing_offset"])
        if calibration_type == "phone_pose_recalibration":
            # A good waveform or a stationary phone does not measure absolute probe pose.
            required = ("source_pose_error_observed", "receiver_pose_error_observed", "pose_observation_std")
            if any(name not in diagnostics for name in required):
                return CalibrationResult(calibration_type, (), before, before, {},
                    "Pose calibration requires measured pose errors and their uncertainty from an external reference.", accepted=False)
            for name in ("source_pose_error", "receiver_pose_error"):
                posterior.parameter(name).update(diagnostics[name + "_observed"], diagnostics["pose_observation_std"], strength)
                updated.append(name)
        noise = float(max(diagnostics.get("noise_floor", diagnostics.get("noise_estimate", 0.005)), 0.0001))
        posterior.parameter("noise_scale").update(noise, max(noise * 0.55, 0.001), strength)
        observation.update({"noise_scale": noise, "coupling_quality": quality.coupling_quality})
        # A channel-quality score is not an observation of the two independent
        # coupling coefficients. Their product is confounded with gain.
        updated.append("noise_scale")
        if calibration_type in {"coupling_repeat", "microphone_level_check", "healthy_reference"}:
            baseline_rms = max(float(diagnostics.get("baseline_rms", 0.0)), 1e-9)
            signal_rms = max(float(diagnostics.get("signal_rms", baseline_rms)), 0.0)
            observed_gain = float(np.clip(signal_rms / baseline_rms, 0.1, 3.0))
            posterior.parameter("gain").update(observed_gain, 0.20, strength)
            observation["estimated_gain"] = observed_gain
            updated.append("gain")
        posterior.calibration_count += 1
        after = posterior.uncertainty_summary()["combined"]
        return CalibrationResult(
            calibration_type, tuple(dict.fromkeys(updated)), before, after, observation,
            f"{calibration_type.replace('_', ' ').title()} changed normalized metrology uncertainty from {before:.3f} to {after:.3f}; propagation uses a correlated first-order Gaussian approximation.",
        )
