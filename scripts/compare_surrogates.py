"""Paired comparison of local, trusted checkpoints on one untouched test bank.

No fitting or checkpoint replacement occurs. Feature prediction is not defect
localization; simulated holdouts cannot establish physical accuracy.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.models.surrogate import ForwardSurrogate
from backend.app.models.checkpoints import load_forward_checkpoint, load_forward_dataset


def predict(checkpoint: dict, inputs: np.ndarray) -> np.ndarray:
    if inputs.shape[1] != checkpoint["input_size"]:
        raise ValueError("Checkpoint input contract does not match the test bank")
    model = ForwardSurrogate(checkpoint["input_size"], checkpoint["output_size"])
    model.load_state_dict(checkpoint["model_state"])
    model.eval()
    normalized = ((inputs - checkpoint["input_mean"]) / checkpoint["input_std"]).astype(np.float32)
    with torch.no_grad():
        parts = [model(torch.from_numpy(batch)).numpy() for batch in np.array_split(normalized, max(1, len(inputs) // 512))]
    return np.concatenate(parts) * checkpoint["target_std"] + checkpoint["target_mean"]


def compare_predictions(targets, baseline, candidate, scale, names) -> dict:
    if targets.ndim != 2 or len(targets) < 2 or targets.shape != baseline.shape or targets.shape != candidate.shape:
        raise ValueError("Comparison requires matching prediction/target matrices with at least two rows")
    if np.shape(scale) != (targets.shape[1],) or len(names) != targets.shape[1] or np.any(scale <= 0):
        raise ValueError("Feature scale and names must match and scale must be positive")
    if not all(np.isfinite(x).all() for x in (targets, baseline, candidate, scale)):
        raise ValueError("Comparison values must be finite")
    results = {}
    for name, values in (("baseline", baseline), ("candidate", candidate)):
        errors = np.abs(values - targets)
        r2 = 1 - np.sum((values-targets)**2, axis=0) / np.maximum(np.sum((targets-targets.mean(0))**2, axis=0), 1e-12)
        results[name] = {"standardized_mae_common_baseline_scale": float(np.mean(errors/scale)),
                         "mean_feature_r2": float(r2.mean()),
                         "per_feature_mae": dict(zip(names, errors.mean(0).astype(float).tolist())),
                         "per_feature_r2": dict(zip(names, r2.astype(float).tolist()))}
    difference = np.mean((np.abs(baseline-targets)-np.abs(candidate-targets))/scale, axis=1)
    rng = np.random.default_rng(73125)
    means = [float(rng.choice(difference, len(difference), replace=True).mean()) for _ in range(2000)]
    results["paired_mae_advantage"] = {"positive_favours": "candidate", "mean": float(difference.mean()),
                                       "bootstrap_95ci": np.quantile(means, [.025, .975]).tolist(),
                                       "bootstrap_seed": 73125, "resamples": 2000}
    results["features_with_over_10_percent_mae_regression"] = [n for n in names if
        results["candidate"]["per_feature_mae"][n] > 1.1 * results["baseline"]["per_feature_mae"][n]]
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--training-data", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        parser.error("Use a new output path; previous evaluation evidence is preserved")
    torch.set_num_threads(4)
    x, y, metadata = load_forward_dataset(args.data)
    test_rows = {row.tobytes() for row in x}
    for training_path in args.training_data:
        training_inputs, _, _ = load_forward_dataset(training_path)
        if any(row.tobytes() in test_rows for row in training_inputs):
            raise ValueError("Test inputs overlap supplied training/development bank")
    checkpoints = [load_forward_checkpoint(p) for p in (args.baseline, args.candidate)]
    if any(c["metadata"]["feature_names"] != metadata["feature_names"] for c in checkpoints):
        raise ValueError("Checkpoint and test feature order differ")
    report = compare_predictions(y, *(predict(c, x) for c in checkpoints),
                                 np.asarray(checkpoints[0]["target_std"]), metadata["feature_names"])
    report["protocol"] = {"samples": len(x), "test_metadata": metadata,
                          "scale": "baseline training target standard deviation for both models",
                          "selection": "candidate selected only by internal validation loss",
                          "input_overlap_with_supplied_training_banks": 0,
                          "data_source": "synthetic", "runtime_model_replaced": False,
                          "limitations": ["IID simulator holdout, not measured physical evidence",
                                         "No defect-localization or field-calibration accuracy established",
                                         "Intervals condition on these two fitted checkpoints"],
                          "sha256": {p: sha256(Path(p).read_bytes()).hexdigest() for p in
                                     [args.baseline, args.candidate, args.data, *args.training_data, __file__]}}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
