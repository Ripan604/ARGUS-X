import io

import numpy as np
from fastapi.testclient import TestClient
from scipy.io import wavfile

from backend.app.main import create_app
from backend.app.database.repository import SessionRepository


def test_health_and_session_lifecycle(tmp_path):
    app = create_app(tmp_path / "argus-test.db")
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "ok"
    created = client.post("/sessions", json={"preset": "easy", "seed": 41, "max_experiments": 5})
    assert created.status_code == 201
    session = created.json()
    listed = client.get("/sessions").json()["sessions"]
    assert listed[0]["id"] == session["id"]
    assert listed[0]["experiment_count"] == 0
    assert session["ground_truth"] is None
    assert np.isclose(np.sum(session["posterior"]), 1.0)
    recommendation = client.get(f"/sessions/{session['id']}/recommendation")
    assert recommendation.status_code == 200
    run = client.post(f"/sessions/{session['id']}/experiments/run", json={})
    assert run.status_code == 200
    assert run.json()["experiment"] == 1
    state = client.get(f"/sessions/{session['id']}").json()
    assert state["status"]["experiment_count"] == 1
    assert np.isclose(np.sum(state["posterior"]), 1.0)
    history = client.get(f"/sessions/{session['id']}/history").json()["experiments"]
    assert len(history) == 1
    assert client.get("/sessions").json()["sessions"][0]["experiment_count"] == 1
    revealed = client.post(f"/sessions/{session['id']}/reveal").json()
    assert revealed["ground_truth"] is not None
    assert revealed["localization_error_mm"] >= 0


def test_database_persistence_across_app_instances(tmp_path):
    database = tmp_path / "persistent.db"
    first = TestClient(create_app(database))
    session = first.post("/sessions", json={"seed": 9}).json()
    first.post(f"/sessions/{session['id']}/experiments/run", json={})
    second = TestClient(create_app(database))
    restored = second.get(f"/sessions/{session['id']}")
    assert restored.status_code == 200
    assert restored.json()["status"]["experiment_count"] == 1


def test_simulated_integration_loop(tmp_path):
    client = TestClient(create_app(tmp_path / "integration.db"))
    state = client.post("/sessions", json={"preset": "medium", "seed": 12, "max_experiments": 6}).json()
    for _ in range(4):
        response = client.post(f"/sessions/{state['id']}/experiments/run", json={})
        assert response.status_code == 200
        state = response.json()["state"]
        assert np.isclose(np.sum(state["posterior"]), 1.0)
    assert state["status"]["experiment_count"] == 4
    estimate = state["status"]
    assert 0 <= estimate["map_x"] <= 1 and 0 <= estimate["map_y"] <= 1


def test_physical_session_cannot_simulate_or_reveal_truth(tmp_path):
    client = TestClient(create_app(tmp_path / "physical.db"))
    session = client.post("/sessions", json={"mode": "physical", "seed": 8}).json()
    assert session["ground_truth"] is None
    assert client.post(f"/sessions/{session['id']}/experiments/run", json={}).status_code == 409
    assert client.post(f"/sessions/{session['id']}/reveal").status_code == 409
    device = client.post(
        f"/sessions/{session['id']}/experiments/device", json={"device": "serial_probe"}
    )
    assert device.status_code == 409


def test_physical_session_accepts_valid_wav_and_updates_belief(tmp_path):
    client = TestClient(create_app(tmp_path / "wav.db"))
    session = client.post("/sessions", json={"mode": "physical", "seed": 18}).json()
    time = np.arange(1_920) / 16_000
    samples = (0.18 * np.sin(2 * np.pi * 2_400 * time) * np.iinfo(np.int16).max).astype(np.int16)
    payload = io.BytesIO()
    wavfile.write(payload, 16_000, samples)
    response = client.post(
        f"/sessions/{session['id']}/experiments/upload",
        files={"file": ("measurement.wav", payload.getvalue(), "audio/wav")},
    )
    assert response.status_code == 200
    result = response.json()
    assert result["state"]["status"]["experiment_count"] == 1
    assert np.isclose(np.sum(result["state"]["posterior"]), 1.0)
    assert len(result["measurement"]["waveform"]) > 0


def test_sqlite_history_query_uses_compound_unique_index(tmp_path):
    repository = SessionRepository(tmp_path / "query-plan.db")
    with repository.connection() as connection:
        plan = connection.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM experiments WHERE session_id=? ORDER BY experiment_index",
            ("session",),
        ).fetchall()
        index_names = {row[1] for row in connection.execute("PRAGMA index_list('experiments')").fetchall()}
    assert "idx_experiments_session" not in index_names
    assert any("USING INDEX" in row[3] for row in plan)
