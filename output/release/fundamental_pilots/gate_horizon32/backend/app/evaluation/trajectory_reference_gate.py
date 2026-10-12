"""Offline, whole-trajectory reference gate for measured guided-wave replay.

This module has no waveform-bank or truth access. It scores only observations
already acquired by a separately frozen controller. Rank p-values describe
reference nonconformity; they are not damage probabilities or field coverage
certificates. The exchangeability of cooling and warming blocks is unverified.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import re
from typing import Literal, Sequence

import numpy as np

FIXED_BUDGETS = (1, 2, 4, 8, 12, 16, 32)
NATIVE_PATH_COUNT = 66
SCORE_ID = "mean_squared_standardized_corrected_di_v1"
MAX_CALIBRATION_BLOCKS = 10000
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")
_BLOCK_ID = re.compile(r"[A-Za-z0-9_.:=-]{1,160}\Z")


def _valid_digest(value: object) -> bool:
    return isinstance(value, str) and _SHA256.fullmatch(value) is not None


def _valid_block_id(value: object) -> bool:
    return isinstance(value, str) and _BLOCK_ID.fullmatch(value) is not None


def _finite_scalar(value: object) -> bool:
    if (isinstance(value, (bool, np.bool_))
            or not isinstance(value, (int, float, np.integer, np.floating))):
        return False
    try:
        return math.isfinite(float(value))
    except (ValueError, OverflowError):
        return False


@dataclass(frozen=True)
class GateBinding:
    """Caller-supplied identities of the frozen model and acquisition protocol.

    Hash equality prevents accidental mixing. It does not authenticate a source
    or prove that the controller was actually executed as declared.
    """
    model_sha256: str
    controller_sha256: str
    protocol_sha256: str
    reference_sha256: str
    budgets: tuple[int, ...] = FIXED_BUDGETS
    path_count: int = NATIVE_PATH_COUNT
    score_id: str = SCORE_ID

    def __post_init__(self):
        object.__setattr__(self, "budgets", tuple(self.budgets))
        if not all(_valid_digest(getattr(self, key)) for key in (
                "model_sha256", "controller_sha256", "protocol_sha256", "reference_sha256")):
            raise ValueError("Binding requires lowercase SHA256 identities")
        if (self.budgets != FIXED_BUDGETS or any(type(x) is not int for x in self.budgets)
                or type(self.path_count) is not int or self.path_count != NATIVE_PATH_COUNT
                or self.score_id != SCORE_ID):
            raise ValueError("Binding differs from the frozen native-path score protocol")

    def to_dict(self) -> dict:
        return {**self.__dict__, "budgets": list(self.budgets)}


@dataclass(frozen=True)
class SelectedObservation:
    """One acquired path; scale must be frozen using fitting data only.

    Signed corrected DI is accepted to allow an explicitly centered residual.
    Both a bounded DI and a finite positive, path-conditioned scale are required.
    Rejected opportunities remain in the trace and make the gate unsupported.
    """
    path_index: int
    corrected_damage_index: float
    healthy_sigma: float
    accepted: bool = True


@dataclass(frozen=True)
class HealthyTrajectory:
    block_id: str
    source_sha256: str
    observations: tuple[SelectedObservation, ...]
    binding: GateBinding
    complete: bool = True

    def __post_init__(self):
        object.__setattr__(self, "observations", tuple(self.observations))


def _snapshot_and_validate(observations: Sequence[SelectedObservation],
                           binding: GateBinding) -> tuple[SelectedObservation, ...]:
    # Never consume a generator with potentially unbounded or future bank access.
    if not isinstance(observations, (tuple, list)):
        raise ValueError("Observations require an already acquired bounded tuple/list")
    if not 1 <= len(observations) <= binding.budgets[-1]:
        raise ValueError("Observation prefix is empty or exceeds the frozen horizon")
    values = tuple(observations)
    paths: set[int] = set()
    for row in values:
        if not isinstance(row, SelectedObservation):
            raise ValueError("Observation schema is unsupported")
        if (isinstance(row.path_index, (bool, np.bool_))
                or not isinstance(row.path_index, (int, np.integer))
                or not 0 <= int(row.path_index) < binding.path_count
                or int(row.path_index) in paths):
            raise ValueError("Selected path is invalid or repeated")
        paths.add(int(row.path_index))
        if type(row.accepted) is not bool or not row.accepted:
            raise ValueError("A rejected acquisition cannot produce a supported gate decision")
        if (not _finite_scalar(row.corrected_damage_index)
                or abs(float(row.corrected_damage_index)) > 1
                or not _finite_scalar(row.healthy_sigma) or float(row.healthy_sigma) <= 0):
            raise ValueError("Corrected DI/healthy scale must be finite, bounded and qualified")
    return values


def prefix_anomaly_score(observations: Sequence[SelectedObservation],
                         binding: GateBinding) -> float:
    """Mean z squared at a prespecified prefix, without querying future paths."""
    values = _snapshot_and_validate(observations, binding)
    if len(values) not in binding.budgets:
        raise ValueError("Only prespecified checkpoint budgets can be scored")
    with np.errstate(over="ignore", divide="ignore", invalid="ignore"):
        standardized = np.asarray([float(row.corrected_damage_index) for row in values]) / np.asarray(
            [float(row.healthy_sigma) for row in values])
        score = float(np.mean(standardized * standardized))
    if not math.isfinite(score):
        raise ValueError("Standardized score exceeds finite numeric support")
    return score


@dataclass(frozen=True)
class GateCalibration:
    binding: GateBinding
    block_ids: tuple[str, ...]
    source_sha256s: tuple[str, ...]
    trajectory_max_scores: tuple[float, ...]
    alpha: float = .05

    def __post_init__(self):
        for key in ("block_ids", "source_sha256s", "trajectory_max_scores"):
            object.__setattr__(self, key, tuple(getattr(self, key)))
        count = len(self.block_ids)
        if not isinstance(self.binding, GateBinding):
            raise ValueError("Calibration requires the frozen gate binding")
        if (not 1 <= count <= MAX_CALIBRATION_BLOCKS
                or len(self.source_sha256s) != count or len(self.trajectory_max_scores) != count
                or not all(_valid_block_id(x) for x in self.block_ids)
                or len(set(self.block_ids)) != count
                or not all(_valid_digest(x) for x in self.source_sha256s)
                or len(set(self.source_sha256s)) != count):
            raise ValueError("Calibration blocks/artifacts must be nonempty, bounded and unique")
        if (not _finite_scalar(self.alpha) or not 0 < float(self.alpha) < 1
                or any(not _finite_scalar(x) or float(x) < 0 for x in self.trajectory_max_scores)):
            raise ValueError("Calibration scores/alpha must be finite and valid")

    @property
    def minimum_p_value(self) -> float:
        return 1 / (len(self.block_ids) + 1)

    def to_dict(self) -> dict:
        return {"binding": self.binding.to_dict(), "block_ids": list(self.block_ids),
                "source_sha256s": list(self.source_sha256s),
                "trajectory_max_scores": list(self.trajectory_max_scores),
                "alpha": float(self.alpha), "minimum_p_value": self.minimum_p_value,
                "unit": "complete_adaptive_trajectory_block",
                "exchangeability_verified": False, "field_coverage_claimed": False}


def calibrate_reference_gate(trajectories: Sequence[HealthyTrajectory],
                             binding: GateBinding, alpha: float = .05) -> GateCalibration:
    """Freeze one maximum per complete healthy replay of the same controller.

    Empty/incomplete/invalid trajectories are rejected, not silently discarded.
    Distinct IDs and file hashes do not establish biological/specimen independence.
    """
    if (not isinstance(trajectories, (list, tuple))
            or not 1 <= len(trajectories) <= MAX_CALIBRATION_BLOCKS
            or not isinstance(binding, GateBinding)):
        raise ValueError("Calibration requires a bounded nonempty trajectory collection")
    blocks, hashes, maxima = [], [], []
    for trajectory in trajectories:
        if not isinstance(trajectory, HealthyTrajectory) or trajectory.binding != binding:
            raise ValueError("Calibration trajectory binding/schema does not match")
        if type(trajectory.complete) is not bool or not trajectory.complete:
            raise ValueError("Only complete healthy trajectories may enter calibration")
        values = _snapshot_and_validate(trajectory.observations, binding)
        if len(values) != binding.budgets[-1]:
            raise ValueError("Healthy calibration trajectory must reach the complete frozen horizon")
        maxima.append(max(prefix_anomaly_score(values[:budget], binding) for budget in binding.budgets))
        blocks.append(trajectory.block_id)
        hashes.append(trajectory.source_sha256)
    return GateCalibration(binding, tuple(blocks), tuple(hashes), tuple(maxima), alpha)


@dataclass(frozen=True)
class GateDecision:
    status: Literal["supported_anomaly", "background_consistent", "unsupported"]
    reason: str
    budget: int
    prefix_score: float | None
    reference_p_value: float | None
    calibration_count: int
    minimum_p_value: float | None
    localization_supported: bool = False
    field_coverage_claimed: bool = False

    def to_dict(self) -> dict:
        return {**self.__dict__, "p_value_interpretation": "empirical_reference_rank_not_damage_probability"}


def evaluate_reference_prefix(calibration: GateCalibration | None,
                              observations: Sequence[SelectedObservation],
                              binding: GateBinding, *, block_id: str, source_sha256: str,
                              reference_qualified: bool, model_quality_accepted: bool) -> GateDecision:
    """Return three states; absence of anomaly is never a healthy release.

    Use only a prefix copied when the checkpoint is reached. Test data may not
    fit the model, scales, controller, alpha or calibration. This API has no
    damage truth parameter and cannot access the unselected observation bank.
    """
    budget = len(observations) if isinstance(observations, (list, tuple)) else 0
    count = len(calibration.block_ids) if isinstance(calibration, GateCalibration) else 0
    min_p = calibration.minimum_p_value if isinstance(calibration, GateCalibration) else None

    def unsupported(reason: str, score: float | None = None) -> GateDecision:
        return GateDecision("unsupported", reason, budget, score, None, count, min_p)

    if not isinstance(calibration, GateCalibration):
        return unsupported("missing_calibration")
    if not isinstance(binding, GateBinding) or binding != calibration.binding:
        return unsupported("binding_mismatch")
    if not _valid_block_id(block_id) or not _valid_digest(source_sha256):
        return unsupported("invalid_test_identity")
    if block_id in calibration.block_ids or source_sha256 in calibration.source_sha256s:
        return unsupported("calibration_block_or_artifact_reused_for_test")
    if type(reference_qualified) is not bool or not reference_qualified:
        return unsupported("reference_not_qualified")
    if type(model_quality_accepted) is not bool or not model_quality_accepted:
        return unsupported("model_quality_not_accepted")
    try:
        score = prefix_anomaly_score(observations, binding)
    except (ValueError, TypeError, OverflowError):
        return unsupported("invalid_or_unsupported_observation_prefix")
    # With too few whole blocks, no observation can meet the frozen alpha.
    # Such a comparison must not become an automatic background/healthy decision.
    if min_p is None or min_p > float(calibration.alpha):
        return unsupported("insufficient_whole_block_rank_resolution", score)
    greater_or_equal = sum(value >= score for value in calibration.trajectory_max_scores)
    p_value = (1 + greater_or_equal) / (count + 1)
    is_anomaly = p_value <= float(calibration.alpha)
    return GateDecision("supported_anomaly" if is_anomaly else "background_consistent",
                        "reference_rank_at_or_below_alpha" if is_anomaly else "reference_rank_above_alpha",
                        budget, score, float(p_value), count, min_p)
