from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from threading import RLock
from types import SimpleNamespace

from fastapi.testclient import TestClient
import numpy as np
import pytest

from backend.app.core.config import ArgusConfig
from backend.app.hardware import devices
from backend.app.hardware.protocol_v2 import ProbeRequest, ProbeTimingCalibration, parse_frame
from backend.app.main import create_app
from backend.app.models.domain import Experiment
from backend.app.schemas.api import ExperimentParameters
from backend.app.security import SecuritySettings
from backend.tests.test_probe_protocol_v2 import CAPS, EXPERIMENT, FakeSerial, calibration_metadata, make_frame


@pytest.fixture
def app(tmp_path):
    return create_app(tmp_path / "probe-api.db", security_settings=SecuritySettings())


@pytest.mark.parametrize("update", [
    {"arrival_adapter_validated": False}, {"arrival_adapter_validated": 1},
    {"max_sample_jitter_us": True}, {"sample_rate_hz": 16000.5},
    {"max_trigger_alignment_error_us": 20}, {"max_clock_error_ppm": 1001},
    {"reference_sha256": "not-a-digest"}, {"device_id": "ESP32_DAC25_ADC34"},
    {"calibrated_at_utc": (datetime.now(timezone.utc) - timedelta(days=91)).isoformat()},
    {"unexpected_self_certification": True},
])
def test_invalid_operator_declaration_never_reaches_connection(app, monkeypatch, update):
    calls = []
    monkeypatch.setattr(app.state.devices["serial_probe"], "connect", lambda **kwargs: calls.append(kwargs) or {"connected": True})
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/devices/connect", json={"device": "serial_probe", "timing_calibration": calibration_metadata(**update)})
        assert response.status_code == 422
        assert calls == []


def test_connection_receives_exact_operator_fields_and_microphone_is_backwards_compatible(app, monkeypatch):
    calls = []
    record = calibration_metadata()
    monkeypatch.setattr(app.state.devices["serial_probe"], "connect", lambda **kwargs: calls.append(kwargs) or {"connected": True})
    monkeypatch.setattr(app.state.devices["microphone"], "connect", lambda **kwargs: calls.append(kwargs) or {"connected": True})
    with TestClient(app, base_url="http://localhost") as client:
        assert client.post("/devices/connect", json={"device": "serial_probe", "timing_calibration": record}).status_code == 200
        assert calls[0]["timing_calibration"] == record
        assert client.post("/devices/connect", json={"device": "microphone"}).status_code == 200
        assert calls[1]["timing_calibration"] is None
        assert client.post("/devices/connect", json={"device": "microphone", "timing_calibration": record}).status_code == 422
        assert len(calls) == 2


def _stub_runtime():
    return SimpleNamespace(lock=RLock(), emergency_stop={"latched": False}, no_go_regions=[], unavailable_action_keys=set(),
        engine=SimpleNamespace(config=ArgusConfig(), current_recommendation=SimpleNamespace(selected=SimpleNamespace(experiment=EXPERIMENT))))


def test_actual_serial_rate_and_independent_metadata_copy_reach_ingestion(app, monkeypatch):
    record = ProbeTimingCalibration.from_metadata(calibration_metadata(sample_rate_hz=8000), CAPS)
    request = ProbeRequest.build(EXPERIMENT, 8000, CAPS, record, "0" * 32)
    frame = parse_frame(make_frame(request), request, CAPS, record)
    runtime = _stub_runtime()
    device = app.state.devices["serial_probe"]
    device.connected = True
    device.timing_calibration = record
    device.last_acquisition_metadata = frame.metadata
    acquired_rates = []
    monkeypatch.setattr(device, "acquire", lambda experiment, rate: acquired_rates.append(rate) or frame.samples)
    monkeypatch.setattr(app.state.manager, "get", lambda session_id: runtime)
    monkeypatch.setattr(app.state.manager, "public_state", lambda runtime: {"id": "physical-test"})
    seen = []

    def process(session_id, samples, source_rate, experiment, **kwargs):
        seen.append((source_rate, kwargs))
        device.last_acquisition_metadata["raw_adc_samples"][0] = 999
        assert kwargs["sensor_metadata"]["acquisition_timing"]["raw_adc_samples"][0] == 2048
        return SimpleNamespace(index=1, analysis={}, diagnostics={})

    monkeypatch.setattr(app.state.manager, "process_samples", process)
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/sessions/physical-test/experiments/device", json={"device": "serial_probe"})
        assert response.status_code == 200
    assert acquired_rates == [8000]
    assert seen[0][0] == 8000
    assert seen[0][1]["hardware_frame_checked"] is True
    assert seen[0][1]["sensor_metadata"]["measurement_id"] == request.request_id
    assert seen[0][1]["sensor_metadata"]["sensor_id"] == CAPS.device_id


def test_unchecked_serial_data_is_not_ingested(app, monkeypatch):
    runtime = _stub_runtime()
    device = app.state.devices["serial_probe"]
    device.connected = True
    monkeypatch.setattr(device, "acquire", lambda experiment, rate: np.zeros(1920, dtype=np.float32))
    monkeypatch.setattr(app.state.manager, "get", lambda session_id: runtime)
    monkeypatch.setattr(app.state.manager, "process_samples", lambda *args, **kwargs: pytest.fail("Unchecked data reached ingestion"))
    with TestClient(app, base_url="http://localhost") as client:
        assert client.post("/sessions/physical-test/experiments/device", json={"device": "serial_probe"}).status_code == 409


def test_complete_serial_frame_timing_is_persisted_with_the_measurement(app, monkeypatch):
    api_experiment = Experiment(**ExperimentParameters.model_validate(EXPERIMENT.to_dict()).model_dump())

    class ApiSerial(FakeSerial):
        def write(self, data):
            if not data.startswith(b"EXPERIMENT2 "):
                return super().write(data)
            self.writes.append(data)
            fields = data.decode().split()
            record = ProbeTimingCalibration.from_metadata(calibration_metadata(), CAPS)
            request = ProbeRequest.build(api_experiment, 16000, CAPS, record, fields[1])
            assert fields[2] == request.experiment_hash
            self.lines.extend(make_frame(request))

    fake = ApiSerial()
    monkeypatch.setitem(__import__("sys").modules, "serial", SimpleNamespace(Serial=lambda *args, **kwargs: fake))
    monkeypatch.setattr(devices.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(devices.SerialProbeDevice, "available_ports", staticmethod(lambda: [{"port": "COM4"}]))
    with TestClient(app, base_url="http://localhost") as client:
        session = client.post("/sessions", json={"mode": "physical", "seed": 17}).json()
        connect = client.post("/devices/connect", json={"device": "serial_probe", "port": "COM4", "timing_calibration": calibration_metadata()})
        assert connect.status_code == 200
        assert connect.json()["arrival_likelihood_supported"] is True
        result = client.post(f"/sessions/{session['id']}/experiments/device", json={"device": "serial_probe", "experiment": EXPERIMENT.to_dict()})
        assert result.status_code == 200, result.json()
        diagnostics = result.json()["diagnostics"]
        assert diagnostics["physical_timing"]["supported"] is True
        assert diagnostics["physical_timing"]["physical_bench_validation_performed_by_host"] is False
        stored = app.state.repository.list_experiments(session["id"])[0]["diagnostics"]
        assert len(stored["hardware_acquisition"]["raw_adc_samples"]) == 1936
        assert stored["hardware_acquisition"]["operator_timing_calibration"]["device_id"] == CAPS.device_id
        assert client.get(f"/api/ledger/{session['id']}/verify").json()["valid"] is True


@pytest.mark.parametrize("metadata", ["[]", "not JSON", json.dumps({"padding": "a" * 17000})])
def test_uploaded_alignment_metadata_remains_publicly_bounded(app, monkeypatch, metadata):
    monkeypatch.setattr(app.state.manager, "get", lambda session_id: _stub_runtime())
    monkeypatch.setattr(app.state.manager, "process_wav", lambda *args, **kwargs: pytest.fail("Invalid metadata reached WAV ingestion"))
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/sessions/physical-test/experiments/upload", files={"file": ("sample.wav", b"not decoded", "audio/wav")}, data={"sensor_metadata_json": metadata})
        assert response.status_code == 422


def test_wav_declaration_passes_to_ingestion_without_hardware_privilege(app, monkeypatch):
    runtime = _stub_runtime()
    declaration = {"units": "normalized", "acquisition_timing": {"kind": "trigger_aligned_recording"}}
    monkeypatch.setattr(app.state.manager, "get", lambda session_id: runtime)
    monkeypatch.setattr(app.state.manager, "public_state", lambda runtime: {})
    calls = []
    monkeypatch.setattr(app.state.manager, "process_wav", lambda *args, **kwargs: calls.append(kwargs) or SimpleNamespace(index=1, analysis={}, diagnostics={}))
    with TestClient(app, base_url="http://localhost") as client:
        response = client.post("/sessions/physical-test/experiments/upload", files={"file": ("sample.wav", b"delegated decoder", "audio/wav")}, data={"sensor_metadata_json": json.dumps(declaration)})
        assert response.status_code == 200
    assert calls == [{"sensor_metadata": declaration}]
    assert "hardware_frame_checked" not in calls[0]
