from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from sklearn.linear_model import Ridge


@dataclass
class OnlineDiscrepancyModel:
    maximum_samples: int = 256
    ridge_alpha: float = 0.8
    inputs: list[list[float]] = field(default_factory=list)
    residuals: list[list[float]] = field(default_factory=list)
    recent_norms: list[float] = field(default_factory=list)

    def features(self, frequency_hz: float, path_length_m: float, geometry: tuple[float, float, float, float]) -> np.ndarray:
        return np.asarray([
            frequency_hz / 7_000.0,
            path_length_m,
            geometry[0], geometry[1], geometry[2], geometry[3],
            abs(geometry[0] - geometry[2]), abs(geometry[1] - geometry[3]),
        ], dtype=np.float64)

    def predict(self, features: np.ndarray, output_size: int = 4) -> tuple[np.ndarray, float]:
        if len(self.inputs) < 5:
            uncertainty = 0.24 + 0.03 * (5 - len(self.inputs))
            return np.zeros(output_size), uncertainty
        x = np.asarray(self.inputs, dtype=np.float64)
        y = np.asarray(self.residuals, dtype=np.float64)
        model = Ridge(alpha=self.ridge_alpha).fit(x, y)
        prediction = np.asarray(model.predict(np.asarray(features).reshape(1, -1))[0])
        fitted = model.predict(x)
        uncertainty = float(np.sqrt(np.mean((fitted - y) ** 2)))
        return prediction, uncertainty

    def update(self, features: np.ndarray, residual: np.ndarray) -> dict:
        values = np.asarray(residual, dtype=np.float64).reshape(-1)
        self.inputs.append(np.asarray(features, dtype=np.float64).tolist())
        self.residuals.append(values.tolist())
        norm = float(np.linalg.norm(values / np.asarray([0.0008, 1.2, 1.0, 1.0])[: len(values)]))
        self.recent_norms.append(norm)
        self.inputs = self.inputs[-self.maximum_samples :]
        self.residuals = self.residuals[-self.maximum_samples :]
        self.recent_norms = self.recent_norms[-64:]
        rms = float(np.sqrt(np.mean(np.square(self.recent_norms[-12:]))))
        trust = float(np.clip(np.exp(-0.42 * rms), 0.02, 1.0))
        return {"sample_count": len(self.inputs), "recent_residual_rms": rms, "uncertainty": min(1.0, rms / 3.0), "model_trust": trust}

    def to_dict(self) -> dict:
        return {
            "maximum_samples": self.maximum_samples,
            "ridge_alpha": self.ridge_alpha,
            "inputs": self.inputs,
            "residuals": self.residuals,
            "recent_norms": self.recent_norms,
        }

    @classmethod
    def from_dict(cls, payload: dict | None) -> "OnlineDiscrepancyModel":
        if not payload:
            return cls()
        allowed = {key: payload[key] for key in ("maximum_samples", "ridge_alpha", "inputs", "residuals", "recent_norms") if key in payload}
        return cls(**allowed)

