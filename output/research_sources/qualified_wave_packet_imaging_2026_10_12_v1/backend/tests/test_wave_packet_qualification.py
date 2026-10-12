import numpy as np
import pytest

from backend.app.evaluation.wave_packet_imaging import PacketCalibration, SAMPLES
from backend.app.evaluation.wave_packet_qualification import qualify_packet_reference


def anchors():
    t = np.arange(SAMPLES) / 10_000_000
    wave = np.exp(-.5 * ((t - 300e-6) / 22e-6) ** 2) * np.cos(2 * np.pi * 40000 * t)
    # Deliberately varied receiver scale does not create an arbitrary per-path
    # amplitude threshold: comparison is within each path across healthy anchors.
    catch = np.broadcast_to(wave, (3, 66, SAMPLES)).copy()
    catch *= np.linspace(.01, 10, 66)[None, :, None]
    pitch = np.broadcast_to(wave, (3, 66, SAMPLES)).copy()
    calibration = PacketCalibration((850., 0., 0.), 0., False, True,
        tuple(range(66)), (200.,) * 66, (0.,) * 66, 0., 10., ())
    return catch, pitch, calibration


def test_healthy_reference_near_dropout_is_rejected_using_same_path_anchors():
    catch, pitch, model = anchors()
    catch[1, 60] *= .0032
    quality = qualify_packet_reference(catch, pitch, 1, model)
    assert quality.supported and quality.low_energy_indices == (60,)
    assert 60 not in quality.eligible_indices
    assert quality.energy_ratios[60] == pytest.approx(.0032, rel=1e-5)
    # A naturally low-amplitude path still qualifies when its anchors agree.
    assert 0 in quality.eligible_indices


def test_source_and_receiver_gain_change_does_not_look_like_a_receiver_dropout():
    catch, pitch, model = anchors()
    catch[1] *= .4
    pitch[1] *= .4
    quality = qualify_packet_reference(catch, pitch, 1, model)
    assert quality.eligible_indices == tuple(range(66))
    assert quality.energy_ratios == pytest.approx((1.,) * 66)


def test_model_rejected_paths_cannot_reenter_through_healthy_energy():
    catch, pitch, model = anchors()
    model = PacketCalibration(model.coefficients_us_per_m, model.delay_us, False, True,
        tuple(range(33)), model.arrival_lags_us, model.residuals_us, 0., 10., ())
    quality = qualify_packet_reference(catch, pitch, 0, model)
    assert quality.eligible_indices == tuple(range(33))
    assert quality.model_rejected_indices == tuple(range(33, 66))


def test_many_failed_reference_paths_withhold_the_branch():
    catch, pitch, model = anchors()
    catch[1, :60] *= .01
    quality = qualify_packet_reference(catch, pitch, 1, model)
    assert not quality.supported and len(quality.eligible_indices) == 6
    assert quality.rejection_reasons


@pytest.mark.parametrize("index", [True, 3, -1, 1.0])
def test_invalid_anchor_identity_cannot_silently_select_a_reference(index):
    catch, pitch, model = anchors()
    with pytest.raises(ValueError, match="exact index"):
        qualify_packet_reference(catch, pitch, index, model)


def test_partial_anchor_coverage_is_rejected():
    catch, pitch, model = anchors()
    with pytest.raises(ValueError, match="Complete"):
        qualify_packet_reference(catch[:2], pitch[:2], 0, model)
