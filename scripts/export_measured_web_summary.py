"""Export compact, source-verified measured-study results for the local web UI.

Metrics come only from the four saved study artifacts. No raw recordings,
predictions, machine paths or model binaries enter frontend/public.
"""
from __future__ import annotations
import hashlib
import json
import math
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "frontend/public/research/measured-data-summary.json"
STUDIES = {
    "gfrp": "research_results/measured_gfrp_validation_2026_10_08.json",
    "impact": "research_results/measured_impact_validation_2026_10_08.json",
    "morpho": "research_results/measured_morpho_quality_2026_10_08.json",
    "ogw": "research_results/measured_guided_wave_validation_2026_10_08.json",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""): digest.update(block)
    return digest.hexdigest()


def load_verified(relative: str) -> tuple[dict, dict]:
    path = ROOT / relative
    raw = path.read_bytes()
    report = json.loads(raw)
    metadata = report.get("metadata", {})
    if "input_source_sha256_after" in report:
        if report.get("status") != "complete" or report.get("changed_files") != []:
            raise ValueError(f"Incomplete or changed study: {relative}")
        after, before = report["input_source_sha256_after"], report["input_source_sha256_before"]
    else:
        if metadata.get("source_changed_during_run") is not False or report.get("completed", True) is not True:
            raise ValueError(f"Incomplete or changed study: {relative}")
        after, before = metadata["source_sha256_after"], metadata["source_sha256_before"]
    if not isinstance(after, dict) or not after or before != after:
        raise ValueError(f"Missing or inconsistent source fingerprint: {relative}")
    for source, expected in after.items():
        resolved = (ROOT / source).resolve()
        if not resolved.is_relative_to(ROOT.resolve()) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("Invalid recorded source path/hash")
        if not resolved.is_file() or sha256(resolved) != expected:
            raise ValueError(f"Current source differs from measured study: {source}")
    identity = {
        "artifact": {"path": relative, "sha256": hashlib.sha256(raw).hexdigest()},
        "source_verification": {"files_checked": len(after), "current_matches": True,
                                "source_changed_during_run": False,
                                "manifest_sha256": hashlib.sha256(json.dumps(after, sort_keys=True, separators=(",", ":")).encode()).hexdigest()},
    }
    return report, identity


def column(key: str, label: str, unit: str) -> dict:
    return {"key": key, "label": label, "unit": unit}


def row(method: str, metrics: dict, keys: list[str]) -> dict:
    values = {key: metrics[key] for key in keys}
    if any(value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)) for value in values.values()):
        raise ValueError("Nonfinite/non-numeric recorded metric")
    return {"method": method, "values": values}


def main() -> None:
    saved = {key: load_verified(path) for key, path in STUDIES.items()}
    result = {"schema_version": 1, "evidence_source": "measured_external_reanalysis", "review_date": "2026-10-08",
              "hardware_validated": False, "sources_verified_at_export": True,
              "scope": "Recorded external measurements; four distinct tasks. Reanalysis and offline replay are not a prospective ARGUS apparatus trial.",
              "studies": []}
    gfrp, identity = saved["gfrp"]
    models = gfrp["evaluation"]["models"]
    lr = models["logistic_regression"]
    gkeys = ["balanced_accuracy", "roc_auc", "f1"]
    result["studies"].append({**identity, "id": "gfrp", "title": "GFRP acoustic tap screening", "task": "tap_screening",
        "native_sample_rate_hz": gfrp["dataset"]["rows"][0]["source_rate_hz"],
        "counts": [{"label": "unaugmented taps", "value": gfrp["dataset"]["retained_sample_count"]},
                   {"label": "physical plates", "value": len(set(gfrp["evaluation_plate_groups"]))}],
        "source_url": gfrp["provenance"]["url"], "doi": None, "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "evidence_scope": gfrp["scope"], "validation": gfrp["split"],
        "headline": {"label": "Logistic regression balanced accuracy", "value": lr["aggregate"]["balanced_accuracy"], "unit": "fraction"},
        "interval": {"label": "95% whole-plate cluster bootstrap; eight plates, fixed out-of-fold predictions",
                     "bounds": lr["plate_cluster_bootstrap"]["ci95_percentile"]["balanced_accuracy"], "unit": "fraction"},
        "tables": [{"caption": "Publisher-labelled screening. Balanced accuracy averages sensitivity and specificity.",
                    "columns": [column("balanced_accuracy", "Balanced accuracy", "fraction"), column("roc_auc", "AUROC", "fraction"), column("f1", "Defect F1", "fraction")],
                    "rows": [row(label, models[key]["aggregate"], gkeys) for key, label in [("majority_no_features", "Majority baseline"), ("logistic_regression", "Logistic regression"), ("random_forest", "Random forest")]]}],
        "risks": [f"This is screening of labelled tap locations; {lr['aggregate']['balanced_accuracy']:.1%} balanced accuracy is not defect-localization accuracy.",
                  f"Logistic regression retained {lr['aggregate']['confusion_counts']['fn']} missed defect labels and {lr['aggregate']['confusion_counts']['fp']} false alarms.",
                  "Eight plates and correlated repeat taps; annotations were not independently remeasured. Previously seen data, not a new blind trial."]})

    impact, identity = saved["impact"]
    imeta, imodels = impact["metadata"], impact["summary"]
    ikeys = ["mean_error_mm", "median_error_mm", "success_within_100_mm"]
    result["studies"].append({**identity, "id": "impact", "title": "Transient impact-source localization", "task": "transient_source_localization",
        "native_sample_rate_hz": imeta["sample_rate_hz"],
        "counts": [{"label": "measured positions", "value": imeta["position_records"]}, {"label": "physical plates", "value": imeta["independent_specimens"]}],
        "source_url": "https://zenodo.org/records/10875042", "doi": imeta["doi"], "license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "evidence_scope": "Three-channel measured source-position recordings; transient excitation, not persistent hidden-defect localization.",
        "validation": imeta["evaluation"].replace("_", " "),
        "headline": {"label": "Train-only calibrated TDoA mean position error", "value": imodels["calibrated_tdoa_q05"]["mean_error_mm"], "unit": "mm"},
        "interval": None,
        "tables": [{"caption": "Leave-one-position-out errors; lower mean/median is better.",
                    "columns": [column("mean_error_mm", "Mean error", "mm"), column("median_error_mm", "Median error", "mm"), column("success_within_100_mm", "Within 100 mm", "fraction")],
                    "rows": [row(label, imodels[key], ikeys) for key, label in [("train_centroid", "Training centroid"), ("knn_3", "3-nearest neighbours"), ("calibrated_tdoa_q05", "Calibrated TDoA")]]}],
        "risks": ["One plate, nine measured positions; no cross-specimen confidence interval.",
                  "No independent repeat axis is established. The previous simulations were excluded.",
                  f"{imodels['calibrated_tdoa_q05']['mean_error_mm']:.0f} mm mean error remains substantial; the audio-range ARGUS hardware was not evaluated."]})

    morpho, identity = saved["morpho"]
    mmeta, mmodels = morpho["metadata"], morpho["summary"]
    rf = mmodels["random_forest"]["pooled_completed_fold_metrics"]
    mkeys = ["true_bad", "missed_bad", "bad_recall", "balanced_accuracy"]
    result["studies"].append({**identity, "id": "morpho", "title": "MORPHO acquisition-quality check", "task": "acquisition_quality",
        "native_sample_rate_hz": mmeta["sample_rate_hz"],
        "counts": [{"label": "selected operator labels", "value": rf["samples"]}, {"label": "physical panels", "value": len(morpho["schema_audit"])}],
        "source_url": "https://zenodo.org/records/20120070", "doi": mmeta["dataset_doi"], "license": "CC BY 4.0", "license_url": "https://creativecommons.org/licenses/by/4.0/",
        "evidence_scope": "Operator-labelled GOOD/BAD ultrasonic signal quality; neither defect detection nor localization.",
        "validation": mmeta["split"].replace("_", " "),
        "headline": {"label": "Random forest BAD recordings caught", "value": rf["true_bad"], "unit": "count"}, "interval": None,
        "tables": [{"caption": f"BAD is the positive class: {rf['bad_support']} BAD and {rf['good_support']} GOOD labels.",
                    "columns": [column("true_bad", "BAD caught", "count"), column("missed_bad", "BAD missed", "count"), column("bad_recall", "BAD recall", "fraction"), column("balanced_accuracy", "Balanced accuracy", "fraction")],
                    "rows": [row(label, mmodels[key]["pooled_completed_fold_metrics"], mkeys) for key, label in [("majority_dummy", "Majority baseline"), ("logistic_regression", "Logistic regression"), ("random_forest", "Random forest")]]}],
        "risks": [f"Random forest missed {rf['missed_bad']} of {rf['bad_support']} BAD labels. Reject this quality model for deployment.",
                  "High overall accuracy mostly reflects GOOD-label prevalence; it does not establish usable fault detection.",
                  "Five panels, selected human labels, uneven BAD prevalence and README/HDF5 cycle-count disagreements."]})

    ogw, identity = saved["ogw"]
    ometa = ogw["metadata"]
    if ogw["bank_failures"] or ogw["fold_failures"]: raise ValueError("OGW summary requires review of failed input banks/folds")
    chosen = [entry for entry in ogw["summary"] if entry["budget"] == 32]
    if len(chosen) != 10 or any(not entry["comparison_has_complete_condition_coverage"] for entry in chosen):
        raise ValueError("Incomplete OGW 32-path comparison")
    adaptive = next(entry for entry in chosen if entry["context"] == "condition_matched_baseline" and entry["policy"] == "adaptive_disagreement")
    okeys = ["mean_location_error_mm", "mean_healthy_false_positive_condition_model_rate", "mean_damage_decision_rate"]
    labels = {"cyclic": "Cyclic", "geometry_spread": "Geometry spread", "training_static": "Training static", "adaptive_disagreement": "Adaptive disagreement", "random": "Random (16 orders)"}
    result["studies"].append({**identity, "id": "ogw", "title": "OGW measured-path replay", "task": "recorded_path_replay",
        "native_sample_rate_hz": ometa["native_sample_rate_hz"],
        "counts": [{"label": "full measured banks", "value": len(ogw["source_banks"])}, {"label": "physical plates", "value": ometa["independent_specimens"]}, {"label": "reference locations", "value": ometa["independent_reference_damage_positions"]}, {"label": "recorded paths per bank", "value": ometa["recorded_paths"]}],
        "source_url": "https://doi.org/10.6084/m9.figshare.c.4488089.v1", "doi": ometa["doi"], "license": ometa["data_license"], "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "evidence_scope": "Native 40 kHz ultrasonic offline path reveals for four reversible surface-disc locations; not a live adaptive acquisition trial.",
        "validation": "Leave an entire reference position out; first healthy cycle for baseline, second for test. 32 of 66 recorded paths revealed per trajectory.",
        "headline": {"label": "Condition-matched adaptive mean location error", "value": adaptive["mean_location_error_mm"], "unit": "mm"}, "interval": None,
        "tables": [{"caption": f"{'Condition-matched baseline' if context=='condition_matched_baseline' else 'Fixed 20°C baseline'} · 32 path reveals; lower location error is better.",
                    "columns": [column("mean_location_error_mm", "Mean error", "mm"), column("mean_healthy_false_positive_condition_model_rate", "Healthy false alarms", "fraction"), column("mean_damage_decision_rate", "Damage decisions", "fraction")],
                    "rows": [row(labels[entry["policy"]], entry, okeys) for entry in chosen if entry["context"] == context]}
                   for context in ("condition_matched_baseline", "twenty_degree_baseline")],
        "risks": [f"Condition-matched adaptive healthy false alarms: {adaptive['mean_healthy_false_positive_condition_model_rate']:.1%}. This is unsuitable for deployment.",
                  "Healthy rates repeat only three unique healthy banks across four fitted models; trajectories are not independent specimens.",
                  "One plate, four reversible aluminium-disc references. Ultrasound and approximate spatial weights do not validate the 16 kHz ARGUS probe.",
                  "Temperature matching is not unseen-temperature generalization. Whole-archive MD5 is unverified; selected member CRC/SHA were checked."]})
    payload = json.dumps(result, indent=2, allow_nan=False).encode("utf-8") + b"\n"
    if len(payload) > 100000: raise ValueError("Public measured summary exceeds 100 KB")
    # Check that report files remained unchanged during source verification/export.
    for study in result["studies"]:
        if sha256(ROOT / study["artifact"]["path"]) != study["artifact"]["sha256"]:
            raise ValueError("Study artifact changed during export")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_bytes(payload); temporary.replace(OUTPUT)
    print(f"Exported {len(result['studies'])} source-verified studies ({len(payload)} bytes) to {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__": main()
