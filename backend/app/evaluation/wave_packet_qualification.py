"""Healthy-reference qualification for experimental wave-packet images.

This is an acquisition/model consistency guard, not a damage detector. Its
relative energy limits are declared development assumptions, not field limits.
"""
from dataclasses import asdict, dataclass

import numpy as np

from backend.app.evaluation.wave_packet_imaging import PacketCalibration, SAMPLES, _filter, _wave

MIN_ENERGY_RATIO, MAX_ENERGY_RATIO = .1, 10.


@dataclass(frozen=True)
class PacketReferenceQualification:
    supported: bool
    baseline_index: int
    eligible_indices: tuple[int, ...]
    energy_ratios: tuple[float, ...]
    low_energy_indices: tuple[int, ...]
    high_energy_indices: tuple[int, ...]
    model_rejected_indices: tuple[int, ...]
    rejection_reasons: tuple[str, ...]

    def to_dict(self) -> dict:
        return {**asdict(self), "minimum_relative_energy": MIN_ENERGY_RATIO,
                "maximum_relative_energy": MAX_ENERGY_RATIO,
                "scale": "bandlimited_receiver_norm_divided_by_source_norm",
                "anchor_reference": "median_of_three_declared_healthy_anchors_per_path",
                "healthy_anchor_count": 3, "damaged_response_used": False,
                "qualification_is_damage_detection": False,
                "limits_are_field_validated": False}


def qualify_packet_reference(healthy_catch_stack: np.ndarray, healthy_pitch_stack: np.ndarray,
                             baseline_index: int, calibration: PacketCalibration) -> PacketReferenceQualification:
    """Require a model-consistent path and a non-anomalous healthy reference.

    Only known healthy catches and their captured electrical sources enter this
    operation. Source-normalized energy distinguishes a near-dropout baseline
    from its same-path anchors without comparing a test receiver to a threshold.
    """
    if type(baseline_index) is not int or baseline_index not in (0, 1, 2):
        raise ValueError("An exact index into three declared healthy anchors is required")
    if not isinstance(calibration, PacketCalibration):
        raise ValueError("A healthy-only packet calibration is required")
    catch = _filter(_wave(healthy_catch_stack, (3, 66, SAMPLES)))
    pitch = _filter(_wave(healthy_pitch_stack, (3, 66, SAMPLES)))
    catch_energy, pitch_energy = np.linalg.norm(catch, axis=-1), np.linalg.norm(pitch, axis=-1)
    if np.any(pitch_energy < 1e-12):
        raise ValueError("Healthy source has no energy within the declared packet band")
    levels = catch_energy / pitch_energy
    median = np.median(levels, axis=0)
    if np.any(median < 1e-12):
        raise ValueError("Healthy reference path lacks a usable energy scale")
    ratios = levels[baseline_index] / median
    energy_ok = (ratios >= MIN_ENERGY_RATIO) & (ratios <= MAX_ENERGY_RATIO)
    model_ok = np.zeros(66, dtype=bool)
    model_ok[list(calibration.inlier_indices)] = calibration.supported
    eligible = np.flatnonzero(energy_ok & model_ok)
    reasons = []
    if not calibration.supported:
        reasons.append("Healthy packet propagation calibration is unsupported")
    if len(eligible) < 12:
        reasons.append("Fewer than twelve reference-qualified recorded paths remain")
    indices = lambda mask: tuple(int(i) for i in np.flatnonzero(mask))
    return PacketReferenceQualification(not reasons, baseline_index, tuple(int(i) for i in eligible),
        tuple(float(value) for value in ratios), indices(ratios < MIN_ENERGY_RATIO),
        indices(ratios > MAX_ENERGY_RATIO), indices(~model_ok), tuple(reasons))
