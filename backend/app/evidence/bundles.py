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
from backend.app.evidence.ledger import GENESIS_HASH, canonical_hash, json_safe, ledger_measurement_matches
from backend.app.inference.joint_state import JointInferenceState
from backend.app.models.domain import Defect, Experiment, Material, Panel
from backend.app.safety.constraints import NoGoRegion
from backend.app.replay.safe_io import load_bounded_npy, strict_json_loads, validate_archive, validate_signal


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


def _read_member(archive: zipfile.ZipFile, name: str) -> bytes:
    try:
        with archive.open(name) as member:
            content = member.read(MAX_BUNDLE_BYTES + 1)
        if len(content) > MAX_BUNDLE_BYTES:
            raise ValueError("Expanded research bundle member exceeds the size limit")
        return content
    except (KeyError, zipfile.BadZipFile, RuntimeError, NotImplementedError, OSError) as exc:
        raise ValueError(f"Research bundle contains an invalid archive member: {name}") from exc


def _load_json(archive: zipfile.ZipFile, name: str):
    try:
        return strict_json_loads(_read_member(archive, name), maximum_bytes=MAX_BUNDLE_BYTES, maximum_nodes=8_000_000)
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError(f"Research bundle contains invalid {name}") from exc


def _validate_grid(value, grid_size: int, *, probability: bool) -> np.ndarray:
    grid = np.asarray(value, dtype=np.float64)
    if grid.shape != (grid_size, grid_size) or not np.isfinite(grid).all() or np.any(grid < 0):
        raise ValueError("Probability or likelihood grid has an invalid shape or values")
    total = float(grid.sum())
    # Session snapshots historically round each cell to ten decimal places.
    tolerance = max(1e-8, grid.size * 5.01e-11)
    if not np.isfinite(total) or total <= 0 or (probability and not np.isclose(total, 1, atol=tolerance, rtol=0)):
        raise ValueError("Probability grid must be normalized; likelihood must have positive mass")
    return grid


def _validate_online_buffers(state: dict, experiment_count: int) -> None:
    """Hydration must not fit attacker-sized online models or fake counters."""
    discrepancy = state.get("discrepancy_model")
    if discrepancy:
        if not isinstance(discrepancy, dict):
            raise ValueError("online discrepancy state must be an object")
        maximum = discrepancy.get("maximum_samples", 256)
        if isinstance(maximum, bool) or not isinstance(maximum, int) or not 1 <= maximum <= 256:
            raise ValueError("online discrepancy sample budget is invalid")
        inputs, residuals = discrepancy.get("inputs", []), discrepancy.get("residuals", [])
        if (not isinstance(inputs, list) or not isinstance(residuals, list) or len(inputs) != len(residuals)
                or len(inputs) > maximum or (inputs and np.asarray(inputs, dtype=np.float64).shape != (len(inputs), 8))
                or (residuals and np.asarray(residuals, dtype=np.float64).shape != (len(residuals), 4))):
            raise ValueError("online discrepancy buffers have invalid dimensions or counts")
        alpha = discrepancy.get("ridge_alpha", 0.8)
        norms = discrepancy.get("recent_norms", [])
        if (isinstance(alpha, bool) or not isinstance(alpha, (int, float)) or alpha <= 0
                or not isinstance(norms, list) or len(norms) > 64
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0 for v in norms)):
            raise ValueError("online discrepancy hyperparameters are invalid")
    ood = state.get("ood_detector")
    if ood:
        if not isinstance(ood, dict):
            raise ValueError("OOD state must be an object")
        vectors = ood.get("residual_vectors", [])
        scores = ood.get("calibration_nonconformity", [])
        if (not isinstance(vectors, list) or len(vectors) > 128
                or (vectors and np.asarray(vectors, dtype=np.float64).shape != (len(vectors), 4))
                or not isinstance(scores, list) or len(scores) > 256
                or any(isinstance(v, bool) or not isinstance(v, (int, float)) or v < 0 for v in scores)):
            raise ValueError("OOD reference buffers have invalid dimensions or counts")
        caution, abstain = ood.get("caution_threshold", 0.55), ood.get("abstain_threshold", 0.82)
        if (any(isinstance(v, bool) or not isinstance(v, (int, float)) for v in (caution, abstain))
                or not 0 <= caution <= abstain <= 1):
            raise ValueError("OOD thresholds are invalid")
    assurance = state.get("assurance")
    if assurance:
        if not isinstance(assurance, dict):
            raise ValueError("assurance state must be an object")
        counts = [assurance.get(field, 0) for field in ("accepted_measurements", "rejected_measurements")]
        if any(isinstance(v, bool) or not isinstance(v, int) or not 0 <= v <= experiment_count for v in counts) or sum(counts) != experiment_count:
            raise ValueError("assurance measurement counts do not match experiment history")
        from backend.app.assurance.monitor import RuntimeAssuranceMonitor
        RuntimeAssuranceMonitor.from_dict(assurance)


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
        if isinstance(state.get("seed"), bool) or not isinstance(state.get("seed"), int) or not 0 <= state["seed"] <= 2_147_483_647:
            raise ValueError("session seed is invalid")
        if not isinstance(state.get("revealed", False), bool):
            raise ValueError("session revealed flag must be boolean")
        posterior = _validate_grid(state["posterior"], config.grid_size, probability=True)
        if experiments and not np.allclose(posterior, np.asarray(experiments[-1]["posterior_after"], dtype=np.float64), atol=5.01e-11, rtol=0):
            raise ValueError("session posterior does not match its final experiment")
        if len(experiments) > config.max_experiments:
            raise ValueError("session experiment history exceeds its configured budget")
        if state.get("joint_inference"):
            joint = state["joint_inference"]
            structural = joint["structural"]
            if isinstance(structural.get("grid_size"), bool) or structural.get("grid_size") != config.grid_size:
                raise ValueError("joint structural grid_size does not match configuration")
            joint_posterior = _validate_grid(structural["posterior"], config.grid_size, probability=True)
            if not np.allclose(joint_posterior, posterior, atol=5.01e-11, rtol=0):
                raise ValueError("joint structural posterior does not match session posterior")
            for field in ("radius_mean", "radius_std", "severity_mean", "severity_std"):
                value = structural.get(field)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 < value <= 1:
                    raise ValueError("joint structural moments are invalid")
            types = structural.get("type_probabilities")
            if (not isinstance(types, dict) or not types or set(types) - {"cavity", "loose_region", "delamination", "dense_inclusion"}
                    or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not 0 <= v <= 1 for v in types.values())
                    or not np.isclose(sum(types.values()), 1, atol=1e-8)):
                raise ValueError("joint structural type probabilities are invalid")
            if experiments:
                diagnostics = experiments[-1]["diagnostics"]
                if canonical_hash(joint.get("verification_state", {})) != canonical_hash(diagnostics.get("verification", {})):
                    raise ValueError("session verification state does not match experiment evidence")
                if canonical_hash(joint.get("last_quality")) != canonical_hash(diagnostics.get("quality")):
                    raise ValueError("session quality state does not match experiment evidence")
            elif joint.get("verification_state", {}).get("accepted"):
                raise ValueError("session verification has no experiment evidence")
            JointInferenceState.from_dict(joint, material)
        state_experiments = [Experiment(**item).to_dict() for item in state.get("experiments", [])]
        metadata_experiments = [Experiment(**item["parameters"]).to_dict() for item in experiments]
        for item in state.get("no_go_regions", []):
            NoGoRegion(**item)
        for name in ("rng_state", "acquisition_rng_state"):
            if state.get(name) is not None:
                generator = np.random.default_rng()
                generator.bit_generator.state = state[name]
        if state.get("acquisition_material"):
            Material(**state["acquisition_material"])
        _validate_online_buffers(state, len(experiments))
    except (KeyError, TypeError, ValueError, AttributeError, OverflowError) as exc:
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
    if action_history is not None and action_history != [item["diagnostics"].get("action_type", "diagnostic") for item in experiments]:
        raise ValueError("Research bundle action history does not match measurement evidence")


def _validate_experiment_metadata(item: dict, grid_size: int, expected_index: int) -> None:
    required = {
        "experiment_index", "created_at", "parameters", "features", "posterior_before",
        "posterior_after", "likelihood", "planner", "diagnostics",
    }
    if not isinstance(item, dict) or not required <= set(item):
        raise ValueError(f"Experiment {expected_index} metadata is incomplete")
    try:
        if isinstance(item["experiment_index"], bool) or not isinstance(item["experiment_index"], int) or item["experiment_index"] != expected_index:
            raise ValueError("Experiment indices must be contiguous and one-based")
        Experiment(**item["parameters"])
        for name in ("posterior_before", "posterior_after", "likelihood"):
            _validate_grid(item[name], grid_size, probability=name != "likelihood")
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
        record_index = record.get("experiment_index")
        entry_index = entry.get("experiment_number")
        if any(isinstance(value, bool) or not isinstance(value, int) for value in (record_index, entry_index)):
            raise ValueError("Evidence ledger indices must be integers")
        if record_index != index or entry_index != index:
            raise ValueError("Evidence ledger indices are not contiguous")
        if record.get("previous_hash") != previous_hash or entry.get("previous_record_hash") != previous_hash:
            raise ValueError(f"Evidence ledger chain is broken at record {index}")
        entry_hash = canonical_hash(entry)
        if record.get("entry_hash") != entry_hash:
            raise ValueError(f"Evidence ledger hash is invalid at record {index}")
        if entry.get("session_id") != session_id:
            raise ValueError(f"Evidence ledger session identity is invalid at record {index}")
        if not ledger_measurement_matches(entry, {**item, "signal": signal}):
            raise ValueError(f"Evidence ledger measurement metadata or hashes are invalid at record {index}")
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
        validate_archive(archive, maximum_members=MAX_BUNDLE_MEMBERS, maximum_bytes=MAX_BUNDLE_BYTES)
        names = [item.filename for item in members]
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
            content = _read_member(archive, name)
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
        if not isinstance(audit, list) or not isinstance(events, list) or len(events) > 10_000:
            raise ValueError("Research bundle audit or event history is invalid")
        for event in events:
            if (not isinstance(event, dict) or not isinstance(event.get("event_type"), str)
                    or not 1 <= len(event["event_type"]) <= 256 or not isinstance(event.get("payload"), dict)
                    or not isinstance(event.get("created_at"), str) or len(event["created_at"]) > 128):
                raise ValueError("Research bundle contains invalid session event metadata")
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
                signal = validate_signal(load_bounded_npy(_read_member(archive, signal_name)))
            except (KeyError, ValueError, OSError) as exc:
                raise ValueError(f"Research bundle signal {index} is invalid") from exc
            if not isinstance(signal, np.ndarray) or signal.ndim != 1 or not 8 <= signal.size <= 384_000 or not np.all(np.isfinite(signal)):
                raise ValueError(f"Research bundle signal {index} must be a finite one-dimensional acquisition")
            signals.append(np.asarray(signal, dtype=np.float32))
        if {name for name in manifest_files if name.startswith("signals/")} != expected_signals:
            raise ValueError("Research bundle signal members do not match experiment metadata")
        _validate_session_state(session, experiments)
        original_id = str(session["id"])
        for item, signal in zip(experiments, signals):
            expected_samples = max(32, int(round(session["state"]["config"]["sample_rate"] * item["parameters"]["duration_s"])))
            if signal.size != expected_samples:
                raise ValueError("Research bundle signal length does not match its acquisition window")
        if manifest.get("session_id") != original_id:
            raise ValueError("Research bundle manifest session identity is inconsistent")
        for previous, current in zip(experiments, experiments[1:]):
            if previous["posterior_after"] != current["posterior_before"]:
                raise ValueError("Research bundle posterior history is discontinuous")
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
            or result_summary.get("ledger_records") != len(audit)
            or result_summary.get("ledger_head") != (audit[-1]["entry_hash"] if audit else None)
            or result_summary.get("revealed") is not session["state"].get("revealed", False)
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
        "authenticity_verified": False,
        "verification_scope": "local_content_and_chain_consistency; imported hashes are not signatures",
    }
