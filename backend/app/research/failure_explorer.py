from __future__ import annotations


def classify_failure(run: dict, maximum_measurements: int) -> list[str]:
    reasons = []
    if run.get("localization_error_mm", 0) > 30:
        reasons.append("localization_failed")
    if run.get("measurements", 0) >= maximum_measurements and not run.get("criterion_reached", False):
        reasons.append("excessive_measurements")
    if run.get("false_confidence", False):
        reasons.append("posterior_overconfident")
    if run.get("abstained", False):
        reasons.append("ood_or_abstention")
    if run.get("calibration_hurt", False):
        reasons.append("calibration_hurt")
    return reasons


def build_failure_explorer(benchmark: dict) -> dict:
    maximum = int(benchmark.get("metadata", {}).get("max_experiments", 0))
    failures = []
    for run in benchmark.get("runs", []):
        reasons = classify_failure(run, maximum)
        if reasons:
            failures.append({"seed": run.get("seed"), "strategy": run.get("strategy"), "reasons": reasons, "trace": run.get("action_trace", []), "metrics": {key: value for key, value in run.items() if key != "action_trace"}})
    return {"failure_count": len(failures), "runs": failures}

