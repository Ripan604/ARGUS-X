from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.models.surrogate import ForwardSurrogate


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the optional ARGUS forward-response surrogate")
    parser.add_argument("--data", default="datasets/generated/argus_forward.npz")
    parser.add_argument("--output", default="models/forward_surrogate.pt")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    payload = np.load(args.data)
    inputs, targets = payload["inputs"], payload["targets"]
    metadata = json.loads(str(payload["metadata"]))
    order = np.random.default_rng(args.seed).permutation(len(inputs))
    train_end, validation_end = int(0.70 * len(order)), int(0.85 * len(order))
    train_idx, validation_idx, test_idx = order[:train_end], order[train_end:validation_end], order[validation_end:]
    x_mean, x_std = inputs[train_idx].mean(0), inputs[train_idx].std(0) + 1e-6
    y_mean, y_std = targets[train_idx].mean(0), targets[train_idx].std(0) + 1e-6

    def tensors(indices):
        return TensorDataset(
            torch.from_numpy(((inputs[indices] - x_mean) / x_std).astype(np.float32)),
            torch.from_numpy(((targets[indices] - y_mean) / y_std).astype(np.float32)),
        )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ForwardSurrogate(inputs.shape[1], targets.shape[1]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1.8e-3, weight_decay=1e-4)
    loss_function = torch.nn.SmoothL1Loss()
    train_loader = DataLoader(tensors(train_idx), batch_size=args.batch_size, shuffle=True)
    validation_loader = DataLoader(tensors(validation_idx), batch_size=args.batch_size)
    best_loss, best_state, stale = float("inf"), None, 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad(set_to_none=True)
            loss = loss_function(model(batch_x.to(device)), batch_y.to(device))
            loss.backward(); optimizer.step()
        model.eval(); losses = []
        with torch.no_grad():
            for batch_x, batch_y in validation_loader:
                losses.append(float(loss_function(model(batch_x.to(device)), batch_y.to(device))))
        validation_loss = float(np.mean(losses))
        if epoch == 1 or epoch % 5 == 0:
            print(f"epoch={epoch:03d} validation_loss={validation_loss:.5f}")
        if validation_loss < best_loss - 1e-4:
            best_loss = validation_loss
            best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
            stale = 0
        else:
            stale += 1
            if stale >= args.patience:
                print(f"Early stopping at epoch {epoch}")
                break
    model.load_state_dict(best_state)
    model.to(device).eval()
    test_loader = DataLoader(tensors(test_idx), batch_size=args.batch_size)
    test_losses = []
    with torch.no_grad():
        for batch_x, batch_y in test_loader:
            test_losses.append(float(loss_function(model(batch_x.to(device)), batch_y.to(device))))
        normalized_test_x = torch.from_numpy(((inputs[test_idx] - x_mean) / x_std).astype(np.float32)).to(device)
        prediction_normalized = model(normalized_test_x).cpu().numpy()
    target_normalized = (targets[test_idx] - y_mean) / y_std
    prediction = prediction_normalized * y_std + y_mean
    feature_mae = np.mean(np.abs(prediction - targets[test_idx]), axis=0)
    residual_sum = np.sum((prediction - targets[test_idx]) ** 2, axis=0)
    total_sum = np.sum((targets[test_idx] - targets[test_idx].mean(axis=0)) ** 2, axis=0)
    feature_r2 = 1.0 - residual_sum / np.maximum(total_sum, 1e-12)
    feature_names = metadata["feature_names"]
    held_out_metrics = {
        "standardized_mae": float(np.mean(np.abs(prediction_normalized - target_normalized))),
        "mean_feature_r2": float(np.mean(feature_r2)),
        "per_feature_mae": {name: float(value) for name, value in zip(feature_names, feature_mae)},
        "per_feature_r2": {name: float(value) for name, value in zip(feature_names, feature_r2)},
    }
    checkpoint = {
        "model_state": best_state, "input_size": inputs.shape[1], "output_size": targets.shape[1],
        "input_mean": x_mean, "input_std": x_std, "target_mean": y_mean, "target_std": y_std,
        "metadata": {
            **metadata,
            "validation_loss": best_loss,
            "test_loss": float(np.mean(test_losses)),
            "device": str(device),
            "seed": args.seed,
            "held_out_metrics": held_out_metrics,
        },
    }
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(checkpoint, output)
    output.with_suffix(".json").write_text(json.dumps(checkpoint["metadata"], indent=2), encoding="utf-8")
    print(f"Saved best checkpoint to {output.resolve()}; test_loss={checkpoint['metadata']['test_loss']:.5f}")


if __name__ == "__main__":
    main()
