import itertools

import numpy as np
import pytest

from backend.app.evaluation.measured_guided_waves import SENSORS, grid_points
from backend.app.evaluation.wave_packet_imaging import (
    RATE, SAMPLES, fit_packet_model, image_summary, residual_path_image, travel_time_us,
)


def packet(t, center, width=22e-6):
    return np.exp(-.5 * ((t - center) / width) ** 2) * np.cos(2 * np.pi * 40000 * (t - center))


@pytest.fixture(scope="module")
def healthy_packets():
    t = np.arange(SAMPLES) / RATE
    pairs = np.array(list(itertools.combinations(range(12), 2)))
    pitch = np.broadcast_to(packet(t, 80e-6), (66, SAMPLES)).copy()
    vectors = SENSORS[pairs[:, 1]] - SENSORS[pairs[:, 0]]
    distances = np.linalg.norm(vectors, axis=1)
    # A known independently constructed propagation scenario, not recorded data.
    catch = np.array([packet(t, 80e-6 + 8e-6 + distance / 1200) for distance in distances])
    fit = fit_packet_model(catch, pitch, pairs)
    return t, pairs, catch, pitch, fit


def test_healthy_only_delay_fit_recovers_known_clock_offset_and_packet_speed(healthy_packets):
    _, pairs, _, _, fit = healthy_packets
    assert fit.supported and len(fit.inlier_indices) >= 33
    assert fit.coefficients_us_per_m[0] == pytest.approx(1e6 / 1200, abs=.5)
    assert fit.delay_us == pytest.approx(8, abs=.2)
    distances = np.linalg.norm(SENSORS[pairs[:, 1]] - SENSORS[pairs[:, 0]], axis=1)
    assert all(distances[i] >= .24 - 1e-12 for i in fit.inlier_indices)
    assert all(fit.arrival_lags_us[i] is None for i in np.flatnonzero(distances < .24 - 1e-12))


def test_directional_delay_is_reciprocal_and_recovers_a_known_synthetic_scenario(healthy_packets):
    t, pairs, _, pitch, _ = healthy_packets
    vectors = SENSORS[pairs[:, 1]] - SENSORS[pairs[:, 0]]
    angles = np.arctan2(vectors[:, 1], vectors[:, 0])
    delays = np.linalg.norm(vectors, axis=1) * (850 + 35 * np.cos(2 * angles) - 20 * np.sin(2 * angles))
    catch = np.array([packet(t, (80 + 6 + delay) * 1e-6) for delay in delays])
    fit = fit_packet_model(catch, pitch, pairs, directional=True)
    assert fit.supported
    assert fit.coefficients_us_per_m == pytest.approx((850, 35, -20), abs=1)
    assert fit.delay_us == pytest.approx(6, abs=.3)
    np.testing.assert_allclose(travel_time_us(vectors, fit), travel_time_us(-vectors, fit))


def test_zero_residual_does_not_invent_a_location_or_a_damage_decision(healthy_packets):
    _, pairs, catch, pitch, fit = healthy_packets
    points = grid_points()
    scores = residual_path_image(catch[5], catch[5], pitch[5], *SENSORS[pairs[5]], points, fit)
    assert np.max(scores) == 0
    summary = image_summary(scores, points)
    assert summary["map_m"] is None and summary["flat_image"]
    assert summary["damage_detection_supported"] is False
    assert summary["scores_are_probabilities"] is False


def test_time_resolved_imaging_localizes_a_synthetic_scattering_packet(healthy_packets):
    t, pairs, catch, pitch, fit = healthy_packets
    truth = np.array([.195, .325])
    points = grid_points()
    scores = np.zeros(len(points))
    for i, pair in enumerate(pairs):
        start, end = SENSORS[pair]
        scatter_delay = (np.linalg.norm(start - truth) + np.linalg.norm(end - truth)) / 1200 + 8e-6
        observed = catch[i] + .2 * packet(t, 80e-6 + scatter_delay)
        scores += residual_path_image(catch[i], observed, pitch[i], start, end, points, fit)
    summary = image_summary(scores, points)
    assert np.linalg.norm(np.array(summary["map_m"]) - truth) < .015
    assert summary["scores_are_probabilities"] is False


def test_nonidentifiable_healthy_observations_are_withheld(healthy_packets):
    t, pairs, _, pitch, _ = healthy_packets
    catch = np.broadcast_to(packet(t, 300e-6), (66, SAMPLES)).copy()
    fit = fit_packet_model(catch, pitch, pairs, directional=True)
    assert not fit.supported and fit.rejection_reasons
    with pytest.raises(ValueError, match="Qualified"):
        residual_path_image(catch[5], catch[5], pitch[5], *SENSORS[pairs[5]], grid_points(), fit)


def test_native_input_contract_refuses_partial_or_nonfinite_records(healthy_packets):
    _, pairs, catch, pitch, _ = healthy_packets
    with pytest.raises(ValueError, match="Complete"):
        fit_packet_model(catch[:, :-1], pitch, pairs)
    invalid = catch.copy()
    invalid[0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        fit_packet_model(invalid, pitch, pairs)
    duplicate = pairs.copy()
    duplicate[-1] = duplicate[0]
    with pytest.raises(ValueError, match="distinct"):
        fit_packet_model(catch, pitch, duplicate)


def test_minimum_signed_integer_cannot_bypass_waveform_amplitude_bound(healthy_packets):
    _, pairs, _, pitch, _ = healthy_packets
    invalid = np.zeros((66, SAMPLES), dtype=np.int64)
    invalid[0, 0] = np.iinfo(np.int64).min
    with pytest.raises(ValueError, match="finite"):
        fit_packet_model(invalid, pitch, pairs)


def test_imaging_refuses_outside_panel_points_and_identical_endpoints(healthy_packets):
    _, pairs, catch, pitch, fit = healthy_packets
    with pytest.raises(ValueError, match="within"):
        residual_path_image(catch[5], catch[5], pitch[5], *SENSORS[pairs[5]], np.array([[.6, .2]]), fit)
    with pytest.raises(ValueError, match="Distinct"):
        residual_path_image(catch[5], catch[5], pitch[5], SENSORS[0], SENSORS[0], grid_points(), fit)


@pytest.mark.parametrize("scores", [np.array([-1., 2.]), np.array([np.nan, 2.]), np.array([np.inf, 2.])])
def test_invalid_image_cannot_generate_a_readout(scores):
    with pytest.raises(ValueError, match="Finite"):
        image_summary(scores, np.array([[.1, .2], [.3, .4]]))
