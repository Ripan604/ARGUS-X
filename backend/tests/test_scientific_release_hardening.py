"""Regression cases for evidence ordering and scientific support boundaries."""

from dataclasses import replace

import numpy as np
import pytest

from backend.app.assurance.monitor import RuntimeAssuranceMonitor
from backend.app.core.config import ArgusConfig
from backend.app.digital_twin.forward_models import AnalyticalForwardModel
from backend.app.inference.belief import BeliefState, measurement_likelihood, normalize_probability_grid, posterior_update
from backend.app.inference.calibration import CalibrationEngine
from backend.app.inference.diagnostics import estimate_measurement_quality
from backend.app.inference.nuisance_posterior import NuisancePosterior
from backend.app.inference.particle_engine import ParticleInferenceEngine
from backend.app.inference.structural_posterior import StructuralPosterior
from backend.app.models.domain import Experiment, Material, Panel
from backend.app.services.engine import ArgusEngine
from backend.app.signal.processing import preprocess_signal


def _engine(seed=847):
    return ArgusEngine(ArgusConfig(seed=seed, candidate_count=8, enable_ood_layer=False,
                                  enable_discrepancy_model=False, max_experiments=10), seed=seed)


def _broken_channel(engine):
    for _ in range(12):
        engine.assurance.update(estimate_measurement_quality(np.zeros(1920)), {}, {"sensor_id": "broken"})


def test_accepted_reading_from_unreliable_channel_cannot_fuse_or_train():
    engine = _engine()
    _broken_channel(engine)
    plan = replace(engine.current_recommendation, action_type="diagnostic")
    signal = engine.acquisition_simulator.simulate(engine.truth, plan.selected.experiment)
    before = engine.belief.posterior.copy()
    nuisance_before = engine.joint_state.nuisance.to_dict()
    screening_before = engine.assurance.damage_log_odds
    result = engine.process_signal(signal, plan.selected.experiment, plan,
                                   {"sensor_id": "broken"}, plan_next=False)
    assert result.quality["accepted"] is True  # waveform quality is not channel recovery
    assert result.diagnostics["sensor_status_before_fusion"] == "UNRELIABLE"
    assert result.diagnostics["evidence_weight"] == 0
    assert result.diagnostics["update_blocked_sensor"] is True
    np.testing.assert_array_equal(engine.belief.posterior, before)
    assert engine.joint_state.nuisance.to_dict() == nuisance_before
    assert engine.assurance.damage_log_odds == screening_before
    assert engine.joint_state.ood_state["status"] == "ABSTAIN"
    assert not engine.prior_signals


def test_accepted_reference_from_unreliable_channel_cannot_calibrate():
    engine = _engine(848)
    _broken_channel(engine)
    experiment = Experiment(0.05, 0.5, 0.95, 0.5)
    plan = replace(engine.current_recommendation, action_type="calibration",
                   structured_explanation={"calibration_type": "direct_path"})
    signal = engine.acquisition_simulator.simulate_baseline(experiment)
    before = engine.joint_state.nuisance.to_dict()
    result = engine.process_signal(signal, experiment, plan, {"sensor_id": "broken"}, plan_next=False)
    assert result.quality["accepted"] is True
    assert result.calibration_result["accepted"] is False
    assert engine.joint_state.nuisance.to_dict() == before


def test_rejected_repeat_cannot_replace_last_accepted_consistency_reference():
    engine = _engine(849)
    plan = replace(engine.current_recommendation, action_type="diagnostic")
    experiment = plan.selected.experiment
    signal = engine.acquisition_simulator.simulate(engine.truth, experiment)
    engine.process_signal(signal, experiment, plan, plan_next=False)
    before = {key: value.copy() for key, value in engine.prior_signals.items()}
    engine.process_signal(np.zeros_like(signal), experiment, plan, plan_next=False)
    assert before.keys() == engine.prior_signals.keys()
    for key in before:
        np.testing.assert_array_equal(before[key], engine.prior_signals[key])


@pytest.mark.parametrize("samples", [np.ones((2, 960)), np.ones(1919), np.full(1920, np.nan)])
def test_invalid_observation_cannot_mutate_engine(samples):
    engine = _engine(850)
    state_before = engine.joint_state.to_dict()
    assurance_before = engine.assurance.to_dict()
    with pytest.raises(ValueError):
        engine.process_signal(samples, engine.current_recommendation.selected.experiment, plan_next=False)
    assert engine.joint_state.to_dict() == state_before
    assert engine.assurance.to_dict() == assurance_before
    assert not engine.results


def test_likelihood_rejects_silent_window_truncation_and_invalid_dimensions():
    engine = _engine(851)
    experiment = engine.current_recommendation.selected.experiment
    with pytest.raises(ValueError, match="window"):
        measurement_likelihood(np.ones(1000), experiment, engine.simulator, 20)
    with pytest.raises(ValueError, match="mono"):
        measurement_likelihood(np.ones((2, 960)), experiment, engine.simulator, 20)
    with pytest.raises(ValueError, match="one-dimensional"):
        preprocess_signal(np.ones((2, 960)), 16000)


def test_probability_normalization_preserves_scale_at_extreme_finite_values():
    weights = np.array([[1., 2.], [3., 4.]])
    for scale in (1e-300, 1e307):
        np.testing.assert_allclose(normalize_probability_grid(weights * scale), weights / weights.sum())
    prior = np.full((2, 2), 0.25)
    expected = weights / weights.sum()
    for scale in (1e-300, 1e307):
        np.testing.assert_allclose(posterior_update(prior, weights * scale), expected, atol=1e-13)


def test_invalid_probability_support_and_shape_are_explicit_errors():
    with pytest.raises(ValueError, match="negative"):
        normalize_probability_grid(np.array([[1., -1.], [1., 1.]]))
    with pytest.raises(ValueError, match="nonnegative"):
        posterior_update(np.ones((2, 2)), np.array([[1., -1.], [1., 1.]]))
    with pytest.raises(ValueError, match="no likelihood support"):
        posterior_update(np.ones((2, 2)), np.zeros((2, 2)))
    with pytest.raises(ValueError, match="shape"):
        BeliefState(10, np.ones((9, 9)))


@pytest.mark.parametrize("context", [{"acceleration_rms": float("nan")}, {"visual_position_error": -0.1}])
def test_invalid_placement_metadata_cannot_supply_good_evidence(context):
    values = np.sin(np.arange(1920) / 3) * 0.1
    quality = estimate_measurement_quality(values, **context)
    assert not quality.accepted
    assert "invalid_placement_metadata" in quality.reasons
    assert quality.evidence_weight == 0


def test_quality_failure_reasons_cannot_be_accepted():
    silent = np.sin(np.arange(1920) / 3) * 5e-6
    quality = estimate_measurement_quality(silent)
    assert "sensor_dropout_or_silence" in quality.reasons
    assert not quality.accepted
    clipped = np.sin(np.arange(1920) / 3) * 0.1
    clipped[:300] = 0.5
    quality = estimate_measurement_quality(clipped)
    assert "clipping" in quality.reasons
    assert not quality.accepted


@pytest.mark.parametrize("kind, diagnostics", [
    ("unknown_calibration", {"noise_floor": 0.007}),
    ("direct_path", {"noise_floor": 0.007}),
    ("coupling_repeat", {"noise_floor": 0.007}),
    ("direct_path", {"peak_delay_s": 0.003}),
    ("phone_pose_recalibration", {"noise_floor": 0.007, "pose_observation_std": 0.01,
                                  "source_pose_error_observed": 0, "receiver_pose_error_observed": 0.9}),
])
def test_missing_or_unsupported_calibration_cannot_partially_change_nuisance(kind, diagnostics):
    nuisance = NuisancePosterior.from_material(Material())
    before = nuisance.to_dict()
    quality = estimate_measurement_quality(np.sin(np.arange(1920) / 3) * 0.1)
    result = CalibrationEngine().update(nuisance, Experiment(0.05, 0.5, 0.95, 0.5), Panel(), diagnostics, quality, kind)
    assert not result.accepted
    assert nuisance.to_dict() == before


def test_screening_cannot_turn_rejected_model_evidence_into_damage_claim():
    monitor = RuntimeAssuranceMonitor()
    quality = estimate_measurement_quality(np.sin(np.arange(1920) / 3) * 0.1)
    before = monitor.damage_log_odds
    monitor.update(quality, {"residual_snr_db": 80, "evidence_weight": 0}, {"sensor_id": "s1"})
    assert monitor.damage_log_odds == before


def test_screening_cannot_release_a_healthy_structure_without_existence_model():
    monitor = RuntimeAssuranceMonitor(damage_log_odds=-5, accepted_measurements=20)
    assessment = monitor.structural_assessment(StructuralPosterior(), ood_state={"score": 0}, model_trust=1)
    assert assessment["engineering_action"] == "VERIFY_WITH_REFERENCE_METHOD"
    assert assessment["healthy_release_supported"] is False
    assert assessment["defect_existence_inferred"] is False
    assert "not_calibrated" in assessment["state_probability_method"]
    hypothesis = assessment["candidate_regions"][0]
    assert hypothesis["attribute_support"] == "unchanged_priors_not_measurement_inference"


def test_unlearned_severity_prior_cannot_change_location_uncertainty_score():
    a = StructuralPosterior(severity_std=0.01)
    b = StructuralPosterior(severity_std=0.8)
    assert a.uncertainty_summary()["combined"] == b.uncertainty_summary()["combined"]


def test_amplitude_only_or_reciprocal_action_is_not_diverse_verification():
    action = Experiment(0.1, 0.2, 0.8, 0.7)
    assert not ArgusEngine._verification_is_diverse(replace(action, amplitude=0.5), action)
    assert not ArgusEngine._verification_is_diverse(replace(action, duration_s=0.2), action)
    assert not ArgusEngine._verification_is_diverse(Experiment(0.8, 0.7, 0.1, 0.2), action)
    assert ArgusEngine._verification_is_diverse(replace(action, receiver_y=0.6), action)
    assert ArgusEngine._verification_is_diverse(replace(action, frequency_start_hz=2000), action)


def test_particle_predictions_preserve_velocity_timing_covariance():
    nuisance = NuisancePosterior.from_material(Material())
    nuisance.update_direct_path(0.4, 0.0008 + 0.4 / 180, 0.00002, 1)
    batch = ParticleInferenceEngine(seed=858).sample(StructuralPosterior(), nuisance, count=40000)
    actual = np.corrcoef(batch.nuisance["wave_velocity"], batch.nuisance["timing_offset"])[0, 1]
    assert actual == pytest.approx(nuisance.velocity_timing_correlation, abs=0.01)
    # The same fixed seed must regenerate the same posterior sample set.
    repeat = ParticleInferenceEngine(seed=858).sample(StructuralPosterior(), nuisance, count=40000)
    np.testing.assert_array_equal(batch.nuisance["timing_offset"], repeat.nuisance["timing_offset"])


def test_gain_uncertainty_increases_forward_log_gain_variance():
    engine = _engine(859)
    model = AnalyticalForwardModel(engine.simulator)
    nuisance = engine.joint_state.nuisance
    action = engine.current_recommendation.selected.experiment
    state = {"x": 0.4, "y": 0.5}
    before = model.predict(action, state, nuisance)
    old_std = nuisance.parameter("gain").std
    nuisance.parameter("gain").std = 2 * old_std
    after = model.predict(action, state, nuisance)
    expected_increment = 3 * old_std**2 / nuisance.parameter("gain").mean**2
    assert after.covariance[1, 1] - before.covariance[1, 1] == pytest.approx(expected_increment)
    np.testing.assert_array_equal(after.mean, before.mean)


def test_persisted_posterior_retains_tiny_hypothesis_support():
    values = np.full((10, 10), 1e-20)
    values[4, 5] = 1
    original = StructuralPosterior(10, values)
    restored = StructuralPosterior.from_state(original.to_state())
    assert restored.posterior[0, 0] > 0
    np.testing.assert_allclose(restored.posterior, original.posterior, rtol=1e-14, atol=0)
    # A later contradictory measurement can still make that supported region
    # plausible after hydration, exactly as it can before hydration.
    likelihood = np.ones((10, 10))
    likelihood[0, 0] = 1e21
    np.testing.assert_allclose(posterior_update(restored.posterior, likelihood),
                               posterior_update(original.posterior, likelihood), rtol=1e-14, atol=0)
