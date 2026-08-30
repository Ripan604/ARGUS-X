from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass

import numpy as np

from backend.app.digital_twin.cache import PredictionCache, deterministic_key
from backend.app.inference.nuisance_posterior import NuisancePosterior
from backend.app.models.domain import Experiment, physical_distance
from backend.app.simulation.physics import AcousticSimulator


@dataclass(frozen=True)
class ForwardCapability:
    model_id: str
    fidelity_level: int
    computational_cost: float
    predicted_fidelity: float
    supported_frequency_hz: tuple[float, float]
    supported_materials: tuple[str, ...]
    uncertainty_estimate: float


@dataclass(frozen=True)
class ForwardPrediction:
    mean: np.ndarray
    covariance: np.ndarray
    model_id: str
    fidelity_level: int
    model_uncertainty: float

    def to_dict(self) -> dict:
        return {
            "mean": self.mean.tolist(),
            "covariance": self.covariance.tolist(),
            "model_id": self.model_id,
            "fidelity_level": self.fidelity_level,
            "model_uncertainty": self.model_uncertainty,
        }


class ForwardModel(ABC):
    capability: ForwardCapability

    @abstractmethod
    def predict(self, experiment: Experiment, latent_state: dict, nuisance: NuisancePosterior) -> ForwardPrediction: ...


class AnalyticalForwardModel(ForwardModel):
    def __init__(self, simulator: AcousticSimulator, cache_size: int = 8_192) -> None:
        self.simulator = simulator
        self.capability = ForwardCapability(
            "analytical_geometry_v1", 0, 0.05, 0.52, (100.0, 8_000.0),
            ("generic_plate", "aluminum_demo", "CFRP_demo", "composite"), 0.28,
        )
        self.cache: PredictionCache[ForwardPrediction] = PredictionCache(cache_size)

    def predict(self, experiment: Experiment, latent_state: dict, nuisance: NuisancePosterior) -> ForwardPrediction:
        x, y = float(latent_state["x"]), float(latent_state["y"])
        relevant_nuisance = {
            name: (round(parameter.mean, 8), round(parameter.std, 8))
            for name, parameter in nuisance.parameters.items()
            if name in {"wave_velocity", "attenuation", "timing_offset", "source_coupling", "receiver_coupling", "gain", "noise_scale", "source_pose_error", "receiver_pose_error"}
        }
        key = deterministic_key(self.capability.model_id, latent_state, experiment.to_dict(), relevant_nuisance)
        return self.cache.get_or_compute(key, lambda: self._predict_uncached(experiment, x, y, nuisance))

    def _predict_uncached(self, experiment: Experiment, x: float, y: float, nuisance: NuisancePosterior) -> ForwardPrediction:
        velocity = nuisance.parameter("wave_velocity")
        attenuation = nuisance.parameter("attenuation")
        timing = nuisance.parameter("timing_offset")
        source_distance = float(physical_distance(experiment.source_x, experiment.source_y, x, y, self.simulator.panel))
        receiver_distance = float(physical_distance(x, y, experiment.receiver_x, experiment.receiver_y, self.simulator.panel))
        path = source_distance + receiver_distance
        delay = timing.mean + path / max(velocity.mean, 1.0)
        coupling = nuisance.parameter("source_coupling").mean * nuisance.parameter("receiver_coupling").mean
        gain = 0.65 * coupling * nuisance.parameter("gain").mean * np.exp(-attenuation.mean * path) / (1 + 5 * path)
        phase = 2 * np.pi * experiment.center_frequency_hz * delay
        mean = np.asarray([delay, np.log(max(gain, 1e-8)), np.sin(phase), np.cos(phase)], dtype=np.float64)
        delay_std = np.sqrt(timing.std**2 + (path * velocity.std / max(velocity.mean**2, 1.0)) ** 2 + 1.5e-8)
        log_gain_std = np.sqrt(
            attenuation.std**2 * path**2
            + (nuisance.parameter("source_coupling").std / max(nuisance.parameter("source_coupling").mean, 0.05)) ** 2
            + (nuisance.parameter("receiver_coupling").std / max(nuisance.parameter("receiver_coupling").mean, 0.05)) ** 2
            + 0.05
        )
        phase_std = min(np.pi, 2 * np.pi * experiment.center_frequency_hz * delay_std)
        covariance = np.diag([delay_std**2, log_gain_std**2, phase_std**2, phase_std**2])
        return ForwardPrediction(mean, covariance, self.capability.model_id, 0, self.capability.uncertainty_estimate)


class PhysicsSignatureModel(AnalyticalForwardModel):
    def __init__(self, simulator: AcousticSimulator, cache_size: int = 8_192) -> None:
        super().__init__(simulator, cache_size)
        self.capability = ForwardCapability(
            "physics_signature_v1", 1, 0.28, 0.76, (100.0, 7_000.0),
            ("generic_plate", "aluminum_demo", "CFRP_demo", "composite"), 0.16,
        )

    def _predict_uncached(self, experiment: Experiment, x: float, y: float, nuisance: NuisancePosterior) -> ForwardPrediction:
        prediction = super()._predict_uncached(experiment, x, y, nuisance)
        nominal = self.simulator.predicted_signature(np.asarray([x]), np.asarray([y]), experiment)[0]
        # Blend the interpretable nominal simulator with nuisance-conditioned geometry.
        mean = 0.35 * nominal + 0.65 * prediction.mean
        covariance = prediction.covariance + np.diag([2e-8, 0.04, 0.03, 0.03])
        return ForwardPrediction(mean, covariance, self.capability.model_id, 1, self.capability.uncertainty_estimate)
