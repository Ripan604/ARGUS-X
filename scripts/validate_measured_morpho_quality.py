"""Frozen leave-panel-out evaluation of measured, selected operator quality labels.

This is independent of ARGUS defect-location inference and its live hardware
contract. No dataset-author code, model binary, or pickle is executed or emitted.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
from time import perf_counter
import warnings

import h5py
import numpy as np
import scipy
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DATA_DIRECTORY = ROOT / "datasets/external/morpho_50khz"
SAMPLE_RATE = 1_000_000
WINDOW_SAMPLES = 500
SEED = 20261008
PANELS = ("FOD3", "FOD4", "FOD5", "FOD6", "FOD7")
METHODS = ("logistic_regression", "random_forest", "majority_dummy", "random_forest_shuffled_train")
README_CYCLES = dict(zip(PANELS, (9, 26, 24, 23, 22)))
FEATURE_NAMES = (
    "log10_rms", "absolute_mean_over_rms", "centered_peak_over_rms", "spectral_entropy",
    "power_fraction_40_60khz", "power_fraction_below_10khz", "leading_edge_rms_ratio",
    "trailing_edge_rms_ratio", "trailing_over_leading_rms", "peak_pile_fraction",
    "difference_rms_ratio", "zero_crossing_fraction", "raw_peak_over_rms",
    "lag20_centered_autocorrelation", "centered_rms_ratio", "finite_sample_fraction",
)


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


def fingerprints(data_directory: Path) -> dict[str, str]:
    files = [Path(__file__), ROOT / "scripts/download_morpho_dataset.py",
             ROOT / "docs/MEASURED_MORPHO_QUALITY_PROTOCOL.md",
             ROOT / "backend/tests/test_measured_morpho_quality.py",
             *(data_directory / name for name in ("morpho_50khz_full.h5", "paper_labels.json", "README.md",
                                                  "LICENSE", "CITATION.cff", "zenodo_record_20120070.json", "download_manifest.json"))]
    return {path.relative_to(ROOT).as_posix(): file_sha256(path) for path in files}


def features_for_signal(signal: np.ndarray, sample_rate: int = SAMPLE_RATE) -> np.ndarray:
    if sample_rate != SAMPLE_RATE or isinstance(sample_rate, bool):
        raise ValueError("The frozen quality study requires native 1 MHz acquisition")
    values = np.asarray(signal, dtype=np.float64)
    if values.ndim != 1 or len(values) < WINDOW_SAMPLES:
        raise ValueError("A complete 500-sample native window is required")
    values = values[:WINDOW_SAMPLES]
    finite_fraction = float(np.isfinite(values).mean())
    values = np.where(np.isfinite(values), values, 0.)
    raw_rms = float(np.sqrt(np.mean(values**2)))
    rms = max(raw_rms, 1e-12)
    centered = values-values.mean()
    centered_rms = float(np.sqrt(np.mean(centered**2)))
    peak = float(np.max(np.abs(centered)))
    spectrum = np.abs(np.fft.rfft(values))**2
    frequency = np.fft.rfftfreq(WINDOW_SAMPLES, 1./SAMPLE_RATE)
    total_power = float(spectrum.sum())
    proportions = spectrum / total_power if total_power > 0 else np.zeros_like(spectrum)
    active = proportions > 0
    entropy = float(-np.sum(proportions[active]*np.log2(proportions[active]))/np.log2(len(proportions)))
    leading = float(np.sqrt(np.mean(values[:50]**2)))
    trailing = float(np.sqrt(np.mean(values[-50:]**2)))
    centered_energy = float(centered @ centered)
    vector = np.asarray([
        np.log10(rms), abs(float(values.mean()))/rms, peak/rms, entropy,
        float(proportions[(frequency >= 40000) & (frequency <= 60000)].sum()),
        float(proportions[frequency < 10000].sum()), leading/rms, trailing/rms,
        trailing/max(leading, 1e-12), float(np.mean(np.abs(centered) >= .98*peak)) if peak > 0 else 0.,
        float(np.sqrt(np.mean(np.diff(values)**2)))/rms,
        float(np.mean(centered[:-1]*centered[1:] < 0)), float(np.max(np.abs(values)))/rms,
        float(centered[:-20] @ centered[20:])/centered_energy if centered_energy > 0 else 0.,
        centered_rms/rms, finite_fraction,
    ])
    if not np.isfinite(vector).all():
        raise ValueError("Waveform statistics exceed the finite numerical feature envelope")
    return vector


def _strict_integer(value, low: int, high: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError("Label row has unsupported numeric coordinates")
    return value


def load_measured_features(data_directory: Path = DATA_DIRECTORY) -> tuple[np.ndarray, np.ndarray, np.ndarray, list[dict], dict]:
    data_directory = data_directory.resolve()
    if not data_directory.is_relative_to(ROOT):
        raise ValueError("Measured data must be retained within the shared workspace")
    manifest_path = data_directory / "download_manifest.json"
    if manifest_path.stat().st_size > 1_000_000:
        raise ValueError("Download manifest exceeds the bounded metadata envelope")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset_doi") != "10.5281/zenodo.20120070" or manifest.get("license_id") != "cc-by-4.0":
        raise ValueError("Verified dataset identity/license is required")
    inventory = {row["filename"]: row for row in manifest["files"]}
    for filename in ("morpho_50khz_full.h5", "paper_labels.json"):
        path = data_directory / filename
        if path.stat().st_size != inventory[filename]["bytes"] or file_sha256(path) != inventory[filename]["sha256"]:
            raise ValueError("Measured publisher file failed retained source integrity")
    labels_path = data_directory / "paper_labels.json"
    if labels_path.stat().st_size > 1_000_000:
        raise ValueError("Label metadata exceeds the declared envelope")
    label_document = json.loads(labels_path.read_text(encoding="utf-8"))
    labelled = label_document["labels"]
    if len(labelled) != 1011 or label_document.get("n_total") != 1011:
        raise ValueError("The frozen study uses exactly the existing 1,011 selected labels")
    feature_rows, targets, panel_rows, records = [], [], [], []
    seen = set()
    schema = {panel: {"signals": 0, "leaf_datasets": 0, "cycles": set(), "shapes": set()} for panel in PANELS}
    with h5py.File(data_directory / "morpho_50khz_full.h5", "r") as handle:
        if set(handle) != set(PANELS) or int(handle.attrs["sample_rate_hz"]) != SAMPLE_RATE or int(handle.attrs["n_signals"]) != 12504:
            raise ValueError("Publisher HDF5 root differs from the frozen numeric acquisition schema")

        def inspect(name, obj):
            if isinstance(obj, h5py.Group):
                for key in obj:
                    if not isinstance(obj.get(key, getlink=True), h5py.HardLink):
                        raise ValueError("External/soft HDF5 links are outside the retained numeric contract")
            if isinstance(obj, h5py.Dataset):
                matched = re.fullmatch(r"(FOD[3-7])/50kHz/act([1-4])/recv([0-3])/cycle([0-9]{1,8})/data", name)
                if (not matched or obj.dtype != np.dtype("float32") or obj.ndim != 2
                        or obj.shape[1] != 2001 or not 1 <= obj.shape[0] <= 80 or obj.is_virtual or obj.external):
                    raise ValueError("Unexpected, external, or nonnumeric HDF5 waveform schema")
                panel = matched.group(1)
                if int(matched.group(3)) == int(matched.group(2))-1:
                    raise ValueError("Drive channels must remain outside the wave-receiver universe")
                schema[panel]["signals"] += obj.shape[0]
                schema[panel]["leaf_datasets"] += 1
                schema[panel]["cycles"].add(int(matched.group(4)))
                schema[panel]["shapes"].add(obj.shape)
        inspect("", handle)
        handle.visititems(inspect)
        if sum(row["signals"] for row in schema.values()) != 12504:
            raise ValueError("Measured signal inventory does not match publisher totals")
        for row in labelled:
            panel = row.get("panel")
            if panel not in PANELS or row.get("label") not in {"GOOD", "BAD"}:
                raise ValueError("Unknown operator quality label or specimen")
            freq = _strict_integer(row.get("freq_khz"), 50, 50)
            actuator = _strict_integer(row.get("actuator"), 1, 4)
            receiver = _strict_integer(row.get("receiver"), 0, 3)
            cycle = _strict_integer(row.get("cycle"), 0, 99999999)
            repetition = _strict_integer(row.get("rep_idx"), 0, 79)
            signal_id = f"{panel}_{freq}kHz_act{actuator}_recv{receiver}_c{cycle}_r{repetition}"
            key = f"{panel}/{freq}kHz/act{actuator}/recv{receiver}/cycle{cycle}/data"
            if signal_id != row.get("signal_id") or signal_id in seen or key not in handle or repetition >= handle[key].shape[0]:
                raise ValueError("Label must bind one unique valid publisher waveform row")
            seen.add(signal_id)
            feature_rows.append(features_for_signal(handle[key][repetition, :WINDOW_SAMPLES]))
            targets.append(int(row["label"] == "BAD"))
            panel_rows.append(panel)
            records.append({**row, "hdf5_path": key})
    audit = {panel: {"signals": row["signals"], "leaf_datasets": row["leaf_datasets"],
                    "actual_distinct_cycles": len(row["cycles"]), "cycle_values": sorted(row["cycles"]),
                    "readme_cycles": README_CYCLES[panel], "readme_cycles_agree": len(row["cycles"]) == README_CYCLES[panel],
                    "numeric_shapes": sorted(row["shapes"]),
                    "label_counts": dict(Counter(r["label"] for r in records if r["panel"] == panel))}
             for panel, row in schema.items()}
    return np.asarray(feature_rows), np.asarray(targets), np.asarray(panel_rows), records, audit


def classification_metrics(targets: np.ndarray, probability_bad: np.ndarray) -> dict:
    y, p = np.asarray(targets), np.asarray(probability_bad, dtype=float)
    if y.ndim != 1 or y.size == 0 or p.shape != y.shape or not np.isin(y, [0, 1]).all() or not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError("Finite matched binary outcomes/probabilities are required")
    prediction = p >= .5
    tp, fn = int(np.sum(prediction & (y == 1))), int(np.sum(~prediction & (y == 1)))
    tn, fp = int(np.sum(~prediction & (y == 0))), int(np.sum(prediction & (y == 0)))
    bad_recall = tp/(tp+fn) if tp+fn else None
    good_recall = tn/(tn+fp) if tn+fp else None
    both = bad_recall is not None and good_recall is not None
    return {"samples": len(y), "bad_support": tp+fn, "good_support": tn+fp,
            "true_bad": tp, "missed_bad": fn, "true_good": tn, "false_bad": fp,
            "accuracy": (tp+tn)/len(y), "bad_precision": tp/(tp+fp) if tp+fp else None,
            "bad_recall": bad_recall, "good_recall": good_recall,
            "balanced_accuracy": (bad_recall+good_recall)/2 if both else None,
            "auroc": float(roc_auc_score(y, p)) if both else None,
            "brier_loss": float(np.mean((p-y)**2))}


def shuffled_training_labels(targets: np.ndarray, panels: np.ndarray) -> np.ndarray:
    result = np.asarray(targets).copy()
    rng = np.random.default_rng(SEED)
    for panel in sorted(set(panels)):
        indices = np.flatnonzero(panels == panel)
        result[indices] = rng.permutation(result[indices])
    return result


def build_model(method: str):
    if method == "logistic_regression":
        return Pipeline([("scale", StandardScaler()), ("model", LogisticRegression(
            C=1., class_weight="balanced", solver="lbfgs", max_iter=2000, random_state=SEED))])
    if method in {"random_forest", "random_forest_shuffled_train"}:
        return RandomForestClassifier(n_estimators=300, max_depth=8, min_samples_leaf=3,
                                      class_weight="balanced", random_state=SEED, n_jobs=1)
    if method == "majority_dummy":
        return DummyClassifier(strategy="most_frequent")
    raise ValueError("Method is outside the frozen quality protocol")


def run_lopo(features: np.ndarray, targets: np.ndarray, panels: np.ndarray, signal_ids: list[str],
             *, methods: tuple[str, ...] = METHODS) -> tuple[list[dict], dict]:
    x, y, group = np.asarray(features), np.asarray(targets), np.asarray(panels)
    if x.ndim != 2 or x.shape[0] != len(y) or len(group) != len(y) or len(signal_ids) != len(y) or not np.isfinite(x).all() or not np.isin(y, [0, 1]).all():
        raise ValueError("Complete finite feature rows and binary labels are required")
    if len(set(signal_ids)) != len(signal_ids) or not set(methods).issubset(METHODS):
        raise ValueError("Unique acquisition rows and registered methods are required")
    folds = []
    for held_out in sorted(set(group)):
        train, test = np.flatnonzero(group != held_out), np.flatnonzero(group == held_out)
        if train.size == 0:
            raise ValueError("At least two independent panels are required")
        train_ids, test_ids = [signal_ids[i] for i in train], [signal_ids[i] for i in test]
        assert not set(train_ids) & set(test_ids)
        for method in methods:
            entry = {"held_out_panel": str(held_out), "method": method, "train_panels": sorted(set(group[train])),
                     "train_ids": train_ids, "test_ids": test_ids, "train_count": len(train), "test_count": len(test),
                     "train_bad": int(y[train].sum()), "test_bad": int(y[test].sum())}
            started = perf_counter()
            try:
                model = build_model(method)
                train_labels = shuffled_training_labels(y[train], group[train]) if method.endswith("shuffled_train") else y[train]
                with warnings.catch_warnings():
                    warnings.simplefilter("error", ConvergenceWarning)
                    model.fit(x[train], train_labels)
                class_index = list(model.classes_).index(1)
                probabilities = model.predict_proba(x[test])[:, class_index]
                entry.update({"completed": True, "metrics": classification_metrics(y[test], probabilities),
                    "predictions": [{"signal_id": signal_ids[i], "true_bad": int(y[i]), "probability_bad": float(prob),
                                     "predicted_bad": int(prob >= .5)} for i, prob in zip(test, probabilities)]})
                if method == "logistic_regression":
                    entry["training_scaler_mean"] = model.named_steps["scale"].mean_.tolist()
            except Exception as exc:
                entry.update({"completed": False, "error_type": type(exc).__name__, "error": str(exc)[:512], "metrics": None,
                    "predictions": [{"signal_id": signal_ids[i], "true_bad": int(y[i]), "probability_bad": None,
                                     "predicted_bad": None} for i in test]})
            entry["elapsed_s"] = perf_counter()-started
            folds.append(entry)
    summaries = {}
    for method in methods:
        method_folds = [fold for fold in folds if fold["method"] == method]
        scored = [row for fold in method_folds if fold["completed"] for row in fold["predictions"]]
        bad_recalls = [fold["metrics"]["bad_recall"] for fold in method_folds
                       if fold["completed"] and fold["metrics"]["bad_recall"] is not None]
        good_recalls = [fold["metrics"]["good_recall"] for fold in method_folds
                        if fold["completed"] and fold["metrics"]["good_recall"] is not None]
        summaries[method] = {"attempted_labels": len(y), "scored_labels": len(scored),
            "attempted_folds": len(method_folds), "failed_folds": sum(not fold["completed"] for fold in method_folds),
            "pooled_completed_fold_metrics": classification_metrics(np.asarray([r["true_bad"] for r in scored]),
                np.asarray([r["probability_bad"] for r in scored])) if scored else None,
            "macro_bad_recall": float(np.mean(bad_recalls)) if bad_recalls else None,
            "macro_good_recall": float(np.mean(good_recalls)) if good_recalls else None,
            "bad_recall_supported_folds": len(bad_recalls), "good_recall_supported_folds": len(good_recalls),
            "metrics_scope": "conditional_on_existing_selected_operator_labels_and_completed_predictions"}
    return folds, summaries


def run_study(data_directory: Path = DATA_DIRECTORY) -> dict:
    before = fingerprints(data_directory)
    started = perf_counter()
    x, y, panels, records, audit = load_measured_features(data_directory)
    folds, summary = run_lopo(x, y, panels, [row["signal_id"] for row in records])
    after = fingerprints(data_directory)
    return {"metadata": {"dataset_doi": "10.5281/zenodo.20120070", "also_cite": "10.5281/zenodo.14627730",
        "license": "CC-BY-4.0", "evidence_source": "measured_native_guided_wave_selected_operator_quality_labels",
        "task": "GOOD_BAD_quality_not_persistent_damage_or_location", "positive_class": "BAD",
        "split": "leave_entire_panel_out", "sample_rate_hz": SAMPLE_RATE, "window_samples": WINDOW_SAMPLES,
        "feature_names": FEATURE_NAMES, "methods": METHODS, "seed": SEED, "threshold_bad": .5,
        "source_sha256_before": before, "source_sha256_after": after, "source_changed_during_run": before != after,
        "library_versions": {"numpy": np.__version__, "scipy": scipy.__version__, "sklearn": sklearn.__version__, "h5py": h5py.__version__},
        "run_elapsed_s": perf_counter()-started, "model_binary_exported": False,
        "limitations": ["actively_selected_human_labels_not_population_random_sample", "five_panels_only",
                        "strong_panel_dependent_BAD_prevalence", "FOD6_has_no_BAD_labels", "README_cycle_counts_disagree_with_HDF5",
                        "shape_proxy_not_ADC_saturation_certification", "quality_task_distinct_from_defect_localization",
                        "one_within_training_panel_shuffle_not_a_permutation_significance_test"]},
        "schema_audit": audit, "labelled_features": [{**row, "bad": int(y[i]), "features": x[i].tolist()}
             for i, row in enumerate(records)], "folds": folds, "summary": summary}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "research_results/measured_morpho_quality_2026_10_08.json")
    args = parser.parse_args()
    if not args.output.resolve().is_relative_to(ROOT):
        raise ValueError("Study output must remain in the workspace")
    report = run_study()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "summary": report["summary"],
                      "source_changed_during_run": report["metadata"]["source_changed_during_run"]}, indent=2))


if __name__ == "__main__":
    main()
