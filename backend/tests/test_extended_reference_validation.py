"""Independent validation of study design; no test depends on favorable results."""
import json

import numpy as np
import pytest

from scripts.validate_reference_design_extended import (
    ASSUMED_QUALITY, COST_M2_PER_UNIT, NOISE_REGIMES, POLICIES,
    acquisition_cost, canonical_hash, run_policy, run_study, scaled_covariance, seal_case,
    select_scaled_optimal_reference,
)


def test_scaled_covariance_is_invariant_to_parameter_unit_changes():
    covariance = np.asarray([[900., .002], [.002, 4e-8]])
    reference = scaled_covariance(covariance, 180., .004)
    # Simultaneously changing each parameter's representation and its scale
    # preserves the dimensionless design, unlike a raw covariance trace.
    units = np.diag([.001, 1000.])
    transformed = scaled_covariance(units @ covariance @ units.T, .180, 4.)
    np.testing.assert_allclose(reference, transformed, rtol=1e-13)
    with pytest.raises(ValueError): scaled_covariance(covariance, 0, .004)


def test_cases_are_prospectively_sealed_reproducible_and_nonuniform():
    first, second = seal_case(970001, 0), seal_case(970001, 0)
    assert first.seal_hash == second.seal_hash
    assert first.prior_json == second.prior_json
    assert first.innovations == second.innovations
    assert first.random_indices == second.random_indices
    np.testing.assert_array_equal(first.posterior, second.posterior)
    assert np.ptp(first.posterior) > 0
    assert first.posterior.sum() == pytest.approx(1)
    assert first.posterior.min() > 0
    assert not first.posterior.flags.writeable


def test_a_and_d_baselines_minimize_declared_scaled_objective_and_preserve_state():
    case = seal_case(970001, 2)
    nuisance = case.prior()
    before = json.dumps(nuisance.to_dict(), sort_keys=True)
    for policy in ("scaled_a_optimal", "scaled_d_optimal"):
        selected, diagnostics = select_scaled_optimal_reference(nuisance, case.panel, case.references,
                                                                 case.starting_pose, case.velocity_ref, policy)
        rows = diagnostics["alternatives"]
        winner = diagnostics["selected"]
        assert winner["objective_m2"] == pytest.approx(min(row["objective_m2"] for row in rows))
        assert case.references[winner["index"]] == selected
        assert winner["acquisition_cost_m2"] == pytest.approx(
            COST_M2_PER_UNIT * acquisition_cost(selected, case.starting_pose))
    assert json.dumps(nuisance.to_dict(), sort_keys=True) == before


def test_acquisition_truth_noise_and_innovations_are_identical_across_policies():
    case = seal_case(970032, 1)
    rows = [run_policy(case, "double_acquisition_noise", policy) for policy in POLICIES]
    assert {row["seal_sha256"] for row in rows} == {case.seal_hash}
    for step in range(3):
        assert len({row["trace"][step]["acquisition_noise_std_s"] for row in rows}) == 1
        assert len({row["trace"][step]["shared_innovation"] for row in rows}) == 1
        assert len({row["trace"][step]["shared_noise_s"] for row in rows}) == 1
    nominal = run_policy(case, "nominal_prior_noise", "task_conditioned")
    mismatch = rows[-1]
    assert mismatch["trace"][0]["acquisition_noise_std_s"] == pytest.approx(
        2*nominal["trace"][0]["acquisition_noise_std_s"])
    # Both policies have identical information before the first acquisition.
    assert mismatch["trace"][0]["reference_index"] == nominal["trace"][0]["reference_index"]


def test_failure_consumes_budget_retains_finite_outcomes_and_is_not_excluded(monkeypatch):
    case = seal_case(970063, 0)
    def reject(*args, **kwargs): raise ValueError("Injected acquisition rejection")
    monkeypatch.setattr("scripts.validate_reference_design_extended.NuisancePosterior.update_direct_path", reject)
    row = run_policy(case, "nominal_prior_noise", "task_conditioned")
    assert row["completed"] is False
    assert row["failures"] == 3
    assert row["attempted_opportunities"] == 3
    assert len(row["trace"]) == 3
    assert row["actual_acquisition_cost_m2"] > 0
    assert np.isfinite(row["target_arrival_rmse_us"])
    assert all(step["failure_phase"] == "calibration" for step in row["trace"])


def test_small_study_retains_every_policy_regime_geometry_and_cost_without_evidence_write():
    report = run_study(seed_count=2, geometry_count=2, bootstrap_samples=100)
    assert len(report["runs"]) == 2*2*len(NOISE_REGIMES)*len(POLICIES)
    assert len(report["sealed_cases"]) == 4
    for sealed in report["sealed_cases"]:
        assert canonical_hash({key: value for key, value in sealed.items() if key != "seal_sha256"}) == sealed["seal_sha256"]
    assert report["metadata"]["source_changed_during_run"] is False
    for regime in NOISE_REGIMES:
        for policy in POLICIES:
            summary = report["summary"][regime][policy]
            assert summary["attempted_runs"] == 4
            assert summary["mean_actual_acquisition_cost_m2"] > 0
            assert summary["selection_latency_p95_ms"] >= 0
    assert all(row["seed_clusters"] == 2 for row in report["paired"])
    assert any(row["regime_group"] == "geometry_0_double_acquisition_noise" for row in report["paired"])
    assert all(len(row["seed_cluster_differences"]) == 2 for row in report["paired"])
    assert all(row["failure_policy"] == "all_attempted_cases_retained" for row in report["paired"])
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize("seed_count,geometry_count,bootstrap", [(0, 4, 100), (1, 0, 100), (1, 5, 100), (1, 4, 0)])
def test_study_bounds_are_explicit(seed_count, geometry_count, bootstrap):
    with pytest.raises(ValueError):
        run_study(seed_count=seed_count, geometry_count=geometry_count, bootstrap_samples=bootstrap)
