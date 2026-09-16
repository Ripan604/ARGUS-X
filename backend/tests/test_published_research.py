import hashlib
import json

import pytest

from scripts.publish_research_report import ROOT, compact_report


def test_published_report_is_derived_from_raw_evidence_not_handwritten_metrics():
    source = (ROOT / "research_results/nuisance_design_validation.json").read_bytes()
    full = json.loads(source)
    compact = compact_report(source)
    assert compact["summary"] == full["summary"]
    assert compact["paired_comparisons"] == full["paired_comparisons"]
    assert compact["artifact_sha256"] == hashlib.sha256(source).hexdigest()
    published = json.loads((ROOT / "frontend/public/research/nuisance-design-summary.json").read_text())
    assert published == compact
    assert "runs" not in compact  # No full trace payload in the initial browser download.


def test_publication_refuses_unmarked_or_changing_evidence():
    artifact = json.loads((ROOT / "research_results/nuisance_design_validation.json").read_text())
    artifact["metadata"]["source_changed_during_run"] = True
    with pytest.raises(ValueError, match="source changed"):
        compact_report(json.dumps(artifact).encode())
    artifact["metadata"]["source_changed_during_run"] = False
    artifact["metadata"]["evidence_source"] = "physical"
    with pytest.raises(ValueError, match="synthetic"):
        compact_report(json.dumps(artifact).encode())
