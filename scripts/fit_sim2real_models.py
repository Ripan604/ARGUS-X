from __future__ import annotations

import argparse
import json
from pathlib import Path
import random
import sys

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)
from sklearn.model_selection import GroupKFold


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.models.domain import Experiment, Material, Panel
from backend.app.models.sim2real import CovarianceTransport
from backend.app.ood.acoustic_reference import AcousticReferenceMonitor, REFERENCE_FEATURES
from backend.app.signal.processing import extract_features
from backend.app.simulation.physics import AcousticSimulator
from scripts.generate_dataset import FEATURE_NAMES


def generate_healthy_reference(samples: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    rows = []
    for _ in range(samples):
        panel = Panel(width_m=0.36, height_m=0.28, material="GFRP")
        material = Material(
            wave_velocity=float(rng.uniform(145, 245)),
            attenuation=float(rng.uniform(1.0, 2.4)),
            resonance_hz=float(rng.uniform(2_000, 5_500)),
            damping=float(rng.uniform(70, 150)),
            noise_std=float(rng.uniform(0.003, 0.015)),
            system_delay_s=float(rng.uniform(0.0005, 0.0012)),
        )
        simulator = AcousticSimulator(panel, material, sample_rate=16_000, seed=int(rng.integers(2**31)))
        experiment = Experiment(
            source_x=float(rng.uniform(0.02, 0.98)),
            source_y=float(rng.uniform(0.02, 0.98)),
            receiver_x=float(rng.uniform(0.02, 0.98)),
            receiver_y=float(rng.uniform(0.02, 0.98)),
            frequency_start_hz=float(rng.uniform(900, 3_000)),
            frequency_end_hz=float(rng.uniform(3_500, 6_800)),
            amplitude=float(rng.uniform(0.3, 0.75)),
            duration_s=0.12,
            waveform="impulse",
        )
        signal = simulator.simulate_baseline(experiment)
        signal = signal + simulator.rng.normal(0, material.noise_std, len(signal))
        feature_mapping = extract_features(signal, simulator.sample_rate)
        rows.append([feature_mapping[name] for name in FEATURE_NAMES])
    return np.asarray(rows, dtype=np.float64)


def classifier_metrics(labels: np.ndarray, probabilities: np.ndarray) -> dict:
    predictions = (probabilities >= 0.5).astype(int)
    return {
        "balanced_accuracy": float(balanced_accuracy_score(labels, predictions)),
        "roc_auc": float(roc_auc_score(labels, probabilities)),
        "average_precision": float(average_precision_score(labels, probabilities)),
        "f1": float(f1_score(labels, predictions)),
        "brier": float(brier_score_loss(labels, probabilities)),
        "confusion_matrix": confusion_matrix(labels, predictions, labels=[0, 1]).tolist(),
    }


def fit_models(
    real_data: Path,
    synthetic_data: Path,
    reference_output: Path,
    transport_output: Path,
    classifier_output: Path,
    metrics_output: Path,
    seed: int,
) -> dict:
    random.seed(seed)
    np.random.seed(seed)
    with np.load(real_data) as payload:
        real_features = payload["features"].astype(np.float64)
        labels = payload["labels"].astype(int)
        groups = payload["groups"].astype(int)
        real_metadata = json.loads(str(payload["metadata"]))
    with np.load(synthetic_data) as payload:
        synthetic_inputs = payload["inputs"].astype(np.float64)
        synthetic_damage = payload["targets"].astype(np.float64)
        synthetic_metadata = json.loads(str(payload["metadata"]))
    if tuple(real_metadata["feature_names"]) != tuple(FEATURE_NAMES):
        raise ValueError("Real-data feature contract does not match ARGUS")
    if tuple(synthetic_metadata["feature_names"]) != tuple(FEATURE_NAMES):
        raise ValueError("Synthetic feature contract does not match ARGUS")

    # Existing synthetic rows encode [impulse, sine, chirp] at columns 16:19.
    impulse_mask = synthetic_inputs[:, 16] > 0.5
    if np.sum(impulse_mask) >= 100:
        synthetic_damage = synthetic_damage[impulse_mask]
    synthetic_healthy = generate_healthy_reference(max(600, len(synthetic_damage)), seed + 101)

    transports = {}
    alignment = {}
    for state, source, target in (
        ("healthy", synthetic_healthy, real_features[labels == 0]),
        ("damage", synthetic_damage, real_features[labels == 1]),
    ):
        fitted = CovarianceTransport.fit(source, target, FEATURE_NAMES)
        transports[state] = fitted.to_dict()
        alignment[state] = {
            **fitted.alignment_metrics(source, target),
            "synthetic_samples": int(len(source)),
            "measured_samples": int(len(target)),
        }
    transport_payload = {
        "method": "class-conditional robust CORAL feature transport",
        "purpose": "Map simulator feature statistics toward the measured GFRP microphone domain; not waveform synthesis or proof of localization accuracy.",
        "synthetic_source": synthetic_metadata.get("description", str(synthetic_data)),
        "measured_source": real_metadata["source"],
        "measured_record": real_metadata["record"],
        "license": real_metadata["license"],
        "feature_names": FEATURE_NAMES,
        "states": transports,
        "alignment_metrics": alignment,
    }
    transport_output.parent.mkdir(parents=True, exist_ok=True)
    transport_output.write_text(json.dumps(transport_payload, indent=2), encoding="utf-8")

    monitor = AcousticReferenceMonitor.fit(
        real_features,
        FEATURE_NAMES,
        provenance={
            "dataset": real_metadata["source"],
            "record": real_metadata["record"],
            "license": real_metadata["license"],
            "samples": int(len(real_features)),
            "sample_rate_hz": int(real_metadata["target_sample_rate"]),
            "validation": "Empirical 90% acceptance region; upper tail feeds ARGUS caution/abstention only for external physical acquisitions.",
        },
    )
    reference_output.parent.mkdir(parents=True, exist_ok=True)
    reference_output.write_text(json.dumps(monitor.to_dict(), indent=2), encoding="utf-8")

    name_to_index = {name: index for index, name in enumerate(FEATURE_NAMES)}
    classifier_names = tuple(REFERENCE_FEATURES)
    classifier_indices = np.asarray([name_to_index[name] for name in classifier_names], dtype=int)
    classifier_features = real_features[:, classifier_indices]
    splitter = GroupKFold(n_splits=4)
    probabilities = np.zeros(len(labels), dtype=np.float64)
    fold_details = []
    for fold, (train, test) in enumerate(splitter.split(classifier_features, labels, groups), start=1):
        model = RandomForestClassifier(
            n_estimators=350,
            max_features="sqrt",
            min_samples_leaf=3,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=seed + fold,
        )
        model.fit(classifier_features[train], labels[train])
        probabilities[test] = model.predict_proba(classifier_features[test])[:, 1]
        fold_details.append({
            "fold": fold,
            "held_out_plates": sorted(np.unique(groups[test]).astype(int).tolist()),
            "samples": int(len(test)),
            **classifier_metrics(labels[test], probabilities[test]),
        })
    held_out_metrics = classifier_metrics(labels, probabilities)
    final_classifier = RandomForestClassifier(
        n_estimators=500,
        max_features="sqrt",
        min_samples_leaf=3,
        class_weight="balanced_subsample",
        n_jobs=-1,
        random_state=seed,
    )
    final_classifier.fit(classifier_features, labels)
    classifier_output.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(
        {
            "model": final_classifier,
            "feature_names": classifier_names,
            "source": real_metadata["source"],
            "record": real_metadata["record"],
            "license": real_metadata["license"],
            "scope": "GFRP pointwise acoustic defect screening; not multistatic localization",
        },
        classifier_output,
    )

    metrics = {
        "dataset": real_metadata["source"],
        "record": real_metadata["record"],
        "license": real_metadata["license"],
        "split": "4-fold GroupKFold with complete physical plates held out",
        "samples": int(len(labels)),
        "plates": sorted(np.unique(groups).astype(int).tolist()),
        "class_counts": {"intact": int(np.sum(labels == 0)), "defect": int(np.sum(labels == 1))},
        "classifier_features": list(classifier_names),
        "held_out_metrics": held_out_metrics,
        "folds": fold_details,
        "alignment_metrics": alignment,
        "limitations": [
            "Detection labels are pointwise microphone/tapping measurements, not full ARGUS source-receiver localization trials.",
            "The final classifier is trained on all eight plates for later transfer; only the out-of-fold metrics estimate unseen-plate performance.",
            "CORAL alignment matches feature moments and cannot establish physical waveform fidelity or field reliability.",
        ],
    }
    metrics_output.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    return metrics


def main() -> None:
    parser = argparse.ArgumentParser(description="Fit ARGUS measured-domain reference, transport, and baseline models")
    parser.add_argument("--real-data", type=Path, default=ROOT / "datasets" / "generated" / "tud_gfrp_features.npz")
    parser.add_argument("--synthetic-data", type=Path, default=ROOT / "datasets" / "generated" / "argus_forward.npz")
    parser.add_argument("--reference-output", type=Path, default=ROOT / "models" / "sim2real_acoustic_reference.json")
    parser.add_argument("--transport-output", type=Path, default=ROOT / "models" / "sim2real_feature_transport.json")
    parser.add_argument("--classifier-output", type=Path, default=ROOT / "models" / "tud_gfrp_reality_baseline.joblib")
    parser.add_argument("--metrics-output", type=Path, default=ROOT / "models" / "sim2real_metrics.json")
    parser.add_argument("--seed", type=int, default=73)
    args = parser.parse_args()
    metrics = fit_models(
        args.real_data,
        args.synthetic_data,
        args.reference_output,
        args.transport_output,
        args.classifier_output,
        args.metrics_output,
        args.seed,
    )
    held_out = metrics["held_out_metrics"]
    print(
        "plate-held-out real-data baseline: "
        f"balanced_accuracy={held_out['balanced_accuracy']:.3f} "
        f"roc_auc={held_out['roc_auc']:.3f} average_precision={held_out['average_precision']:.3f}"
    )
    for state, values in metrics["alignment_metrics"].items():
        print(
            f"{state} transport: Wasserstein {values['mean_standardized_wasserstein_before']:.3f} -> "
            f"{values['mean_standardized_wasserstein_after']:.3f}; covariance error "
            f"{values['relative_covariance_error_before']:.3f} -> {values['relative_covariance_error_after']:.3f}"
        )


if __name__ == "__main__":
    main()
