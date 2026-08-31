from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.signal.processing import extract_features
from scripts.generate_dataset import FEATURE_NAMES


DEFAULT_SOURCE = ROOT / "datasets" / "external" / "tud_gfrp_2026" / "unaugmented_data"
DEFAULT_OUTPUT = ROOT / "datasets" / "generated" / "tud_gfrp_features.npz"
NAME_PATTERN = re.compile(
    r"^(?P<mounting>[^_]+)_P(?P<plate>\d+)_(?:(?P<modifier>Schlagschaden|Zusatz)_)?"
    r"(?P<side>[AB])_D(?P<run>\d+)_(?P<point>\d+)\.wav$",
    re.IGNORECASE,
)


def parse_waveform_name(path: Path) -> dict:
    match = NAME_PATTERN.match(path.name)
    if match is None:
        raise ValueError(f"Unrecognized TU Darmstadt waveform name: {path.name}")
    values = match.groupdict()
    point = int(values["point"])
    if not 1 <= point <= 48:
        raise ValueError(f"Grid point outside 1..48 in {path.name}")
    label_name = path.parent.name.lower()
    if label_name not in {"intact", "defect"}:
        raise ValueError(f"Waveform must be under an intact/defect directory: {path}")
    x, y = point_to_xy(point)
    is_defect = label_name == "defect"
    return {
        "mounting": values["mounting"],
        "plate": int(values["plate"]),
        "side": values["side"].upper(),
        "run": int(values["run"]),
        "point": point,
        "x": x,
        "y": y,
        "label": int(is_defect),
        "measurement_modifier": values["modifier"],
        "damage_type": "impact" if values["modifier"] == "Schlagschaden" else ("delamination" if is_defect else "healthy"),
    }


def point_to_xy(point: int) -> tuple[float, float]:
    """Map the publisher's column-major 8 x 6 point numbering to [0, 1]^2."""

    zero_based = point - 1
    column, row = divmod(zero_based, 6)
    return column / 7.0, row / 5.0


def read_resampled(path: Path, target_rate: int) -> tuple[np.ndarray, int]:
    source_rate, samples = wavfile.read(path)
    values = np.asarray(samples)
    if values.ndim == 2:
        values = values.astype(np.float64).mean(axis=1)
    if np.issubdtype(values.dtype, np.integer):
        limit = max(abs(np.iinfo(values.dtype).min), np.iinfo(values.dtype).max)
        values = values.astype(np.float64) / limit
    else:
        values = values.astype(np.float64)
    if not np.all(np.isfinite(values)) or len(values) < 32:
        raise ValueError(f"Invalid waveform: {path}")
    if int(source_rate) != target_rate:
        divisor = int(np.gcd(int(source_rate), target_rate))
        values = resample_poly(values, target_rate // divisor, int(source_rate) // divisor)
    return values.astype(np.float32), int(source_rate)


def prepare(source: Path, output: Path, target_rate: int = 16_000) -> dict:
    paths = sorted(source.rglob("*.wav"))
    if not paths:
        raise FileNotFoundError(
            f"No WAV files found under {source}; run scripts/download_sim2real_datasets.py first"
        )
    features: list[list[float]] = []
    labels: list[int] = []
    groups: list[int] = []
    coordinates: list[list[float]] = []
    rows: list[dict] = []
    for index, path in enumerate(paths, start=1):
        row = parse_waveform_name(path)
        signal, source_rate = read_resampled(path, target_rate)
        extracted = extract_features(signal, target_rate)
        features.append([extracted[name] for name in FEATURE_NAMES])
        labels.append(row["label"])
        groups.append(row["plate"])
        coordinates.append([row["x"], row["y"]])
        rows.append({
            **row,
            "scenario": f"plate-{row['plate']}",
            "source_rate": source_rate,
            "target_rate": target_rate,
            "relative_path": path.relative_to(source).as_posix(),
        })
        if index % 500 == 0:
            print(f"processed {index}/{len(paths)}", flush=True)
    feature_array = np.asarray(features, dtype=np.float32)
    label_array = np.asarray(labels, dtype=np.int64)
    if not np.all(np.isfinite(feature_array)):
        raise RuntimeError("Feature extraction produced non-finite values")
    metadata = {
        "source": "Data for the Paper: Audio Signal-Based Defect Detection for Wind Turbine Rotor Blades Using an Autoencoder",
        "record": "33756af4-eb6d-4156-8708-a41cbed33e7b",
        "url": "https://tudatalib.ulb.tu-darmstadt.de/items/33756af4-eb6d-4156-8708-a41cbed33e7b",
        "license": "CC BY 4.0",
        "samples": len(paths),
        "intact_samples": int(np.sum(label_array == 0)),
        "defect_samples": int(np.sum(label_array == 1)),
        "plates": sorted(set(groups)),
        "feature_names": FEATURE_NAMES,
        "source_sample_rate": 51_200,
        "target_sample_rate": target_rate,
        "preprocessing": "mono -> rational polyphase resample -> ARGUS 250-7000 Hz feature pipeline v1",
        "split_policy": "hold out complete physical plates; never randomly split repeated points/runs",
        "rows": rows,
        "limitations": "Pointwise microphone/tapping labels support acoustic defect detection and domain calibration, not stand-alone multistatic defect localization.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        inputs=feature_array,
        targets=label_array,
        features=feature_array,
        labels=label_array,
        groups=np.asarray(groups, dtype=np.int64),
        coordinates=np.asarray(coordinates, dtype=np.float32),
        metadata=json.dumps(metadata),
    )
    return metadata


def main() -> None:
    parser = argparse.ArgumentParser(description="Adapt TU Darmstadt real GFRP microphone data to ARGUS features")
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--target-rate", type=int, default=16_000)
    args = parser.parse_args()
    metadata = prepare(args.source, args.output, args.target_rate)
    print(
        f"saved {metadata['samples']} measured waveforms "
        f"({metadata['defect_samples']} defect, {metadata['intact_samples']} intact) to {args.output.resolve()}"
    )
    print(f"attribution: {metadata['source']} [{metadata['license']}]")


if __name__ == "__main__":
    main()
