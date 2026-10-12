from __future__ import annotations

import argparse
from hashlib import sha256
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
from backend.app.models.checkpoints import save_forward_checkpoint, load_forward_dataset


def split_indices(metadata: dict, sample_count: int, seed: int, mode: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    if sample_count < 10:
        raise ValueError("Training requires at least ten samples and nonempty held-out splits")
    if mode not in {"auto", "random", "group"}:
        raise ValueError("Unknown split mode")
    rows = metadata.get("rows", [])
    has_groups = len(rows) == sample_count and all("scenario" in row for row in rows)
    resolved_mode = "group" if mode == "auto" and has_groups else ("random" if mode == "auto" else mode)
    rng = np.random.default_rng(seed)
    if resolved_mode == "group":
        if not has_groups:
            raise ValueError("Group split requires metadata.rows with one scenario value per sample")
        groups = np.asarray([row["scenario"] for row in rows])
        unique_groups = np.unique(groups)
        if len(unique_groups) < 3:
            raise ValueError("Group split requires at least three independent scenarios")
        shuffled_groups = rng.permutation(unique_groups)
        train_group_count = max(1, int(0.67 * len(shuffled_groups)))
        validation_group_count = max(1, int(0.17 * len(shuffled_groups)))
        validation_end = min(len(shuffled_groups) - 1, train_group_count + validation_group_count)
        train_groups = shuffled_groups[:train_group_count]
        validation_groups = shuffled_groups[train_group_count:validation_end]
        test_groups = shuffled_groups[validation_end:]
        train_idx = np.flatnonzero(np.isin(groups, train_groups))
        validation_idx = np.flatnonzero(np.isin(groups, validation_groups))
        test_idx = np.flatnonzero(np.isin(groups, test_groups))
        detail = {
            "mode": "group",
            "group_field": "scenario",
            "train_groups": train_groups.tolist(),
            "validation_groups": validation_groups.tolist(),
            "test_groups": test_groups.tolist(),
        }
    else:
        order = rng.permutation(sample_count)
        train_end, validation_end = int(0.70 * len(order)), int(0.85 * len(order))
        train_idx, validation_idx, test_idx = order[:train_end], order[train_end:validation_end], order[validation_end:]
        detail = {"mode": "random"}
    detail["sample_counts"] = {
        "train": int(len(train_idx)), "validation": int(len(validation_idx)), "test": int(len(test_idx))
    }
    return train_idx, validation_idx, test_idx, detail


def evaluate_loss(model, loader, device) -> float:
    """Sample-weighted loss: a small final batch must not receive full weight."""
    total, count = 0.0, 0
    model.eval()
    with torch.no_grad():
        for batch_x, batch_y in loader:
            loss = torch.nn.functional.smooth_l1_loss(model(batch_x.to(device)), batch_y.to(device))
            total += float(loss) * len(batch_x)
            count += len(batch_x)
    if not count:
        raise ValueError("Cannot evaluate an empty split")
    return total / count


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the optional ARGUS forward-response surrogate")
    parser.add_argument("--data", default="datasets/generated/argus_forward.npz")
    parser.add_argument("--output", default="models/forward_surrogate.npz")
    parser.add_argument("--epochs", type=int, default=80)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--patience", type=int, default=10)
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--threads", type=int, default=4, help="Bound CPU use for a responsive local app")
    parser.add_argument("--learning-rate", type=float, default=1.8e-3)
    parser.add_argument("--lr-patience", type=int, default=6)
    parser.add_argument(
        "--split-mode", choices=("auto", "random", "group"), default="auto",
        help="Auto uses scenario-held-out splits for adapted experimental data and random splits for independent synthetic samples",
    )
    args = parser.parse_args()
    if min(args.epochs, args.batch_size, args.patience, args.threads, args.lr_patience) < 1 or not np.isfinite(args.learning_rate) or args.learning_rate <= 0:
        parser.error("Training counts and learning rate must be finite and positive")
    torch.set_num_threads(args.threads)
    random.seed(args.seed); np.random.seed(args.seed); torch.manual_seed(args.seed)
    inputs, targets, metadata = load_forward_dataset(args.data)
    if inputs.ndim != 2 or targets.ndim != 2 or len(inputs) != len(targets) or not np.isfinite(inputs).all() or not np.isfinite(targets).all():
        raise ValueError("Inputs and targets must be finite aligned matrices")
    if len(metadata["feature_names"]) != targets.shape[1]:
        raise ValueError("Feature names do not match target columns")
    train_idx, validation_idx, test_idx, split = split_indices(metadata, len(inputs), args.seed, args.split_mode)
    print(f"split={split['mode']} train={len(train_idx)} validation={len(validation_idx)} test={len(test_idx)}")
    x_mean, x_std = inputs[train_idx].mean(0), inputs[train_idx].std(0) + 1e-6
    y_mean, y_std = targets[train_idx].mean(0), targets[train_idx].std(0) + 1e-6

    def tensors(indices):
        return TensorDataset(
            torch.from_numpy(((inputs[indices] - x_mean) / x_std).astype(np.float32)),
            torch.from_numpy(((targets[indices] - y_mean) / y_std).astype(np.float32)),
        )

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = ForwardSurrogate(inputs.shape[1], targets.shape[1]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=args.lr_patience, factor=0.5, min_lr=1e-5)
    loss_function = torch.nn.SmoothL1Loss()
    train_loader = DataLoader(tensors(train_idx), batch_size=args.batch_size, shuffle=True)
    validation_loader = DataLoader(tensors(validation_idx), batch_size=args.batch_size)
    best_loss, best_state, stale = float("inf"), None, 0
    history, best_epoch = [], 0
    for epoch in range(1, args.epochs + 1):
        model.train()
        for batch_x, batch_y in train_loader:
            optimizer.zero_grad(set_to_none=True)
            loss = loss_function(model(batch_x.to(device)), batch_y.to(device))
            loss.backward(); optimizer.step()
        validation_loss = evaluate_loss(model, validation_loader, device)
        if not np.isfinite(validation_loss):
            raise RuntimeError("Nonfinite validation loss; checkpoint not saved")
        history.append({"epoch": epoch, "validation_loss": validation_loss, "learning_rate": optimizer.param_groups[0]["lr"]})
        scheduler.step(validation_loss)
        if epoch == 1 or epoch % 5 == 0:
            print(f"epoch={epoch:03d} validation_loss={validation_loss:.5f}")
        if validation_loss < best_loss - 1e-4:
            best_loss = validation_loss
            best_epoch = epoch
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
    test_loss = evaluate_loss(model, test_loader, device)
    with torch.no_grad():
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
    checkpoint_metadata = {key: value for key, value in metadata.items() if key != "rows"}
    checkpoint = {
        "model_state": best_state, "input_size": inputs.shape[1], "output_size": targets.shape[1],
        "input_mean": x_mean, "input_std": x_std, "target_mean": y_mean, "target_std": y_std,
        "metadata": {
            **checkpoint_metadata,
            "validation_loss": best_loss,
            "test_loss": test_loss,
            "training": {"epochs_completed": epoch, "best_epoch": best_epoch,
                         "batch_size": args.batch_size, "patience": args.patience,
                         "learning_rate": args.learning_rate, "lr_patience": args.lr_patience,
                         "threads": args.threads, "selection": "validation Smooth L1 with min_delta=0.0001; test excluded",
                         "history": history},
            "dataset_sha256": sha256(Path(args.data).read_bytes()).hexdigest(),
            "dataset_seed": metadata.get("seed"),
            "trainer_sha256": sha256(Path(__file__).read_bytes()).hexdigest(),
            "torch_version": str(torch.__version__),
            "device": str(device),
            "seed": args.seed,
            "split": split,
            "held_out_metrics": held_out_metrics,
        },
    }
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    save_forward_checkpoint(checkpoint, output)
    output.with_suffix(".json").write_text(json.dumps(checkpoint["metadata"], indent=2), encoding="utf-8")
    print(f"Saved best checkpoint to {output.resolve()}; test_loss={checkpoint['metadata']['test_loss']:.5f}")


if __name__ == "__main__":
    main()
