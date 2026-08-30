import io
import json

import numpy as np
from fastapi.testclient import TestClient
from scipy.io import wavfile

from backend.app.assurance.monitor import RuntimeAssuranceMonitor
from backend.app.inference.diagnostics import estimate_measurement_quality
from backend.app.inference.structural_posterior import StructuralPosterior
from backend.app.main import create_app


def _wav_payload(frequency_hz: float = 2_300) -> bytes:
    time = np.arange(1_920) / 16_000
    samples = (0.16 * np.sin(2 * np.pi * frequency_hz * time) * np.iinfo(np.int16).max).astype(np.int16)
    payload = io.BytesIO()
    wavfile.write(payload, 16_000, samples)
    return payload.getvalue()


def test_assurance_state_is_normalized_and_conservative():
    monitor = RuntimeAssuranceMonitor()
    samples = np.sin(np.linspace(0, 20, 1_920)) * 0.08
    quality = estimate_measurement_quality(samples)
    monitor.update(quality, {"residual_snr_db": 8.0}, {"sensor_id": "s1", "temperature_c": 24})
    assessment = monitor.structural_assessment(
        StructuralPosterior(), ood_state={"score": 0.1, "status": "NOMINAL"}, model_trust=0.9
    )
    assert np.isclose(sum(assessment["state_probabilities"].values()), 1.0)
    assert np.isclose(sum(assessment["defect_count_screening"].values()), 1.0)
    assert assessment["scope"] == "research_screening_only"
    assert assessment["minimum_detectable_damage_size"] == "not_established_without_POD_campaign"


def test_repeated_bad_sensor_evidence_lowers_reliability():
    monitor = RuntimeAssuranceMonitor()
    silent = np.zeros(1_920)
    for _ in range(3):
        monitor.update(estimate_measurement_quality(silent), {}, {"sensor_id": "dead-channel"})
    sensor = monitor.to_dict()["sensors"]["dead-channel"]
    assert sensor["status"] == "UNRELIABLE"
    assert sensor["rejected_count"] == 3
    assessment = monitor.structural_assessment(
        StructuralPosterior(), ood_state={"score": 0.0, "status": "NOMINAL"}, model_trust=1.0
    )
    assert assessment["engineering_action"] == "REACQUIRE_OR_REPAIR_SENSOR"


def test_emergency_stop_is_latched_audited_and_requires_acknowledgement(tmp_path):
    database = tmp_path / "stop.db"
    client = TestClient(create_app(database))
    state = client.post("/sessions", json={"mode": "simulation", "seed": 22}).json()
    session_id = state["id"]
    stopped = client.post(
        f"/api/sessions/{session_id}/emergency-stop", json={"reason": "operator observed unsafe motion"}
    )
    assert stopped.status_code == 200
    assert stopped.json()["safety"]["emergency_stop"]["latched"] is True
    assert client.post(f"/sessions/{session_id}/experiments/run", json={}).status_code == 409
    client = TestClient(create_app(database))
    assert client.get(f"/sessions/{session_id}").json()["safety"]["emergency_stop"]["latched"] is True
    assert client.post(f"/sessions/{session_id}/experiments/run", json={}).status_code == 409
    refused = client.post(
        f"/api/sessions/{session_id}/emergency-stop/release",
        json={"reason": "inspection complete", "acknowledgement": False},
    )
    assert refused.status_code == 422
    released = client.post(
        f"/api/sessions/{session_id}/emergency-stop/release",
        json={"reason": "area checked by operator", "acknowledgement": True},
    )
    assert released.status_code == 200
    assert released.json()["safety"]["emergency_stop"]["latched"] is False
    events = client.get(f"/api/events/{session_id}").json()["events"]
    assert [event["event_type"] for event in events][-2:] == ["emergency_stop_latched", "emergency_stop_released"]


def test_duplicate_physical_payload_and_unsafe_custom_action_are_rejected(tmp_path):
    client = TestClient(create_app(tmp_path / "integrity.db"))
    state = client.post("/sessions", json={"mode": "physical", "seed": 7}).json()
    session_id = state["id"]
    payload = _wav_payload()
    first = client.post(
        f"/sessions/{session_id}/experiments/upload",
        files={"file": ("measurement.wav", payload, "audio/wav")},
    )
    assert first.status_code == 200
    duplicate = client.post(
        f"/sessions/{session_id}/experiments/upload",
        files={"file": ("measurement.wav", payload, "audio/wav")},
    )
    assert duplicate.status_code == 400
    assert "Duplicate measurement payload" in duplicate.text

    experiment = state["recommendation"]["experiment"]
    experiment["amplitude"] = 0.95
    unsafe = client.post(
        f"/sessions/{session_id}/experiments/upload",
        files={"file": ("unsafe.wav", _wav_payload(2_500), "audio/wav")},
        data={"experiment_json": json.dumps(experiment)},
    )
    assert unsafe.status_code == 400
    assert "amplitude_limit" in unsafe.text


def test_assurance_survives_database_hydration(tmp_path):
    database = tmp_path / "assurance-persistence.db"
    first = TestClient(create_app(database))
    state = first.post("/sessions", json={"seed": 31}).json()
    state = first.post(f"/sessions/{state['id']}/experiments/run", json={}).json()["state"]
    assert state["assurance"]["accepted_measurements"] == 1
    second = TestClient(create_app(database))
    restored = second.get(f"/sessions/{state['id']}").json()
    assert restored["assurance"]["accepted_measurements"] == 1
    assert restored["status"]["integrity_assessment"]["scope"] == "research_screening_only"
