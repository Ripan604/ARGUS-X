from __future__ import annotations

from dataclasses import FrozenInstanceError
import json

import numpy as np
import pytest
from threadpoolctl import threadpool_limits

from backend.app.evaluation.healthy_wave_transport import (
    DELAY_LIMIT_S, NATIVE_RATE, NATIVE_SAMPLES, SIGMA_FLOOR,
    FitPolicy, WarpParameters, fit_healthy_transport, fit_path_warp, source_alignment,
    warp_reference,
)


TIME = np.arange(NATIVE_SAMPLES) / NATIVE_RATE


def electrical_pitch(t):
    duration = 125e-6
    valid = (t >= 0) & (t <= duration)
    return np.where(valid, np.sin(2*np.pi*40000*t) * np.sin(np.pi*np.clip(t, 0, duration)/duration)**2, 0.)


def healthy_receiver(t, path=0):
    signal = np.zeros_like(t)
    # Separated wave packets make propagation stretch distinguishable from a
    # common electronics delay. This is an injected contract, not field data.
    for amplitude, center, width, phase in ((1., 190e-6 + path*15e-6, 22e-6, .2),
                                           (.6, 600e-6 + path*20e-6, 30e-6, -.3),
                                           (.35, 1050e-6 - path*10e-6, 25e-6, .4)):
        signal += amplitude*np.exp(-.5*((t-center)/width)**2)*np.sin(2*np.pi*40000*t+phase)
    return signal


def training_fixture():
    catches = []; pitches = []
    for anchor in range(3):
        scale = 1 + anchor*.002; delay = -anchor*1.5e-6; gain = 1 + anchor*.1
        source_delay = anchor*1e-6
        catches.append([gain*healthy_receiver((TIME-source_delay-delay)/scale, path) for path in range(2)])
        pitches.append([electrical_pitch(TIME-source_delay) for _ in range(2)])
    return np.array(catches), np.array(pitches), np.array([[20., 20.], [40., 40.], [60., 60.]])


@pytest.fixture(scope="module")
def transport():
    catch, pitch, temperatures = training_fixture()
    with threadpool_limits(limits=1):
        return fit_healthy_transport(catch, pitch, temperatures)


def test_recorded_electrical_source_delay_has_correct_sign_and_subsample_resolution():
    with threadpool_limits(limits=1):
        alignment = source_alignment(electrical_pitch(TIME), electrical_pitch(TIME-3.25e-6))
    assert alignment.supported
    assert alignment.delay_s == pytest.approx(3.25e-6, abs=2e-8)
    assert alignment.signed_correlation > .999


def test_source_delay_bound_and_zero_excitation_do_not_claim_supported_alignment():
    with threadpool_limits(limits=1):
        outside = source_alignment(electrical_pitch(TIME), electrical_pitch(TIME-15e-6))
    assert not outside.supported
    with pytest.raises(ValueError, match="energy"):
        source_alignment(electrical_pitch(TIME), np.zeros(NATIVE_SAMPLES))


def test_injected_healthy_stretch_phase_delay_and_gain_are_recovered():
    reference = healthy_receiver(TIME)
    observation = 1.25*healthy_receiver((TIME+2.4e-6)/1.005)
    with threadpool_limits(limits=1):
        fit = fit_path_warp(reference, observation)
    assert fit.supported and fit.identifiable
    assert fit.parameters.scale == pytest.approx(1.005, abs=3e-5)
    assert fit.parameters.delay_s == pytest.approx(-2.4e-6, abs=3e-8)
    assert fit.parameters.gain == pytest.approx(1.25, abs=.002)
    assert fit.normalized_rms < .002
    assert fit.evaluations <= 60


def test_temperature_interpolation_and_current_pitch_predict_reference_without_test_catch(transport):
    source_delay = 4.2e-6
    with threadpool_limits(limits=1):
        prediction = transport.predict_reference(0, [30., 30.], electrical_pitch(TIME-source_delay))
    expected = 1.05*healthy_receiver((TIME-source_delay+.75e-6)/1.001)
    expected -= expected.mean()
    assert prediction.supported
    assert prediction.parameters.scale == pytest.approx(1.001, abs=3e-5)
    assert prediction.parameters.delay_s == pytest.approx(-.75e-6, abs=3e-8)
    assert np.linalg.norm(prediction.reference-expected)/np.linalg.norm(expected) < .003


def test_changing_observed_catch_cannot_change_any_reference_warp_or_frozen_fit(transport):
    pitch = electrical_pitch(TIME-2e-6)
    clean = 1.05*healthy_receiver((TIME-2e-6+.75e-6)/1.001)
    changed = clean + .3*np.exp(-.5*((TIME-800e-6)/20e-6)**2)*np.sin(2*np.pi*40000*TIME)
    fingerprint = transport.model_sha256
    anchors = transport.parameter_anchors.copy()
    with threadpool_limits(limits=1):
        first = transport.observe(0, 30., pitch, clean)
        second = transport.observe(0, 30., pitch, changed)
    assert np.array_equal(first.prediction.reference, second.prediction.reference)
    assert first.prediction.parameters == second.prediction.parameters
    assert transport.model_sha256 == fingerprint
    assert np.array_equal(transport.parameter_anchors, anchors)
    assert 0 <= first.damage_index <= 1 and 0 <= second.damage_index <= 1


def test_templates_coefficients_and_fit_records_are_immutable(transport):
    for values in (transport.receiver_reference, transport.pitch_reference, transport.parameter_anchors,
                   transport.temperatures_c, transport.healthy_sigma, transport.development_damage_index):
        with pytest.raises(ValueError):
            values.flat[0] = 123.
        with pytest.raises(ValueError):
            values.setflags(write=True)
    with pytest.raises(FrozenInstanceError):
        transport.fits[2][0].parameters.scale = 1.01


def test_middle_healthy_development_residual_alone_sets_frozen_path_scale(transport):
    assert np.array_equal(transport.healthy_sigma, np.maximum(SIGMA_FLOOR, transport.development_damage_index))
    assert transport.healthy_sigma.shape == (2,)
    assert len(transport.training_sha256) == len(transport.model_sha256) == 64
    summary = transport.to_dict()
    assert summary["test_catch_used_to_fit"] is False
    assert summary["sigma_is_residual_proxy_not_independent_noise_estimate"] is True
    json.dumps(summary, allow_nan=False)


def test_small_extrapolation_is_disclosed_and_larger_excursion_is_unsupported(transport):
    with threadpool_limits(limits=1):
        cold = transport.predict_reference(0, 19., electrical_pitch(TIME))
        outside = transport.predict_reference(0, 16., electrical_pitch(TIME))
    assert cold.extrapolated and cold.supported
    assert outside.extrapolated and not outside.supported
    assert "surface_temperature_outside_qualified_extrapolation" in outside.rejection_reasons


@pytest.mark.parametrize("fault", ["missing_anchor", "wrong_window", "nonfinite", "unsorted_temperature", "missing_pitch", "object_array"])
def test_native_healthy_input_contract_is_fail_closed(fault):
    catch, pitch, temperatures = training_fixture()
    if fault == "missing_anchor": catch = catch[:2]
    elif fault == "wrong_window": catch = catch[:, :, :-1]
    elif fault == "nonfinite": catch[1, 0, 20] = np.nan
    elif fault == "unsorted_temperature": temperatures[[0, 2]] = temperatures[[2, 0]]
    elif fault == "missing_pitch": pitch = pitch[:2]
    else: catch = catch.astype(object)
    with pytest.raises(ValueError):
        fit_healthy_transport(catch, pitch, temperatures)


def test_predicted_reference_remains_complete_native_data_and_rejects_bad_indices(transport):
    with threadpool_limits(limits=1):
        prediction = transport.predict_reference(1, 40., electrical_pitch(TIME))
    assert prediction.reference.shape == (13108,)
    assert np.isfinite(prediction.reference).all()
    for index in (-1, True, 2):
        with pytest.raises(ValueError):
            transport.predict_reference(index, 40., electrical_pitch(TIME))
    with pytest.raises(ValueError):
        transport.observe(0, 40., electrical_pitch(TIME), np.zeros(NATIVE_SAMPLES))


def test_warp_bounds_cannot_be_silently_extended():
    for parameters in (WarpParameters(1.06, 0., 1.), WarpParameters(1., DELAY_LIMIT_S*2, 1.), WarpParameters(1., 0., 3.)):
        with pytest.raises(ValueError, match="bounds"):
            warp_reference(healthy_receiver(TIME), parameters)


def test_three_percent_healthy_stretch_is_recovered_without_relaxing_qualification():
    policy = FitPolicy()
    reference = healthy_receiver(TIME)
    observation = 1.15*healthy_receiver((TIME-1.8e-6)/1.03)
    with threadpool_limits(limits=1):
        fit = fit_path_warp(reference, observation, policy=policy)
    assert fit.supported and fit.identifiable
    assert fit.parameters.scale == pytest.approx(1.03, abs=3e-5)
    assert fit.parameters.delay_s == pytest.approx(1.8e-6, abs=3e-8)
    assert fit.parameters.gain == pytest.approx(1.15, abs=.002)
    assert fit.normalized_rms < .002
    assert policy.maximum_normalized_fit_rms == .30
    assert policy.minimum_source_correlation == .80


@pytest.mark.parametrize("values", [
    {"stretch_bound": 0}, {"stretch_bound": .051}, {"stretch_bound": float("nan")},
    {"delay_limit_s": 11e-6}, {"gain_lower": .4}, {"gain_upper": 2.1},
    {"minimum_source_correlation": .79}, {"maximum_normalized_fit_rms": .31},
    {"maximum_identifiability_condition": 10001}, {"sigma_floor": .019},
    {"maximum_extrapolation_c": 3.1}, {"coarse_grid_size": 40},
    {"coarse_grid_size": 103}, {"maximum_fit_evaluations": 61}, {"fit_stride": True},
])
def test_fit_policy_rejects_invalid_domains_or_relaxed_qualification(values):
    with pytest.raises(ValueError, match="policy"):
        FitPolicy(**values)


def test_fit_policy_and_runtime_model_configuration_are_immutable(transport):
    with pytest.raises(FrozenInstanceError):
        transport.policy.stretch_bound = .1
    assert transport.policy.stretch_bound == .05
    assert transport.to_dict()["fit_policy"] == transport.policy.to_dict()
    assert len(transport.implementation_source_sha256) == 64
    # Old conservative domains remain explicit policies instead of global
    # monkeypatches; a caller cannot make that model accept a wider warp.
    with pytest.raises(ValueError):
        warp_reference(healthy_receiver(TIME), WarpParameters(1.03, 0., 1.), policy=FitPolicy(stretch_bound=.01, coarse_grid_size=21))


def test_same_training_inputs_with_different_policies_have_distinct_model_binding(transport):
    catch, pitch, temperatures = training_fixture()
    with threadpool_limits(limits=1):
        conservative = fit_healthy_transport(catch, pitch, temperatures, policy=FitPolicy(stretch_bound=.01, coarse_grid_size=21))
    assert conservative.training_sha256 == transport.training_sha256
    assert conservative.model_sha256 != transport.model_sha256
    assert conservative.policy.stretch_bound == .01
