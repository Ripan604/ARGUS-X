from __future__ import annotations

import numpy as np
from fastapi.testclient import TestClient

from backend.app.demo.scenarios import model_mismatch
from backend.app.evaluation.neo_benchmark import STRATEGIES, run_benchmark_matrix
from backend.app.inference.diagnostics import estimate_measurement_quality
from backend.app.research.faults import inject_fault
from backend.app.main import create_app


def test_benchmark_policies_share_paired_hidden_seeds():
    result = run_benchmark_matrix(cases=1, max_experiments=2, seed=91)
    assert set(result["summary"]) == set(STRATEGIES)
    assert {row["seed"] for row in result["runs"]} == {91}
    assert all(row["measurements"] <= 2 for row in result["runs"])
    assert result["metadata"]["evidence_source"] == "simulated"


def test_model_mismatch_demo_observes_calibration_and_reduces_error():
    result = model_mismatch()
    neo = result["argus_neo"]["summary"]
    naive = result["naive_ablation"]["summary"]
    assert neo["action_counts"]["calibration"] >= 1
    assert neo["localization_error_mm"] < naive["localization_error_mm"]
    assert naive["decision_confidence"] > neo["decision_confidence"]
    assert result["observed_effect"]["neo_error_advantage_mm"] > 0
    assert result["observed_effect"]["naive_error_mm"] > 30
    assert result["observed_effect"]["naive_confidence_gap"] > 0


def test_fault_injection_detects_dropout_clipping_and_corruption():
    base = (0.2 * np.sin(np.linspace(0, 50, 1_920))).astype(np.float32)
    dropout, _ = inject_fault(base, "sensor_dropout")
    assert not estimate_measurement_quality(dropout).accepted
    clipped, _ = inject_fault(base, "clipped_measurement", severity=1.0)
    assert "clipping" in estimate_measurement_quality(clipped).reasons
    corrupted, _ = inject_fault(base, "corrupted_packet", severity=1.0)
    assert "non_finite_samples" in estimate_measurement_quality(corrupted).reasons


def test_session_and_probe_websocket_protocol(tmp_path):
    client = TestClient(create_app(tmp_path / "websocket.db"))
    state = client.post("/sessions", json={"seed": 99}).json()
    with client.websocket_connect(f"/ws/session/{state['id']}") as socket:
        socket.send_json([])
        assert socket.receive_json()["type"] == "error"
        socket.send_json({"type": "state"})
        payload = socket.receive_json()
        assert payload["type"] == "state"
        assert payload["state"]["id"] == state["id"]
    with client.websocket_connect("/ws/probe/edge-test") as socket:
        socket.send_json({"type": "hello", "node_type": ["invalid"], "capabilities": []})
        assert socket.receive_json()["type"] == "error"
        socket.send_json({"type": "hello", "node_type": "edge_laptop", "capabilities": {"microphone": True}, "session_id": state["id"]})
        payload = socket.receive_json()
        assert payload["type"] == "ack"
        assert payload["node"]["node_type"] == "edge_laptop"
