from copy import deepcopy
from dataclasses import FrozenInstanceError, replace
from datetime import datetime, timedelta, timezone
import json

import pytest

from backend.app.hardware.protocol_v2 import DRIVE_FAMILY, ProbeCapabilities, ProbeRequest, ProbeTimingCalibration
from backend.app.hardware.timing_contract import assess_physical_timing, canonical_experiment_sha256
from backend.app.models.domain import Experiment

EXPERIMENT = Experiment(.1, .1, .9, .9, 1200, 3000, .28, .12, "chirp")
RATE = 16000
COUNT = 1920


def external_metadata(**updates):
    declaration = {"kind": "trigger_aligned_recording", "sample_rate_hz": RATE,
        "trigger_sample_index": 0, "max_trigger_alignment_error_us": 5., "max_clock_error_ppm": 100.,
        "reference_sha256": "a"*64, "operator": "Timing test operator", "arrival_adapter_validated": True,
        "calibrated_at_utc": datetime.now(timezone.utc).isoformat(),
        "experiment_sha256": canonical_experiment_sha256(EXPERIMENT), "drive_adapter": "validated_experiment_reference"}
    return {"acquisition_timing": {**declaration, **updates}}


def frame_metadata():
    device_id = "ESP32_DAC25_ADC34_001122334455"
    caps = ProbeCapabilities(device_id, 16000, 4096, 12, DRIVE_FAMILY, ("CHIRP", "TONE_BURST"), 16)
    cal = {"device_id": device_id, "sample_rate_hz": RATE, "calibration_id": "fixture-cal-1",
           "calibrated_at_utc": datetime.now(timezone.utc).isoformat(), "reference_sha256": "a"*64,
           "operator": "Timing test operator", "drive_family": DRIVE_FAMILY, "max_sample_jitter_us": 5.,
           "max_clock_error_ppm": 100., "max_trigger_alignment_error_us": 5., "max_drive_code_error": 2,
           "arrival_adapter_validated": True}
    request = ProbeRequest.build(EXPERIMENT, RATE, caps, ProbeTimingCalibration.from_metadata(cal, caps), "0"*32)
    timestamps = [round(i*1000000/RATE) for i in range(request.total_samples)]
    trigger = timestamps[16]
    clock = abs(timestamps[-1]/((request.total_samples-1)*1000000/RATE)-1)*1000000
    return {"acquisition_timing": {"protocol_version": 2, "device_id": device_id,
        "sample_rate_hz": RATE, "used_sample_count": COUNT, "raw_sample_count": COUNT+16,
        "pretrigger_sample_count": 16, "operator_timing_calibration": cal,
        "experiment_sha256": request.experiment_hash, "request_id": request.request_id,
        "raw_frame_sha256": "b"*64, "frame_fnv1a32": "12345678",
        "evidence_status": "frame_contract_checked_with_operator_attestation",
        "sensor_authenticity_verified": False, "physical_bench_validation_performed_by_host": False,
        "sample_timestamps_us": timestamps, "recorded_drive_codes": [128]*request.total_samples,
        "raw_adc_samples": [2048]*request.total_samples, "trigger_time_us": trigger,
        "drive_start_us": trigger, "drive_end_us": trigger+request.burst_us,
        "observed_clock_error_ppm": clock, "maximum_sample_jitter_us": .5,
        "trigger_alignment_error_us": 0., "maximum_drive_code_error": 0}}


def test_absent_contract_has_unknown_time_origin_and_cannot_support_arrival_inference():
    for metadata in (None, {}, {"hardware_frame_checked": True}, {"time": "recorded later"}):
        assessment = assess_physical_timing(metadata, EXPERIMENT, RATE, COUNT)
        assert not assessment.supported
        assert assessment.reason == "unknown_excitation_time_origin"


def test_external_declaration_is_immutable_bounded_summary_and_keeps_operator_scope():
    assessment = assess_physical_timing(external_metadata(), EXPERIMENT, RATE, COUNT)
    assert assessment.supported
    assert assessment.evidence_status == "operator_declared"
    assert not assessment.sensor_authenticity_verified
    assert not assessment.physical_bench_validation_performed_by_host
    summary = assessment.to_dict()
    assert "sample_timestamps_us" not in summary
    json.dumps(summary, allow_nan=False)
    with pytest.raises(FrozenInstanceError): assessment.supported = False


@pytest.mark.parametrize("updates", [
    {"trigger_sample_index": 1}, {"trigger_sample_index": False}, {"sample_rate_hz": 8000},
    {"sample_rate_hz": True}, {"arrival_adapter_validated": 1}, {"arrival_adapter_validated": False},
    {"drive_adapter": "unverified_audio_output"}, {"reference_sha256": "not-a-digest"},
    {"experiment_sha256": "c"*64}, {"operator": ""}, {"operator": "bad\noperator"},
    {"max_trigger_alignment_error_us": 16}, {"max_trigger_alignment_error_us": 0},
    {"max_trigger_alignment_error_us": float("nan")}, {"max_clock_error_ppm": float("inf")},
    {"max_clock_error_ppm": True}, {"max_clock_error_ppm": 1001},
    {"kind": "post_excitation_decay"}, {"hardware_frame_checked": True},
    {"calibrated_at_utc": "2026-10-07"},
    {"calibrated_at_utc": (datetime.now(timezone.utc)-timedelta(days=91)).isoformat()},
    {"calibrated_at_utc": (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()},
])
def test_invalid_external_declarations_are_unsupported(updates):
    assessment = assess_physical_timing(external_metadata(**updates), EXPERIMENT, RATE, COUNT)
    assert not assessment.supported
    assert assessment.reason == "invalid_acquisition_timing_contract"


@pytest.mark.parametrize("rate,count", [(8000, COUNT), (RATE, COUNT-1), (True, COUNT), (RATE, True), (RATE, 999999)])
def test_actual_source_must_bind_rate_count_and_complete_recording(rate, count):
    assert not assess_physical_timing(external_metadata(), EXPERIMENT, rate, count).supported


def test_changed_pose_and_sample_rate_are_bound_by_full_experiment_hash():
    assert not assess_physical_timing(external_metadata(), replace(EXPERIMENT, source_x=.2), RATE, COUNT).supported
    assert not assess_physical_timing(external_metadata(), replace(EXPERIMENT, sample_rate_hz=8000), RATE, COUNT).supported


def test_public_flags_never_elevate_a_fake_serial_frame_or_external_declaration():
    frame = frame_metadata()
    frame["hardware_frame_checked"] = True
    assert not assess_physical_timing(frame, EXPERIMENT, RATE, COUNT).supported
    assert assess_physical_timing(frame, EXPERIMENT, RATE, COUNT).reason == "untrusted_frame_metadata"
    declared = external_metadata()
    declared["hardware_frame_checked"] = True
    assert assess_physical_timing(declared, EXPERIMENT, RATE, COUNT).evidence_status == "operator_declared"
    assert not assess_physical_timing(declared, EXPERIMENT, RATE, COUNT, hardware_frame_checked=True).supported
    assert not assess_physical_timing(frame, EXPERIMENT, RATE, COUNT, hardware_frame_checked=1).supported


def test_server_frame_checked_contract_binds_operator_calibration_and_excludes_raw_arrays():
    frame = frame_metadata()
    before = deepcopy(frame)
    assessment = assess_physical_timing(frame, EXPERIMENT, RATE, COUNT, hardware_frame_checked=True)
    assert assessment.supported, assessment.to_dict()
    assert assessment.evidence_status == "framechecked_operatorattested"
    assert assessment.source_sample_count == COUNT
    assert frame == before
    assert not assessment.sensor_authenticity_verified
    assert not assessment.physical_bench_validation_performed_by_host
    assert len(json.dumps(assessment.to_dict())) < 2000
    assert not any(isinstance(v, (list, tuple)) for v in assessment.to_dict().values())


@pytest.mark.parametrize("key,value", [
    ("protocol_version", True), ("protocol_version", 2.0), ("sample_rate_hz", 8000), ("used_sample_count", 1919),
    ("raw_sample_count", 1935), ("pretrigger_sample_count", 15), ("experiment_sha256", "c"*64),
    ("device_id", "unbound-chip"), ("maximum_drive_code_error", 3),
    ("observed_clock_error_ppm", 10000), ("observed_clock_error_ppm", 0.), ("maximum_sample_jitter_us", float("nan")),
    ("trigger_alignment_error_us", 50), ("drive_start_us", 1050), ("drive_end_us", 500000),
    ("sensor_authenticity_verified", True), ("physical_bench_validation_performed_by_host", True),
    ("raw_frame_sha256", "invalid"), ("frame_fnv1a32", "bad"), ("raw_adc_samples", []),
])
def test_checked_frame_still_requires_consistent_bounded_retained_metadata(key, value):
    metadata = frame_metadata()
    metadata["acquisition_timing"][key] = value
    assert not assess_physical_timing(metadata, EXPERIMENT, RATE, COUNT, hardware_frame_checked=True).supported


@pytest.mark.parametrize("updates", [
    {"device_id": "ESP32_DAC25_ADC34_ffffffffffff"}, {"sample_rate_hz": 8000},
    {"arrival_adapter_validated": False}, {"drive_family": "PWM_SQUARE"},
    {"max_sample_jitter_us": 100}, {"max_trigger_alignment_error_us": True},
    {"calibrated_at_utc": (datetime.now(timezone.utc)-timedelta(days=91)).isoformat()},
])
def test_frame_operator_reference_must_bind_current_chip_rate_adapter_and_time(updates):
    metadata = frame_metadata()
    metadata["acquisition_timing"]["operator_timing_calibration"].update(updates)
    assert not assess_physical_timing(metadata, EXPERIMENT, RATE, COUNT, hardware_frame_checked=True).supported
