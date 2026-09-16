from __future__ import annotations

import numpy as np
import pytest

from backend.app.evaluation.research_validation import (
    acquisition_rng, bank_digest, bootstrap_mean_ci, candidate_banks, run_case, summarize, validate_pairing,
)
from backend.app.core.config import ArgusConfig
from backend.app.safety.constraints import ExperimentConstraintEngine


def test_candidate_opportunities_are_reproducible_safe_and_step_specific():
    banks = candidate_banks(123, 2, 12)
    repeated = candidate_banks(123, 2, 12)
    assert [bank_digest(b) for b in banks] == [bank_digest(b) for b in repeated]
    assert bank_digest(banks[0]) != bank_digest(banks[1])
    constraints = ExperimentConstraintEngine(ArgusConfig())
    assert all(constraints.evaluate(e).feasible for b in banks for e in b)
    assert all(len(b) == 12 for b in banks)


def test_noise_pairing_cannot_be_shifted_by_previous_actions():
    previous = acquisition_rng(123, 0)
    previous.normal(size=19_201)
    np.testing.assert_array_equal(acquisition_rng(123, 1).normal(size=1920),
                                  acquisition_rng(123, 1).normal(size=1920))
    assert not np.array_equal(acquisition_rng(123, 0).normal(size=20),
                              acquisition_rng(123, 1).normal(size=20))


def test_paired_bootstrap_uses_matched_seed_differences_and_reports_failures():
    rows = []
    for seed, old, new in ((1, 10, 9), (2, 100, 99), (3, 40, 39)):
        for variant, error in (("legacy_proxy", old), ("nuisance_aware", new)):
            rows.append(dict(seed=seed, context="nominal", variant=variant, completed=True,
                             localization_error_mm=error, success_20mm=error <= 20, failure_30mm=error > 30,
                             false_confidence=False, abstained=False, measurements=8, calibrations=0,
                             normalized_entropy=0.5, computation_seconds=1, rejected_measurements=0))
    rows.append(dict(seed=4, context="nominal", variant="nuisance_aware", completed=False))
    summary, paired = summarize(rows, ("nominal",), ("legacy_proxy", "nuisance_aware"))
    assert paired["nominal"]["complete_pairs"] == 3
    assert paired["nominal"]["bootstrap_95ci_mm"] == [1.0, 1.0]
    assert summary["nominal"]["nuisance_aware"]["execution_failures"] == 1
    assert summary["nominal"]["legacy_proxy"]["localization_error_mm"]["p90"] == 88.0
    with pytest.raises(ValueError):
        bootstrap_mean_ci([])


def test_controlled_engine_replays_same_truth_candidates_and_outcomes():
    first = run_case(31_999, "nominal", "legacy_proxy", steps=2, count=8)
    second = run_case(31_999, "nominal", "legacy_proxy", steps=2, count=8)
    assert first["sealed_truth"] == second["sealed_truth"]
    assert first["localization_error_mm"] == second["localization_error_mm"]
    assert first["trace"] == second["trace"]
    mismatch = run_case(31_999, "mismatch_noise", "legacy_proxy", steps=2, count=8)
    assert mismatch["sealed_truth"] == first["sealed_truth"]
    assert mismatch["acquisition_material"]["noise_std"] == 2 * first["acquisition_material"]["noise_std"]
    assert mismatch["assumed_material"] == first["assumed_material"]


def test_pairing_rejects_different_environment_and_duplicate_runs():
    row = dict(seed=1, context="nominal", variant="legacy_proxy", completed=True,
               sealed_truth={"x": 0.5}, assumed_material={"noise": 1}, acquisition_material={"noise": 1},
               measurements=1, trace=[{"candidate_bank_sha256": "shared"}])
    paired = {**row, "variant": "nuisance_aware"}
    validate_pairing([row, paired])
    with pytest.raises(ValueError, match="Duplicate run"):
        validate_pairing([row, row])
    with pytest.raises(ValueError, match="Pairing mismatch"):
        validate_pairing([row, {**paired, "sealed_truth": {"x": 0.6}}])
