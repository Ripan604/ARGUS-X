from __future__ import annotations

from hashlib import sha256
import io
import json
from pathlib import PurePosixPath
import re
import secrets
import zipfile

import numpy as np

from backend.app.database.repository import SessionRepository
from backend.app.core.config import ArgusConfig
from backend.app.evidence.ledger import GENESIS_HASH, canonical_hash, json_safe
from backend.app.inference.belief import normalize_probability_grid
from backend.app.inference.joint_state import JointInferenceState
from backend.app.models.domain import Defect, Experiment, Material, Panel
from backend.app.safety.constraints import NoGoRegion


MAX_BUNDLE_BYTES = 100 * 1024 * 1024
MAX_BUNDLE_EXPERIMENTS = 1_000
MAX_BUNDLE_MEMBERS = MAX_BUNDLE_EXPERIMENTS + 16
REQUIRED_FILES = {
    "session.json", "audit.json", "events.json", "README.txt",
    "experiments.json", "posterior_history.json", "configuration.json",
    "result_summary.json",
}


def _json_bytes(value: object) -> bytes:
    return json.dumps(json_safe(value), indent=2, sort_keys=True).encode("utf-8")


def _load_json(archive: zipfile.ZipFile, name: str):
    try:
        return json.loads(
            archive.read(name).decode("utf-8"),
            parse_constant=lambda value: (_ for _ in ()).throw(ValueError(f"Non-finite JSON number: {value}")),
        )
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Research bundle contains invalid {name}") from exc


def _validate_session_state(session: dict, experiments: list[dict]) -> None:
    if not isinstance(session, dict) or not isinstance(session.get("state"), dict):
        raise ValueError("Research bundle session state is missing")
    if session.get("mode") not in {"simulation", "physical"} or session.get("preset") not in {"easy", "medium", "hard"}:
        raise ValueError("Research bundle session mode or preset is invalid")
    original_id = session.get("id")
    if (
        not isinstance(original_id, str)
        or not 3 <= len(original_id) <= 128
        or re.fullmatch(r"[A-Za-z0-9_-]+", original_id) is None
    ):
        raise ValueError("Research bundle session id is invalid")
    state = session["state"]
    try:
        config = ArgusConfig(**state["config"])
        panel = Panel(**state["panel"])
        material = Material(**state["material"])
        if session["mode"] == "simulation":
            Defect(**state["truth"])
        elif state.get("truth") is not None:
            raise ValueError("physical session evidence must not contain synthetic ground truth")
        if state.get("joint_inference"):
            JointInferenceState.from_dict(state["joint_inference"], material)
        else:
            posterior = np.asarray(state["posterior"], dtype=np.float64)
            if posterior.shape != (config.grid_size, config.grid_size):
                raise ValueError("posterior shape does not match grid_size")
            normalize_probability_grid(posterior)
        state_experiments = [Experiment(**item).to_dict() for item in state.get("experiments", [])]
        metadata_experiments = [Experiment(**item["parameters"]).to_dict() for item in experiments]
        for item in state.get("no_go_regions", []):
            NoGoRegion(**item)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Research bundle contains invalid session state: {exc}") from exc
    if state_experiments != metadata_experiments:
        raise ValueError("Research bundle session history does not match experiment metadata")
    action_history = state.get("action_history")
    if action_history is not None and (
        not isinstance(action_history, list)
        or len(action_history) != len(experiments)
        or any(action not in {"diagnostic", "calibration", "verification", "exploration"} for action in action_history)
    ):
        raise ValueError("Research bundle action history is invalid")


def _validate_experiment_metadata(item: dict, grid_size: int, expected_index: int) -> None:
    required = {
        "experiment_index", "created_at", "parameters", "features", "posterior_before",
        "posterior_after", "likelihood", "planner", "diagnostics",
    }
    if not isinstance(item, dict) or not required <= set(item):
        raise ValueError(f"Experiment {expected_index} metadata is incomplete")
    try:
        if isinstance(item["experiment_index"], bool) or int(item["experiment_index"]) != expected_index:
            raise ValueError("Experiment indices must be contiguous and one-based")
        Experiment(**item["parameters"])
        for name in ("posterior_before", "posterior_after", "likelihood"):
            grid = np.asarray(item[name], dtype=np.float64)
            if grid.shape != (grid_size, grid_size):
                raise ValueError(f"Experiment {expected_index} has an invalid {name} shape")
            normalize_probability_grid(grid)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError(f"Experiment {expected_index} metadata is invalid: {exc}") from exc
    if not isinstance(item["features"], dict) or not isinstance(item["planner"], dict) or not isinstance(item["diagnostics"], dict):
        raise ValueError(f"Experiment {expected_index} contains invalid structured metadata")


def _validate_audit(audit: list[dict], experiments: list[dict], signals: list[np.ndarray], session_id: str) -> None:
    if len(audit) != len(experiments):
        raise ValueError("Evidence ledger length does not match experiment history")
    previous_hash = GENESIS_HASH
    for index, (record, item, signal) in enumerate(zip(audit, experiments, signals), start=1):
        entry = record.get("entry") if isinstance(record, dict) else None
        if not isinstance(entry, dict):
            raise ValueError(f"Evidence ledger record {index} is invalid")
        try:
            record_index = int(record.get("experiment_index", -1))
            entry_index = int(entry.get("experiment_number", -1))
        except (TypeError, ValueError) as exc:
            raise ValueError("Evidence ledger indices must be integers") from exc
        if record_index != index or entry_index != index:
            raise ValueError("Evidence ledger indices are not contiguous")
        if record.get("previous_hash") != previous_hash or entry.get("previous_record_hash") != previous_hash:
            raise ValueError(f"Evidence ledger chain is broken at record {index}")
        entry_hash = canonical_hash(entry)
        if record.get("entry_hash") != entry_hash:
            raise ValueError(f"Evidence ledger hash is invalid at record {index}")
        if entry.get("session_id") != session_id:
            raise ValueError(f"Evidence ledger session identity is invalid at record {index}")
        raw_hash = sha256(np.asarray(signal, dtype=np.float32).tobytes()).hexdigest()
        if entry.get("raw_data_hash") != raw_hash:
            raise ValueError(f"Evidence ledger signal hash is invalid at record {index}")
        if entry.get("processed_data_hash") != canonical_hash(item["features"]):
            raise ValueError(f"Evidence ledger processed-data hash is invalid at record {index}")
        if entry.get("posterior_before_hash") != canonical_hash(np.asarray(item["posterior_before"], dtype=np.float64)):
            raise ValueError(f"Evidence ledger prior hash is invalid at record {index}")
        if entry.get("posterior_after_hash") != canonical_hash(np.asarray(item["posterior_after"], dtype=np.float64)):
            raise ValueError(f"Evidence ledger posterior hash is invalid at record {index}")
        if entry.get("likelihood_hash") != canonical_hash(np.asarray(item["likelihood"], dtype=np.float64)):
            raise ValueError(f"Evidence ledger likelihood hash is invalid at record {index}")
        previous_hash = entry_hash


def export_research_bundle(repository: SessionRepository, session_id: str) -> bytes:
    session = repository.get_session(session_id)
    if session is None:
        raise KeyError(session_id)
    session_payload = json.loads(json.dumps({key: value for key, value in session.items() if key != "state_json"}))
    if session_payload.get("mode") == "physical":
        session_payload["state"]["truth"] = None
    experiments = repository.list_experiments(session_id, include_signal=True)
    ledger = repository.list_ledger_entries(session_id)
    events = repository.list_events(session_id)
    files: dict[str, bytes] = {
        "session.json": _json_bytes(session_payload),
        "audit.json": _json_bytes(ledger),
        "events.json": _json_bytes(events),
        "README.txt": (
            "ARGUS NEO research bundle\n"
            "Evidence source and limitations are recorded in session.json.\n"
            "This research prototype is not a certified safety-critical NDE report.\n"
        ).encode("utf-8"),
    }
    experiment_metadata = []
    posterior_history = []
    for item in experiments:
        signal = item.pop("signal")
        buffer = io.BytesIO()
        np.save(buffer, np.asarray(signal, dtype=np.float32), allow_pickle=False)
        files[f"signals/{int(item['experiment_index']):04d}.npy"] = buffer.getvalue()
        experiment_metadata.append(item)
        posterior_history.append(item["posterior_after"])
    files["experiments.json"] = _json_bytes(experiment_metadata)
    files["posterior_history.json"] = _json_bytes(posterior_history)
    files["configuration.json"] = _json_bytes(session_payload["state"].get("config", {}))
    result_summary = {
        "experiment_count": len(experiments),
        "revealed": bool(session_payload["state"].get("revealed", False)),
        "ledger_records": len(ledger),
        "ledger_head": ledger[-1]["entry_hash"] if ledger else None,
        "bundle_state_hash": canonical_hash(session_payload["state"]),
    }
    files["result_summary.json"] = _json_bytes(result_summary)
    manifest = {
        "schema_version": 1,
        "session_id": session_id,
        "files": {name: {"sha256": sha256(content).hexdigest(), "size": len(content)} for name, content in files.items()},
    }
    files["manifest.json"] = _json_bytes(manifest)
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
    return output.getvalue()


def import_research_bundle(repository: SessionRepository, payload: bytes) -> dict:
    if len(payload) > MAX_BUNDLE_BYTES:
        raise ValueError("Research bundle exceeds the 100 MB import limit")
    try:
        archive_context = zipfile.ZipFile(io.BytesIO(payload))
    except zipfile.BadZipFile as exc:
        raise ValueError("Invalid research bundle ZIP archive") from exc
    with archive_context as archive:
        members = archive.infolist()
        if len(members) > MAX_BUNDLE_MEMBERS:
            raise ValueError("Research bundle contains too many archive members")
        names = [item.filename for item in members]
        if len(names) != len(set(names)):
            raise ValueError("Research bundle contains duplicate member names")
        if sum(item.file_size for item in members) > MAX_BUNDLE_BYTES:
            raise ValueError("Expanded research bundle exceeds the 100 MB limit")
        for item in members:
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts or item.flag_bits & 0x1:
                raise ValueError("Research bundle contains an unsafe or encrypted member")
        manifest = _load_json(archive, "manifest.json")
        if not isinstance(manifest, dict) or manifest.get("schema_version") != 1 or not isinstance(manifest.get("files"), dict):
            raise ValueError("Research bundle manifest schema is invalid")
        manifest_files = set(manifest["files"])
        if manifest_files != set(names) - {"manifest.json"} or not REQUIRED_FILES <= manifest_files:
            raise ValueError("Research bundle members do not exactly match its manifest")
        for name, expected in manifest["files"].items():
            path = PurePosixPath(name)
            if path.is_absolute() or ".." in path.parts or not isinstance(expected, dict):
                raise ValueError("Research bundle manifest contains an unsafe entry")
            content = archive.read(name)
            expected_hash = expected.get("sha256")
            expected_size = expected.get("size")
            if (
                not isinstance(expected_hash, str)
                or len(expected_hash) != 64
                or isinstance(expected_size, bool)
                or not isinstance(expected_size, int)
                or expected_size < 0
                or len(content) != expected_size
                or sha256(content).hexdigest() != expected_hash
            ):
                raise ValueError(f"Research bundle integrity failure: {name}")

        session = _load_json(archive, "session.json")
        experiments = _load_json(archive, "experiments.json")
        audit = _load_json(archive, "audit.json")
        events = _load_json(archive, "events.json")
        posterior_history = _load_json(archive, "posterior_history.json")
        configuration = _load_json(archive, "configuration.json")
        result_summary = _load_json(archive, "result_summary.json")
        if not isinstance(experiments, list) or len(experiments) > MAX_BUNDLE_EXPERIMENTS:
            raise ValueError("Research bundle experiment count exceeds the import limit")
        if not isinstance(audit, list) or not isinstance(events, list):
            raise ValueError("Research bundle audit or event history is invalid")
        grid_size_raw = session.get("state", {}).get("config", {}).get("grid_size", 0) if isinstance(session, dict) else 0
        if isinstance(grid_size_raw, bool) or not isinstance(grid_size_raw, int) or not 4 <= grid_size_raw <= 256:
            raise ValueError("Research bundle grid_size is invalid")
        grid_size = grid_size_raw
        signals: list[np.ndarray] = []
        expected_signals: set[str] = set()
        for index, item in enumerate(experiments, start=1):
            _validate_experiment_metadata(item, grid_size, index)
            signal_name = f"signals/{index:04d}.npy"
            expected_signals.add(signal_name)
            try:
                signal = np.load(io.BytesIO(archive.read(signal_name)), allow_pickle=False)
            except (KeyError, ValueError, OSError) as exc:
                raise ValueError(f"Research bundle signal {index} is invalid") from exc
            if not isinstance(signal, np.ndarray) or signal.ndim != 1 or not 8 <= signal.size <= 384_000 or not np.all(np.isfinite(signal)):
                raise ValueError(f"Research bundle signal {index} must be a finite one-dimensional acquisition")
            signals.append(np.asarray(signal, dtype=np.float32))
        if {name for name in manifest_files if name.startswith("signals/")} != expected_signals:
            raise ValueError("Research bundle signal members do not match experiment metadata")
        _validate_session_state(session, experiments)
        original_id = str(session["id"])
        _validate_audit(audit, experiments, signals, original_id)
        if posterior_history != [item["posterior_after"] for item in experiments]:
            raise ValueError("Research bundle posterior history does not match experiment metadata")
        if configuration != session["state"]["config"]:
            raise ValueError("Research bundle configuration does not match session state")
        summary_count = result_summary.get("experiment_count", -1) if isinstance(result_summary, dict) else -1
        if (
            not isinstance(result_summary, dict)
            or isinstance(summary_count, bool)
            or not isinstance(summary_count, int)
            or summary_count != len(experiments)
            or result_summary.get("bundle_state_hash") != canonical_hash(session["state"])
        ):
            raise ValueError("Research bundle result summary is inconsistent")

        session_id = original_id if repository.get_session(original_id) is None else f"bundle-{secrets.token_urlsafe(10)}"
        preserved_identity = session_id == original_id
        created = False
        try:
            repository.create_session(session_id, session["mode"], session["preset"], session["state"])
            created = True
            for item, signal in zip(experiments, signals):
                repository.import_experiment(session_id, item, signal)
            if preserved_identity:
                for record in audit:
                    repository.append_ledger_entry(
                        session_id, int(record["experiment_index"]), record["previous_hash"], record["entry"], record["entry_hash"]
                    )
            else:
                # A session-ID collision requires a new local identity. Rebase
                # the already-verified chain so the imported measurements keep
                # a complete, verifiable ledger under that identity. Preserve
                # every source hash inside the derived entry for provenance.
                previous_hash = GENESIS_HASH
                for record in audit:
                    entry = dict(record["entry"])
                    entry["session_id"] = session_id
                    entry["previous_record_hash"] = previous_hash
                    entry["import_provenance"] = {
                        "original_session_id": original_id,
                        "original_entry_hash": record["entry_hash"],
                    }
                    entry_hash = canonical_hash(entry)
                    repository.append_ledger_entry(
                        session_id, int(record["experiment_index"]), previous_hash, entry, entry_hash
                    )
                    previous_hash = entry_hash
            for event in events:
                if not isinstance(event, dict) or not isinstance(event.get("event_type"), str) or not isinstance(event.get("payload"), dict):
                    raise ValueError("Research bundle contains invalid session event metadata")
                repository.import_event(session_id, str(event.get("created_at", "")), event["event_type"], event["payload"])
            repository.add_event(
                session_id,
                "research_bundle_imported",
                {"original_session_id": original_id, "manifest_hash": canonical_hash(manifest), "ledger_identity_preserved": preserved_identity},
            )
        except Exception:
            if created:
                repository.delete_session(session_id)
            raise
    return {
        "session_id": session_id,
        "original_session_id": original_id,
        "experiment_count": len(experiments),
        "event_count": len(events),
        "manifest_verified": True,
        "ledger_verified": True,
        "ledger_identity_preserved": preserved_identity,
        "ledger_rebased": not preserved_identity,
    }
