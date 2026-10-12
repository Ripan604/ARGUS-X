"""Healthy-only native-wave nuisance transport, never fitted to a test catch.

Affine baseline stretch and phase/delay compensation are established methods.
This bounded implementation is an experimental approximation, not a calibrated
physical propagation model or a certificate that an observation is healthy.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import math

import numpy as np
from scipy.optimize import least_squares
from scipy.signal import correlate, correlation_lags

NATIVE_RATE = 10000000
NATIVE_SAMPLES = 13108
MAX_PATHS = 66
SCALE_LIMIT = .01
DELAY_LIMIT_S = 10e-6
GAIN_BOUNDS = (.5, 2.)
PITCH_WINDOW_US = 250.
MIN_SOURCE_CORRELATION = .80
MAX_NORMALIZED_FIT_RMS = .30
MAX_IDENTIFIABILITY_CONDITION = 10000.
MAX_EXTRAPOLATION_C = 3.
SIGMA_FLOOR = .02
FIT_STRIDE = 4
COARSE_GRID_SIZE = 21
MAX_FIT_EVALUATIONS = 60


def transport_configuration() -> dict:
    return {"native_rate_hz": NATIVE_RATE, "native_samples": NATIVE_SAMPLES,
            "scale_limit": SCALE_LIMIT, "delay_limit_s": DELAY_LIMIT_S, "gain_bounds": list(GAIN_BOUNDS),
            "pitch_window_us": PITCH_WINDOW_US, "minimum_signed_source_correlation": MIN_SOURCE_CORRELATION,
            "maximum_normalized_fit_rms": MAX_NORMALIZED_FIT_RMS,
            "maximum_identifiability_condition": MAX_IDENTIFIABILITY_CONDITION,
            "maximum_temperature_extrapolation_c": MAX_EXTRAPOLATION_C,
            "sigma_floor": SIGMA_FLOOR, "fit_stride": FIT_STRIDE,
            "coarse_grid_size": COARSE_GRID_SIZE, "maximum_fit_evaluations": MAX_FIT_EVALUATIONS}


def _immutable(values: np.ndarray) -> np.ndarray:
    values = np.ascontiguousarray(values)
    return np.frombuffer(values.tobytes(), dtype=values.dtype).reshape(values.shape)


def _wave(values: np.ndarray) -> np.ndarray:
    values = np.asarray(values)
    if (values.shape != (NATIVE_SAMPLES,) or values.dtype.kind not in "iuf"
            or not np.isfinite(values).all() or np.max(np.abs(values)) > 1e12):
        raise ValueError("A finite complete native 13108-sample numeric waveform is required")
    values = values.astype(np.float64)
    values -= values.mean()
    if np.linalg.norm(values) < 1e-12:
        raise ValueError("Zero-energy native waveform")
    return values


def _temperature(value) -> float:
    values = np.asarray(value)
    if values.shape not in {(), (2,)} or values.dtype.kind not in "iuf" or not np.isfinite(values).all():
        raise ValueError("Actual surface temperature must be a finite scalar or two sensor values")
    if np.any(values < 15) or np.any(values > 70):
        raise ValueError("Surface temperatures are outside the declared experimental domain")
    return float(values.mean())


def _di(reference: np.ndarray, observation: np.ndarray) -> float:
    a = reference - reference.mean(); b = observation - observation.mean()
    denominator = float(np.linalg.norm(a) * np.linalg.norm(b))
    if not math.isfinite(denominator) or denominator < 1e-12:
        raise ValueError("Zero-energy or invalid predicted/observed catch")
    return float(np.clip(1 - abs(float(np.dot(a, b) / denominator)), 0, 1))


@dataclass(frozen=True)
class SourceAlignment:
    delay_s: float
    signed_correlation: float
    amplitude_ratio: float
    at_bound: bool
    supported: bool


def source_alignment(reference_pitch: np.ndarray, observed_pitch: np.ndarray) -> SourceAlignment:
    """Positive delay means the newly recorded electrical source occurred later."""
    reference = _wave(reference_pitch); observed = _wave(observed_pitch)
    window = round(PITCH_WINDOW_US * 1e-6 * NATIVE_RATE)
    a = reference[:window] - reference[:window].mean()
    b = observed[:window] - observed[:window].mean()
    energies = float(np.linalg.norm(a)), float(np.linalg.norm(b))
    if min(energies) < 1e-12:
        raise ValueError("Pitch has no energy in the fixed excitation window")
    correlation = correlate(b, a, mode="full", method="fft")
    lags = correlation_lags(len(b), len(a), mode="full")
    selected = np.flatnonzero(np.abs(lags) <= round(DELAY_LIMIT_S * NATIVE_RATE))
    winner = int(selected[int(np.argmax(correlation[selected]))])
    at_bound = winner in {int(selected[0]), int(selected[-1])}
    fraction = 0.
    if not at_bound:
        left, middle, right = correlation[winner - 1:winner + 2]
        curvature = float(left - 2 * middle + right)
        if abs(curvature) > 1e-12:
            fraction = float(np.clip(.5 * (left - right) / curvature, -.5, .5))
    delay = float((lags[winner] + fraction) / NATIVE_RATE)
    t = np.arange(window) / NATIVE_RATE
    prediction = np.interp(t - delay, np.arange(NATIVE_SAMPLES) / NATIVE_RATE, reference, left=0., right=0.)
    prediction -= prediction.mean()
    denominator = float(np.linalg.norm(prediction) * np.linalg.norm(b))
    signed = float(np.dot(prediction, b) / denominator) if denominator > 1e-12 else 0.
    return SourceAlignment(delay, signed, energies[1] / energies[0], at_bound,
                           not at_bound and signed >= MIN_SOURCE_CORRELATION)


@dataclass(frozen=True)
class WarpParameters:
    scale: float
    delay_s: float
    gain: float


@dataclass(frozen=True)
class WarpFit:
    parameters: WarpParameters
    normalized_rms: float
    damage_index: float
    jacobian_condition: float | None
    at_parameter_bound: bool
    identifiable: bool
    supported: bool
    evaluations: int


def warp_reference(reference: np.ndarray, parameters: WarpParameters, *, source_delay_s: float = 0.) -> np.ndarray:
    reference = _wave(reference)
    if (not np.isfinite([parameters.scale, parameters.delay_s, parameters.gain, source_delay_s]).all()
            or not 1-SCALE_LIMIT <= parameters.scale <= 1+SCALE_LIMIT
            or abs(parameters.delay_s) > DELAY_LIMIT_S + 1e-15
            or not GAIN_BOUNDS[0] <= parameters.gain <= GAIN_BOUNDS[1]
            or abs(source_delay_s) > DELAY_LIMIT_S + 1e-15):
        raise ValueError("Reference warp exceeds the frozen physical approximation bounds")
    t = np.arange(NATIVE_SAMPLES) / NATIVE_RATE
    return parameters.gain * np.interp((t - source_delay_s - parameters.delay_s) / parameters.scale,
                                      t, reference, left=0., right=0.)


def fit_path_warp(reference: np.ndarray, healthy_observation: np.ndarray) -> WarpFit:
    """Bounded fit of a HEALTHY receiver waveform; never called on a test catch."""
    reference = _wave(reference); target = _wave(healthy_observation)
    t = np.arange(NATIVE_SAMPLES) / NATIVE_RATE
    chosen = np.arange(0, NATIVE_SAMPLES, FIT_STRIDE)
    selected_t = t[chosen]; y = target[chosen]
    rms = float(np.sqrt(np.mean(y*y)))

    def predict(coordinates):
        scale = 1 + SCALE_LIMIT * coordinates[0]
        delay = DELAY_LIMIT_S * coordinates[1]
        candidate = np.interp((selected_t - delay)/scale, t, reference, left=0., right=0.)
        gain = float(np.clip(np.dot(candidate, y)/max(float(np.dot(candidate, candidate)), 1e-300), *GAIN_BOUNDS))
        return gain * candidate, gain

    def residual(coordinates):
        predicted, _ = predict(coordinates)
        return (predicted - y)/max(rms, 1e-12)

    best = None
    for stretch in np.linspace(-1, 1, COARSE_GRID_SIZE):
        for delay in np.linspace(-1, 1, COARSE_GRID_SIZE):
            error = float(np.mean(residual([stretch, delay])**2))
            if best is None or error < best[0]:
                best = (error, np.array([stretch, delay]))
    initial = np.clip(best[1], -.999999, .999999)
    optimized = least_squares(residual, initial, bounds=([-1., -1.], [1., 1.]),
                              max_nfev=MAX_FIT_EVALUATIONS, ftol=1e-9, xtol=1e-9, gtol=1e-9)
    coordinates = optimized.x
    _, gain = predict(coordinates)
    parameters = WarpParameters(float(1 + SCALE_LIMIT*coordinates[0]), float(DELAY_LIMIT_S*coordinates[1]), gain)
    prediction = warp_reference(reference, parameters)
    normalized_rms = float(np.linalg.norm(target - prediction)/np.linalg.norm(target))
    singular = np.linalg.svd(optimized.jac, compute_uv=False)
    condition = float(singular[0]/singular[-1]) if singular[-1] > 1e-12 else math.inf
    identifiable = math.isfinite(condition) and condition <= MAX_IDENTIFIABILITY_CONDITION
    at_bound = bool(np.any(np.abs(coordinates) >= .999) or gain <= GAIN_BOUNDS[0]+1e-6 or gain >= GAIN_BOUNDS[1]-1e-6)
    supported = bool(optimized.success and identifiable and not at_bound and normalized_rms <= MAX_NORMALIZED_FIT_RMS)
    return WarpFit(parameters, normalized_rms, _di(prediction, target), condition if math.isfinite(condition) else None,
                   at_bound, identifiable, supported, int(optimized.nfev))


def _parameters_at(temperatures: np.ndarray, values: np.ndarray, target: float) -> np.ndarray:
    # Piecewise interpolation plus explicitly bounded edge extrapolation.
    if target < temperatures[0]:
        lower, upper = 0, 1
    elif target > temperatures[-1]:
        lower, upper = len(temperatures)-2, len(temperatures)-1
    else:
        upper = min(len(temperatures)-1, max(1, int(np.searchsorted(temperatures, target))))
        lower = upper-1
    fraction = (target-temperatures[lower])/(temperatures[upper]-temperatures[lower])
    return values[lower] + fraction*(values[upper]-values[lower])


@dataclass(frozen=True)
class ReferencePrediction:
    reference: np.ndarray
    parameters: WarpParameters
    source: SourceAlignment
    surface_temperature_c: float
    extrapolated: bool
    supported: bool
    rejection_reasons: tuple[str, ...]
    outside_template_samples: int

    def diagnostics(self) -> dict:
        return {"parameters": asdict(self.parameters), "source_alignment": asdict(self.source),
                "surface_temperature_c": self.surface_temperature_c, "extrapolated": self.extrapolated,
                "supported": self.supported, "rejection_reasons": list(self.rejection_reasons),
                "outside_template_samples": self.outside_template_samples}


@dataclass(frozen=True)
class TransportObservation:
    damage_index: float
    healthy_sigma_path: float
    normalized_rms_residual: float
    prediction: ReferencePrediction


@dataclass(frozen=True)
class HealthyWaveTransport:
    temperatures_c: np.ndarray
    receiver_reference: np.ndarray
    pitch_reference: np.ndarray
    parameter_anchors: np.ndarray  # anchor,path,(scale,delay,gain)
    supported_anchors: np.ndarray
    healthy_sigma: np.ndarray
    development_damage_index: np.ndarray
    fits: tuple[tuple[WarpFit, ...], ...]
    training_sha256: str
    model_sha256: str

    def predict_reference(self, path_index: int, surface_temperature_c,
                          observed_pitch: np.ndarray) -> ReferencePrediction:
        if isinstance(path_index, bool) or not isinstance(path_index, (int, np.integer)) or not 0 <= path_index < len(self.healthy_sigma):
            raise ValueError("Unknown recorded path index")
        target = _temperature(surface_temperature_c)
        source = source_alignment(self.pitch_reference[path_index], observed_pitch)
        values = _parameters_at(self.temperatures_c, self.parameter_anchors[:, path_index], target)
        parameters = WarpParameters(*map(float, values))
        reasons = []
        excursion = max(float(self.temperatures_c[0]-target), float(target-self.temperatures_c[-1]), 0.)
        if excursion > MAX_EXTRAPOLATION_C:
            reasons.append("surface_temperature_outside_qualified_extrapolation")
        if not source.supported:
            reasons.append("source_clock_alignment_not_supported")
        if not self.supported_anchors[:, path_index].all():
            reasons.append("healthy_receiver_warp_not_identifiable_or_supported")
        # Predict at a bounded parameter value while preserving the rejection;
        # unsupported predictions must not update the downstream damage model.
        if (not 1-SCALE_LIMIT <= parameters.scale <= 1+SCALE_LIMIT
                or abs(parameters.delay_s) > DELAY_LIMIT_S or not GAIN_BOUNDS[0] <= parameters.gain <= GAIN_BOUNDS[1]):
            reasons.append("interpolated_warp_outside_parameter_domain")
            parameters = WarpParameters(float(np.clip(parameters.scale, 1-SCALE_LIMIT, 1+SCALE_LIMIT)),
                float(np.clip(parameters.delay_s, -DELAY_LIMIT_S, DELAY_LIMIT_S)), float(np.clip(parameters.gain, *GAIN_BOUNDS)))
        reference = _immutable(warp_reference(self.receiver_reference[path_index], parameters, source_delay_s=source.delay_s))
        t = np.arange(NATIVE_SAMPLES)/NATIVE_RATE
        query = (t-source.delay_s-parameters.delay_s)/parameters.scale
        outside = int(np.count_nonzero((query < 0) | (query > t[-1])))
        return ReferencePrediction(reference, parameters, source, target, excursion > 0., not reasons, tuple(reasons), outside)

    def observe(self, path_index: int, surface_temperature_c, observed_pitch: np.ndarray,
                observed_catch: np.ndarray) -> TransportObservation:
        # The reference is created before catch validation/comparison and has
        # no test-catch argument. Catch cannot alter any fitted/predicted warp.
        prediction = self.predict_reference(path_index, surface_temperature_c, observed_pitch)
        observed = _wave(observed_catch)
        residual = float(np.linalg.norm(observed-prediction.reference)/np.linalg.norm(prediction.reference))
        return TransportObservation(_di(prediction.reference, observed), float(self.healthy_sigma[path_index]), residual, prediction)

    def to_dict(self) -> dict:
        return {"method": "healthy-only bounded affine baseline stretch plus queried electrical-source alignment",
                "native_sample_rate_hz": NATIVE_RATE, "sample_count": NATIVE_SAMPLES,
                "path_count": len(self.healthy_sigma), "temperature_means_c": self.temperatures_c.tolist(),
                "parameter_anchors": self.parameter_anchors.tolist(), "supported_anchors": self.supported_anchors.tolist(),
                "healthy_sigma": self.healthy_sigma.tolist(), "development_damage_index": self.development_damage_index.tolist(),
                "fits": [[asdict(fit) for fit in anchor] for anchor in self.fits],
                "training_sha256": self.training_sha256, "model_sha256": self.model_sha256,
                "frozen_configuration": transport_configuration(),
                "sigma_is_residual_proxy_not_independent_noise_estimate": True,
                "test_catch_used_to_fit": False, "physical_bench_validation_performed": False}


def fit_healthy_transport(healthy_catch: np.ndarray, healthy_pitch: np.ndarray,
                         surface_temperatures_c: np.ndarray) -> HealthyWaveTransport:
    catch = np.asarray(healthy_catch); pitch = np.asarray(healthy_pitch); surfaces = np.asarray(surface_temperatures_c)
    if (catch.ndim != 3 or catch.shape[0] != 3 or not 1 <= catch.shape[1] <= MAX_PATHS
            or catch.shape[2] != NATIVE_SAMPLES or pitch.shape != catch.shape
            or surfaces.shape != (3, 2) or catch.dtype.kind not in "iuf" or pitch.dtype.kind not in "iuf"
            or not np.isfinite(catch).all() or not np.isfinite(pitch).all()):
        raise ValueError("Three complete healthy native catch/pitch anchors and two surface temperatures are required")
    temperatures = np.array([_temperature(row) for row in surfaces])
    if np.any(np.diff(temperatures) < 1):
        raise ValueError("Healthy surface-temperature anchors must be ordered, separated and unique")
    count = catch.shape[1]
    receivers = np.array([_wave(wave) for wave in catch[0]])
    sources = np.array([_wave(wave) for wave in pitch[0]])
    anchors = np.zeros((3, count, 3)); anchors[:, :, 0] = 1.; anchors[:, :, 2] = 1.
    supported = np.ones((3, count), dtype=bool)
    fits = [[WarpFit(WarpParameters(1., 0., 1.), 0., 0., None, False, True, True, 0) for _ in range(count)]]
    for temperature_index in (1, 2):
        current = []
        for path_index in range(count):
            source = source_alignment(sources[path_index], pitch[temperature_index, path_index])
            wave = _wave(catch[temperature_index, path_index])
            t = np.arange(NATIVE_SAMPLES)/NATIVE_RATE
            aligned = np.interp(t+source.delay_s, t, wave, left=0., right=0.)
            fit = fit_path_warp(receivers[path_index], aligned)
            anchors[temperature_index, path_index] = [fit.parameters.scale, fit.parameters.delay_s, fit.parameters.gain]
            supported[temperature_index, path_index] = fit.supported and source.supported
            current.append(fit)
        fits.append(current)
    development = np.empty(count)
    for path_index in range(count):
        # Pure healthy leave-middle-temperature-out check: no middle receiver
        # is used to estimate the endpoint interpolation being evaluated.
        values = _parameters_at(temperatures[[0, 2]], anchors[[0, 2], path_index], float(temperatures[1]))
        source = source_alignment(sources[path_index], pitch[1, path_index])
        prediction = warp_reference(receivers[path_index], WarpParameters(*map(float, values)), source_delay_s=source.delay_s)
        development[path_index] = _di(prediction, _wave(catch[1, path_index]))
    sigma = np.maximum(SIGMA_FLOOR, development)
    training_hash = hashlib.sha256()
    for array in (catch, pitch, surfaces):
        training_hash.update(np.ascontiguousarray(array, dtype="<f8").tobytes())
    training_sha = training_hash.hexdigest()
    identity = {"training_sha256": training_sha, "parameters": anchors.tolist(), "supported": supported.tolist(),
                "sigma": sigma.tolist(), "temperatures": temperatures.tolist(), "sample_rate": NATIVE_RATE,
                "configuration": transport_configuration()}
    model_sha = hashlib.sha256(json.dumps(identity, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()
    return HealthyWaveTransport(_immutable(temperatures), _immutable(receivers), _immutable(sources),
        _immutable(anchors), _immutable(supported), _immutable(sigma), _immutable(development),
        tuple(tuple(anchor) for anchor in fits), training_sha, model_sha)
