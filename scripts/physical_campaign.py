"""Prepare a measured response-bank plan or audit an actual acquisition manifest.

No command generates physical evidence. The plan deliberately contains no truth
labels or WAV samples; record these using an independently documented specimen.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import numpy as np
from backend.app.control.dual_control import AdaptiveDualControlManager
from backend.app.evaluation.research_validation import candidate_banks
from backend.app.models.domain import Experiment, Panel
from backend.app.replay.datasets import WAVCollectionCounterfactualDataset, action_key


def make_plan() -> dict:
    diagnostics = candidate_banks(62000, 1, 16)[0]
    calibrations = [AdaptiveDualControlManager.calibration_experiment("direct_path", i) for i in range(3)]
    return {
        "schema_version": 1, "evidence_source": "planned_not_acquired",
        "metadata": {"specimen_id": "REPLACE", "acquisition_session_id": "REPLACE", "split": "test",
                     "panel": Panel().to_dict(), "units": "normalized_pcm", "recording_chain": "REPLACE",
                     "synchronization_method": "REPLACE", "coupling_protocol": "REPLACE",
                     "physical_target": "REPLACE: impact proxy or independently verified persistent defect",
                     "reference_truth_method": "REPLACE", "reference_truth_uncertainty_mm": None,
                     "temperature_c": None, "sample_rate": 16000},
        "truth": {},
        "actions": [{"experiment": e.to_dict(), "wav": f"diagnostic_{i+1:02d}.wav", "action_type": "diagnostic"}
                    for i, e in enumerate(diagnostics)] +
                   [{"experiment": e.to_dict(), "wav": f"reference_{i+1:02d}.wav", "action_type": "calibration", "calibration_type": "direct_path"}
                    for i, e in enumerate(calibrations)],
        "instructions": ["Use one manifest per independent remount/session and specimen.",
                         "Acquire every listed action. Never synthesize missing WAV files.",
                         "A direct-path reference must exclude defect scatter through a justified acquisition protocol.",
                         "Use a common clock/trigger or document and measure timing offset.",
                         "Assign entire specimens to train, calibration or test before model fitting.",
                         "Store sealed reference labels separately from the operator during blind trials.",
                         "Replace evidence_source with physical only after actual acquisition; preserve raw files."]}


def audit_manifests(paths: list[Path]) -> dict:
    specimen_splits: dict[str, str] = {}
    seen_sessions: set[str] = set()
    observations: dict[str, str] = {}
    action_sets: list[set[str]] = []
    rows, errors = [], []
    for path in paths:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            metadata = payload["metadata"]
            if payload.get("evidence_source") != "physical":
                raise ValueError("Manifest is not declared acquired physical evidence")
            for key in ("specimen_id", "acquisition_session_id", "recording_chain", "synchronization_method",
                        "coupling_protocol", "physical_target", "reference_truth_method", "units"):
                if not isinstance(metadata.get(key), str) or not metadata[key].strip() or "REPLACE" in metadata[key]:
                    raise ValueError(f"Missing measured metadata: {key}")
            split, specimen, session = metadata["split"], metadata["specimen_id"], metadata["acquisition_session_id"]
            if split not in {"train", "calibration", "test"}:
                raise ValueError("Split must be train, calibration or test")
            if specimen in specimen_splits and specimen_splits[specimen] != split:
                raise ValueError("Specimen leakage across dataset splits")
            if session in seen_sessions:
                raise ValueError("Duplicate acquisition session")
            specimen_splits[specimen] = split
            seen_sessions.add(session)
            Panel(**metadata["panel"])
            uncertainty = metadata.get("reference_truth_uncertainty_mm")
            if not isinstance(uncertainty, (float, int)) or not np.isfinite(uncertainty) or uncertainty < 0:
                raise ValueError("Reference-truth uncertainty must be recorded in millimetres")
            truth = payload.get("truth", {})
            if not all(isinstance(truth.get(k), (int, float)) and np.isfinite(truth[k]) and 0 <= truth[k] <= 1 for k in ("center_x", "center_y")):
                raise ValueError("Independently measured normalized reference coordinates are required")
            dataset = WAVCollectionCounterfactualDataset(path)
            metadata_loaded = dataset.get_metadata()
            keys = set()
            for action in dataset.list_available_actions():
                key = action_key(action)
                signal = dataset.get_observation(action)
                rate = metadata_loaded["sample_rates"][key]
                if len(signal) < round(Experiment(**action).duration_s * rate):
                    raise ValueError("An acquisition is shorter than the declared excitation window")
                digest = sha256(signal.tobytes()).hexdigest()
                if digest in observations:
                    raise ValueError(f"Duplicate raw samples, also present in {observations[digest]}")
                observations[digest] = str(path)
                keys.add(key)
            action_sets.append(keys)
            rows.append({"manifest": str(path), "sha256": sha256(path.read_bytes()).hexdigest(),
                         "specimen_id": specimen, "split": split, "actions": len(keys)})
        except (ValueError, KeyError, TypeError, OSError) as exc:
            errors.append({"manifest": str(path), "error": str(exc)})
    if action_sets and any(keys != action_sets[0] for keys in action_sets[1:]):
        errors.append({"error": "Counterfactual action coverage differs between sessions"})
    return {"valid": not errors and bool(rows), "manifests": rows, "errors": errors,
            "independent_specimens": len(specimen_splits), "evidence_source": "physical_manifest_audit",
            "accuracy_established": False, "patentability_established": False,
            "limitation": "Metadata and file checks cannot authenticate specimens or replace blind physical validation."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    plan = sub.add_parser("plan")
    plan.add_argument("--output", type=Path, required=True)
    audit = sub.add_parser("audit")
    audit.add_argument("manifests", nargs="+", type=Path)
    audit.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output exists; choose a new path to preserve acquisition/evidence records")
    result = make_plan() if args.command == "plan" else audit_manifests(args.manifests)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "valid": result.get("valid"), "errors": result.get("errors", [])}))
    if args.command == "audit" and not result["valid"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
