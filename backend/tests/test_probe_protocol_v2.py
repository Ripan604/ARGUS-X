from __future__ import annotations

from collections import deque
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import numpy as np
import pytest

from backend.app.hardware import devices
from backend.app.hardware.devices import SerialProbeDevice
from backend.app.hardware.protocol_v2 import (
    DRIVE_FAMILY, MAX_LINE_BYTES, ProbeCapabilities, ProbeRequest,
    ProbeTimingCalibration, fnv1a32, parse_frame, wire_line,
)
from backend.app.models.domain import Experiment


CAPS_LINE = b"CAPS,2,ESP32_DAC25_ADC34_001122334455,16000,4096,12,concurrent_triggered,DAC8_SAMPLED_SINE,CHIRP|TONE_BURST,16\n"
CAPS = ProbeCapabilities.parse(CAPS_LINE)
EXPERIMENT = Experiment(0.1, 0.1, 0.9, 0.9, 1200, 3000, 0.28, 0.12, "chirp")


def calibration_metadata(**updates):
    metadata = {
        "device_id": CAPS.device_id, "sample_rate_hz": 16000,
        "calibration_id": "bench-reference-001", "calibrated_at_utc": datetime.now(timezone.utc).isoformat(),
        "reference_sha256": "a" * 64, "operator": "Test operator",
        "drive_family": DRIVE_FAMILY, "max_sample_jitter_us": 5.0,
        "max_clock_error_ppm": 100.0, "max_trigger_alignment_error_us": 5.0,
        "max_drive_code_error": 2, "arrival_adapter_validated": True,
    }
    return {**metadata, **updates}


@pytest.fixture
def calibration():
    return ProbeTimingCalibration.from_metadata(calibration_metadata(), CAPS)


@pytest.fixture
def probe_request(calibration):
    return ProbeRequest.build(EXPERIMENT, 16000, CAPS, calibration, "0" * 32)


def make_frame(probe_request):
    rate = probe_request.sample_rate_hz
    trigger = round(probe_request.pretrigger_samples * 1000000 / rate)
    experiment = probe_request.experiment
    header = (f"BEGIN2,{probe_request.request_id},{probe_request.experiment_hash},{probe_request.total_samples},{rate},12,{DRIVE_FAMILY},"
              f"{probe_request.wire_waveform},{probe_request.pretrigger_samples},{trigger},{experiment.frequency_start_hz},"
              f"{experiment.frequency_end_hz},{experiment.amplitude},{probe_request.window_us},{probe_request.burst_us},"
              f"{trigger},{trigger + probe_request.burst_us}\n").encode()
    codes = probe_request.expected_drive_codes()
    data = [f"DATA2,{index},{round(index * 1000000 / rate)},{2048 + index % 16},{codes[index]}\n".encode()
            for index in range(probe_request.total_samples)]
    lines = [header, *data, b"placeholder\n"]
    return reseal(lines, probe_request)


def reseal(lines, probe_request):
    checksum = 2166136261
    for raw in lines[1:-1]:
        canonical = raw.removeprefix(b"DATA2,")
        checksum = fnv1a32(canonical, checksum)
    return [*lines[:-1], f"END2,{probe_request.request_id},{probe_request.total_samples},{checksum:08x},OK,0\n".encode()]


def changed_line(line, field, value):
    fields = line.decode().strip().split(",")
    fields[field] = str(value)
    return (",".join(fields) + "\n").encode()


def test_complete_frame_preserves_trigger_relative_window_and_provenance(probe_request, calibration):
    frame = parse_frame(make_frame(probe_request), probe_request, CAPS, calibration)
    assert len(frame.samples) == round(EXPERIMENT.duration_s * 16000)
    assert frame.samples.dtype == np.float32
    assert frame.samples[0] == 0  # ADC2048 at index16, no median-based guessed scaling.
    assert frame.samples[1] == pytest.approx(1 / 2048)
    metadata = frame.metadata
    assert metadata["raw_sample_count"] == len(frame.samples) + 16
    assert metadata["pretrigger_sample_count"] == 16
    assert metadata["trigger_time_us"] == 1000
    assert metadata["sample_timestamps_us"][16] == 1000
    assert len(metadata["raw_adc_samples"]) == probe_request.total_samples
    assert len(metadata["recorded_drive_codes"]) == probe_request.total_samples
    assert metadata["sensor_authenticity_verified"] is False
    assert metadata["physical_bench_validation_performed_by_host"] is False
    assert metadata["operator_timing_calibration"]["reference_sha256"] == "a" * 64


def test_complete_experiment_hash_binds_pose_and_all_model_parameters(probe_request):
    canonical = json.dumps(EXPERIMENT.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    assert probe_request.experiment_hash == hashlib.sha256(canonical).hexdigest()
    assert len(probe_request.command().split()) == 10
    assert probe_request.command().startswith(b"EXPERIMENT2 " + b"0" * 32)
    assert probe_request.experiment_hash.encode() in probe_request.command()
    changed = replace(EXPERIMENT, source_x=0.2)
    other = ProbeRequest.build(changed, 16000, CAPS, ProbeTimingCalibration.from_metadata(calibration_metadata(), CAPS), "0" * 32)
    assert other.experiment_hash != probe_request.experiment_hash


@pytest.mark.parametrize("field,value", [
    (1, "1" * 32), (2, "b" * 64), (3, 1900), (4, 8000), (5, 10),
    (6, "PWM_SQUARE"), (7, "TONE_BURST"), (8, 15), (9, 1050),
    (10, 1300), (11, 3500), (12, 0.6), (13, 100000), (14, 8000),
    (15, 1050), (16, 16000),
])
def test_frame_header_rejects_rebound_or_unaligned_experiment(probe_request, calibration, field, value):
    lines = make_frame(probe_request)
    lines[0] = changed_line(lines[0], field, value)
    with pytest.raises(ValueError):
        parse_frame(lines, probe_request, CAPS, calibration)


@pytest.mark.parametrize("field,value", [(1, 7), (2, -1), (2, "nan"), (3, 4096), (3, -1), (4, 256), (4, -1)])
def test_invalid_adc_samples_and_indices_are_rejected(probe_request, calibration, field, value):
    lines = make_frame(probe_request)
    lines[6] = changed_line(lines[6], field, value)
    with pytest.raises(ValueError):
        parse_frame(lines, probe_request, CAPS, calibration)


def test_transport_bit_corruption_never_produces_partial_evidence(probe_request, calibration):
    lines = make_frame(probe_request)
    lines[20] = changed_line(lines[20], 3, 2040)
    with pytest.raises(ValueError, match="checksum"):
        parse_frame(lines, probe_request, CAPS, calibration)


@pytest.mark.parametrize("fault", ["missing", "truncated", "trailer_missing", "extra", "overrun", "stopped", "wrong_count"])
def test_frame_must_be_complete_and_successful(probe_request, calibration, fault):
    lines = make_frame(probe_request)
    if fault == "missing":
        del lines[10]
    elif fault == "truncated":
        lines[10] = lines[10].removesuffix(b"\n")
    elif fault == "trailer_missing":
        lines.pop()
    elif fault == "extra":
        lines.append(b"DATA2,0,0,2048,128\n")
    elif fault == "overrun":
        lines[-1] = changed_line(lines[-1], 4, "OVERRUN")
    elif fault == "stopped":
        lines[-1] = changed_line(lines[-1], 4, "STOPPED")
    else:
        lines[-1] = changed_line(lines[-1], 2, probe_request.total_samples - 1)
    with pytest.raises(ValueError):
        parse_frame(lines, probe_request, CAPS, calibration)


@pytest.mark.parametrize("fault", ["wrong_clock", "jitter", "repeated_time", "nonzero_start", "wrong_drive", "lateness"])
def test_resealed_frame_still_requires_physical_timing_and_drive_contract(probe_request, calibration, fault):
    lines = make_frame(probe_request)
    if fault == "wrong_clock":
        for index in range(probe_request.total_samples):
            lines[index + 1] = changed_line(lines[index + 1], 2, round(index * 63.0))
    elif fault == "jitter":
        lines[101] = changed_line(lines[101], 2, 6270)
    elif fault == "repeated_time":
        lines[101] = changed_line(lines[101], 2, 6188)
    elif fault == "nonzero_start":
        lines[1] = changed_line(lines[1], 2, 1)
    elif fault == "wrong_drive":
        lines[40] = changed_line(lines[40], 4, 255)
    lines = reseal(lines, probe_request)
    if fault == "lateness":
        lines[-1] = changed_line(lines[-1], 5, 25)
    with pytest.raises(ValueError):
        parse_frame(lines, probe_request, CAPS, calibration)


@pytest.mark.parametrize("updates", [
    {"arrival_adapter_validated": False}, {"arrival_adapter_validated": 1},
    {"device_id": "another-probe"}, {"drive_family": "PWM_SQUARE"},
    {"sample_rate_hz": 20000}, {"sample_rate_hz": True},
    {"reference_sha256": "missing"}, {"operator": ""}, {"calibration_id": "x"},
    {"max_sample_jitter_us": 200}, {"max_sample_jitter_us": float("nan")},
    {"max_clock_error_ppm": 1001}, {"max_trigger_alignment_error_us": 20},
    {"max_drive_code_error": 3}, {"max_drive_code_error": True},
    {"calibrated_at_utc": "2026-01-01"},
    {"calibrated_at_utc": (datetime.now(timezone.utc) - timedelta(days=91)).isoformat()},
    {"calibrated_at_utc": (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()},
])
def test_calibration_is_bounded_device_specific_operator_evidence(updates):
    with pytest.raises(ValueError):
        ProbeTimingCalibration.from_metadata(calibration_metadata(**updates), CAPS)


def test_incomplete_or_extra_calibration_fields_are_rejected():
    metadata = calibration_metadata()
    del metadata["reference_sha256"]
    with pytest.raises(ValueError):
        ProbeTimingCalibration.from_metadata(metadata, CAPS)
    with pytest.raises(ValueError):
        ProbeTimingCalibration.from_metadata(calibration_metadata(verified_by_version=True), CAPS)


def test_calibration_cannot_silently_move_between_same_family_chips():
    second = ProbeCapabilities.parse(CAPS_LINE.replace(b"001122334455", b"001122334466"))
    with pytest.raises(ValueError, match="device"):
        ProbeTimingCalibration.from_metadata(calibration_metadata(), second)


@pytest.mark.parametrize("field,value", [(1, 1), (2, "ESP32_DAC25_ADC34"), (3, 20000), (4, 200000),
                                        (5, 8), (6, "post_excitation"), (7, "PWM_SQUARE"), (8, "CHIRP"), (9, 0)])
def test_unsupported_capability_claims_fail_closed(field, value):
    with pytest.raises(ValueError):
        ProbeCapabilities.parse(changed_line(CAPS_LINE, field, value))


@pytest.mark.parametrize("experiment", [
    replace(EXPERIMENT, waveform="phase_coded"), replace(EXPERIMENT, waveform="impulse"),
    replace(EXPERIMENT, amplitude=0.61), replace(EXPERIMENT, duration_s=0.3),
    replace(EXPERIMENT, frequency_end_hz=6500), replace(EXPERIMENT, waveform="sine"),
    replace(EXPERIMENT, code_length=4), replace(EXPERIMENT, sample_rate_hz=8000),
])
def test_unsupported_experiment_is_rejected_before_actuation(experiment, calibration):
    with pytest.raises(ValueError):
        ProbeRequest.build(experiment, 16000, CAPS, calibration, "0" * 32)


def test_sine_and_tone_burst_have_explicit_equivalent_wire_contract(calibration):
    sine = replace(EXPERIMENT, waveform="sine", frequency_end_hz=1200)
    tone = replace(sine, waveform="tone_burst")
    first = ProbeRequest.build(sine, 16000, CAPS, calibration, "0" * 32)
    second = ProbeRequest.build(tone, 16000, CAPS, calibration, "0" * 32)
    assert first.wire_waveform == second.wire_waveform == "TONE_BURST"
    assert first.experiment_hash != second.experiment_hash
    np.testing.assert_array_equal(first.expected_drive_codes(), second.expected_drive_codes())
    parse_frame(make_frame(first), first, CAPS, calibration)


@pytest.mark.parametrize("raw", [b"x" * (MAX_LINE_BYTES + 1) + b"\n", b"DATA2,0", b"bad\xff\n", b"DATA2,0\x00\n", b"DATA2,0\n\n"])
def test_serial_lines_have_bounded_complete_ascii_representation(raw):
    with pytest.raises(ValueError):
        wire_line(raw)


class FakeSerial:
    def __init__(self, pong=b"PONG,ARGUS_PROBE,2\n", corruption=False):
        self.pong = pong
        self.lines = deque()
        self.writes = []
        self.closed = False
        self.corruption = corruption

    def reset_input_buffer(self):
        self.lines.clear()

    def write(self, data):
        self.writes.append(data)
        if data == b"PING\n":
            self.lines.append(self.pong)
        elif data == b"CAPABILITIES\n":
            self.lines.append(CAPS_LINE)
        elif data.startswith(b"EXPERIMENT2 "):
            fields = data.decode().split()
            calibration = ProbeTimingCalibration.from_metadata(calibration_metadata(), CAPS)
            probe_request = ProbeRequest.build(EXPERIMENT, 16000, CAPS, calibration, fields[1])
            assert fields[2] == probe_request.experiment_hash
            lines = make_frame(probe_request)
            if self.corruption:
                lines[-1] = changed_line(lines[-1], 4, "OVERRUN")
            self.lines.extend(lines)

    def readline(self, size):
        assert size == MAX_LINE_BYTES + 1
        return self.lines.popleft() if self.lines else b""

    def close(self):
        self.closed = True


def connected_device(monkeypatch, fake, metadata=None):
    monkeypatch.setitem(sys.modules, "serial", SimpleNamespace(Serial=lambda *args, **kwargs: fake))
    monkeypatch.setattr(devices.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(SerialProbeDevice, "available_ports", staticmethod(lambda: [{"port": "COM4"}]))
    device = SerialProbeDevice()
    result = device.connect(port="COM4", timing_calibration=metadata)
    return device, result


def test_wire_version_alone_cannot_enable_arrival_ingestion(monkeypatch):
    fake = FakeSerial()
    device, status = connected_device(monkeypatch, fake)
    assert status["connected"] is True
    assert status["protocol_version"] == 2
    assert status["arrival_likelihood_supported"] is False
    with pytest.raises(RuntimeError, match="explicit"):
        device.acquire(EXPERIMENT, 16000)
    assert not any(item.startswith(b"EXPERIMENT") for item in fake.writes)


def test_legacy_remains_blocked_even_if_support_flag_is_manually_changed(monkeypatch):
    fake = FakeSerial(pong=b"PONG,ARGUS_PROBE,1\n")
    device, status = connected_device(monkeypatch, fake)
    assert status["connected"] is True
    assert status["protocol_version"] == 1
    device.arrival_likelihood_supported = True
    with pytest.raises(RuntimeError):
        device.acquire(EXPERIMENT, 16000)
    assert not any(item.startswith(b"EXPERIMENT") for item in fake.writes)


def test_calibrated_v2_device_returns_only_complete_trigger_aligned_window(monkeypatch):
    fake = FakeSerial()
    device, status = connected_device(monkeypatch, fake, calibration_metadata())
    assert status["arrival_likelihood_supported"] is True
    samples = device.acquire(EXPERIMENT, 16000)
    assert samples.size == 1920
    assert device.last_acquisition_metadata["raw_sample_count"] == 1936
    assert device.status()["last_frame_contract_checked"] is True
    assert not any(item.startswith(b"EXPERIMENT ") for item in fake.writes)


def test_corrupted_device_frame_closes_and_revokes_acquisition_permission(monkeypatch):
    fake = FakeSerial(corruption=True)
    device, _ = connected_device(monkeypatch, fake, calibration_metadata())
    with pytest.raises(RuntimeError, match="rejected"):
        device.acquire(EXPERIMENT, 16000)
    assert fake.closed is True
    assert device.connected is False
    assert device.arrival_likelihood_supported is False
    assert device.last_acquisition_metadata is None
    assert b"STOP\n" in fake.writes


def test_invalid_calibration_or_command_never_reaches_device_excitation(monkeypatch):
    fake = FakeSerial()
    device, status = connected_device(monkeypatch, fake, calibration_metadata(reference_sha256="bad"))
    assert status["connected"] is False
    assert fake.closed is True
    assert not any(item.startswith(b"EXPERIMENT") for item in fake.writes)
    fake = FakeSerial()
    device, _ = connected_device(monkeypatch, fake, calibration_metadata())
    with pytest.raises(ValueError):
        device.acquire(replace(EXPERIMENT, amplitude=0.75), 16000)
    assert not any(item.startswith(b"EXPERIMENT") for item in fake.writes)


def test_missing_frame_uses_bounded_deadline_and_drops_permission(monkeypatch):
    fake = FakeSerial()
    device, _ = connected_device(monkeypatch, fake, calibration_metadata())
    original_write = fake.write

    def discard_frame(data):
        result = original_write(data)
        if data.startswith(b"EXPERIMENT2 "):
            fake.lines.clear()
        return result

    fake.write = discard_frame
    ticks = iter(range(0, 1000, 10))
    monkeypatch.setattr(devices.time, "monotonic", lambda: next(ticks))
    with pytest.raises(RuntimeError, match="Timed out"):
        device.acquire(EXPERIMENT, 16000)
    assert device.connected is False
    assert fake.closed is True
    assert device.last_acquisition_metadata is None


def test_opaque_or_misleading_pong_is_not_a_capability_handshake(monkeypatch):
    fake = FakeSerial(pong=b"other,PONG,ARGUS_PROBE,2\n")
    _, status = connected_device(monkeypatch, fake)
    assert status["connected"] is False
    assert status["arrival_likelihood_supported"] is False
    assert fake.closed is True


def test_host_accepts_compiled_firmware_mock_fixture_when_binding_matches(probe_request, calibration):
    fixture = Path(__file__).resolve().parents[2] / "output/release/probe-v2-host-fixture.txt"
    if not fixture.exists():
        pytest.skip("Firmware mock fixture is unavailable")
    # The standalone C++ mock uses an opaque example hash; probe_request-builder
    # canonical binding is tested separately. Firmware only echoes that hash.
    matching = replace(probe_request, experiment_hash="a" * 64)
    lines = fixture.read_bytes().splitlines(keepends=True)
    frame = parse_frame(lines, matching, CAPS, calibration)
    assert frame.samples.size == 1920
    assert frame.metadata["maximum_drive_code_error"] <= 2
