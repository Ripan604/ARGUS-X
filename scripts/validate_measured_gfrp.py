"""Predeclared whole-plate evaluation of measured audio taps, not localization."""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import platform
import sys
import time
import warnings
from zipfile import ZipFile

import numpy as np
import scipy
from scipy.io import wavfile
from scipy.signal import resample_poly
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.signal.processing import extract_features
from scripts.generate_dataset import FEATURE_NAMES
from scripts.prepare_tud_gfrp_dataset import parse_waveform_name

SEED = 20261008
TARGET_RATE = 16000
BOOTSTRAPS = 2000
PERMUTATIONS = 10
MODEL_NAMES = ("majority_no_features", "logistic_regression", "random_forest")
DATA_ROOT = ROOT / "datasets/external/tud_gfrp_2026"
RAW_ROOT = DATA_ROOT / "unaugmented_data"
CACHE = ROOT / "datasets/generated/tud_gfrp_features.npz"
PROTOCOL = ROOT / "docs/MEASURED_GFRP_VALIDATION_PROTOCOL.md"
DEFAULT_OUTPUT = ROOT / "research_results/measured_gfrp_validation_2026_10_08.json"
SOURCE_FILES = (Path(__file__), PROTOCOL, ROOT / "backend/tests/test_measured_gfrp_validation.py",
                ROOT / "backend/app/signal/processing.py", ROOT / "scripts/prepare_tud_gfrp_dataset.py",
                ROOT / "scripts/generate_dataset.py")


def digest(path: Path, algorithm: str = "sha256") -> str:
    value = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def count_classes(labels: np.ndarray) -> dict:
    return {"intact": int(np.count_nonzero(labels == 0)), "defect": int(np.count_nonzero(labels == 1))}


def publisher_label(row: dict) -> int:
    plate, point = row["plate"], row["point"]
    modifier = (row.get("measurement_modifier") or "").lower()
    if not 1 <= plate <= 8 or not 1 <= point <= 48:
        raise ValueError("Publisher label rule covers only plates 1..8 and points 1..48")
    if plate <= 4:
        if modifier not in {"", "schlagschaden"}:
            raise ValueError("Unexpected modifier on an intact/impact plate")
        return int(modifier == "schlagschaden")
    if modifier and not (plate == 7 and modifier == "zusatz"):
        raise ValueError("Unsupported filename modifier for publisher point labels")
    if plate in {5, 6}:
        return int(point in {9, 10, 15, 16, 32, 35, 38, 41})
    if plate == 7:
        return int(modifier == "zusatz" or 25 <= point <= 30)
    return int(19 <= point <= 30)


def verify_manifest(data_root: Path) -> dict:
    manifest = json.loads((data_root / "argus_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("record_id") != "33756af4-eb6d-4156-8708-a41cbed33e7b" or manifest.get("license") != "CC-BY-4.0":
        raise ValueError("Unexpected dataset provenance/license declaration")
    checks = []
    for item in manifest["files"]:
        name = item["name"]
        if Path(name).name != name:
            raise ValueError("Manifest names must be local basenames")
        path = data_root / name
        actual_md5 = digest(path, "md5")
        matched = path.stat().st_size == item["size"] and actual_md5 == item["md5"]
        checks.append({"file": name, "size_bytes": path.stat().st_size, "publisher_md5": item["md5"],
                       "actual_md5": actual_md5, "sha256": digest(path), "verified": matched})
        if not matched:
            raise ValueError(f"Publisher checksum/size mismatch: {name}")
    return {"record": manifest["record_id"], "url": manifest["url"], "license": manifest["license"],
            "publisher_file_checks": checks, "live_verification": "Browser page/API unavailable; downloaded publisher documents and manifest verified"}


def normalized_pcm(samples: np.ndarray) -> np.ndarray:
    values = np.asarray(samples)
    if values.ndim not in {1, 2} or values.shape[0] < 32 or values.shape[0] > 10_000_000:
        raise ValueError("Unsupported recording dimensions/length")
    if np.issubdtype(values.dtype, np.integer):
        limits = np.iinfo(values.dtype)
        if limits.min == 0:
            midpoint = (limits.max + 1) / 2
            values = (values.astype(np.float64) - midpoint) / midpoint
        else:
            values = values.astype(np.float64) / max(abs(limits.min), limits.max)
    elif np.issubdtype(values.dtype, np.floating):
        values = values.astype(np.float64)
    else:
        raise ValueError("Only numeric PCM is supported")
    if values.ndim == 2:
        values = np.mean(values, axis=1)
    if not np.isfinite(values).all():
        raise ValueError("Non-finite waveform")
    return values


def cross_plate_duplicates(rows: list[dict]) -> list[int]:
    groups = defaultdict(list)
    for index, row in enumerate(rows):
        groups[row["pcm_sha256"]].append(index)
    excluded = []
    for indices in groups.values():
        if len({rows[index]["plate"] for index in indices}) > 1:
            excluded.extend(indices)
    return sorted(excluded)


def verify_archive_members(archive: Path, rows: list[dict]) -> dict:
    """Bind the extracted clips to the publisher-checksummed ZIP without extraction."""
    with ZipFile(archive) as source:
        names = sorted(item.filename for item in source.infolist() if item.filename.lower().endswith(".wav"))
        requested = sorted(row["relative_path"] for row in rows)
        if names != requested:
            raise ValueError("Extracted WAV cohort does not match the publisher ZIP member list")
        for row in rows:
            item = source.getinfo(row["relative_path"])
            if item.file_size > 2 * 1024 * 1024:
                raise ValueError("Unexpectedly large clipped WAV member")
            if hashlib.sha256(source.read(item)).hexdigest() != row["wav_sha256"]:
                raise ValueError(f"Extracted WAV differs from publisher archive: {row['relative_path']}")
    return {"verified_wav_members": len(rows), "all_extracted_wav_bytes_match_archive": True}


def load_raw_dataset(raw_root: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    paths = sorted(raw_root.rglob("*.wav"))
    if not paths:
        raise FileNotFoundError("No unaugmented measured WAV clips found")
    features, rows, layouts = [], [], Counter()
    for index, path in enumerate(paths):
        row = parse_waveform_name(path)
        if row["label"] != publisher_label(row):
            raise ValueError(f"Directory label disagrees with publisher README: {path.name}")
        rate, pcm = wavfile.read(path)
        rate = int(rate)
        if not 1000 <= rate <= 384000:
            raise ValueError("Unsupported original sample rate")
        raw_key = json.dumps({"rate": rate, "dtype": pcm.dtype.str, "shape": list(pcm.shape)}, sort_keys=True).encode()
        pcm_hash = hashlib.sha256(raw_key + pcm.tobytes()).hexdigest()
        signal = normalized_pcm(pcm)
        if rate != TARGET_RATE:
            divisor = int(np.gcd(rate, TARGET_RATE))
            signal = resample_poly(signal, TARGET_RATE // divisor, rate // divisor)
        vector = extract_features(signal.astype(np.float32), TARGET_RATE)
        features.append([vector[name] for name in FEATURE_NAMES])
        rows.append({"index": index, "relative_path": path.relative_to(raw_root).as_posix(),
                     "plate": row["plate"], "label": row["label"], "side": row["side"], "run": row["run"],
                     "point": row["point"], "modifier": row.get("measurement_modifier"),
                     "source_rate_hz": rate, "source_sample_count": len(pcm), "source_dtype": str(pcm.dtype),
                     "wav_sha256": digest(path), "pcm_sha256": pcm_hash})
        layouts[(rate, str(pcm.dtype), tuple(pcm.shape))] += 1
        if (index + 1) % 500 == 0:
            print(f"Recomputed measured features {index + 1}/{len(paths)}", flush=True)
    x = np.asarray(features, dtype=np.float32)
    y = np.asarray([row["label"] for row in rows], dtype=np.int64)
    groups = np.asarray([row["plate"] for row in rows], dtype=np.int64)
    if x.shape != (len(rows), 15) or not np.isfinite(x).all() or list(np.unique(groups)) != list(range(1, 9)):
        raise ValueError("The registered study requires finite 15-feature data from all eight plates")
    excluded = cross_plate_duplicates(rows)
    keep = ~np.isin(np.arange(len(y)), excluded)
    feature_hash = hashlib.sha256(x.astype("<f4").tobytes()).hexdigest()
    return x, y, groups, {"rows": rows, "retained_indices": np.flatnonzero(keep).tolist(),
        "excluded_cross_plate_duplicate_indices": excluded, "excluded_reason": "all members of exact cross-plate duplicate PCM sets",
        "within_plate_duplicate_sets": sum(len(v) > 1 and len({rows[i]['plate'] for i in v}) == 1 for v in _pcm_groups(rows).values()),
        "feature_names": list(FEATURE_NAMES), "feature_matrix_sha256_float32_little_endian": feature_hash,
        "raw_sample_count": len(y), "retained_sample_count": int(keep.sum()), "class_counts": count_classes(y),
        "retained_class_counts": count_classes(y[keep]), "plate_class_counts": {str(g): count_classes(y[groups == g]) for g in np.unique(groups)},
        "raw_layouts": [{"rate": key[0], "dtype": key[1], "shape": list(key[2]), "count": value} for key, value in layouts.items()]}


def _pcm_groups(rows: list[dict]) -> dict:
    groups = defaultdict(list)
    for row in rows:
        groups[row["pcm_sha256"]].append(row["index"])
    return groups


def load_feature_cache(path: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict]:
    with np.load(path, allow_pickle=False) as payload:
        features = np.asarray(payload["features"], dtype=np.float64)
        labels = np.asarray(payload["labels"])
        groups = np.asarray(payload["groups"])
        metadata = json.loads(str(payload["metadata"]))
    if (features.ndim != 2 or features.shape[1] != 15 or not np.isfinite(features).all()
            or labels.shape != (len(features),) or groups.shape != labels.shape
            or labels.dtype.kind not in "iu" or groups.dtype.kind not in "iu"
            or not set(np.unique(labels)).issubset({0, 1})):
        raise ValueError("Cached feature archive does not satisfy the numeric contract")
    return features, labels, groups, metadata


def audit_cache(path: Path, x: np.ndarray, y: np.ndarray, groups: np.ndarray, rows: list[dict]) -> dict:
    if not path.exists():
        return {"available": False, "used_to_fit": False}
    try:
        cached_x, cached_y, cached_groups, metadata = load_feature_cache(path)
        alignment = (cached_x.shape == x.shape and np.array_equal(cached_y, y) and np.array_equal(cached_groups, groups)
                     and metadata.get("feature_names") == list(FEATURE_NAMES)
                     and [row["relative_path"] for row in metadata.get("rows", [])] == [row["relative_path"] for row in rows])
        return {"available": True, "used_to_fit": False, "allow_pickle": False, "path_labels_groups_aligned": alignment,
                "maximum_absolute_feature_difference": float(np.max(np.abs(cached_x - x))) if alignment else None,
                "sha256": digest(path)}
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return {"available": True, "used_to_fit": False, "allow_pickle": False, "rejected": f"{type(exc).__name__}: {exc}"}


def make_model(name: str, seed: int) -> Pipeline:
    if name == "majority_no_features":
        estimator = DummyClassifier(strategy="most_frequent")
    elif name == "logistic_regression":
        estimator = LogisticRegression(C=1.0, class_weight="balanced", solver="lbfgs", max_iter=2000, random_state=seed)
    elif name == "random_forest":
        estimator = RandomForestClassifier(n_estimators=300, max_features="sqrt", min_samples_leaf=3,
                                          class_weight="balanced_subsample", n_jobs=1, random_state=seed)
    else:
        raise ValueError("Undeclared model")
    return Pipeline([("scale", StandardScaler()), ("model", estimator)])


def metrics(labels: np.ndarray, probabilities: np.ndarray) -> dict:
    if len(labels) == 0 or len(np.unique(labels)) != 2 or not np.isfinite(probabilities).all():
        raise ValueError("Metrics require finite predictions with both actual classes")
    predictions = probabilities >= 0.5
    tn = int(np.sum((labels == 0) & ~predictions)); fp = int(np.sum((labels == 0) & predictions))
    fn = int(np.sum((labels == 1) & ~predictions)); tp = int(np.sum((labels == 1) & predictions))
    return {"samples": len(labels), "accuracy": (tn + tp) / len(labels),
            "balanced_accuracy": 0.5 * (tn / (tn + fp) + tp / (tp + fn)),
            "roc_auc": float(roc_auc_score(labels, probabilities)), "f1": 2 * tp / max(1, 2 * tp + fp + fn),
            "confusion_matrix_labels": ["intact", "defect"], "confusion_matrix": [[tn, fp], [fn, tp]],
            "confusion_counts": {"tn": tn, "fp": fp, "fn": fn, "tp": tp}}


def evaluate_grouped(x: np.ndarray, labels: np.ndarray, groups: np.ndarray, *, n_splits: int = 4,
                     seed: int = SEED, model_names: tuple[str, ...] = MODEL_NAMES) -> dict:
    if (x.ndim != 2 or labels.shape != (len(x),) or groups.shape != labels.shape
            or not np.isfinite(x).all() or set(np.unique(labels)) != {0, 1}):
        raise ValueError("Invalid evaluation feature/label/group contract")
    probabilities = {name: np.full(len(labels), np.nan) for name in model_names}
    folds = []
    for number, (train, test) in enumerate(GroupKFold(n_splits=n_splits).split(x, labels, groups), start=1):
        train_groups = np.unique(groups[train]); test_groups = np.unique(groups[test])
        if np.intersect1d(train_groups, test_groups).size:
            raise RuntimeError("Physical plates overlap between training and test")
        fold = {"fold": number, "train_indices": train.tolist(), "test_indices": test.tolist(),
                "train_plates": train_groups.tolist(), "test_plates": test_groups.tolist(),
                "train_class_counts": count_classes(labels[train]), "test_class_counts": count_classes(labels[test]),
                "models": {}}
        folds.append(fold)
        if len(np.unique(labels[train])) != 2 or len(np.unique(labels[test])) != 2:
            fold["status"] = "rejected_single_class_partition"
            continue
        fold["status"] = "evaluated"
        for name in model_names:
            began = time.perf_counter()
            try:
                data = np.zeros((len(x), 1)) if name == "majority_no_features" else x
                model = make_model(name, seed + number)
                with warnings.catch_warnings(record=True) as captured:
                    warnings.simplefilter("always")
                    model.fit(data[train], labels[train])
                values = model.predict_proba(data[test])[:, 1]
                probabilities[name][test] = values
                fold["models"][name] = {"status": "evaluated", "metrics": metrics(labels[test], values),
                    "training_scaler_mean": model.named_steps["scale"].mean_.tolist(),
                    "training_scaler_variance": model.named_steps["scale"].var_.tolist(),
                    "warnings": [f"{warning.category.__name__}: {warning.message}" for warning in captured],
                    "runtime_s": time.perf_counter() - began}
            except Exception as exc:
                fold["models"][name] = {"status": "failed", "error": f"{type(exc).__name__}: {exc}", "runtime_s": time.perf_counter() - began}
                probabilities[name][test] = np.nan
    outputs = {}
    for name, values in probabilities.items():
        valid = np.isfinite(values)
        plate_metrics = {}
        for group in np.unique(groups):
            selected = (groups == group) & valid
            if selected.any() and len(np.unique(labels[selected])) == 2:
                plate_metrics[str(group)] = metrics(labels[selected], values[selected])
        outputs[name] = {"predictions_oof": [float(value) if np.isfinite(value) else None for value in values],
                        "valid_prediction_count": int(valid.sum()), "missing_prediction_indices": np.flatnonzero(~valid).tolist(),
                        "aggregate": metrics(labels[valid], values[valid]) if valid.any() and len(np.unique(labels[valid])) == 2 else None,
                        "aggregate_condition": "all rows" if valid.all() else "valid-fold rows only; missing indices retained",
                        "held_out_plate_metrics": plate_metrics,
                        "equal_weight_plate_means": {key: float(np.mean([item[key] for item in plate_metrics.values()]))
                                                     for key in ("balanced_accuracy", "roc_auc", "f1")} if plate_metrics else None}
    return {"folds": folds, "models": outputs}


def cluster_bootstrap(labels: np.ndarray, probabilities: np.ndarray, groups: np.ndarray, *, repeats: int = BOOTSTRAPS, seed: int = SEED) -> dict:
    rng = np.random.default_rng(seed)
    clusters = np.unique(groups)
    indices = {group: np.flatnonzero(groups == group) for group in clusters}
    samples = defaultdict(list)
    rejected = 0
    for _ in range(repeats):
        selected = np.concatenate([indices[group] for group in rng.choice(clusters, len(clusters), replace=True)])
        try:
            report = metrics(labels[selected], probabilities[selected])
            for key in ("balanced_accuracy", "roc_auc", "f1"):
                samples[key].append(report[key])
        except ValueError:
            rejected += 1
    return {"resampling_unit": "whole physical plate", "independent_clusters": len(clusters),
            "requested_resamples": repeats, "valid_resamples": repeats - rejected, "rejected_resamples": rejected,
            "ci95_percentile": {key: np.quantile(values, [0.025, 0.975]).tolist() for key, values in samples.items()},
            "limitation": "Eight plates; intervals condition on already fitted OOF predictions and do not refit models"}


def permute_within_plates(labels: np.ndarray, groups: np.ndarray, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    result = labels.copy()
    for group in np.unique(groups):
        selected = np.flatnonzero(groups == group)
        result[selected] = rng.permutation(labels[selected])
    return result


def snapshot(raw_root: Path, data_root: Path, cache: Path) -> dict:
    files = [*SOURCE_FILES, data_root / "argus_manifest.json", *(data_root / item for item in ("README.md", "README_unaugmented_data.md", "README_raw_measurement_data.md", "unaugmented_data.zip"))]
    if cache.exists():
        files.append(cache)
    files.extend(sorted(raw_root.rglob("*.wav")))
    return {str(path.relative_to(ROOT).as_posix()) if path.is_relative_to(ROOT) else str(path): digest(path) for path in files}


def run_study(output: Path, *, raw_root: Path = RAW_ROOT, data_root: Path = DATA_ROOT, cache: Path = CACHE) -> dict:
    if output.exists():
        raise FileExistsError("Refusing to overwrite an existing measured-data result")
    began = time.perf_counter()
    before = snapshot(raw_root, data_root, cache)
    provenance = verify_manifest(data_root)
    x, labels, groups, dataset = load_raw_dataset(raw_root)
    if len(labels) != 2568 or count_classes(labels) != {"intact": 2100, "defect": 468}:
        raise ValueError("Raw cohort changed from the 2568-clip/2100-intact/468-defect registered dataset")
    provenance["extracted_archive_binding"] = verify_archive_members(data_root / "unaugmented_data.zip", dataset["rows"])
    cache_audit = audit_cache(cache, x, labels, groups, dataset["rows"])
    retained = np.asarray(dataset["retained_indices"], dtype=np.int64)
    x, labels, groups = x[retained], labels[retained], groups[retained]
    if len(np.unique(groups)) != 8:
        raise ValueError("Duplicate exclusion removed a complete plate; registered eight-cluster study cannot proceed")
    print("Inputs verified; fitting the frozen whole-plate baselines", flush=True)
    evaluation = evaluate_grouped(x, labels, groups)
    for name, result in evaluation["models"].items():
        values = np.asarray([np.nan if value is None else value for value in result["predictions_oof"]])
        valid = np.isfinite(values)
        result["plate_cluster_bootstrap"] = cluster_bootstrap(labels[valid], values[valid], groups[valid]) if valid.any() else None
        print(f"{name}: {json.dumps(result['aggregate'])}", flush=True)
    controls = []
    for number in range(PERMUTATIONS):
        shuffled = permute_within_plates(labels, groups, SEED + 1000 + number)
        control = evaluate_grouped(x, shuffled, groups, model_names=("logistic_regression", "random_forest"))
        controls.append({"permutation": number + 1, "seed": SEED + 1000 + number,
                         "permuted_labels_sha256": hashlib.sha256(shuffled.astype("<i8").tobytes()).hexdigest(),
                         "folds": control["folds"], "models": control["models"]})
        print(f"Completed label-permutation diagnostic {number + 1}/{PERMUTATIONS}", flush=True)
    after = snapshot(raw_root, data_root, cache)
    changed = sorted(name for name in before.keys() | after.keys() if before.get(name) != after.get(name))
    result = {"study": "Measured GFRP whole-plate held-out acoustic tap screening", "date": "2026-10-08",
        "completed_at_utc": datetime.now(timezone.utc).isoformat(), "seed": SEED,
        "status": "complete" if not changed else "invalidated_input_or_source_changes",
        "scope": "Pointwise publisher-labelled audio-tap defect screening; not persistent-defect localization or ARGUS apparatus validation",
        "independent_prospective_blind_trial": False, "protocol": PROTOCOL.relative_to(ROOT).as_posix(),
        "provenance": provenance, "dataset": dataset, "cache_consistency_audit": cache_audit,
        "model_configuration": {name: make_model(name, SEED).named_steps["model"].get_params() for name in MODEL_NAMES},
        "split": "Four GroupKFold folds; complete physical plates held out; no hyperparameter/threshold tuning",
        "evaluation_row_indices_in_raw_manifest": retained.tolist(), "evaluation_labels": labels.tolist(), "evaluation_plate_groups": groups.tolist(),
        "evaluation": evaluation, "label_permutation_diagnostic": {"formal_significance_test": False,
            "method": "Labels shuffled within each plate, preserving plate class counts; fresh fold-local pipeline fits",
            "runs": controls}, "input_source_sha256_before": before, "input_source_sha256_after": after,
        "changed_files": changed, "runtime_s": time.perf_counter() - began,
        "software": {"python": platform.python_version(), "numpy": np.__version__, "scipy": scipy.__version__, "sklearn": sklearn.__version__},
        "limitations": ["Only eight independent plates, with correlated repeated tap locations/runs.",
                        "Directory/README labels are publisher annotations, not independently remeasured damage truth.",
                        "Amplitude features may reflect tap-force/coupling/acquisition changes; clipped hammer force is unavailable for reliable normalization.",
                        "No source-receiver waveform timing, adaptive inspection, defect-coordinate evaluation, or physical arrival-adapter validation.",
                        "This is a predeclared reanalysis of a previously seen dataset, not fresh blind evidence."]}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, allow_nan=False)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run_study(args.output)
    print(f"Saved {result['status']} JSON evidence to {args.output}", flush=True)


if __name__ == "__main__":
    main()
