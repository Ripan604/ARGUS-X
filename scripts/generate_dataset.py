from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.models.domain import Defect, Experiment, Material, Panel
from backend.app.signal.processing import extract_features
from backend.app.simulation.physics import AcousticSimulator

FEATURE_NAMES = [
    "rms", "peak_amplitude", "crest_factor", "zero_crossing_rate",
    "spectral_centroid_hz", "spectral_bandwidth_hz", "spectral_rolloff_hz",
    "dominant_frequency_hz", "spectral_entropy", "band_energy_low",
    "band_energy_mid", "band_energy_high", "envelope_peak_time_s", "decay_time_s", "snr_db",
]
TYPE_NAMES = ["cavity", "loose_region", "delamination", "dense_inclusion"]


def generate(samples: int, seed: int) -> tuple[np.ndarray, np.ndarray, dict]:
    rng = np.random.default_rng(seed)
    inputs: list[list[float]] = []
    targets: list[list[float]] = []
    for _ in range(samples):
        panel = Panel(width_m=float(rng.uniform(0.45, 0.85)), height_m=float(rng.uniform(0.30, 0.60)))
        material = Material(
            wave_velocity=float(rng.uniform(145, 245)), attenuation=float(rng.uniform(1.0, 2.4)),
            resonance_hz=float(rng.uniform(2_500, 4_200)), damping=float(rng.uniform(70, 135)),
            noise_std=float(rng.uniform(0.003, 0.014)), system_delay_s=float(rng.uniform(0.00055, 0.0011)),
        )
        simulator = AcousticSimulator(panel, material, sample_rate=16_000, seed=int(rng.integers(2**31)))
        defect_type = str(rng.choice(TYPE_NAMES))
        defect = Defect(
            float(rng.uniform(0.08, 0.92)), float(rng.uniform(0.08, 0.92)),
            float(rng.uniform(0.04, 0.14)), float(rng.uniform(0.04, 0.14)),
            float(rng.uniform(0.35, 0.96)), defect_type,
        )
        frequency_start = float(rng.uniform(900, 4_000))
        experiment = Experiment(
            float(rng.uniform(0.03, 0.97)), float(rng.uniform(0.03, 0.97)),
            float(rng.uniform(0.03, 0.97)), float(rng.uniform(0.03, 0.97)),
            frequency_start, min(6_800.0, frequency_start + float(rng.uniform(1_200, 2_800))),
            float(rng.uniform(0.32, 0.72)), 0.12, str(rng.choice(["impulse", "sine", "chirp"], p=[0.25, 0.15, 0.60])),
        )
        signal = simulator.simulate(defect, experiment)
        features = extract_features(signal, simulator.sample_rate)
        type_one_hot = [float(defect_type == name) for name in TYPE_NAMES]
        waveform_one_hot = [float(experiment.waveform == name) for name in ["impulse", "sine", "chirp"]]
        inputs.append([
            defect.center_x, defect.center_y, defect.radius_x, defect.radius_y, defect.severity,
            *type_one_hot, experiment.source_x, experiment.source_y, experiment.receiver_x, experiment.receiver_y,
            experiment.frequency_start_hz / 7_000, experiment.frequency_end_hz / 7_000,
            experiment.amplitude, *waveform_one_hot, panel.width_m, panel.height_m,
            material.wave_velocity / 300, material.attenuation / 3, material.resonance_hz / 5_000,
        ])
        targets.append([features[name] for name in FEATURE_NAMES])
    metadata = {
        "seed": seed, "samples": samples, "input_size": len(inputs[0]), "output_size": len(targets[0]),
        "feature_names": FEATURE_NAMES, "defect_types": TYPE_NAMES,
        "description": "Domain-randomized physics simulator data for the learned forward-response surrogate.",
    }
    return np.asarray(inputs, dtype=np.float32), np.asarray(targets, dtype=np.float32), metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate physics-inspired ARGUS training data")
    parser.add_argument("--samples", type=int, default=2_500)
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--output", default="datasets/generated/argus_forward.npz")
    args = parser.parse_args()
    if args.samples < 50:
        raise SystemExit("Generate at least 50 samples")
    inputs, targets, metadata = generate(args.samples, args.seed)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(output, inputs=inputs, targets=targets, metadata=json.dumps(metadata))
    print(f"Saved {len(inputs):,} samples to {output.resolve()}")
    print(f"Input shape {inputs.shape}; target shape {targets.shape}")


if __name__ == "__main__":
    main()
