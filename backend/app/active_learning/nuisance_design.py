"""Arrival-time experimental design with explicit nuisance marginalization.

The design target is a coarsening of the complete spatial posterior. Gaussian
moment matching and a first-order velocity/pose model make this an approximate
design model, not a calibrated likelihood or a confidence certificate.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from scipy.special import logsumexp

from backend.app.inference.belief import normalize_probability_grid
from backend.app.inference.nuisance_posterior import NuisancePosterior
from backend.app.models.domain import Experiment, Panel


@lru_cache(maxsize=8)
def _quadrature(order: int) -> tuple[np.ndarray, np.ndarray]:
    nodes, weights = np.polynomial.hermite.hermgauss(order)
    return np.sqrt(2.0) * nodes, weights / np.sqrt(np.pi)


def gaussian_mixture_information(
    probabilities: np.ndarray, means: np.ndarray, variances: np.ndarray, *, order: int = 48,
) -> tuple[float, float]:
    """Return raw I(component; scalar observation), and component entropy, in bits.

    Integrates E[log p(y|component) - log p(y)] under each Gaussian using
    deterministic quadrature. Does not silently clamp a numerical violation.
    """
    p, mu, var = (np.asarray(value, dtype=np.float64) for value in (probabilities, means, variances))
    if p.ndim != 1 or p.size == 0 or mu.shape != p.shape or var.shape != p.shape:
        raise ValueError("Mixture parameters must be non-empty vectors of equal shape")
    if not all(np.all(np.isfinite(value)) for value in (p, mu, var)) or np.any(p < 0) or np.any(var <= 0) or p.sum() <= 0:
        raise ValueError("Mixture weights and moments must be finite with positive variance and mass")
    if order < 8 or order > 256:
        raise ValueError("Quadrature order must be between 8 and 256")
    active = p > 0
    p, mu, var = p[active] / p.sum(), mu[active], var[active]
    entropy_bits = float(-np.sum(p * np.log2(p)))
    if p.size == 1:
        return 0.0, entropy_bits
    # Center and scale all observations together: no unit-specific epsilon is
    # added to variances, and seconds/milliseconds yield identical information.
    origin = float(np.sum(p * mu))
    scale = float(np.sqrt(np.sum(p * (var + (mu - origin) ** 2))))
    mu, var = (mu - origin) / scale, var / scale**2
    nodes, quadrature_weights = _quadrature(order)
    observations = mu[:, None] + np.sqrt(var[:, None]) * nodes[None, :]
    log_density = -0.5 * (
        np.log(2 * np.pi * var)[None, None, :]
        + (observations[:, :, None] - mu[None, None, :]) ** 2 / var[None, None, :]
    )
    log_mixture = logsumexp(log_density + np.log(p)[None, None, :], axis=2)
    log_own = -0.5 * (np.log(2 * np.pi * var)[:, None] + nodes[None, :] ** 2)
    information = float(np.sum(p[:, None] * quadrature_weights[None, :] * (log_own - log_mixture)) / np.log(2.0))
    return information, entropy_bits


@dataclass(frozen=True)
class SpatialDesignRegions:
    coordinates_m: np.ndarray
    cell_probabilities: np.ndarray
    membership: np.ndarray
    probabilities: np.ndarray
    centers_m: np.ndarray

    @classmethod
    def from_posterior(cls, posterior: np.ndarray, hypotheses: list[dict], panel: Panel) -> "SpatialDesignRegions":
        if not hypotheses:
            raise ValueError("At least one spatial representative is required")
        grid = normalize_probability_grid(posterior)
        rows, columns = np.indices(grid.shape)
        coordinates = np.column_stack((
            (columns.ravel() + 0.5) * panel.width_m / grid.shape[1],
            (rows.ravel() + 0.5) * panel.height_m / grid.shape[0],
        ))
        centers = np.asarray([(h["x"] * panel.width_m, h["y"] * panel.height_m) for h in hypotheses])
        membership = np.argmin(np.sum((coordinates[:, None, :] - centers[None, :, :]) ** 2, axis=2), axis=1)
        p = grid.ravel()
        masses = np.bincount(membership, weights=p, minlength=len(centers))
        active = np.flatnonzero(masses > 0)
        remap = np.zeros(len(centers), dtype=int)
        remap[active] = np.arange(len(active))
        return cls(coordinates, p, remap[membership], masses[active], centers[active])


@dataclass(frozen=True)
class NuisanceDesignAnalysis:
    information_bits: float
    hypothesis_entropy_bits: float
    separation: float
    worst_case_separation: float
    diagnostics: dict


class NuisanceArrivalTimeDesign:
    """A scalar observation model aligned with ARGUS's delay-based update."""

    def __init__(self, panel: Panel, sample_rate: int) -> None:
        self.panel = panel
        # Existing forward-model floor plus the seven-sample matched-filter
        # neighborhood used by measurement_likelihood. This is an assumption,
        # not a learned sensor-noise estimate or a Cramer-Rao bound.
        self.measurement_variance = 1.5e-8 + (3.0 / sample_rate) ** 2 / 3.0

    def analyze(self, experiment: Experiment, regions: SpatialDesignRegions, nuisance: NuisancePosterior) -> NuisanceDesignAnalysis:
        dimensions = np.asarray([self.panel.width_m, self.panel.height_m])
        source = np.asarray([experiment.source_x, experiment.source_y]) * dimensions
        receiver = np.asarray([experiment.receiver_x, experiment.receiver_y]) * dimensions
        source_delta = regions.coordinates_m - source
        receiver_delta = regions.coordinates_m - receiver
        ds, dr = np.linalg.norm(source_delta, axis=1), np.linalg.norm(receiver_delta, axis=1)
        path = ds + dr
        velocity, timing = nuisance.parameter("wave_velocity"), nuisance.parameter("timing_offset")
        n = len(regions.probabilities)

        def average(values: np.ndarray) -> np.ndarray:
            return np.bincount(regions.membership, weights=regions.cell_probabilities * values, minlength=n) / regions.probabilities

        path_mean = average(path)
        path_variance = average((path - path_mean[regions.membership]) ** 2)
        means = timing.mean + path_mean / velocity.mean
        structural_variance = path_variance / velocity.mean**2
        # Each scalar pose uncertainty is interpreted as isotropic independent
        # error per normalized coordinate. A nonzero scalar mean has no known
        # direction, so its square is conservatively included in the second moment.
        def pose_variance(delta: np.ndarray, distance: np.ndarray, name: str) -> np.ndarray:
            parameter = nuisance.parameter(name)
            unit = np.divide(delta, distance[:, None], out=np.zeros_like(delta), where=distance[:, None] > 1e-12)
            sensitivity = np.sum((unit * dimensions) ** 2, axis=1)
            # The range derivative is undefined at a coincident probe. Use the
            # squared panel diagonal there instead of falsely assigning zero noise.
            sensitivity[distance <= 1e-12] = float(np.sum(dimensions**2))
            return sensitivity * (parameter.std**2 + parameter.mean**2) / velocity.mean**2

        components = {
            "timing": np.full(n, timing.std**2),
            "velocity": average(path**2) * velocity.std**2 / velocity.mean**4,
            "velocity_timing_cross": -2 * path_mean * nuisance.propagation_covariance()[0, 1] / velocity.mean**2,
            "pose": average(pose_variance(source_delta, ds, "source_pose_error") + pose_variance(receiver_delta, dr, "receiver_pose_error")),
        }
        nominal_variances = structural_variance + self.measurement_variance
        variances = nominal_variances + sum(components.values())
        low, _ = gaussian_mixture_information(regions.probabilities, means, variances, order=24)
        raw, entropy_bits = gaussian_mixture_information(regions.probabilities, means, variances, order=48)
        discrepancy = abs(raw - low)
        order = 48
        if discrepancy > 0.002:
            refined, _ = gaussian_mixture_information(regions.probabilities, means, variances, order=96)
            discrepancy, raw, order = abs(refined - raw), refined, 96
        information = float(np.clip(raw, 0.0, entropy_bits))
        nominal_raw, _ = gaussian_mixture_information(regions.probabilities, means, nominal_variances, order=96)
        nominal_information = float(np.clip(nominal_raw, 0.0, entropy_bits))
        separations, pair_weights = [], []
        for left in range(n):
            for right in range(left + 1, n):
                pooled = 0.5 * (variances[left] + variances[right])
                # Mean-only Hellinger separation under a common pooled Gaussian;
                # covariance differences are not counted as a separation bonus.
                separations.append(float(-np.expm1(-(means[left] - means[right]) ** 2 / (8.0 * pooled))))
                pair_weights.append(float(regions.probabilities[left] * regions.probabilities[right]))
        separation = float(np.average(separations, weights=pair_weights)) if pair_weights else 0.0
        penalty = max(0.0, nominal_information - information)
        diagnostics = {
            "enabled": True,
            "method": "nuisance_marginal_arrival_time_information_v1",
            "observation": "matched_filter_arrival_time",
            "information_bits": information,
            "raw_information_bits": raw,
            "hypothesis_entropy_bits": entropy_bits,
            "normalized_information": information / entropy_bits if entropy_bits > 1e-12 else 0.0,
            "nominal_information_bits": nominal_information,
            "nuisance_penalty_bits": penalty,
            "nuisance_information_change_bits": information - nominal_information,
            "quadrature_error_bits": discrepancy,
            "quadrature_order": order,
            "quadrature_converged": bool(discrepancy <= 0.002),
            "numerical_clamp_bits": abs(raw - information),
            "region_count": n,
            "posterior_mass": float(regions.probabilities.sum()),
            "region_probabilities": regions.probabilities.tolist(),
            "region_centers_m": regions.centers_m.tolist(),
            "arrival_means_s": means.tolist(),
            "arrival_std_s": np.sqrt(variances).tolist(),
            "variance_budget_s2": {
                "within_region": float(regions.probabilities @ structural_variance),
                "measurement_floor": self.measurement_variance,
                **{key: float(regions.probabilities @ value) for key, value in components.items()},
            },
            "approximation": "spatial_region_gaussian_moment_matching_and_correlated_first_order_velocity_timing_pose",
            "velocity_relative_std": velocity.std / velocity.mean,
            "field_calibrated": False,
        }
        return NuisanceDesignAnalysis(information, entropy_bits, separation, min(separations, default=0.0), diagnostics)
