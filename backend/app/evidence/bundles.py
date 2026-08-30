from __future__ import annotations

from hashlib import sha256
import io
import json
from pathlib import PurePosixPath
import secrets
import zipfile

import numpy as np

from backend.app.database.repository import SessionRepository
from backend.app.evidence.ledger import canonical_hash, json_safe


MAX_BUNDLE_BYTES = 100 * 1024 * 1024


def _json_bytes(value: object) -> bytes:
    return json.dumps(json_safe(value), indent=2, sort_keys=True).encode("utf-8")


def export_research_bundle(repository: SessionRepository, session_id: str) -> bytes:
    session = repository.get_session(session_id)
    if session is None:
        raise KeyError(session_id)
    experiments = repository.list_experiments(session_id, include_signal=True)
    ledger = repository.list_ledger_entries(session_id)
    events = repository.list_events(session_id)
    files: dict[str, bytes] = {
        "session.json": _json_bytes({key: value for key, value in session.items() if key != "state_json"}),
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
    files["configuration.json"] = _json_bytes(session["state"].get("config", {}))
    result_summary = {
        "experiment_count": len(experiments),
        "revealed": bool(session["state"].get("revealed", False)),
        "ledger_records": len(ledger),
        "ledger_head": ledger[-1]["entry_hash"] if ledger else None,
        "bundle_state_hash": canonical_hash(session["state"]),
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
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        members = archive.infolist()
        if sum(item.file_size for item in members) > MAX_BUNDLE_BYTES:
            raise ValueError("Expanded research bundle exceeds the 100 MB limit")
        for item in members:
            path = PurePosixPath(item.filename)
            if path.is_absolute() or ".." in path.parts:
                raise ValueError("Research bundle contains an unsafe path")
        manifest = json.loads(archive.read("manifest.json"))
        for name, expected in manifest["files"].items():
            content = archive.read(name)
            if len(content) != int(expected["size"]) or sha256(content).hexdigest() != expected["sha256"]:
                raise ValueError(f"Research bundle integrity failure: {name}")
        session = json.loads(archive.read("session.json"))
        experiments = json.loads(archive.read("experiments.json"))
        original_id = str(session["id"])
        session_id = original_id if repository.get_session(original_id) is None else f"bundle-{secrets.token_urlsafe(10)}"
        repository.create_session(session_id, session["mode"], session["preset"], session["state"])
        for item in experiments:
            signal_bytes = archive.read(f"signals/{int(item['experiment_index']):04d}.npy")
            signal = np.load(io.BytesIO(signal_bytes), allow_pickle=False)
            repository.import_experiment(session_id, item, signal)
        preserved_identity = session_id == original_id
        if preserved_identity:
            for record in json.loads(archive.read("audit.json")):
                repository.append_ledger_entry(
                    session_id, int(record["experiment_index"]), record["previous_hash"], record["entry"], record["entry_hash"]
                )
        repository.add_event(
            session_id,
            "research_bundle_imported",
            {"original_session_id": original_id, "manifest_hash": canonical_hash(manifest), "ledger_identity_preserved": preserved_identity},
        )
    return {
        "session_id": session_id,
        "original_session_id": original_id,
        "experiment_count": len(experiments),
        "manifest_verified": True,
        "ledger_identity_preserved": preserved_identity,
    }

