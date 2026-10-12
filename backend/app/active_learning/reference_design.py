"""Task-conditioned direct-reference selection under the propagation model.

This uses established Gaussian experimental-design mathematics. It reduces a
declared propagation variance, not certified location error or physical risk.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np

from backend.app.inference.belief import normalize_probability_grid
from backend.app.models.domain import Experiment, Panel, physical_distance


@dataclass(frozen=True)
class ReferenceSelection:
    experiment: Experiment
    diagnostics: dict


def reference_observation_std(nuisance, panel: Panel, sample_rate: int) -> float:
    velocity = nuisance.parameter("wave_velocity").mean
    pose = max(panel.width_m, panel.height_m) * np.hypot(
        nuisance.parameter("source_pose_error").std, nuisance.parameter("receiver_pose_error").std)
    return float(np.hypot(max(1 / sample_rate, 0.00020), pose / velocity))


def select_task_reference(posterior, nuisance, panel: Panel, diagnostic: Experiment,
                          candidates: list[Experiment], *, sample_rate: int,
                          cost_function, cost_m2_per_unit: float = 0.0001,
                          assumed_quality: float = 0.75) -> ReferenceSelection:
    """Rank already-feasible references without changing belief, RNG or truth."""
    p = normalize_probability_grid(posterior)
    if not candidates or len(candidates) > 256:
        raise ValueError("A bounded nonempty reference candidate list is required")
    if (isinstance(sample_rate, bool) or not isinstance(sample_rate, int) or sample_rate < 1000
            or not np.isfinite([cost_m2_per_unit, assumed_quality]).all()
            or cost_m2_per_unit < 0 or not 0 < assumed_quality <= 1):
        raise ValueError("Invalid reference-design rate, cost or assumed quality")
    velocity = nuisance.parameter("wave_velocity").mean
    covariance = nuisance.propagation_covariance()
    rows, columns = np.indices(p.shape)
    x, y = (columns + .5) / p.shape[1], (rows + .5) / p.shape[0]
    paths = (physical_distance(diagnostic.source_x, diagnostic.source_y, x, y, panel)
             + physical_distance(x, y, diagnostic.receiver_x, diagnostic.receiver_y, panel))
    derivatives = np.column_stack((-paths.ravel() / velocity**2, np.ones(p.size)))
    second_moment = np.einsum('n,ni,nj->ij', p.ravel(), derivatives, derivatives)
    before_s2 = float(np.trace(second_moment @ covariance))
    observation_std = reference_observation_std(nuisance, panel, sample_rate)
    scored = []
    seen = set()
    for candidate in candidates:
        key = tuple(candidate.to_dict().items())
        if key in seen:
            continue
        seen.add(key)
        distance = float(physical_distance(candidate.source_x, candidate.source_y,
                                           candidate.receiver_x, candidate.receiver_y, panel))
        if distance <= 0 or candidate.frequency_end_hz >= sample_rate / 2:
            raise ValueError("Reference must have a positive path and supported frequency band")
        _, after_covariance = nuisance.conditioned_propagation(distance, observation_std, assumed_quality)
        after_s2 = float(np.trace(second_moment @ after_covariance))
        tolerance = max(before_s2, 1e-20) * 1e-10
        if after_s2 < -tolerance or after_s2 > before_s2 + tolerance:
            raise ValueError("Conditioning did not preserve the modeled variance bounds")
        after_s2 = float(np.clip(after_s2, 0, before_s2))
        cost = float(cost_function(candidate))
        if not np.isfinite(cost) or cost < 0:
            raise ValueError("Declared reference cost must be finite and nonnegative")
        after_m2 = velocity**2 * after_s2
        reduction_m2 = velocity**2 * (before_s2 - after_s2)
        length_history = [*nuisance.direct_path_lengths_m, distance]
        normalized_design = np.column_stack((np.asarray(length_history) / np.hypot(panel.width_m, panel.height_m),
                                             np.ones(len(length_history))))
        rank = int(np.linalg.matrix_rank(normalized_design))
        scored.append({"experiment": candidate.to_dict(), "path_length_m": distance,
                       "expected_task_variance_after_s2": after_s2,
                       "path_equivalent_variance_after_m2": after_m2,
                       "path_equivalent_reduction_m2": reduction_m2,
                       "acquisition_cost_m2": cost_m2_per_unit * cost,
                       "objective_m2": after_m2 + cost_m2_per_unit * cost,
                       "normalized_reference_design_rank": rank,
                       "reference_path_span_m": float(np.ptp(length_history)),
                       "conditioned_covariance": after_covariance.tolist()})
    scored.sort(key=lambda row: (row["objective_m2"], -row["normalized_reference_design_rank"], row["path_length_m"]))
    selected = scored[0]
    chosen = next(e for e in candidates if e.to_dict() == selected["experiment"])
    return ReferenceSelection(chosen, {
        "method": "full_grid_task_conditioned_reference_v1",
        "target_diagnostic": diagnostic.to_dict(), "posterior_mass": float(p.sum()),
        "cell_count": int(p.size), "propagation_covariance_before": covariance.tolist(),
        "expected_task_variance_before_s2": before_s2,
        "path_equivalent_variance_before_m2": velocity**2 * before_s2,
        "assumed_quality": assumed_quality, "reference_observation_std_s": observation_std,
        "cost_m2_per_unit": cost_m2_per_unit,
        "selected": selected, "alternatives": scored, "field_validated": False,
        "metric_scope": "posterior_weighted_propagation_arrival_variance_not_location_error",
        "assumptions": ["first_order_correlated_velocity_timing", "fixed_target_geometry",
                        "assumed_reference_noise_and_quality", "one_dominant_scatterer"],
    })
