from __future__ import annotations

import numpy as np

from backend.app.inference.belief import BeliefState, normalize_probability_grid, spatial_mode_cells


class StructuralPosterior(BeliefState):
    """Spatial structural belief plus lightweight size/type/severity moments."""

    def __init__(
        self,
        grid_size: int = 20,
        posterior: np.ndarray | None = None,
        *,
        radius_mean: float = 0.085,
        radius_std: float = 0.035,
        severity_mean: float = 0.65,
        severity_std: float = 0.20,
        type_probabilities: dict[str, float] | None = None,
    ) -> None:
        super().__init__(grid_size, posterior)
        self.radius_mean = float(radius_mean)
        self.radius_std = float(max(radius_std, 1e-4))
        self.severity_mean = float(severity_mean)
        self.severity_std = float(max(severity_std, 1e-4))
        self.type_probabilities = type_probabilities or {
            "cavity": 0.25,
            "loose_region": 0.25,
            "delamination": 0.25,
            "dense_inclusion": 0.25,
        }
        self._normalize_types()

    def _normalize_types(self) -> None:
        total = sum(max(0.0, float(value)) for value in self.type_probabilities.values())
        if total <= 1e-12:
            count = max(1, len(self.type_probabilities))
            self.type_probabilities = {key: 1.0 / count for key in self.type_probabilities}
        else:
            self.type_probabilities = {key: max(0.0, float(value)) / total for key, value in self.type_probabilities.items()}

    def top_hypotheses(self, count: int = 5, minimum_separation_cells: int = 2) -> list[dict]:
        values = normalize_probability_grid(self.posterior)
        result: list[dict] = []
        for row, column in spatial_mode_cells(values, count, minimum_separation_cells):
            result.append(
                {
                    "rank": len(result) + 1,
                    "x": float((column + 0.5) / self.grid_size),
                    "y": float((row + 0.5) / self.grid_size),
                    "probability": float(values[row, column]),
                    "radius_mean": self.radius_mean,
                    "severity_mean": self.severity_mean,
                    "dominant_type": max(self.type_probabilities, key=self.type_probabilities.get),
                }
            )
        return result

    def credible_region(self, mass: float = 0.90) -> dict:
        if not 0 < mass < 1:
            raise ValueError("credible-region mass must be in (0, 1)")
        values = normalize_probability_grid(self.posterior)
        order = np.argsort(values.ravel())[::-1]
        count = int(np.searchsorted(np.cumsum(values.ravel()[order]), mass) + 1)
        mask = np.zeros(values.size, dtype=bool)
        mask[order[:count]] = True
        rows, columns = np.nonzero(mask.reshape(values.shape))
        return {
            "mass": mass,
            "cell_count": count,
            "area_fraction": float(count / values.size),
            "x_min": float(columns.min() / self.grid_size),
            "x_max": float((columns.max() + 1) / self.grid_size),
            "y_min": float(rows.min() / self.grid_size),
            "y_max": float((rows.max() + 1) / self.grid_size),
        }

    def ambiguity(self) -> float:
        modes = self.top_hypotheses(2)
        if len(modes) < 2:
            return 0.0
        return float(np.clip(modes[1]["probability"] / (modes[0]["probability"] + 1e-12), 0, 1))

    def uncertainty_summary(self) -> dict:
        estimate = self.estimate()
        credible = self.credible_region(0.90)
        combined = float(
            np.clip(
                0.50 * estimate["normalized_entropy"]
                + 0.25 * credible["area_fraction"]
                + 0.20 * self.ambiguity()
                + 0.05 * min(1.0, self.severity_std / 0.35),
                0,
                1,
            )
        )
        return {
            "normalized_entropy": estimate["normalized_entropy"],
            "credible_region_90_area_fraction": credible["area_fraction"],
            "competing_hypothesis_ambiguity": self.ambiguity(),
            "severity_relative_std": float(np.clip(self.severity_std / max(self.severity_mean, 0.05), 0, 1)),
            "combined": combined,
        }

    def to_state(self) -> dict:
        return {
            "grid_size": self.grid_size,
            "posterior": self.to_list(),
            "radius_mean": self.radius_mean,
            "radius_std": self.radius_std,
            "severity_mean": self.severity_mean,
            "severity_std": self.severity_std,
            "type_probabilities": self.type_probabilities,
        }

    @classmethod
    def from_state(cls, payload: dict) -> "StructuralPosterior":
        return cls(
            grid_size=int(payload.get("grid_size", len(payload["posterior"]))),
            posterior=np.asarray(payload["posterior"], dtype=np.float64),
            radius_mean=float(payload.get("radius_mean", 0.085)),
            radius_std=float(payload.get("radius_std", 0.035)),
            severity_mean=float(payload.get("severity_mean", 0.65)),
            severity_std=float(payload.get("severity_std", 0.20)),
            type_probabilities=payload.get("type_probabilities"),
        )


def structural_entropy_bounds(grid_size: int) -> tuple[float, float]:
    return 0.0, float(np.log2(grid_size * grid_size))
