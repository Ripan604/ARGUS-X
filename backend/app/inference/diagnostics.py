from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np


@dataclass
class QualityEstimate:
    coupling_quality: float
    placement_quality: float
    signal_quality: float
    repeated_measurement_consistency: float
    spectral_stability: float
    direct_path_energy: float
    clipping_fraction: float
    accepted: bool
    reasons: tuple[str, ...]

    @property
    def evidence_weight(self) -> float:
        if not self.accepted:
            return 0.0
        return float(np.clip(self.signal_quality * np.sqrt(max(self.coupling_quality, 0.0) * max(self.placement_quality, 0.0)), 0, 1))

    def to_dict(self) -> dict:
        return asdict(self)


def estimate_measurement_quality(
    samples: np.ndarray,
    reference: np.ndarray | None = None,
    *,
    acceleration_rms: float | None = None,
    visual_position_error: float | None = None,
) -> QualityEstimate:
    values = np.asarray(samples, dtype=np.float64).reshape(-1)
    finite_fraction = float(np.mean(np.isfinite(values))) if values.size else 0.0
    values = np.nan_to_num(values)
    peak = float(np.max(np.abs(values))) if values.size else 0.0
    rms = float(np.sqrt(np.mean(values**2))) if values.size else 0.0
    if peak > 0:
        plateau = float(np.mean(np.isclose(np.abs(values), peak, rtol=1e-5, atol=max(1e-7, peak * 1e-6))))
        clipping = plateau if peak >= 0.98 or plateau >= 0.02 else 0.0
    else:
        clipping = 0.0
    direct_window = values[: max(8, len(values) // 4)]
    direct_energy = float(np.sqrt(np.mean(direct_window**2))) if direct_window.size else 0.0
    dynamic_quality = float(np.clip((rms - 1e-4) / 0.035, 0, 1))
    clipping_quality = float(np.clip(1.0 - clipping / 0.12, 0, 1))
    signal_quality = float(np.clip(0.55 * dynamic_quality + 0.35 * clipping_quality + 0.10 * finite_fraction, 0, 1))
    consistency, spectral_stability = 0.70, 0.70
    if reference is not None:
        prior = np.asarray(reference, dtype=np.float64).reshape(-1)
        common = min(len(prior), len(values))
        if common >= 16 and np.std(prior[:common]) > 1e-12 and np.std(values[:common]) > 1e-12:
            consistency = float(np.clip((np.corrcoef(prior[:common], values[:common])[0, 1] + 1) / 2, 0, 1))
            a, b = np.abs(np.fft.rfft(prior[:common])), np.abs(np.fft.rfft(values[:common]))
            spectral_stability = float(np.clip(1 - np.mean(np.abs(a / (np.linalg.norm(a) + 1e-12) - b / (np.linalg.norm(b) + 1e-12))), 0, 1))
    motion_quality = 1.0 if acceleration_rms is None else float(np.exp(-3.0 * max(0.0, acceleration_rms)))
    visual_quality = 1.0 if visual_position_error is None else float(np.exp(-8.0 * max(0.0, visual_position_error)))
    placement = float(np.clip(np.sqrt(motion_quality * visual_quality), 0, 1))
    coupling = float(np.clip(0.45 * consistency + 0.30 * spectral_stability + 0.25 * np.clip(direct_energy / 0.06, 0, 1), 0, 1))
    reasons: list[str] = []
    if finite_fraction < 1:
        reasons.append("non_finite_samples")
    if clipping > 0.12:
        reasons.append("clipping")
    if rms < 1e-5:
        reasons.append("sensor_dropout_or_silence")
    if placement < 0.25:
        reasons.append("placement_motion")
    accepted = finite_fraction >= 0.98 and clipping <= 0.20 and rms >= 1e-6
    return QualityEstimate(coupling, placement, signal_quality, consistency, spectral_stability, direct_energy, clipping, accepted, tuple(reasons))
