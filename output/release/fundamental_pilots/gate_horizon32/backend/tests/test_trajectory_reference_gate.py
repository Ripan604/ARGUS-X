"""Causal and finite-sample rank checks, independent of confirmation waveforms."""
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
import math

import numpy as np
import pytest

from backend.app.evaluation.trajectory_reference_gate import (
    FIXED_BUDGETS, GateBinding, GateCalibration, HealthyTrajectory,
    SelectedObservation, calibrate_reference_gate, evaluate_reference_prefix,
    prefix_anomaly_score,
)


def digest(value):
    return sha256(str(value).encode()).hexdigest()


def binding():
    return GateBinding(*(digest(name) for name in ("model", "controller", "protocol", "reference")))


def observations(score=1., count=32):
    return tuple(SelectedObservation(i, math.sqrt(score) * .01, .01) for i in range(count))


def trajectories(count=19):
    fixed = binding()
    return [HealthyTrajectory(f"healthy-cooling-{i}", digest(f"raw-{i}"), observations(i), fixed)
            for i in range(count)]


def evaluate(calibration, values, **kwargs):
    inputs = {"block_id": "test-warming-30", "source_sha256": digest("unseen-test"),
              "reference_qualified": True, "model_quality_accepted": True}
    inputs.update(kwargs)
    return evaluate_reference_prefix(calibration, values, binding(), **inputs)


def test_nineteen_whole_blocks_give_point_zero_five_resolution_not_66_times_more_samples():
    cal = calibrate_reference_gate(trajectories(), binding())
    assert len(cal.trajectory_max_scores) == 19
    assert cal.minimum_p_value == .05
    decision = evaluate(cal, observations(20., 1))
    assert decision.status == "supported_anomaly"
    assert decision.reference_p_value == .05
    assert not decision.localization_supported and not decision.field_coverage_claimed
    assert decision.to_dict()["p_value_interpretation"] == "empirical_reference_rank_not_damage_probability"


def test_exact_rank_and_conservative_ties_cannot_alert_on_equal_maximum():
    cal = calibrate_reference_gate(trajectories(), binding())
    # Avoid roundoff from a synthetic square-root fixture by equal observation.
    decision = evaluate(cal, trajectories()[-1].observations[:1])
    assert decision.reference_p_value == .1
    assert decision.status == "background_consistent"
    zero = evaluate(cal, observations(0., 4))
    assert zero.reference_p_value == 1.


def test_calibration_block_order_does_not_change_p_value_or_status():
    rows = trajectories()
    cal_a = calibrate_reference_gate(rows, binding())
    cal_b = calibrate_reference_gate(list(reversed(rows)), binding())
    assert evaluate(cal_a, observations(7.5, 8)) == evaluate(cal_b, observations(7.5, 8))


def test_calibration_maximum_uses_early_prefix_and_not_only_final_budget():
    rows = trajectories()
    early = (SelectedObservation(0, .2, .01),) + tuple(SelectedObservation(i, 0., .01) for i in range(1, 32))
    rows[0] = replace(rows[0], observations=early)
    cal = calibrate_reference_gate(rows, binding())
    assert cal.trajectory_max_scores[0] == 400.
    assert prefix_anomaly_score(early, binding()) == 12.5
    assert evaluate(cal, observations(30., 1)).reference_p_value == .1


def test_whole_maximum_dominates_every_prespecified_calibration_prefix():
    rng = np.random.default_rng(8108)
    rows = trajectories()
    for i, row in enumerate(rows):
        values = tuple(SelectedObservation(path, float(v), .04)
                       for path, v in enumerate(rng.uniform(0., .2, 32)))
        rows[i] = replace(row, observations=values)
    cal = calibrate_reference_gate(rows, binding())
    for row, maximum in zip(rows, cal.trajectory_max_scores):
        assert all(prefix_anomaly_score(row.observations[:b], binding()) <= maximum for b in FIXED_BUDGETS)


def test_scoring_has_no_future_access_and_prefix_does_not_depend_on_future_changes():
    values = list(observations(2.))
    prefix = tuple(values[:4])
    score = prefix_anomaly_score(prefix, binding())
    values[4:] = [SelectedObservation(i, float("nan"), 0.) for i in range(4, 32)]
    assert prefix_anomaly_score(values[:4], binding()) == score
    cal = calibrate_reference_gate(trajectories(), binding())
    assert evaluate(cal, prefix) == evaluate(cal, values[:4])
    # A lazy source could query future data while being consumed; it is refused.
    def forbidden_generator():
        raise AssertionError("Future bank accessed")
        yield None
    decision = evaluate(cal, forbidden_generator())
    assert decision.status == "unsupported"


def test_negative_centered_di_has_same_squared_score():
    positive = observations(2., 8)
    negative = tuple(replace(row, corrected_damage_index=-row.corrected_damage_index) for row in positive)
    assert prefix_anomaly_score(positive, binding()) == prefix_anomaly_score(negative, binding())


@pytest.mark.parametrize("values", [(), observations(1., 3), observations(1., 33)])
def test_empty_unplanned_and_over_horizon_prefixes_are_unsupported(values):
    cal = calibrate_reference_gate(trajectories(), binding())
    result = evaluate(cal, values)
    assert result.status == "unsupported" and result.reference_p_value is None


@pytest.mark.parametrize("change", [
    {"corrected_damage_index": float("nan")}, {"corrected_damage_index": float("inf")},
    {"corrected_damage_index": 1.1}, {"corrected_damage_index": True},
    {"healthy_sigma": 0.}, {"healthy_sigma": -1.}, {"healthy_sigma": float("nan")},
    {"healthy_sigma": float("inf")}, {"healthy_sigma": True}, {"healthy_sigma": 1e-320},
    {"path_index": True}, {"path_index": -1}, {"path_index": 66}, {"path_index": 1.5},
    {"accepted": False}, {"accepted": 1},
])
def test_invalid_observation_cannot_become_anomaly_or_background(change):
    cal = calibrate_reference_gate(trajectories(), binding())
    result = evaluate(cal, (replace(observations()[0], **change),))
    assert result.status == "unsupported" and result.reference_p_value is None


def test_duplicate_path_does_not_count_as_independent_observation():
    cal = calibrate_reference_gate(trajectories(), binding())
    result = evaluate(cal, (observations()[0], observations()[0]))
    assert result.status == "unsupported"


@pytest.mark.parametrize("kwargs,reason", [
    ({"block_id": "healthy-cooling-0"}, "calibration_block_or_artifact_reused_for_test"),
    ({"source_sha256": digest("raw-0")}, "calibration_block_or_artifact_reused_for_test"),
    ({"source_sha256": "x"}, "invalid_test_identity"),
    ({"block_id": "../unseen"}, "invalid_test_identity"),
    ({"reference_qualified": False}, "reference_not_qualified"),
    ({"reference_qualified": 1}, "reference_not_qualified"),
    ({"model_quality_accepted": False}, "model_quality_not_accepted"),
])
def test_provenance_and_quality_guards_precede_any_positive_decision(kwargs, reason):
    cal = calibrate_reference_gate(trajectories(), binding())
    result = evaluate(cal, observations(100., 1), **kwargs)
    assert result.status == "unsupported" and result.reason == reason


def test_new_model_controller_protocol_or_reference_requires_new_calibration():
    cal = calibrate_reference_gate(trajectories(), binding())
    for key in ("model_sha256", "controller_sha256", "protocol_sha256", "reference_sha256"):
        other = replace(binding(), **{key: digest("different")})
        result = evaluate_reference_prefix(cal, observations(100., 1), other, block_id="test",
                                           source_sha256=digest("test"), reference_qualified=True,
                                           model_quality_accepted=True)
        assert result.status == "unsupported" and result.reason == "binding_mismatch"


def test_missing_or_insufficient_calibration_cannot_release_healthy():
    assert evaluate(None, observations(0., 1)).status == "unsupported"
    cal = calibrate_reference_gate(trajectories(18), binding())
    for score in (0., 100.):
        result = evaluate(cal, observations(score, 1))
        assert result.status == "unsupported"
        assert result.reason == "insufficient_whole_block_rank_resolution"
        assert result.minimum_p_value == 1 / 19


@pytest.mark.parametrize("edit", [
    lambda rows: [], lambda rows: [replace(rows[0], complete=False)],
    lambda rows: [replace(rows[0], complete=1)],
    lambda rows: [replace(rows[0], observations=observations(1., 16))],
    lambda rows: [replace(rows[0], observations=(SelectedObservation(0, float("nan"), .1),) + rows[0].observations[1:])],
    lambda rows: [rows[0], rows[0]],
    lambda rows: [rows[0], replace(rows[1], source_sha256=rows[0].source_sha256)],
    lambda rows: [replace(rows[0], binding=replace(binding(), controller_sha256=digest("other")))],
])
def test_calibration_rejects_empty_incomplete_failed_or_reused_blocks_instead_of_dropping(edit):
    with pytest.raises(ValueError):
        calibrate_reference_gate(edit(trajectories()), binding())


def test_calibration_is_immutable_and_snapshots_caller_collections():
    rows = trajectories()
    cal = calibrate_reference_gate(rows, binding())
    before = cal.to_dict()
    rows.clear()
    with pytest.raises(FrozenInstanceError):
        cal.alpha = .99
    export = cal.to_dict()
    export["trajectory_max_scores"][0] = 1e50
    assert cal.to_dict() == before


@pytest.mark.parametrize("change", [{"alpha": float("nan")}, {"alpha": True}, {"alpha": 0.},
                                    {"trajectory_max_scores": (float("inf"),) * 19}])
def test_manually_constructed_invalid_calibration_is_rejected(change):
    cal = calibrate_reference_gate(trajectories(), binding())
    with pytest.raises(ValueError):
        replace(cal, **change)


@pytest.mark.parametrize("change", [{"budgets": (1, 2, 32)}, {"path_count": 67},
                                    {"score_id": "tuned_after_test"}, {"model_sha256": "X" * 64}])
def test_binding_rejects_changed_or_unbounded_protocol(change):
    with pytest.raises(ValueError):
        replace(binding(), **change)
