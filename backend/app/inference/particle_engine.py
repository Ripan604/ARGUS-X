from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from backend.app.inference.nuisance_posterior import NuisancePosterior
from backend.app.inference.structural_posterior import StructuralPosterior


@dataclass(frozen=True)
class JointParticleBatch:
    structural_xy: np.ndarray
    nuisance: dict[str, np.ndarray]
    weights: np.ndarray


class ParticleInferenceEngine:
    """Seeded posterior samples for practical posterior-predictive planning."""

    def __init__(self, seed: int = 71) -> None:
        self.rng = np.random.default_rng(seed)

    def sample(self, structural: StructuralPosterior, nuisance: NuisancePosterior, count: int = 32) -> JointParticleBatch:
        count = max(4, int(count))
        flat = structural.posterior.ravel()
        indices = self.rng.choice(flat.size, size=count, p=flat)
        jitter = self.rng.uniform(-0.45, 0.45, size=(count, 2)) / structural.grid_size
        xy = np.column_stack(((indices % structural.grid_size + 0.5) / structural.grid_size, (indices // structural.grid_size + 0.5) / structural.grid_size))
        nuisance_samples = {
            name: np.clip(self.rng.normal(parameter.mean, parameter.std, count), parameter.lower, parameter.upper)
            for name, parameter in nuisance.parameters.items()
        }
        return JointParticleBatch(np.clip(xy + jitter, 0, 1), nuisance_samples, np.full(count, 1.0 / count))

