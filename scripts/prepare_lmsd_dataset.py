from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.signal.processing import extract_features
from scripts.generate_dataset import FEATURE_NAMES


def response_to_signal(frf: np.ndarray, frequency: np.ndarray) -> tuple[np.ndarray, int]:
    values = np.asarray(frf).reshape(-1)
    frequencies = np.asarray(frequency, dtype=np.float64).reshape(-1)
    if values.size != frequencies.size or values.size < 4:
        raise ValueError("FRF and frequency axes must be aligned and non-empty")
    spacing = float(np.median(np.diff(frequencies)))
    sample_count = 2 * (values.size - 1)
    sample_rate = int(round(spacing * sample_count))
    signal = np.fft.irfft(values, n=sample_count).real
    target_length = max(32, int(round(0.12 * sample_rate)))
    return signal[:target_length].astype(np.float32), sample_rate


def scenario_geometry(mass_nodes: np.ndarray, node_position: np.ndarray) -> tuple[float, float, float, float, float]:
    positions = node_position[np.asarray(mass_nodes, dtype=int).reshape(-1)]
    center = positions.mean(axis=0) / 600.0
    half_extent = (positions.max(axis=0) - positions.min(axis=0)) / 2 + 25.0
    radius = np.maximum(half_extent / 600.0, 0.025)
    severity = min(0.95, 0.42 + 0.075 * len(positions))
    return float(center[0]), float(center[1]), float(radius[0]), float(radius[1]), float(severity)


def prepare(source: Path, output: Path) -> dict:
    baseline_path = source / "baseline.npz"
    if not baseline_path.exists():
        raise FileNotFoundError("baseline.npz is missing; run download_lmsd_dataset.py first")
    with np.load(baseline_path) as baseline:
        frequency = baseline["frequency"].astype(np.float64)
        node_position = baseline["node_position"].astype(np.float64)
        probing_nodes = baseline["probing_nodes"].astype(int)
    scenario_paths = sorted(path for path in source.glob("*.npz") if path.name != "baseline.npz")
    if not scenario_paths:
        raise FileNotFoundError("No damage-scenario NPZ files were downloaded")
    inputs: list[list[float]] = []
    targets: list[list[float]] = []
    rows: list[dict] = []
    for scenario_path in scenario_paths:
        with np.load(scenario_path) as scenario:
            frf = scenario["frf"]
            mass_nodes = scenario["mass_nodes"].astype(int)
        center_x, center_y, radius_x, radius_y, severity = scenario_geometry(mass_nodes, node_position)
        for receiver_index, receiver_node in enumerate(probing_nodes):
            for source_index, source_node in enumerate(probing_nodes):
                signal, sample_rate = response_to_signal(frf[receiver_index, source_index], frequency)
                features = extract_features(signal, sample_rate)
                source_xy = node_position[source_node] / 600.0
                receiver_xy = node_position[receiver_node] / 600.0
                # The added masses are represented as dense inclusions. Unknown
                # material/coupling values use neutral normalized constants and
                # should be calibrated before mixing with synthetic examples.
                inputs.append([
                    center_x, center_y, radius_x, radius_y, severity,
                    0.0, 0.0, 0.0, 1.0,
                    float(source_xy[0]), float(source_xy[1]), float(receiver_xy[0]), float(receiver_xy[1]),
                    float(frequency[0] / 7_000), float(frequency[-1] / 7_000),
                    1.0, 1.0, 0.0, 0.0,
                    0.6, 0.6, 0.65, 0.55, 0.32,
                ])
                targets.append([features[name] for name in FEATURE_NAMES])
                rows.append({
                    "scenario": scenario_path.name,
                    "source_node": int(source_node),
                    "receiver_node": int(receiver_node),
                    "sample_rate": sample_rate,
                })
    metadata = {
        "source": "LMSD 2021 Dataset for Damage Identification in Plates",
        "doi": "10.48804/GDE9TW",
        "license": "CC BY 4.0",
        "adapter": "ARGUS FRF-to-impulse-response feature adapter v1",
        "samples": len(inputs),
        "input_size": len(inputs[0]),
        "output_size": len(targets[0]),
        "feature_names": FEATURE_NAMES,
        "scenarios": [path.name for path in scenario_paths],
        "rows": rows,
        "limitations": "Added-mass scattering data; not literal cavity/delamination labels. Neutral nuisance parameters require calibration.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        inputs=np.asarray(inputs, dtype=np.float32),
        targets=np.asarray(targets, dtype=np.float32),
        metadata=json.dumps(metadata),
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Adapt the experimental LMSD FRFs to the ARGUS surrogate contract")
    parser.add_argument("--source", type=Path, default=ROOT / "datasets" / "external" / "lmsd2021")
    parser.add_argument("--output", type=Path, default=ROOT / "datasets" / "generated" / "lmsd_forward.npz")
    args = parser.parse_args()
    metadata = prepare(args.source, args.output)
    print(f"Saved {metadata['samples']} real-response examples from {len(metadata['scenarios'])} scenarios")
    print(f"Output: {args.output.resolve()}")
    print(f"Attribution: {metadata['source']}, DOI {metadata['doi']}, {metadata['license']}")


if __name__ == "__main__":
    main()
