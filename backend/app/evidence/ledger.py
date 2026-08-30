from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import numpy as np

from backend.app.database.repository import SessionRepository


GENESIS_HASH = "0" * 64


def json_safe(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        return {str(key): json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_safe(item) for item in value]
    return value


def canonical_bytes(value: object) -> bytes:
    return json.dumps(json_safe(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def canonical_hash(value: object) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def software_revision(root: str | Path | None = None) -> str:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True, timeout=2, check=True
        ).stdout.strip()
    except Exception:
        return "uncommitted-or-unavailable"


class EvidenceLedger:
    def __init__(self, repository: SessionRepository, repository_root: str | Path | None = None) -> None:
        self.repository = repository
        self.repository_root = repository_root

    def append(self, session_id: str, result, engine, acquisition_source: str) -> dict:
        prior_entries = self.repository.list_ledger_entries(session_id)
        previous_hash = prior_entries[-1]["entry_hash"] if prior_entries else GENESIS_HASH
        raw_hash = sha256(np.asarray(result.signal, dtype=np.float32).tobytes()).hexdigest()
        entry = {
            "schema_version": 1,
            "session_id": session_id,
            "experiment_number": result.index,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "previous_record_hash": previous_hash,
            "experiment_specification": result.parameters.to_dict(),
            "action_type": result.action_type,
            "acquisition_source": acquisition_source,
            "raw_data_hash": raw_hash,
            "processed_data_hash": canonical_hash(result.analysis),
            "preprocessing_configuration": {
                "sample_rate": engine.config.sample_rate,
                "bandpass_hz": [250.0, 7_000.0],
                "pipeline": "dc_remove->bandpass->features/v1",
            },
            "posterior_before_hash": canonical_hash(result.posterior_before),
            "posterior_after_hash": canonical_hash(result.posterior_after),
            "likelihood_hash": canonical_hash(result.likelihood),
            "model_id": result.recommendation.reason_for_fidelity,
            "model_fidelity_level": result.recommendation.chosen_model_fidelity,
            "planner_configuration": engine.config.to_dict(),
            "recommendation_score_components": result.recommendation.to_dict(),
            "calibration_state": engine.joint_state.last_calibration,
            "quality_state": result.quality,
            "ood_state": engine.joint_state.ood_state,
            "model_discrepancy_state": engine.joint_state.discrepancy_state,
            "software_revision": software_revision(self.repository_root),
            "random_seed": engine.seed,
        }
        entry_hash = canonical_hash(entry)
        self.repository.append_ledger_entry(session_id, result.index, previous_hash, json_safe(entry), entry_hash)
        return {"entry": json_safe(entry), "entry_hash": entry_hash}

    def verify(self, session_id: str) -> dict:
        entries = self.repository.list_ledger_entries(session_id)
        expected_previous = GENESIS_HASH
        for position, record in enumerate(entries, start=1):
            entry = record["entry"]
            if record["experiment_index"] != position:
                return {"status": "FAILED", "valid": False, "failed_at_record": position, "reason": "non_contiguous_experiment_index"}
            if record["previous_hash"] != expected_previous or entry.get("previous_record_hash") != expected_previous:
                return {"status": "FAILED", "valid": False, "failed_at_record": position, "reason": "previous_hash_mismatch"}
            calculated = canonical_hash(entry)
            if calculated != record["entry_hash"]:
                return {"status": "FAILED", "valid": False, "failed_at_record": position, "reason": "entry_hash_mismatch"}
            expected_previous = record["entry_hash"]
        return {
            "status": "PASS",
            "valid": True,
            "record_count": len(entries),
            "head_hash": expected_previous,
        }

