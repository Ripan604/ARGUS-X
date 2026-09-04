from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.ndimage import gaussian_filter, maximum_filter1d
from scipy.signal import correlate, correlation_lags

from backend.app.models.domain import Experiment
from backend.app.simulation.physics import AcousticSimulator

EPSILON = 1e-12


def normalize_probability_grid(probability: np.ndarray) -> np.ndarray:
    values = np.asarray(probability, dtype=np.float64)
    if values.ndim != 2 or values.size == 0 or not np.all(np.isfinite(values)):
        raise ValueError("Probability grid must be a finite, non-empty 2D array")
    values = np.maximum(values, 0.0)
    total = float(np.sum(values))
    if total <= EPSILON:
        return np.full_like(values, 1.0 / values.size)
    return values / total


def entropy(probability: np.ndarray, *, normalized: bool = False) -> float:
    values = normalize_probability_grid(probability).ravel()
    result = float(-np.sum(values * np.log2(values + EPSILON)))
    return result / np.log2(values.size) if normalized and values.size > 1 else result


def posterior_update(prior: np.ndarray, likelihood: np.ndarray) -> np.ndarray:
    if np.shape(prior) != np.shape(likelihood):
        raise ValueError("Prior and likelihood grids must have the same shape")
    return normalize_probability_grid(np.asarray(prior) * np.maximum(np.asarray(likelihood), EPSILON))


def spatial_mode_cells(
    probability: np.ndarray,
    count: int,
    minimum_separation_cells: int = 2,
) -> list[tuple[int, int]]:
    """Select probability-aware, spatially diverse representative cells.

    Plain argsort has a pathological tie behavior for a uniform prior: it can
    return a row of adjacent cells and make the first active experiment depend
    on array ordering. This farthest-weighted selection remains concentrated
    on real modes while distributing equal-probability representatives.
    """

    values = normalize_probability_grid(probability)
    rows, columns = np.indices(values.shape)
    chosen: list[tuple[int, int]] = []
    available = np.ones(values.shape, dtype=bool)
    target = max(1, min(int(count), values.size))
    separation = max(0, int(minimum_separation_cells))
    for _ in range(target):
        if not np.any(available):
            break
        if not chosen:
            maximum = float(np.max(values[available]))
            tied = np.argwhere(available & np.isclose(values, maximum, rtol=1e-12, atol=1e-15))
            center = np.asarray([(values.shape[0] - 1) / 2, (values.shape[1] - 1) / 2])
            row, column = tied[int(np.argmin(np.sum((tied - center) ** 2, axis=1)))]
        else:
            distances = np.full(values.shape, np.inf)
            for old_row, old_column in chosen:
                distances = np.minimum(distances, np.hypot(rows - old_row, columns - old_column))
            eligible = available & (distances >= separation)
            if not np.any(eligible):
                break
            normalized_distance = distances / max(np.hypot(*values.shape), 1.0)
            probability_ratio = values / max(float(np.max(values)), EPSILON)
            utility = probability_ratio * (0.35 + 0.65 * normalized_distance)
            utility[~eligible] = -np.inf
            row, column = np.unravel_index(int(np.argmax(utility)), values.shape)
        chosen.append((int(row), int(column)))
        if separation <= 0:
            available[row, column] = False
        else:
            available &= np.hypot(rows - row, columns - column) >= separation
    return chosen


def measurement_likelihood(
    samples: np.ndarray,
    experiment: Experiment,
    simulator: AcousticSimulator,
    grid_size: int,
    temperature: float = 4.8,
) -> tuple[np.ndarray, dict[str, float]]:
    measured = np.asarray(samples, dtype=np.float64)
    baseline = simulator.simulate_baseline(experiment)
    if len(measured) != len(baseline):
        common = min(len(measured), len(baseline))
        measured, baseline = measured[:common], baseline[:common]
    residual = measured - baseline
    excitation = simulator.excitation(experiment)[: len(residual)]
    correlation = np.abs(correlate(residual, excitation, mode="full", method="fft"))
    lags = correlation_lags(len(residual), len(excitation), mode="full")
    positive = lags >= 0
    positive_corr = correlation[positive]
    positive_lags = lags[positive]
    positive_corr = maximum_filter1d(positive_corr, size=7, mode="nearest")

    axis = (np.arange(grid_size) + 0.5) / grid_size
    x, y = np.meshgrid(axis, axis)
    signature = simulator.predicted_signature(x.ravel(), y.ravel(), experiment)
    predicted_lags = np.rint(signature[:, 0] * simulator.sample_rate).astype(int)
    lag_indices = np.searchsorted(positive_lags, predicted_lags).clip(0, len(positive_corr) - 1)
    raw_score = positive_corr[lag_indices].reshape(grid_size, grid_size)
    smooth_score = gaussian_filter(raw_score, sigma=0.55)
    low, high = np.percentile(smooth_score, [8, 98])
    scaled = np.clip((smooth_score - low) / (high - low + EPSILON), 0, 1)
    residual_rms = float(np.sqrt(np.mean(residual**2)))
    noise_floor = float(np.median(np.abs(residual - np.median(residual))) * 1.4826 + EPSILON)
    snr = residual_rms / noise_floor
    effective_temperature = temperature * float(np.clip((snr - 0.75) / 1.8, 0.30, 1.0))
    likelihood = np.exp(effective_temperature * scaled)
    likelihood = normalize_probability_grid(likelihood) * likelihood.size
    diagnostics = {
        "residual_rms": residual_rms,
        "noise_floor": noise_floor,
        "residual_snr_db": float(20 * np.log10(snr + EPSILON)),
        "likelihood_temperature": effective_temperature,
        "peak_delay_s": float(positive_lags[int(np.argmax(positive_corr))] / simulator.sample_rate),
    }
    return likelihood, diagnostics


@dataclass
class BeliefState:
    grid_size: int = 20
    posterior: np.ndarray | None = None
    history: list[np.ndarray] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.grid_size < 4:
            raise ValueError("grid_size must be at least 4")
        if self.posterior is None:
            self.posterior = np.full((self.grid_size, self.grid_size), 1.0 / self.grid_size**2)
        else:
            self.posterior = normalize_probability_grid(self.posterior)
        if not self.history:
            self.history.append(self.posterior.copy())

    def update(
        self,
        samples: np.ndarray,
        experiment: Experiment,
        simulator: AcousticSimulator,
        temperature: float = 4.8,
        evidence_weight: float = 1.0,
    ) -> tuple[np.ndarray, dict[str, float]]:
        likelihood, diagnostics = measurement_likelihood(
            samples, experiment, simulator, self.grid_size, temperature=temperature
        )
        weight = float(np.clip(evidence_weight, 0.0, 1.0))
        tempered_likelihood = np.power(np.maximum(likelihood, EPSILON), weight)
        self.posterior = posterior_update(self.posterior, tempered_likelihood)
        self.history.append(self.posterior.copy())
        diagnostics["evidence_weight"] = weight
        return likelihood, diagnostics

    def estimate(self) -> dict[str, float | list[list[float]]]:
        axis = (np.arange(self.grid_size) + 0.5) / self.grid_size
        x, y = np.meshgrid(axis, axis)
        map_y, map_x = np.unravel_index(np.argmax(self.posterior), self.posterior.shape)
        mean_x = float(np.sum(x * self.posterior))
        mean_y = float(np.sum(y * self.posterior))
        dx, dy = x - mean_x, y - mean_y
        covariance = np.array(
            [
                [np.sum(self.posterior * dx * dx), np.sum(self.posterior * dx * dy)],
                [np.sum(self.posterior * dx * dy), np.sum(self.posterior * dy * dy)],
            ]
        )
        radius = max(1, self.grid_size // 16)
        y0, y1 = max(0, map_y - radius), min(self.grid_size, map_y + radius + 1)
        x0, x1 = max(0, map_x - radius), min(self.grid_size, map_x + radius + 1)
        local_mass = float(np.sum(self.posterior[y0:y1, x0:x1]))
        normalized_entropy = entropy(self.posterior, normalized=True)
        confidence = float(np.clip(0.55 * local_mass + 0.45 * (1 - normalized_entropy), 0, 1))
        return {
            "map_x": float(axis[map_x]),
            "map_y": float(axis[map_y]),
            "mean_x": mean_x,
            "mean_y": mean_y,
            "peak_probability": float(self.posterior[map_y, map_x]),
            "local_probability_mass": local_mass,
            "confidence": confidence,
            "entropy_bits": entropy(self.posterior),
            "normalized_entropy": normalized_entropy,
            "covariance": covariance.tolist(),
        }

    def to_list(self) -> list[list[float]]:
        return self.posterior.round(10).tolist()
