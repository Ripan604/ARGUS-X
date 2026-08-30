from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import numpy as np

from backend.app.models.domain import Experiment
from backend.app.simulation.physics import AcousticSimulator


class StructuralInference(ABC):
    """Interchangeable structural-posterior contract."""

    @abstractmethod
    def update(
        self,
        samples: np.ndarray,
        experiment: Experiment,
        simulator: AcousticSimulator,
        temperature: float,
        evidence_weight: float = 1.0,
    ) -> tuple[np.ndarray, dict[str, float]]: ...

    @abstractmethod
    def estimate(self) -> dict[str, Any]: ...

    @abstractmethod
    def to_list(self) -> list[list[float]]: ...


class SerializableInferenceState(ABC):
    @abstractmethod
    def to_dict(self) -> dict: ...

