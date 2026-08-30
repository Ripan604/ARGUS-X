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

    def to_dict(self) -> dict:
        return {
            "calibration_type": self.calibration_type,
            "updated_parameters": list(self.updated_parameters),
            "uncertainty_before": self.uncertainty_before,
            "uncertainty_after": self.uncertainty_after,
            "observation": self.observation,
            "explanation": self.explanation,
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
        strength = float(np.clip(max(quality.evidence_weight, 0.08), 0, 1))
        updated: list[str] = []
        observation: dict[str, float] = {}
        if calibration_type in {"direct_path", "timing_calibration", "healthy_reference", "frequency_sweep"}:
            distance = float(physical_distance(experiment.source_x, experiment.source_y, experiment.receiver_x, experiment.receiver_y, panel))
            observed_delay = float(diagnostics.get("peak_delay_s", 0.0))
            travel_time = observed_delay - posterior.parameter("timing_offset").mean
            if distance > 0.01 and travel_time > 1e-5:
                observed_velocity = float(np.clip(distance / travel_time, 80.0, 400.0))
                posterior.parameter("wave_velocity").update(observed_velocity, 14.0, strength)
                observation["estimated_wave_velocity_m_s"] = observed_velocity
                updated.append("wave_velocity")
            observed_timing = float(np.clip(observed_delay - distance / max(posterior.parameter("wave_velocity").mean, 1.0), 0.0, 0.004))
            posterior.parameter("timing_offset").update(observed_timing, 0.00020, strength)
            observation["estimated_timing_offset_s"] = observed_timing
            updated.append("timing_offset")
        noise = float(max(diagnostics.get("noise_floor", diagnostics.get("noise_estimate", 0.005)), 0.0001))
        posterior.parameter("noise_scale").update(noise, max(noise * 0.55, 0.001), strength)
        posterior.parameter("source_coupling").update(quality.coupling_quality, 0.18, strength)
        posterior.parameter("receiver_coupling").update(quality.coupling_quality, 0.18, strength)
        observation.update({"noise_scale": noise, "coupling_quality": quality.coupling_quality})
        updated.extend(["noise_scale", "source_coupling", "receiver_coupling"])
        posterior.calibration_count += 1
        after = posterior.uncertainty_summary()["combined"]
        return CalibrationResult(
            calibration_type, tuple(dict.fromkeys(updated)), before, after, observation,
            f"{calibration_type.replace('_', ' ').title()} reduced normalized metrology uncertainty from {before:.3f} to {after:.3f}.",
        )
