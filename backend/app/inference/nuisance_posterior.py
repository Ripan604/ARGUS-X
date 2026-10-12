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
        if not np.isfinite([self.mean, self.std, self.lower, self.upper]).all() or self.lower >= self.upper or self.std <= 0:
            raise ValueError("Gaussian parameter requires finite ordered bounds and positive uncertainty")
        self.mean = float(np.clip(self.mean, self.lower, self.upper))
        self.std = float(max(self.std, 1e-9))

    def update(self, observation: float, observation_std: float, strength: float = 1.0) -> None:
        if not np.isfinite([observation, observation_std, strength]).all() or observation_std <= 0:
            raise ValueError("Parameter observations must be finite with positive uncertainty")
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
    velocity_timing_correlation: float = 0.0
    direct_path_lengths_m: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not np.isfinite(self.velocity_timing_correlation) or abs(self.velocity_timing_correlation) >= 1:
            raise ValueError("Velocity/timing correlation must be finite and strictly inside (-1, 1)")
        if any(not np.isfinite(d) or d <= 0 for d in self.direct_path_lengths_m):
            raise ValueError("Calibration path lengths must be finite and positive")

    def propagation_covariance(self) -> np.ndarray:
        """Joint covariance in (m/s, s); a single delay is a rank-one observation."""
        v, t = self.parameter("wave_velocity"), self.parameter("timing_offset")
        cross = self.velocity_timing_correlation * v.std * t.std
        return np.asarray([[v.std**2, cross], [cross, t.std**2]])

    def arrival_variance(self, path_m: np.ndarray | float) -> np.ndarray:
        derivative = -np.asarray(path_m) / self.parameter("wave_velocity").mean**2
        covariance = self.propagation_covariance()
        return np.maximum(0.0, derivative**2 * covariance[0, 0] + 2 * derivative * covariance[0, 1] + covariance[1, 1])

    def conditioned_propagation(self, distance_m: float, observation_std_s: float, strength: float = 1.0) -> tuple[np.ndarray, np.ndarray]:
        if not np.isfinite([distance_m, observation_std_s, strength]).all() or distance_m <= 0 or observation_std_s <= 0 or not 0 < strength <= 1:
            raise ValueError("Direct-path conditioning requires positive finite distance/noise and strength in (0, 1]")
        covariance = self.propagation_covariance()
        h = np.asarray([-distance_m / self.parameter("wave_velocity").mean**2, 1.0])
        noise = observation_std_s**2 / strength
        gain = covariance @ h / (float(h @ covariance @ h) + noise)
        # Joseph form preserves positive semidefiniteness in mixed physical units.
        residual = np.eye(2) - np.outer(gain, h)
        updated = residual @ covariance @ residual.T + noise * np.outer(gain, gain)
        return gain, (updated + updated.T) / 2

    def set_propagation_covariance(self, covariance: np.ndarray) -> None:
        covariance = np.asarray(covariance, dtype=float)
        if covariance.shape != (2, 2) or not np.isfinite(covariance).all() or not np.allclose(covariance, covariance.T, rtol=1e-10, atol=1e-18):
            raise ValueError("Propagation covariance must be finite and symmetric")
        if np.any(np.diag(covariance) <= 0):
            raise ValueError("Propagation covariance must be positive definite")
        std = np.sqrt(np.diag(covariance))
        correlation = covariance[0, 1] / np.prod(std)
        if not np.isfinite(std).all() or np.any(std <= 0) or abs(correlation) >= 1:
            raise ValueError("Propagation covariance must be positive definite")
        self.parameter("wave_velocity").std = float(std[0])
        self.parameter("timing_offset").std = float(std[1])
        self.velocity_timing_correlation = float(correlation)

    def update_direct_path(self, distance_m: float, delay_s: float, observation_std_s: float, strength: float) -> dict:
        """First-order joint Gaussian update; never count one delay as two observations."""
        if not np.isfinite(delay_s) or delay_s <= 0:
            raise ValueError("Observed direct-path delay must be finite and positive")
        velocity, timing = self.parameter("wave_velocity"), self.parameter("timing_offset")
        predicted = timing.mean + distance_m / velocity.mean
        gain, covariance = self.conditioned_propagation(distance_m, observation_std_s, strength)
        means = np.asarray([velocity.mean, timing.mean]) + gain * (delay_s - predicted)
        if not (velocity.lower <= means[0] <= velocity.upper and timing.lower <= means[1] <= timing.upper):
            raise ValueError("Direct-path observation is outside propagation-model support")
        # Validate covariance before changing means, so a failed numerical
        # conditioning step leaves the entire propagation block unchanged.
        self.set_propagation_covariance(covariance)
        velocity.mean, timing.mean = map(float, means)
        self.direct_path_lengths_m = [*self.direct_path_lengths_m, float(distance_m)][-256:]
        return {"observed_delay_s": float(delay_s), "predicted_delay_before_s": predicted,
                "innovation_s": float(delay_s - predicted), "observation_std_s": observation_std_s,
                "velocity_timing_correlation": self.velocity_timing_correlation,
                "path_length_span_m": float(np.ptp(self.direct_path_lengths_m)),
                "estimated_wave_velocity_m_s": velocity.mean, "estimated_timing_offset_s": timing.mean}

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
            "velocity_timing_correlation": self.velocity_timing_correlation,
            "direct_path_lengths_m": self.direct_path_lengths_m,
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
        # Quality gates evidence; it cannot separately identify TX/RX coupling.
        self.passive_update_count += 1

    def to_dict(self) -> dict:
        return {
            "parameters": {name: value.to_dict() for name, value in self.parameters.items()},
            "calibration_count": self.calibration_count,
            "passive_update_count": self.passive_update_count,
            "velocity_timing_correlation": self.velocity_timing_correlation,
            "direct_path_lengths_m": list(self.direct_path_lengths_m),
        }

    @classmethod
    def from_dict(cls, payload: dict, fallback_material: Material | None = None) -> "NuisancePosterior":
        if not payload or "parameters" not in payload:
            return cls.from_material(fallback_material or Material())
        return cls(
            parameters={name: GaussianParameter(**value) for name, value in payload["parameters"].items()},
            calibration_count=int(payload.get("calibration_count", 0)),
            passive_update_count=int(payload.get("passive_update_count", 0)),
            velocity_timing_correlation=float(payload.get("velocity_timing_correlation", 0.0)),
            direct_path_lengths_m=list(payload.get("direct_path_lengths_m", [])),
        )
