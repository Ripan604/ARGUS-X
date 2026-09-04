from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.models.surrogate import ForwardSurrogate


def evaluate(checkpoint_path: Path, inputs: np.ndarray, targets: np.ndarray) -> dict:
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=False)
    model = ForwardSurrogate(checkpoint["input_size"], checkpoint["output_size"])
    model.load_state_dict(checkpoint["model_state"])
    model.eval()

    input_mean = np.asarray(checkpoint["input_mean"], dtype=np.float32)
    input_std = np.asarray(checkpoint["input_std"], dtype=np.float32)
    target_mean = np.asarray(checkpoint["target_mean"], dtype=np.float32)
    target_std = np.asarray(checkpoint["target_std"], dtype=np.float32)
    normalized_inputs = (inputs - input_mean) / input_std
    with torch.no_grad():
        normalized_predictions = model(torch.from_numpy(normalized_inputs.astype(np.float32))).numpy()
    predictions = normalized_predictions * target_std + target_mean

    reference_std = np.maximum(targets.std(axis=0), 1e-6)
    standardized_mae = np.mean(np.abs(predictions - targets) / reference_std)
    residual_sum = np.sum((predictions - targets) ** 2, axis=0)
    total_sum = np.sum((targets - targets.mean(axis=0)) ** 2, axis=0)
    feature_r2 = 1.0 - residual_sum / np.maximum(total_sum, 1e-12)
    feature_names = checkpoint["metadata"]["feature_names"]
    return {
        "checkpoint": str(checkpoint_path),
        "training_samples": int(checkpoint["metadata"]["samples"]),
        "standardized_mae": float(standardized_mae),
        "mean_feature_r2": float(np.mean(feature_r2)),
        "per_feature_r2": {name: float(value) for name, value in zip(feature_names, feature_r2)},
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare ARGUS surrogate checkpoints on one fixed external test set")
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--checkpoints", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    payload = np.load(args.data)
    inputs = payload["inputs"].astype(np.float32)
    targets = payload["targets"].astype(np.float32)
    dataset_metadata = json.loads(str(payload["metadata"]))
    results = {
        "evaluation_dataset": str(args.data),
        "evaluation_seed": dataset_metadata.get("seed"),
        "evaluation_samples": len(inputs),
        "models": [evaluate(path, inputs, targets) for path in args.checkpoints],
    }
    rendered = json.dumps(results, indent=2)
    print(rendered)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
