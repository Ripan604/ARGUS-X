from __future__ import annotations

from dataclasses import asdict, dataclass, field

import numpy as np

from backend.app.models.domain import Experiment, Material


@dataclass
class GaussianParameter:
    mean: float
    std: float
    lower: float
    upper: float
    unit: str
    label: str

    def __post_init__(self) -> None:
        self.mean = float(np.clip(self.mean, self.lower, self.upper))
        self.std = float(max(self.std, 1e-9))

    def update(self, observation: float, observation_std: float, strength: float = 1.0) -> None:
        observation_std = max(float(observation_std), 1e-9)
        strength = float(np.clip(strength, 0.0, 1.0))
        if strength <= 0:
            return
        prior_precision = 1.0 / self.std**2
        observation_precision = strength / observation_std**2
        variance = 1.0 / (prior_precision + observation_precision)
        mean = variance * (prior_precision * self.mean + observation_precision * float(observation))
        self.mean = float(np.clip(mean, self.lower, self.upper))
        self.std = float(np.sqrt(variance))

    def inflate(self, factor: float, cap_fraction: float = 0.5) -> None:
        self.std = float(min(max((self.upper - self.lower) * cap_fraction, 1e-9), self.std * max(1.0, factor)))

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class NuisancePosterior:
    parameters: dict[str, GaussianParameter] = field(default_factory=dict)
    calibration_count: int = 0
    passive_update_count: int = 0

    @classmethod
    def from_material(cls, material: Material) -> "NuisancePosterior":
        return cls(
            {
                "wave_velocity": GaussianParameter(material.wave_velocity, 28.0, 80.0, 400.0, "m/s", "Propagation velocity"),
                "attenuation": GaussianParameter(material.attenuation, 0.48, 0.1, 6.0, "1/m", "Attenuation"),
                "timing_offset": GaussianParameter(material.system_delay_s, 0.00022, 0.0, 0.004, "s", "Timing offset"),
                "source_coupling": GaussianParameter(0.82, 0.18, 0.05, 1.5, "ratio", "Source coupling"),
                "receiver_coupling": GaussianParameter(0.82, 0.18, 0.05, 1.5, "ratio", "Receiver coupling"),
                "gain": GaussianParameter(1.0, 0.22, 0.1, 3.0, "ratio", "Acquisition gain"),
                "noise_scale": GaussianParameter(material.noise_std, max(material.noise_std * 0.65, 0.001), 0.0001, 0.2, "amplitude", "Noise scale"),
                "source_pose_error": GaussianParameter(0.0, 0.045, -0.25, 0.25, "normalized", "Source placement error"),
                "receiver_pose_error": GaussianParameter(0.0, 0.045, -0.25, 0.25, "normalized", "Receiver placement error"),
                "temperature_proxy": GaussianParameter(0.5, 0.18, 0.0, 1.0, "normalized", "Temperature proxy"),
            }
        )

    def parameter(self, name: str) -> GaussianParameter:
        return self.parameters[name]

    def normalized_uncertainties(self) -> dict[str, float]:
        reference = {
            "wave_velocity": 55.0, "attenuation": 1.2, "timing_offset": 0.00055,
            "source_coupling": 0.35, "receiver_coupling": 0.35, "gain": 0.55,
            "noise_scale": 0.020, "source_pose_error": 0.10,
            "receiver_pose_error": 0.10, "temperature_proxy": 0.30,
        }
        return {name: float(np.clip(parameter.std / reference[name], 0, 1)) for name, parameter in self.parameters.items()}

    def uncertainty_summary(self) -> dict:
        values = self.normalized_uncertainties()
        weights = {
            "wave_velocity": 0.18, "attenuation": 0.08, "timing_offset": 0.17,
            "source_coupling": 0.13, "receiver_coupling": 0.13, "gain": 0.06,
            "noise_scale": 0.12, "source_pose_error": 0.05,
            "receiver_pose_error": 0.05, "temperature_proxy": 0.03,
        }
        contributions = {name: weights[name] * value for name, value in values.items()}
        total = float(np.clip(sum(contributions.values()), 0, 1))
        dominant = max(contributions, key=contributions.get)
        return {
            "combined": total,
            "normalized_components": values,
            "weighted_contributions": contributions,
            "dominant_component": dominant,
            "dominant_share": float(contributions[dominant] / (sum(contributions.values()) + 1e-12)),
            "calibration_count": self.calibration_count,
            "passive_update_count": self.passive_update_count,
        }

    def predictive_variance(self, experiment: Experiment) -> dict[str, float]:
        velocity = self.parameter("wave_velocity")
        timing = self.parameter("timing_offset")
        coupling = np.hypot(self.parameter("source_coupling").std, self.parameter("receiver_coupling").std)
        pose = np.hypot(self.parameter("source_pose_error").std, self.parameter("receiver_pose_error").std)
        raw = {
            "timing_velocity": (timing.std / 0.00055) ** 2 + (velocity.std / max(velocity.mean, 1.0) / 0.30) ** 2,
            "coupling_gain": (coupling / 0.5) ** 2 + (self.parameter("gain").std / 0.6) ** 2,
            "noise": (self.parameter("noise_scale").std / 0.02) ** 2,
            "pose": (pose / 0.14) ** 2,
            "frequency_extrapolation": max(0.0, (experiment.center_frequency_hz - 6_500.0) / 2_000.0) ** 2,
        }
        total = sum(raw.values()) + 1e-12
        return {**{name: float(value / total) for name, value in raw.items()}, "magnitude": float(np.clip(total / 6.0, 0, 1))}

    def passive_quality_update(self, noise_estimate: float, coupling_quality: float, signal_quality: float) -> None:
        strength = 0.12 * float(np.clip(signal_quality, 0, 1))
        self.parameter("noise_scale").update(noise_estimate, max(noise_estimate * 0.8, 0.002), strength)
        self.parameter("source_coupling").update(coupling_quality, 0.30, strength)
        self.parameter("receiver_coupling").update(coupling_quality, 0.30, strength)
        self.passive_update_count += 1

    def to_dict(self) -> dict:
        return {
            "parameters": {name: value.to_dict() for name, value in self.parameters.items()},
            "calibration_count": self.calibration_count,
            "passive_update_count": self.passive_update_count,
        }

    @classmethod
    def from_dict(cls, payload: dict, fallback_material: Material | None = None) -> "NuisancePosterior":
        if not payload or "parameters" not in payload:
            return cls.from_material(fallback_material or Material())
        return cls(
            parameters={name: GaussianParameter(**value) for name, value in payload["parameters"].items()},
            calibration_count=int(payload.get("calibration_count", 0)),
            passive_update_count=int(payload.get("passive_update_count", 0)),
        )

