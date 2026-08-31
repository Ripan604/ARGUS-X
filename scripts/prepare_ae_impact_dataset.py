from __future__ import annotations

import argparse
import json
from pathlib import Path
import re

import numpy as np
from scipy.io import loadmat
from scipy.signal import butter, hilbert, sosfiltfilt, windows


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "datasets" / "external" / "ae_impact_2024"
DEFAULT_OUTPUT = ROOT / "datasets" / "generated" / "ae_impact_features.npz"
SAMPLE_RATE = 2_000_000
WINDOW_SAMPLES = 1_600
FEATURE_NAMES = (
    "energy_q01_s",
    "energy_q05_s",
    "energy_q10_s",
    "energy_q25_s",
    "energy_q50_s",
    "envelope_peak_s",
    "rms",
    "crest_factor",
    "spectral_centroid_hz",
    "spectral_bandwidth_hz",
    "spectral_entropy",
    "envelope_kurtosis",
)
EXPERIMENT_PATTERN = re.compile(r"Test_x(?P<x>\d+\.\d+)_y(?P<y>\d+\.\d+)Fs", re.IGNORECASE)


def ultrasonic_features(signal: np.ndarray, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    values = np.asarray(signal, dtype=np.float64).reshape(-1)[:WINDOW_SAMPLES]
    if len(values) < WINDOW_SAMPLES or not np.all(np.isfinite(values)):
        raise ValueError("Ultrasonic feature window must contain 1,600 finite samples")
    values = values - np.mean(values)
    nyquist = sample_rate / 2
    sos = butter(4, [100_000 / nyquist, 400_000 / nyquist], btype="bandpass", output="sos")
    filtered = sosfiltfilt(sos, values)
    envelope = np.abs(hilbert(filtered))
    energy = envelope**2
    cumulative = np.cumsum(energy) / max(float(np.sum(energy)), 1e-18)
    quantile_times = [float(np.searchsorted(cumulative, q) / sample_rate) for q in (0.01, 0.05, 0.10, 0.25, 0.50)]
    rms = float(np.sqrt(np.mean(filtered**2)))
    peak = float(np.max(np.abs(filtered)))
    spectrum = np.abs(np.fft.rfft(filtered * windows.hann(len(filtered), sym=False))) ** 2
    frequencies = np.fft.rfftfreq(len(filtered), 1 / sample_rate)
    spectrum = spectrum / max(float(np.sum(spectrum)), 1e-18)
    centroid = float(np.sum(frequencies * spectrum))
    bandwidth = float(np.sqrt(np.sum((frequencies - centroid) ** 2 * spectrum)))
    entropy = float(-np.sum(spectrum * np.log2(spectrum + 1e-18)) / np.log2(len(spectrum)))
    centered_envelope = envelope - np.mean(envelope)
    variance = float(np.mean(centered_envelope**2))
    kurtosis = float(np.mean(centered_envelope**4) / max(variance**2, 1e-18))
    return np.asarray([
        *quantile_times,
        float(np.argmax(envelope) / sample_rate),
        rms,
        peak / max(rms, 1e-18),
        centroid,
        bandwidth,
        entropy,
        kurtosis,
    ], dtype=np.float64)


def prepare(source: Path, output: Path) -> dict:
    simulation_paths = sorted((source / "simulation").glob("TX*_Fs2MHz_1x1x0.003_Al.mat"))
    experimental_paths = sorted(source.glob("Test_x*_y*Fs2MHz_1x1x0.003_Al.csv"))
    if len(simulation_paths) != 40 or len(experimental_paths) != 9:
        raise FileNotFoundError(
            "Expected 40 simulated MAT files and 9 experimental CSV files; run the sim-to-real downloader"
        )
    simulation_features = []
    simulation_toa = []
    simulation_tx = []
    simulation_rx = []
    simulation_groups = []
    for group, path in enumerate(simulation_paths):
        payload = loadmat(path, squeeze_me=True, struct_as_record=False)["data"]
        signals = np.asarray(getattr(payload, "sata", getattr(payload, "data", None)), dtype=np.float64)
        tx = np.asarray(payload.Tx, dtype=np.float64).T
        rx = np.asarray(payload.Rx, dtype=np.float64).T
        labels = np.asarray(payload.Label, dtype=np.float64).reshape(-1)
        for receiver in range(signals.shape[1]):
            simulation_features.append(ultrasonic_features(signals[:, receiver]))
            simulation_toa.append(labels[receiver])
            simulation_tx.append(tx[receiver])
            simulation_rx.append(rx[receiver])
            simulation_groups.append(group)

    experimental_features = []
    experimental_positions = []
    experimental_sensor_indices = []
    for event_index, path in enumerate(experimental_paths):
        match = EXPERIMENT_PATTERN.match(path.stem)
        if match is None:
            raise ValueError(f"Cannot parse experimental position from {path.name}")
        position = [float(match.group("x")), float(match.group("y"))]
        signals = np.loadtxt(path, delimiter=",", skiprows=1)
        if signals.shape != (5_000, 3):
            raise ValueError(f"Unexpected experimental CSV shape {signals.shape} in {path.name}")
        # The record specifies a 1,500-sample pre-trigger. Align sample zero to
        # that trigger before applying the same 0.8 ms feature window.
        post_trigger = signals[1_500 : 1_500 + WINDOW_SAMPLES]
        for sensor in range(3):
            experimental_features.append(ultrasonic_features(post_trigger[:, sensor]))
            experimental_positions.append(position)
            experimental_sensor_indices.append(sensor)

    metadata = {
        "source": "Acoustic Emission dataset for impact localization: numerical and experimental case studies",
        "record": "10875042",
        "doi": "10.5281/zenodo.10875042",
        "license": "CC BY 4.0",
        "sample_rate": SAMPLE_RATE,
        "window_samples": WINDOW_SAMPLES,
        "feature_names": list(FEATURE_NAMES),
        "simulation_paths": len(simulation_features),
        "experimental_events": len(experimental_paths),
        "experimental_channels": len(experimental_features),
        "experimental_sensor_coordinates_m": [[0.05, 0.95], [0.05, 0.05], [0.95, 0.05]],
        "limitations": "The experimental record supplies nine impact positions, not persistent hidden defects. Timing calibration is evaluated leave-one-position-out.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        simulation_features=np.asarray(simulation_features, dtype=np.float32),
        simulation_toa=np.asarray(simulation_toa, dtype=np.float64),
        simulation_tx=np.asarray(simulation_tx, dtype=np.float64),
        simulation_rx=np.asarray(simulation_rx, dtype=np.float64),
        simulation_groups=np.asarray(simulation_groups, dtype=np.int64),
        experimental_features=np.asarray(experimental_features, dtype=np.float32),
        experimental_positions=np.asarray(experimental_positions, dtype=np.float64),
        experimental_sensor_indices=np.asarray(experimental_sensor_indices, dtype=np.int64),
        metadata=json.dumps(metadata),
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare paired simulated/experimental AE impact-localization features")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    metadata = prepare(args.source, args.output)
    print(
        f"saved {metadata['simulation_paths']} simulated paths and "
        f"{metadata['experimental_channels']} measured channels to {args.output.resolve()}"
    )


if __name__ == "__main__":
    main()
