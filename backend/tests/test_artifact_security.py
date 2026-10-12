from __future__ import annotations

from hashlib import sha256
import io
import json
from pathlib import Path
import shutil
import subprocess
import zipfile
import zlib

import numpy as np
import pytest
from scipy.io import wavfile

from backend.app.core.config import ArgusConfig
from backend.app.database.repository import SessionRepository
from backend.app.evidence.bundles import export_research_bundle, import_research_bundle
from backend.app.evidence.ledger import EvidenceLedger, canonical_hash, software_revision
from backend.app.models.domain import Experiment
from backend.app.replay.datasets import (
    InMemoryCounterfactualDataset, NPZCounterfactualDataset, WAVCollectionCounterfactualDataset, action_key,
)
from backend.app.replay.runner import AdaptiveReplayRunner
from backend.app.replay.safe_io import load_bounded_npy, strict_json_loads, validate_archive
from backend.app.research.jobs import ResearchJobManager
from backend.app.schemas.api import CreateSessionRequest
from backend.app.services.engine import ArgusEngine
from backend.app.services.session_manager import SessionManager


@pytest.fixture
def evidence(tmp_path):
    repository = SessionRepository(tmp_path / "source.db")
    manager = SessionManager(repository)
    runtime = manager.create(CreateSessionRequest(seed=871, max_experiments=1))
    manager.run(runtime.id)
    return repository, runtime.id, export_research_bundle(repository, runtime.id)


def repack(bundle: bytes, change) -> bytes:
    with zipfile.ZipFile(io.BytesIO(bundle)) as archive:
        files = {name: archive.read(name) for name in archive.namelist() if name != "manifest.json"}
    change(files)
    session = json.loads(files["session.json"])
    summary = json.loads(files["result_summary.json"])
    summary["bundle_state_hash"] = canonical_hash(session["state"])
    files["result_summary.json"] = json.dumps(summary).encode()
    manifest = {"schema_version": 1, "session_id": session["id"], "files": {
        name: {"sha256": sha256(content).hexdigest(), "size": len(content)} for name, content in files.items()
    }}
    result = io.BytesIO()
    with zipfile.ZipFile(result, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in files.items():
            archive.writestr(name, content)
        archive.writestr("manifest.json", json.dumps(manifest))
    return result.getvalue()


def altered_json(files: dict, name: str, change):
    value = json.loads(files[name])
    change(value)
    files[name] = json.dumps(value).encode()


def npy_header(shape, descr="<f4") -> bytes:
    output = io.BytesIO()
    np.lib.format.write_array_header_1_0(output, {"descr": descr, "fortran_order": False, "shape": shape})
    return output.getvalue()


@pytest.mark.parametrize("shape,descr", [((10**12,), "<f4"), ((8,), "|O"), ((8,), "<f4")])
def test_npy_header_is_rejected_before_numpy_allocation(monkeypatch, shape, descr):
    def forbidden_load(*args, **kwargs):
        pytest.fail("Malformed NumPy headers must be rejected before np.load allocates")
    monkeypatch.setattr(np, "load", forbidden_load)
    with pytest.raises(ValueError, match="header"):
        load_bounded_npy(npy_header(shape, descr))


def test_bundle_rejects_malicious_array_header_without_database_writes(evidence, tmp_path):
    _, _, bundle = evidence
    malicious = repack(bundle, lambda files: files.__setitem__("signals/0001.npy", npy_header((10**12,))))
    destination = SessionRepository(tmp_path / "destination.db")
    with pytest.raises(ValueError, match="signal 1 is invalid"):
        import_research_bundle(destination, malicious)
    assert destination.list_sessions() == []


def test_bundle_rejects_zip_bomb_before_reading_manifest(tmp_path, monkeypatch):
    import backend.app.evidence.bundles as bundles
    monkeypatch.setattr(bundles, "MAX_BUNDLE_BYTES", 4_096)
    payload = io.BytesIO()
    with zipfile.ZipFile(payload, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("signals/0001.npy", b"0" * 40_000)
    repository = SessionRepository(tmp_path / "bomb.db")
    with pytest.raises(ValueError, match="Expanded"):
        import_research_bundle(repository, payload.getvalue())
    assert repository.list_sessions() == []


@pytest.mark.parametrize("name", ["../response.npy", "/response.npy", "signals\\response.npy", "C:/response.npy", "signals/./response.npy"])
def test_archive_rejects_noncanonical_and_escaping_paths(name):
    output = io.BytesIO()
    with zipfile.ZipFile(output, "w") as archive:
        member = zipfile.ZipInfo("safe.npy")
        member.filename = name
        archive.writestr(member, b"signal")
    with zipfile.ZipFile(io.BytesIO(output.getvalue())) as archive:
        with pytest.raises(ValueError, match="unsafe"):
            validate_archive(archive, maximum_members=1)


@pytest.mark.parametrize("content", ['{"seed":1,"seed":2}', '{"value":1e999}', '{"value":NaN}', '{"value":"\\ud800"}', "[" * 65 + "0" + "]" * 65])
def test_research_json_rejects_ambiguous_or_unbounded_values(content):
    with pytest.raises(ValueError):
        strict_json_loads(content)


@pytest.mark.parametrize("change,pattern", [
    (lambda state: state["joint_inference"]["structural"].__setitem__("grid_size", 10**12), "grid_size"),
    (lambda state: state["joint_inference"]["verification_state"].__setitem__("accepted", True), "verification"),
    (lambda state: state["action_history"].__setitem__(0, "verification"), "action history"),
    (lambda state: state["posterior"][0].__setitem__(0, -1), "grid"),
    (lambda state: state["discrepancy_model"].__setitem__("maximum_samples", 10**12), "discrepancy"),
    (lambda state: state["ood_detector"].__setitem__("residual_vectors", [[0] * 4] * 129), "OOD"),
    (lambda state: state["assurance"].__setitem__("accepted_measurements", 999), "assurance"),
])
def test_bundle_rejects_inconsistent_state_even_with_recomputed_hashes(evidence, tmp_path, change, pattern):
    _, _, bundle = evidence
    malicious = repack(bundle, lambda files: altered_json(files, "session.json", lambda session: change(session["state"])))
    destination = SessionRepository(tmp_path / "destination.db")
    with pytest.raises(ValueError, match=pattern):
        import_research_bundle(destination, malicious)
    assert destination.list_sessions() == []


def test_bundle_binds_planner_metadata_to_ledger(evidence, tmp_path):
    _, _, bundle = evidence
    malicious = repack(bundle, lambda files: altered_json(files, "experiments.json", lambda items: items[0]["planner"].__setitem__("reason", "forged recommendation")))
    with pytest.raises(ValueError, match="measurement metadata"):
        import_research_bundle(SessionRepository(tmp_path / "destination.db"), malicious)


def test_ledger_binds_quality_diagnostics_and_verify_is_read_only(evidence):
    repository, session_id, _ = evidence
    with repository.connection() as connection:
        before = [tuple(row) for row in connection.execute("SELECT * FROM ledger_entries ORDER BY id")]
    assert EvidenceLedger(repository).verify(session_id)["valid"]
    with repository.connection() as connection:
        after = [tuple(row) for row in connection.execute("SELECT * FROM ledger_entries ORDER BY id")]
        assert before == after
        metadata = json.loads(connection.execute("SELECT diagnostics_json FROM experiments WHERE session_id=?", (session_id,)).fetchone()[0])
        metadata["evidence_weight"] = 999
        connection.execute("UPDATE experiments SET diagnostics_json=? WHERE session_id=?", (json.dumps(metadata), session_id))
    assert EvidenceLedger(repository).verify(session_id)["reason"] == "measurement_data_mismatch"


def test_ledger_rejects_oversized_compressed_database_signal(evidence):
    repository, session_id, _ = evidence
    with repository.connection() as connection:
        connection.execute("UPDATE experiments SET raw_signal=? WHERE session_id=?", (zlib.compress(b"0" * 2_000_000), session_id))
    assert EvidenceLedger(repository).verify(session_id)["reason"] == "invalid_stored_evidence"


def test_unknown_session_is_not_a_valid_empty_ledger(tmp_path):
    assert EvidenceLedger(SessionRepository(tmp_path / "unknown.db")).verify("missing")["valid"] is False


def test_npz_rejects_duplicate_actions_and_nonfinite_samples(tmp_path):
    action = Experiment(0.1, 0.1, 0.9, 0.9).to_dict()
    path = tmp_path / "bank.npz"
    np.savez_compressed(path, actions_json=json.dumps([action, action]), signals=np.zeros((2, 32)),
                        truth_json="{}", metadata_json="{}")
    with pytest.raises(ValueError, match="Duplicate"):
        NPZCounterfactualDataset(path)
    np.savez_compressed(path, actions_json=json.dumps([action]), signals=np.full((1, 32), np.nan),
                        truth_json="{}", metadata_json="{}")
    with pytest.raises(ValueError, match="finite"):
        NPZCounterfactualDataset(path)


def test_replay_metadata_cannot_leak_evaluation_labels():
    action = Experiment(0.1, 0.1, 0.9, 0.9).to_dict()
    with pytest.raises(ValueError, match="Ground truth"):
        InMemoryCounterfactualDataset({action_key(action): np.zeros(32)}, [action], {}, {"context": {"ground_truth": {"center_x": 0.5}}})


def test_dataset_returns_defensive_copies():
    action = Experiment(0.1, 0.1, 0.9, 0.9).to_dict()
    dataset = InMemoryCounterfactualDataset({action_key(action): np.zeros(32)}, [action], {"center_x": 0.5, "center_y": 0.4}, {"nested": {"value": 1}})
    dataset.list_available_actions()[0]["amplitude"] = 1
    dataset.get_metadata()["nested"]["value"] = 2
    truth = dataset.end_blind_evaluation()
    truth["center_x"] = 0
    assert dataset.list_available_actions()[0]["amplitude"] == 0.45
    assert dataset.get_metadata()["nested"]["value"] == 1
    assert dataset.get_hidden_truth()["center_x"] == 0.5


@pytest.mark.parametrize("samples,rate,pattern", [(32, 16_000, "shorter"), (1_920, 1_000, "Nyquist")])
def test_replay_preflight_rejects_invalid_acquisition_without_state_mutation(samples, rate, pattern):
    engine = ArgusEngine(ArgusConfig(seed=872, candidate_count=8, max_experiments=1), seed=872)
    action = engine.current_recommendation.selected.experiment.to_dict()
    dataset = InMemoryCounterfactualDataset({action_key(action): np.zeros(samples)}, [action], {}, {"sample_rate": rate})
    before = canonical_hash(engine.joint_state.to_dict())
    recommendation = engine.current_recommendation
    with pytest.raises(ValueError, match=pattern):
        AdaptiveReplayRunner(engine, dataset).run(1)
    assert canonical_hash(engine.joint_state.to_dict()) == before
    assert engine.current_recommendation is recommendation
    assert engine.experiments == []
    assert dataset.truth_is_sealed


def test_blind_replay_records_window_provenance_and_refuses_revealed_bank():
    engine = ArgusEngine(ArgusConfig(seed=873, candidate_count=8, max_experiments=1), seed=873)
    experiment = engine.current_recommendation.selected.experiment
    signal = engine.simulator.simulate(engine.truth, experiment)
    dataset = InMemoryCounterfactualDataset({action_key(experiment): signal}, [experiment.to_dict()], engine.truth.to_dict(), {"sample_rate": 16_000, "evidence_source": "simulated"})
    report = AdaptiveReplayRunner(engine, dataset).run(1)
    assert report["truth_was_sealed_during_execution"]
    assert report["trace"][0]["acquisition_provenance"]["padding_applied"] is False
    assert report["trace"][0]["evidence_source_declaration"] == "simulated"
    with pytest.raises(PermissionError, match="revealed"):
        AdaptiveReplayRunner(engine, dataset).run(1)
    assert len(engine.experiments) == 1


def test_wav_rejects_more_than_two_channels_and_path_escape(tmp_path):
    action = Experiment(0.1, 0.1, 0.9, 0.9).to_dict()
    wavfile.write(tmp_path / "response.wav", 16_000, np.zeros((64, 8), dtype=np.int16))
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"actions": [{"experiment": action, "wav": "response.wav"}]}))
    with pytest.raises(ValueError, match="one-dimensional"):
        WAVCollectionCounterfactualDataset(manifest)
    manifest.write_text(json.dumps({"actions": [{"experiment": action, "wav": "../response.wav"}]}))
    with pytest.raises(ValueError, match="escapes"):
        WAVCollectionCounterfactualDataset(manifest)


def test_replay_calibration_needs_explicit_reference_type():
    action = Experiment(0.1, 0.1, 0.9, 0.9).to_dict()
    key = action_key(action)
    with pytest.raises(ValueError, match="direct-path reference"):
        InMemoryCounterfactualDataset({key: np.zeros(32)}, [action], {}, {"action_types": {key: "calibration"}})


@pytest.mark.parametrize("value", [float("inf"), float("nan"), 1.5, "2", True])
def test_research_job_counts_reject_type_confusion_and_nonfinite_values(value):
    with pytest.raises(ValueError, match="integer"):
        ResearchJobManager._validated_request("benchmark", {"cases": value})


def test_source_fingerprint_tracks_dirty_and_untracked_code_but_not_results(tmp_path):
    if not shutil.which("git"):
        pytest.skip("git not installed")
    def git(*arguments):
        subprocess.run(["git", *arguments], cwd=tmp_path, capture_output=True, check=True)
    git("init")
    source = tmp_path / "backend" / "app.py"
    source.parent.mkdir()
    source.write_text("value = 1\n")
    git("add", "backend/app.py")
    git("-c", "user.name=Artifact Test", "-c", "user.email=artifact@example.invalid", "commit", "-m", "source")
    initial = software_revision(tmp_path)
    source.write_text("value = 2\n")
    dirty = software_revision(tmp_path)
    assert dirty != initial
    (source.parent / "new.py").write_text("value = 3\n")
    new_source = software_revision(tmp_path)
    assert new_source != dirty
    results = tmp_path / "output"
    results.mkdir()
    (results / "report.json").write_text('{"run":1}')
    assert software_revision(tmp_path) == new_source
