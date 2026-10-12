"""Experimental healthy-calibrated, time-resolved guided-wave imaging.

Delay-and-sum and direction-dependent group-delay fitting are established ideas.
This approximation isolates what the scalar damage-index model discards. Its
intensities are neither defect probabilities nor permission to release a panel.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import numpy as np
from scipy.optimize import least_squares
from scipy.signal import butter, correlate, correlation_lags, find_peaks, hilbert, sosfiltfilt

from backend.app.evaluation.measured_guided_waves import SENSORS

RATE = 10_000_000
SAMPLES = 13_108
LOW_HZ, HIGH_HZ = 20_000, 60_000
SPEED_BOUNDS_M_S = (600., 2500.)
PACKET_RELATIVE_HEIGHT = .5
MAX_RESIDUAL_US = 25.  # One cycle at the recorded 40 kHz excitation.
MAX_DELAY_US = 25.
MIN_INLIERS = 12
MIN_CALIBRATION_DISTANCE_M = .24
MIN_PACKET_LAG_US = 62.5  # Half the five-cycle source burst, not a known mode boundary.


def packet_configuration() -> dict:
    return {"sample_rate_hz": RATE, "sample_count": SAMPLES,
            "bandpass_hz": [LOW_HZ, HIGH_HZ], "filter_order": 4,
            "speed_bounds_m_s": list(SPEED_BOUNDS_M_S),
            "first_packet_relative_height": PACKET_RELATIVE_HEIGHT,
            "maximum_fit_residual_us": MAX_RESIDUAL_US,
            "maximum_instrument_delay_us": MAX_DELAY_US,
            "minimum_inlier_paths": MIN_INLIERS, "minimum_inlier_fraction": .5,
            "minimum_calibration_distance_m": MIN_CALIBRATION_DISTANCE_M,
            "minimum_packet_lag_us": MIN_PACKET_LAG_US,
            "fit_uses_damage_labels": False, "scores_are_probabilities": False}


def _wave(values: np.ndarray, shape: tuple[int, ...]) -> np.ndarray:
    a = np.asarray(values)
    if a.shape != shape or a.dtype.kind not in "iuf":
        raise ValueError("Complete finite native numeric waveforms are required")
    a = a.astype(float)
    # Convert before abs: abs(minimum signed integer) overflows in its dtype.
    if not np.isfinite(a).all() or np.max(np.abs(a)) > 1e12:
        raise ValueError("Complete finite native numeric waveforms are required")
    a = a - a.mean(axis=-1, keepdims=True)
    if np.any(np.linalg.norm(a, axis=-1) < 1e-12):
        raise ValueError("Zero-energy native waveform")
    return a


def _filter(values: np.ndarray) -> np.ndarray:
    sos = butter(4, [LOW_HZ, HIGH_HZ], fs=RATE, btype="bandpass", output="sos")
    return sosfiltfilt(sos, values, axis=-1)


def _pairs(values: np.ndarray) -> np.ndarray:
    pairs = np.asarray(values)
    if (pairs.shape != (66, 2) or pairs.dtype.kind not in "iu"
            or np.any(pairs < 0) or np.any(pairs >= len(SENSORS))
            or np.any(pairs[:, 0] >= pairs[:, 1]) or len(np.unique(pairs, axis=0)) != 66):
        raise ValueError("The complete 66 distinct unordered sensor pairs are required")
    return pairs.astype(int)


@dataclass(frozen=True)
class PacketCalibration:
    coefficients_us_per_m: tuple[float, float, float]
    delay_us: float
    directional: bool
    supported: bool
    inlier_indices: tuple[int, ...]
    arrival_lags_us: tuple[float | None, ...]
    residuals_us: tuple[float | None, ...]
    inlier_rmse_us: float | None
    design_condition: float | None
    rejection_reasons: tuple[str, ...]

    def __post_init__(self):
        coefficients = np.asarray(self.coefficients_us_per_m)
        if (type(self.inlier_indices) is not tuple
                or any(type(index) is not int or not 0 <= index < 66 for index in self.inlier_indices)
                or len(set(self.inlier_indices)) != len(self.inlier_indices)):
            raise ValueError("Packet inliers must be distinct exact path indices within [0, 65]")
        if (coefficients.shape != (3,) or not np.isfinite(coefficients).all()
                or not math.isfinite(self.delay_us) or abs(self.delay_us) > MAX_DELAY_US + 1e-8
                or type(self.directional) is not bool or type(self.supported) is not bool):
            raise ValueError("Invalid packet calibration parameters")
        if self.supported:
            lo = coefficients[0] - np.linalg.norm(coefficients[1:])
            hi = coefficients[0] + np.linalg.norm(coefficients[1:])
            if (lo < 1e6 / SPEED_BOUNDS_M_S[1] - 1e-8
                    or hi > 1e6 / SPEED_BOUNDS_M_S[0] + 1e-8
                    or len(self.inlier_indices) < 33 or self.rejection_reasons
                    or self.inlier_rmse_us is None or not 0 <= self.inlier_rmse_us <= MAX_RESIDUAL_US
                    or self.design_condition is None or not 1 <= self.design_condition <= 1000):
                raise ValueError("Supported packet calibration lacks qualification")
        if not self.directional and np.any(coefficients[1:] != 0):
            raise ValueError("Isotropic calibration cannot carry directional coefficients")

    def to_dict(self) -> dict:
        return {**asdict(self), "configuration": packet_configuration(),
                "group_delay_model_is_approximate": True,
                "mode_identity_independently_verified": False}


def _features(vectors: np.ndarray, directional: bool) -> np.ndarray:
    lengths = np.linalg.norm(vectors, axis=-1)
    theta = np.arctan2(vectors[..., 1], vectors[..., 0])
    columns = [lengths]
    if directional:
        columns += [lengths * np.cos(2 * theta), lengths * np.sin(2 * theta)]
    return np.stack([*columns, np.ones_like(lengths)], axis=-1)


def fit_packet_model(reference_catch: np.ndarray, reference_pitch: np.ndarray,
                     pairs: np.ndarray, *, directional: bool = False) -> PacketCalibration:
    """Fit effective packet group delays using a declared healthy bank only.

    Earliest correlation-envelope local peak above half the strongest plausible
    peak is a fixed packet heuristic. Multiple modes/reflections can invalidate
    it; rejected paths and unqualified models remain in the experiment report.
    """
    if type(directional) is not bool:
        raise ValueError("Directional mode must be an explicit boolean")
    pairs = _pairs(pairs)
    catch = _filter(_wave(reference_catch, (66, SAMPLES)))
    pitch = _filter(_wave(reference_pitch, (66, SAMPLES)))
    vectors = SENSORS[pairs[:, 1]] - SENSORS[pairs[:, 0]]
    lengths = np.linalg.norm(vectors, axis=1)
    lags = correlation_lags(SAMPLES, SAMPLES) / RATE
    arrivals = np.full(66, np.nan)
    for i, distance in enumerate(lengths):
        # Short-path packets overlap source/crosstalk. Do not identify speed
        # from them; these paths remain available for imaging comparisons.
        if distance < MIN_CALIBRATION_DISTANCE_M - 1e-12:
            continue
        envelope = np.abs(hilbert(correlate(catch[i], pitch[i], method="fft")))
        plausible = (lags >= max(distance / SPEED_BOUNDS_M_S[1], MIN_PACKET_LAG_US * 1e-6)) & (lags <= distance / SPEED_BOUNDS_M_S[0])
        peaks, _ = find_peaks(envelope)
        peaks = peaks[plausible[peaks]]
        if not len(peaks) or float(envelope[peaks].max()) < 1e-12:
            continue
        selected = int(peaks[envelope[peaks] >= PACKET_RELATIVE_HEIGHT * envelope[peaks].max()][0])
        arrivals[i] = lags[selected] * 1e6
    X = _features(vectors, directional)
    available = np.isfinite(arrivals)
    n_parameters = X.shape[1]
    lower = [1e6 / SPEED_BOUNDS_M_S[1]] + ([-400., -400.] if directional else []) + [-MAX_DELAY_US]
    upper = [1e6 / SPEED_BOUNDS_M_S[0]] + ([400., 400.] if directional else []) + [MAX_DELAY_US]
    initial = np.array([900.] + ([0., 0.] if directional else []) + [0.])
    rejection = []
    inliers = np.zeros(66, dtype=bool)
    residuals = np.full(66, np.nan)
    fitted = initial
    condition, rmse = None, None
    if available.sum() < MIN_INLIERS or np.linalg.matrix_rank(X[available]) < n_parameters:
        rejection.append("Insufficient healthy packet observations or geometry rank")
    else:
        solve = lambda mask, start: least_squares(
            lambda beta: X[mask] @ beta - arrivals[mask], start,
            bounds=(lower, upper), loss="soft_l1", f_scale=MAX_RESIDUAL_US / 2,
            max_nfev=200)
        fit = solve(available, initial)
        fitted = fit.x
        residuals[available] = X[available] @ fitted - arrivals[available]
        inliers = available & (np.abs(residuals) <= MAX_RESIDUAL_US)
        if inliers.sum() >= MIN_INLIERS and np.linalg.matrix_rank(X[inliers]) == n_parameters:
            fit = solve(inliers, fitted)
            fitted = fit.x
            residuals[available] = X[available] @ fitted - arrivals[available]
            inliers = available & (np.abs(residuals) <= MAX_RESIDUAL_US)
        if inliers.sum() < max(MIN_INLIERS, 33):
            rejection.append("Fewer than half of all healthy paths agree within one excitation cycle")
        if inliers.sum() >= n_parameters:
            singular = np.linalg.svd(X[inliers], compute_uv=False)
            condition = float(singular[0] / singular[-1]) if singular[-1] > 1e-12 else None
            rmse = float(np.sqrt(np.mean(residuals[inliers] ** 2)))
        if condition is None or condition > 1000:
            rejection.append("Packet geometry is not identifiable")
        if not fit.success:
            rejection.append("Bounded healthy delay fit did not converge")
        if np.any(np.isclose(fitted, lower, atol=1e-6)) or np.any(np.isclose(fitted, upper, atol=1e-6)):
            rejection.append("Healthy fit reached a declared parameter bound")
    coefficients = (float(fitted[0]), float(fitted[1]) if directional else 0.,
                    float(fitted[2]) if directional else 0.)
    spread = math.hypot(coefficients[1], coefficients[2])
    if (coefficients[0] - spread < 1e6 / SPEED_BOUNDS_M_S[1]
            or coefficients[0] + spread > 1e6 / SPEED_BOUNDS_M_S[0]):
        rejection.append("Directional group-delay model exceeds the speed domain")
    nullable = lambda values: tuple(float(v) if np.isfinite(v) else None for v in values)
    return PacketCalibration(coefficients, float(fitted[-1]), directional, not rejection,
                             tuple(int(i) for i in np.flatnonzero(inliers)), nullable(arrivals),
                             nullable(residuals), rmse, condition, tuple(rejection))


def travel_time_us(vectors: np.ndarray, calibration: PacketCalibration) -> np.ndarray:
    vectors = np.asarray(vectors)
    if (vectors.ndim < 1 or vectors.shape[-1] != 2 or vectors.dtype.kind not in "iuf"
            or not np.isfinite(vectors).all() or np.any(np.abs(vectors) > .5)):
        raise ValueError("Finite panel displacement vectors are required")
    lengths = np.linalg.norm(vectors, axis=-1)
    angle = np.arctan2(vectors[..., 1], vectors[..., 0])
    s0, sc, ss = calibration.coefficients_us_per_m
    return lengths * (s0 + sc * np.cos(2 * angle) + ss * np.sin(2 * angle))


def residual_path_image(reference_path: np.ndarray, observed_path: np.ndarray,
                        pitch_path: np.ndarray, start_xy: np.ndarray, end_xy: np.ndarray,
                        points: np.ndarray, calibration: PacketCalibration) -> np.ndarray:
    """Backproject source-correlated residual envelope; no test waveform fitting."""
    if not isinstance(calibration, PacketCalibration) or not calibration.supported:
        raise ValueError("Qualified healthy-only packet calibration required")
    points, start, end = np.asarray(points), np.asarray(start_xy), np.asarray(end_xy)
    if (points.ndim != 2 or points.shape[1] != 2 or not 1 <= len(points) <= 10000
            or start.shape != (2,) or end.shape != (2,)):
        raise ValueError("Bounded two-dimensional panel geometry required")
    for values in (points, start, end):
        if values.dtype.kind not in "iuf" or not np.isfinite(values).all() or np.any(values < 0) or np.any(values > .5):
            raise ValueError("Panel coordinates must lie within [0, 0.5] metres")
    if np.linalg.norm(start - end) < 1e-12:
        raise ValueError("Distinct source and receiver coordinates required")
    reference = _filter(_wave(reference_path, (SAMPLES,)))
    observed = _filter(_wave(observed_path, (SAMPLES,)))
    pitch = _filter(_wave(pitch_path, (SAMPLES,)))
    norm = float(np.linalg.norm(reference) * np.linalg.norm(pitch))
    if norm < 1e-12:
        raise ValueError("No energy inside the declared packet band")
    residual = observed - reference
    envelope = np.abs(hilbert(correlate(residual, pitch, method="fft"))) / norm
    delays = (calibration.delay_us + travel_time_us(points - start, calibration)
              + travel_time_us(points - end, calibration))
    axis = correlation_lags(SAMPLES, SAMPLES) / RATE * 1e6
    return np.interp(delays, axis, envelope, left=0., right=0.)


def image_summary(scores: np.ndarray, points: np.ndarray) -> dict:
    scores, points = np.asarray(scores), np.asarray(points)
    if (scores.ndim != 1 or points.shape != (len(scores), 2) or not len(scores)
            or scores.dtype.kind not in "iuf" or points.dtype.kind not in "iuf"
            or not np.isfinite(scores).all() or not np.isfinite(points).all()
            or np.any(scores < 0) or np.any(points < 0) or np.any(points > .5)):
        raise ValueError("Finite nonnegative image scores and panel points required")
    flat = bool(np.max(scores) - np.min(scores) <= 1e-12)
    return {"map_m": None if flat else points[int(np.argmax(scores))].tolist(),
            "peak_to_mean": float(np.max(scores) / np.mean(scores)) if np.mean(scores) > 1e-12 else None,
            "flat_image": flat, "scores_are_probabilities": False,
            "damage_detection_supported": False}
