"""Publish a small browser-readable view of the recorded paired experiment.

This never launches a benchmark or changes results; the full artifact is the
source of truth. Regenerate after deliberately updating that artifact.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def compact_report(artifact_bytes: bytes) -> dict:
    artifact = json.loads(artifact_bytes)
    metadata = artifact["metadata"]
    if metadata["evidence_source"] != "synthetic_only":
        raise ValueError("This report view only supports explicitly synthetic evidence")
    if metadata["source_changed_during_run"]:
        raise ValueError("Cannot publish a run whose source changed during execution")
    report = {
        "schema_version": 1,
        "evidence_source": "synthetic_only",
        "artifact": "research_results/nuisance_design_validation.json",
        "artifact_sha256": hashlib.sha256(artifact_bytes).hexdigest(),
        "command": metadata["command"],
        "seeds": metadata["seeds"],
        "steps": metadata["steps"],
        "candidate_count": metadata["candidate_count"],
        "summary": artifact["summary"],
        "paired_comparisons": artifact["paired_comparisons"],
    }
    # Refuse NaN/Infinity rather than letting the browser display false evidence.
    json.dumps(report, allow_nan=False)
    return report


if __name__ == "__main__":
    source = ROOT / "research_results/nuisance_design_validation.json"
    destination = ROOT / "frontend/public/research/nuisance-design-summary.json"
    destination.parent.mkdir(parents=True, exist_ok=True)
    report = compact_report(source.read_bytes())
    destination.write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"Published {destination.relative_to(ROOT)} from SHA-256 {report['artifact_sha256']}")
