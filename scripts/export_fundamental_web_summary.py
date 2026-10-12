"""Export a compact, source-checked view of completed fundamental studies.

Reads preserved results only. It neither fits a model nor reruns an experiment.
Refuses changed/missing study artifacts or source manifests instead of presenting
stale measurements as current verification.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "frontend/public/research/fundamental-summary.json"
SUMMARY = "output/fundamental_upgrade_summary.json"
DOC = "docs/FUNDAMENTAL_UPGRADE_RESULTS_2026_10_08.md"
ARTIFACTS = {
    "healthy": "healthy_reference_development_2026_10_08.json",
    "development": "reference_conditioned_development_2026_10_08.json",
    "confirmation": "reference_conditioned_confirmation_2026_10_08.json",
}
VARIANTS = {"raw_global": "Raw response / global noise", "transport_global": "Healthy transport / global noise",
            "transport_heteroscedastic": "Healthy transport / path-specific noise"}


def digest(path: Path) -> str:
    result = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def source_path(name: str) -> Path:
    if not isinstance(name, str):
        raise ValueError("Source-manifest paths must be strings")
    path = PurePosixPath(name)
    if path.is_absolute() or ".." in path.parts or "\\" in name or ":" in name or str(path) != name:
        raise ValueError("Unsafe source-manifest path")
    resolved = (ROOT / name).resolve()
    if not resolved.is_relative_to(ROOT) or not resolved.is_file():
        raise ValueError(f"Source artifact is missing or outside the project: {name}")
    return resolved


def read_json(path: Path) -> dict:
    if path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError("Study JSON exceeds the export reader size bound")
    def finite(value):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Study JSON contains a non-finite value")
        return number
    value = json.loads(path.read_text(encoding="utf-8"), parse_float=finite,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Non-finite study JSON")))
    if not isinstance(value, dict):
        raise ValueError("Study JSON must be an object")
    return value


def verify_sources(report: dict) -> dict:
    metadata = report["metadata"]
    before, after = metadata["source_sha256_before"], metadata["source_sha256_after"]
    if not isinstance(before, dict) or not before or before != after or metadata.get("source_changed_during_run") is not False:
        raise ValueError("Study source hashes changed during its execution")
    for name, expected in before.items():
        if not isinstance(expected, str) or len(expected) != 64 or digest(source_path(name)) != expected:
            raise ValueError(f"Current source/data does not match the recorded study: {name}")
    return {"files_checked": len(before), "matches_at_export": True, "source_changed_during_run": False,
            "manifest_sha256": sha256(json.dumps(before, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}


def stage_summary(stage: str, report: dict) -> dict:
    if report.get("status") != "completed" or report.get("stage") != stage or report.get("failures"):
        raise ValueError(f"{stage} study is missing completion or retains failed opportunities")
    if report.get("confirmation_scored") is not (stage == "confirmation"):
        raise ValueError("Study stage and confirmation state disagree")
    meta = report["metadata"]
    if meta["independent_specimens"] != 1 or meta.get("gate_exchangeability_verified") is not False or meta.get("gate_field_coverage_established") is not False:
        raise ValueError("Study scope flags require scientific review")
    runs, calibrations = report["runs"], report["calibrations"]
    if not runs or not calibrations or any(row.get("error") is not None for row in calibrations):
        raise ValueError("Incomplete trajectory calibration")
    blocks = {block for item in calibrations for block in item["calibration"]["block_ids"]}
    rows = []
    for variant, label in VARIANTS.items():
        summary = next(item for item in report["summary"] if item["variant"] == variant and item["policy"] == "adaptive")
        selected = [run for run in runs if run["variant"] == variant and run["policy"] == "adaptive"]
        damage = {run["source_sha256"] for run in selected if run["test_state"] != "healthy"}
        healthy = {run["source_sha256"] for run in selected if run["test_state"] == "healthy"}
        damage_alerts = {run["source_sha256"] for run in selected if run["test_state"] != "healthy" and run["any_prefix_supported_anomaly"]}
        healthy_alerts = {run["source_sha256"] for run in selected if run["test_state"] == "healthy" and run["any_prefix_supported_anomaly"]}
        if len(selected) != summary["trajectories"] or len(damage) != summary["damage_conditions"]:
            raise ValueError("Adaptive condition counts do not match recorded trajectories")
        error = summary["mean_conditional_location_error_mm"]
        if not isinstance(error, (int, float)) or isinstance(error, bool) or not math.isfinite(error) or error < 0:
            raise ValueError("Invalid recorded location error")
        rows.append({"variant": variant, "label": label, "mean_error_mm": error,
                     "damage_alerts": len(damage_alerts), "damage_conditions": len(damage),
                     "healthy_alerts": len(healthy_alerts), "unique_healthy_banks": len(healthy),
                     "model_order_trajectories": len(selected), "unsupported_trajectories": summary["gate_unsupported_count"],
                     "descriptive_healthy_model_positive_rate": summary["descriptive_healthy_model_positive_rate"]})
    return {"stage": stage, "previously_seen_data": meta["previously_seen_data"], "horizon": max(meta["budgets"]),
            "model_order_trajectories": len(runs), "controller_model_calibrations": len(calibrations),
            "unique_calibration_blocks": len(blocks), "unique_test_banks": len({run["source_sha256"] for run in runs}),
            "minimum_reference_rank": calibrations[0]["calibration"]["minimum_p_value"], "alpha": calibrations[0]["calibration"]["alpha"],
            "adaptive": rows}


def export_summary() -> dict:
    canonical_hash = digest(source_path(SUMMARY))
    document_hash = digest(source_path(DOC))
    canonical = read_json(source_path(SUMMARY))
    if (canonical.get("confirmation_status") != "completed" or canonical.get("confirmation_acquired") != canonical.get("confirmation_required")
            or canonical.get("field_accuracy_established") is not False or canonical.get("patent_novelty_established") is not False):
        raise ValueError("Canonical upgrade summary does not describe completed, bounded confirmation")
    saved, artifacts, source_checks = {}, [], []
    for role, filename in ARTIFACTS.items():
        path = source_path(f"research_results/{filename}")
        expected = canonical["artifact_sha256"][filename]
        if digest(path) != expected:
            raise ValueError(f"Study artifact hash does not match canonical results: {filename}")
        report = read_json(path)
        verification = verify_sources(report)
        saved[role] = report
        artifacts.append({"role": role, "path": f"research_results/{filename}", "sha256": expected, "source_verification": verification})
        source_checks.append(report["metadata"]["source_sha256_before"])
    healthy = saved["healthy"]
    development = stage_summary("development", saved["development"])
    confirmation = stage_summary("confirmation", saved["confirmation"])
    before, after = canonical["healthy_reference_diagnostic_mean_DI_before"], healthy["summary"]["mean_healthy_middle_left_out_DI"]
    if after != canonical["healthy_reference_diagnostic_mean_DI_after"] or healthy["summary"]["qualified_path_count"] != canonical["qualified_paths"]:
        raise ValueError("Canonical healthy-reference metrics disagree with preserved results")
    for key, stage in [("development_location_comparison", development), ("confirmation_location_comparison", confirmation)]:
        if any(row["mean_error_mm"] != next(item["mean_conditional_location_error_mm"] for item in canonical[key] if item["variant"] == row["variant"])
               for row in stage["adaptive"]):
            raise ValueError("Canonical location comparisons disagree with preserved results")
    if confirmation["unique_calibration_blocks"] + confirmation["unique_test_banks"] != canonical["confirmation_acquired"]:
        raise ValueError("Acquired bank counts disagree with the calibration/test identities")
    union = {name: value for manifest in source_checks for name, value in manifest.items()}
    result = {
        "schema_version": 1, "evidence_source": "measured_reference_conditioned_external_reanalysis",
        "review_date": canonical["date"], "exported_at_utc": datetime.now(timezone.utc).isoformat(),
        "hardware_validated": False, "field_accuracy_established": False, "patent_novelty_established": False,
        "status": "completed", "sources_verified_at_export": True, "source_files_checked": len(union),
        "scope": "Recorded OGW development and separate confirmation on one specimen; model/order trajectories reuse physical banks. No prospective ARGUS apparatus trial.",
        "source_url": "https://doi.org/10.6084/m9.figshare.c.4488089.v1", "license": "CC0 1.0",
        "license_url": "https://creativecommons.org/publicdomain/zero/1.0/",
        "native_sample_rate_hz": healthy["model"]["native_sample_rate_hz"], "excitation_hz": 40_000,
        "specimens": 1, "recorded_paths": healthy["summary"]["recorded_paths"], "qualified_paths": canonical["qualified_paths"],
        "healthy_reference": {"before_di": before, "after_di": after, "unit": "dimensionless_damage_index",
                              "paths_in_diagnostic_mean": healthy["summary"]["recorded_paths"], "healthy_anchors": healthy["metadata"]["healthy_anchors"],
                              "scope": "Leave-middle-temperature-out healthy reference discrepancy over all 66 paths, including unqualified fits; not localization accuracy."},
        "confirmation_acquired_banks": canonical["confirmation_acquired"], "confirmation_required_banks": canonical["confirmation_required"],
        "development": development, "confirmation": confirmation,
        "risks": [
            "Compensated adaptive localization worsened on separate confirmation: 161.2 mm raw, 206.5 mm global transport, 215.4 mm path-specific transport.",
            "Each adaptive variant produced supported alerts in 0 of 8 damage conditions and 0 of 2 unique healthy banks. Zero healthy alerts alongside zero damage detections does not establish detector success.",
            "864 confirmation trajectories and 216 controller/model calibrations reuse the same measured banks; they are not independent physical trials.",
            "Cooling calibration and warming tests on one plate have unverified exchangeability. No field false-alarm guarantee or specimen generalization is established.",
            "Qualified paths are a development selection; healthy residual scales remain proxies. Compensated/reference-gated modes remain experimental and outside production physical acquisition.",
        ],
        "artifacts": artifacts,
        "canonical_summary": {"path": SUMMARY, "sha256": canonical_hash},
        "review_document": {"path": DOC, "sha256": document_hash},
        "verification_scope": "Study JSON hashes and their recorded source/data SHA-256 manifests matched local files at export; the browser does not rehash raw recordings or rerun studies.",
    }
    for artifact in artifacts:
        if digest(source_path(artifact["path"])) != artifact["sha256"]:
            raise ValueError("Study changed during compact export")
    if digest(source_path(SUMMARY)) != canonical_hash or digest(source_path(DOC)) != document_hash:
        raise ValueError("Canonical summary or review document changed during export")
    payload = json.dumps(result, indent=2, allow_nan=False).encode("utf-8") + b"\n"
    if len(payload) > 100_000:
        raise ValueError("Compact public summary exceeds 100 KB")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix(".json.tmp")
    temporary.write_bytes(payload)
    temporary.replace(OUTPUT)
    print(f"Exported completed confirmation and healthy reference ({len(payload)} bytes; {len(union)} verified source/data files).")
    return result


if __name__ == "__main__":
    export_summary()
