from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import subprocess

import numpy as np

from backend.app.database.repository import SessionRepository


GENESIS_HASH = "0" * 64
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".css", ".json", ".toml",
                   ".yaml", ".yml", ".txt", ".h", ".c", ".cpp", ".ino", ".ps1", ".sh", ".bat", ".html", ".lock"}
SOURCE_PATHS = ["backend", "frontend", "scripts", "firmware", "run_argus.py", "run_argus.ps1", "run_edge_node.py",
                "start_argus.bat", "start_argus.sh", "start_backend.bat", "start_backend.sh", "start_frontend.bat", "start_frontend.sh"]


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
    return json.dumps(json_safe(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def canonical_hash(value: object) -> str:
    return sha256(canonical_bytes(value)).hexdigest()


def software_revision(root: str | Path | None = None) -> str:
    """Commit plus current source fingerprint; generated data are not source.

    A commit ID alone is misleading when experiments use an edited checkout.
    This is reproducibility metadata, not proof of authorship or a signature.
    """
    source_root = Path(root).resolve() if root is not None else Path(__file__).resolve().parents[3]
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=source_root, capture_output=True,
                                  text=True, timeout=2, check=True).stdout.strip()
        listed = subprocess.run(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z", "--", *SOURCE_PATHS],
                                cwd=source_root, capture_output=True, timeout=2, check=True).stdout
        names = sorted({name.decode("utf-8", errors="strict") for name in listed.split(b"\0") if name
                        and Path(name.decode("utf-8", errors="strict")).suffix.lower() in SOURCE_SUFFIXES})
        digest = sha256()
        for name in names:
            path = source_root / name
            digest.update(name.encode("utf-8") + b"\0")
            if path.is_symlink():
                digest.update(b"SYMLINK\0" + str(path.readlink()).encode("utf-8"))
            elif path.is_file():
                digest.update(b"FILE\0" + str(path.stat().st_size).encode("ascii") + b"\0")
                with path.open("rb") as handle:
                    for block in iter(lambda: handle.read(65_536), b""):
                        digest.update(block)
            else:
                digest.update(b"MISSING\0")
        return f"{revision}+source-sha256:{digest.hexdigest()}"
    except Exception:
        return "source-identity-unavailable"


def experiment_content_hashes(experiment: dict) -> dict:
    return {
        "raw_data_hash": sha256(np.asarray(experiment["signal"], dtype=np.float32).tobytes()).hexdigest(),
        "processed_data_hash": canonical_hash(experiment["features"]),
        "posterior_before_hash": canonical_hash(np.asarray(experiment["posterior_before"], dtype=np.float64)),
        "posterior_after_hash": canonical_hash(np.asarray(experiment["posterior_after"], dtype=np.float64)),
        "likelihood_hash": canonical_hash(np.asarray(experiment["likelihood"], dtype=np.float64)),
        "planner_metadata_hash": canonical_hash(experiment["planner"]),
        "diagnostics_metadata_hash": canonical_hash(experiment["diagnostics"]),
    }


def ledger_measurement_matches(entry: dict, experiment: dict) -> bool:
    """Bind a record to stored acquisition content, keeping v1 readable."""
    if entry.get("schema_version") not in {1, 2}:
        return False
    hashes = experiment_content_hashes(experiment)
    required_hashes = hashes if entry["schema_version"] == 2 else {
        key: value for key, value in hashes.items() if key not in {"planner_metadata_hash", "diagnostics_metadata_hash"}
    }
    return (all(entry.get(key) == value for key, value in required_hashes.items())
            and canonical_hash(entry.get("experiment_specification")) == canonical_hash(experiment["parameters"])
            and canonical_hash(entry.get("recommendation_score_components")) == canonical_hash(experiment["planner"])
            and canonical_hash(entry.get("quality_state")) == canonical_hash(experiment["diagnostics"].get("quality"))
            and entry.get("action_type") == experiment["diagnostics"].get("action_type"))


class EvidenceLedger:
    def __init__(self, repository: SessionRepository, repository_root: str | Path | None = None) -> None:
        self.repository = repository
        self.repository_root = repository_root

    def append(self, session_id: str, result, engine, acquisition_source: str) -> dict:
        prior_entries = self.repository.list_ledger_entries(session_id)
        previous_hash = prior_entries[-1]["entry_hash"] if prior_entries else GENESIS_HASH
        raw_hash = sha256(np.asarray(result.signal, dtype=np.float32).tobytes()).hexdigest()
        entry = {
            "schema_version": 2,
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
            "planner_metadata_hash": canonical_hash(result.recommendation.to_dict()),
            "diagnostics_metadata_hash": canonical_hash({
                **result.diagnostics, "quality": result.quality,
                "calibration_result": result.calibration_result, "action_type": result.action_type,
            }),
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

    def verify(self, session_id: str, *, trusted_head_hash: str | None = None, trusted_record_count: int | None = None) -> dict:
        if self.repository.get_session(session_id) is None:
            return {"status": "FAILED", "valid": False, "reason": "session_not_found"}
        try:
            entries = self.repository.list_ledger_entries(session_id)
            experiments = self.repository.list_experiments(session_id, include_signal=True)
        except (TypeError, ValueError, KeyError, OverflowError) as exc:
            return {"status": "FAILED", "valid": False, "reason": "invalid_stored_evidence"}
        if (trusted_head_hash is None) != (trusted_record_count is None):
            raise ValueError("A trusted checkpoint requires both head hash and record count")
        if trusted_head_hash is not None and (not isinstance(trusted_head_hash, str) or len(trusted_head_hash) != 64 or any(c not in "0123456789abcdef" for c in trusted_head_hash)
                                               or isinstance(trusted_record_count, bool) or not isinstance(trusted_record_count, int) or trusted_record_count < 0):
            raise ValueError("Trusted checkpoint requires a lowercase SHA-256 hash and nonnegative integer count")
        if len(entries) != len(experiments):
            return {"status": "FAILED", "valid": False, "reason": "ledger_experiment_count_mismatch"}
        expected_previous = GENESIS_HASH
        for position, record in enumerate(entries, start=1):
            entry = record["entry"]
            if not isinstance(entry, dict):
                return {"status": "FAILED", "valid": False, "failed_at_record": position, "reason": "invalid_entry_schema"}
            if entry.get("session_id") != session_id or entry.get("experiment_number") != position:
                return {"status": "FAILED", "valid": False, "failed_at_record": position, "reason": "entry_identity_mismatch"}
            if record["experiment_index"] != position:
                return {"status": "FAILED", "valid": False, "failed_at_record": position, "reason": "non_contiguous_experiment_index"}
            if record["previous_hash"] != expected_previous or entry.get("previous_record_hash") != expected_previous:
                return {"status": "FAILED", "valid": False, "failed_at_record": position, "reason": "previous_hash_mismatch"}
            try:
                calculated = canonical_hash(entry)
            except (TypeError, ValueError, OverflowError):
                return {"status": "FAILED", "valid": False, "failed_at_record": position, "reason": "invalid_entry_schema"}
            if calculated != record["entry_hash"]:
                return {"status": "FAILED", "valid": False, "failed_at_record": position, "reason": "entry_hash_mismatch"}
            experiment = experiments[position - 1]
            try:
                matches = ledger_measurement_matches(entry, experiment)
            except (KeyError, TypeError, ValueError, OverflowError):
                matches = False
            if not matches:
                return {"status": "FAILED", "valid": False, "failed_at_record": position, "reason": "measurement_data_mismatch"}
            expected_previous = record["entry_hash"]
        if trusted_head_hash is not None and (trusted_head_hash != expected_previous or trusted_record_count != len(entries)):
            return {"status": "FAILED", "valid": False, "reason": "trusted_checkpoint_mismatch"}
        return {
            "status": "PASS",
            "valid": True,
            "record_count": len(entries),
            "head_hash": expected_previous,
            "verification_scope": "measurement_content_and_trusted_checkpoint" if trusted_head_hash is not None else "local_content_and_chain_consistency",
            "externally_anchored": trusted_head_hash is not None,
            "authenticity_verified": False,
            "limitation": "A whole-history rewrite is detectable only against a checkpoint retained independently; this is not a signature or trusted timestamp.",
        }

    def checkpoint(self, session_id: str) -> dict:
        if self.repository.get_session(session_id) is None:
            raise KeyError(session_id)
        report = self.verify(session_id)
        if not report["valid"]:
            raise ValueError("Cannot checkpoint an inconsistent evidence ledger")
        return {"schema_version": 1, "session_id": session_id, "record_count": report["record_count"],
                "head_hash": report["head_hash"], "retain_independently": True,
                "created_at": datetime.now(timezone.utc).isoformat()}
