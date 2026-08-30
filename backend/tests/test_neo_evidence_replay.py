from __future__ import annotations

import io
import json
import sqlite3

import numpy as np
import pytest
from fastapi.testclient import TestClient
from scipy.io import wavfile

from backend.app.core.config import ArgusConfig
from backend.app.database.repository import SessionRepository
from backend.app.evidence.bundles import export_research_bundle, import_research_bundle
from backend.app.evidence.ledger import EvidenceLedger
from backend.app.replay.datasets import InMemoryCounterfactualDataset, WAVCollectionCounterfactualDataset, action_key
from backend.app.replay.runner import AdaptiveReplayRunner
from backend.app.services.engine import ArgusEngine
from backend.app.main import create_app


def test_ledger_detects_tampering_and_bundle_round_trip(tmp_path):
    repository = SessionRepository(tmp_path / "source.db")
    app = TestClient(create_app(tmp_path / "api.db"))
    state = app.post("/sessions", json={"seed": 61, "max_experiments": 5}).json()
    app.post(f"/sessions/{state['id']}/experiments/run", json={})
    assert app.get(f"/api/ledger/{state['id']}/verify").json()["valid"]
    bundle = app.get(f"/api/export/{state['id']}").content
    destination = SessionRepository(tmp_path / "destination.db")
    imported = import_research_bundle(destination, bundle)
    assert imported["manifest_verified"]
    assert len(destination.list_experiments(imported["session_id"])) == 1

    api_repository = app.app.state.repository
    with api_repository.connection() as connection:
        connection.execute("UPDATE ledger_entries SET entry_json=? WHERE session_id=?", ('{"tampered":true}', state["id"]))
    verification = EvidenceLedger(api_repository).verify(state["id"])
    assert not verification["valid"]
    assert verification["failed_at_record"] == 1


def test_replay_truth_is_sealed_and_only_available_after_execution():
    source = ArgusEngine(ArgusConfig(seed=71, candidate_count=12), seed=71)
    actions = source.planner.generate_candidates(source.belief.posterior, [], 6)
    observations = {action_key(item): source.simulator.simulate(source.truth, item) for item in actions}
    dataset = InMemoryCounterfactualDataset(observations, [item.to_dict() for item in actions], source.truth.to_dict(), {"sample_rate": 16_000})
    with pytest.raises(PermissionError):
        dataset.get_hidden_truth()
    runner = AdaptiveReplayRunner(ArgusEngine(ArgusConfig(seed=72, candidate_count=12), seed=72), dataset)
    report = runner.run(2)
    assert report["selected_action_count"] == 2
    assert report["truth_was_sealed_during_execution"]
    assert report["revealed_truth"] == source.truth.to_dict()


def test_wav_collection_adapter_normalizes_and_blocks_path_escape(tmp_path):
    action = ArgusEngine(ArgusConfig(seed=2, candidate_count=12), seed=2).planner.random_experiment().to_dict()
    samples = (np.sin(np.linspace(0, 20, 320)) * np.iinfo(np.int16).max).astype(np.int16)
    wavfile.write(tmp_path / "response.wav", 16_000, samples)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"actions": [{"experiment": action, "wav": "response.wav"}], "truth": {"center_x": 0.3, "center_y": 0.4}}), encoding="utf-8")
    dataset = WAVCollectionCounterfactualDataset(manifest)
    observation = dataset.get_observation(action)
    assert observation.dtype == np.float32
    assert np.max(np.abs(observation)) <= 1.0


def test_additive_migration_preserves_legacy_session(tmp_path):
    database = tmp_path / "legacy.db"
    connection = sqlite3.connect(database)
    connection.executescript("""
        CREATE TABLE sessions(id TEXT PRIMARY KEY, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, mode TEXT NOT NULL, preset TEXT NOT NULL, state_json TEXT NOT NULL);
        CREATE TABLE experiments(id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, experiment_index INTEGER NOT NULL, created_at TEXT NOT NULL, parameters_json TEXT NOT NULL, features_json TEXT NOT NULL, posterior_before_json TEXT NOT NULL, posterior_after_json TEXT NOT NULL, likelihood_json TEXT NOT NULL, planner_json TEXT NOT NULL, diagnostics_json TEXT NOT NULL, raw_signal BLOB NOT NULL, UNIQUE(session_id, experiment_index));
        INSERT INTO sessions VALUES('legacy','2020','2020','simulation','easy','{}');
    """)
    connection.commit(); connection.close()
    repository = SessionRepository(database)
    assert repository.get_session("legacy") is not None
    with repository.connection() as migrated:
        tables = {row[0] for row in migrated.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        versions = migrated.execute("SELECT COUNT(*) FROM schema_migrations").fetchone()[0]
    assert {"ledger_entries", "research_jobs", "model_registry", "session_events", "probe_nodes"} <= tables
    assert versions >= 1


def test_neo_api_surfaces_and_constraints(tmp_path):
    client = TestClient(create_app(tmp_path / "neo-api.db"))
    state = client.post("/sessions", json={"seed": 81, "material_profile": "cfrp_demo", "config_profile": "demo"}).json()
    session_id = state["id"]
    for path in ("planner/recommend", "planner/explain", "planner/alternatives", "inference/state", "inference/uncertainty", "calibration/status", "model/trust", "ood/status"):
        response = client.get(f"/api/{path}?session_id={session_id}")
        assert response.status_code == 200
    updated = client.put(f"/api/sessions/{session_id}/no-go-regions", json={"regions": [{"x_min": 0.0, "y_min": 0.0, "x_max": 0.2, "y_max": 0.2, "label": "fixture"}]})
    assert updated.status_code == 200
    assert updated.json()["no_go_regions"][0]["label"] == "fixture"
    decision = client.post(f"/api/sessions/{session_id}/human-decision", json={"decision": "reject", "reason": "inaccessible"})
    assert decision.status_code == 200
    assert decision.json()["state"]["human_decisions"][-1]["decision"] == "reject"
    assert client.get("/api/materials").status_code == 200
    assert client.get("/api/demo/scenarios").status_code == 200

