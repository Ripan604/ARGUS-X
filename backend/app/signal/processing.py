from __future__ import annotations

import math

import numpy as np
from scipy.signal import butter, hilbert, sosfiltfilt, spectrogram, welch, windows


def preprocess_signal(
    samples: np.ndarray,
    sample_rate: int,
    bandpass: tuple[float, float] | None = (250.0, 7_000.0),
    normalize: bool = False,
) -> np.ndarray:
    values = np.asarray(samples, dtype=np.float64).reshape(-1)
    if values.size < 8 or not np.all(np.isfinite(values)):
        raise ValueError("Signal must contain at least eight finite samples")
    values = values - np.mean(values)
    if bandpass is not None and values.size >= 48:
        low, high = bandpass
        nyquist = sample_rate / 2
        low = max(1.0, low)
        high = min(high, nyquist * 0.96)
        if low < high:
            sos = butter(4, [low / nyquist, high / nyquist], btype="bandpass", output="sos")
            values = sosfiltfilt(sos, values)
            values = values - np.mean(values)
    if normalize:
        scale = np.max(np.abs(values))
        if scale > 1e-12:
            values = values / scale
    return values.astype(np.float32)


def _spectral_distribution(values: np.ndarray, sample_rate: int) -> tuple[np.ndarray, np.ndarray]:
    windowed = values * windows.hann(len(values), sym=False)
    spectrum = np.abs(np.fft.rfft(windowed)) ** 2
    frequencies = np.fft.rfftfreq(len(values), 1 / sample_rate)
    spectrum = spectrum / (np.sum(spectrum) + 1e-12)
    return frequencies, spectrum


def extract_features(samples: np.ndarray, sample_rate: int) -> dict[str, float]:
    values = preprocess_signal(samples, sample_rate, normalize=False)
    magnitude = np.abs(values)
    rms = float(np.sqrt(np.mean(values**2)))
    peak = float(np.max(magnitude))
    frequencies, power = _spectral_distribution(values, sample_rate)
    centroid = float(np.sum(frequencies * power))
    bandwidth = float(np.sqrt(np.sum(((frequencies - centroid) ** 2) * power)))
    cumulative = np.cumsum(power)
    rolloff_index = min(int(np.searchsorted(cumulative, 0.85)), len(frequencies) - 1)
    dominant_index = int(np.argmax(power[1:]) + 1) if len(power) > 1 else 0
    entropy = float(-np.sum(power * np.log2(power + 1e-12)) / max(math.log2(len(power)), 1.0))
    envelope = np.abs(hilbert(values))
    peak_index = int(np.argmax(envelope))
    tail = envelope[peak_index:]
    if len(tail) > 8 and np.max(tail) > 1e-12:
        threshold = np.max(tail) / math.e
        below = np.flatnonzero(tail <= threshold)
        decay_time = float(below[0] / sample_rate) if below.size else float(len(tail) / sample_rate)
    else:
        decay_time = 0.0
    signs = np.signbit(values)
    zcr = float(np.mean(signs[1:] != signs[:-1]))
    edge = max(4, len(values) // 10)
    noise_estimate = float(np.median(np.abs(values[:edge] - np.median(values[:edge]))) * 1.4826)

    def band_energy(low: float, high: float) -> float:
        mask = (frequencies >= low) & (frequencies < high)
        return float(np.sum(power[mask]))

    return {
        "rms": rms,
        "peak_amplitude": peak,
        "crest_factor": peak / (rms + 1e-12),
        "zero_crossing_rate": zcr,
        "spectral_centroid_hz": centroid,
        "spectral_bandwidth_hz": bandwidth,
        "spectral_rolloff_hz": float(frequencies[rolloff_index]),
        "dominant_frequency_hz": float(frequencies[dominant_index]),
        "spectral_entropy": entropy,
        "band_energy_low": band_energy(250, 1_500),
        "band_energy_mid": band_energy(1_500, 3_500),
        "band_energy_high": band_energy(3_500, min(7_000, sample_rate / 2)),
        "envelope_peak_time_s": peak_index / sample_rate,
        "decay_time_s": decay_time,
        "noise_estimate": noise_estimate,
        "snr_db": 20 * math.log10((rms + 1e-12) / (noise_estimate + 1e-12)),
    }


def analyze_signal(samples: np.ndarray, sample_rate: int, max_points: int = 700) -> dict:
    values = preprocess_signal(samples, sample_rate, normalize=False)
    stride = max(1, int(np.ceil(len(values) / max_points)))
    indices = np.arange(0, len(values), stride)
    frequencies, power = _spectral_distribution(values, sample_rate)
    psd_f, psd = welch(values, fs=sample_rate, nperseg=min(256, len(values)))
    spec_f, spec_t, spec_power = spectrogram(values, fs=sample_rate, nperseg=min(128, len(values)), noverlap=min(96, max(0, len(values) // 4)))
    spec_db = 10 * np.log10(spec_power + 1e-12)
    return {
        "sample_rate": sample_rate,
        "time_s": (indices / sample_rate).round(7).tolist(),
        "waveform": values[indices].round(7).tolist(),
        "fft_frequency_hz": frequencies[::stride].round(2).tolist(),
        "fft_power": power[::stride].round(9).tolist(),
        "psd_frequency_hz": psd_f.round(2).tolist(),
        "psd": psd.round(10).tolist(),
        "spectrogram_time_s": spec_t.round(5).tolist(),
        "spectrogram_frequency_hz": spec_f.round(2).tolist(),
        "spectrogram_db": spec_db.round(3).tolist(),
        "features": extract_features(values, sample_rate),
    }
