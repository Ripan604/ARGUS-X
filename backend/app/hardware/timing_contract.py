"""Server assessment of an acquisition's excitation-relative time origin.

The serial parser performs wire/frame checks. This module checks consistency of
its retained metadata and operator evidence without parsing or authenticating a
frame again. External declarations remain operator assertions. Neither path is
host-performed physical bench validation or a sensor authenticity certificate.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
from typing import Mapping

from backend.app.hardware.protocol_v2 import (
    DEVICE_ID_PREFIX, DRIVE_FAMILY, MAX_CALIBRATION_AGE_DAYS, MAX_FRAME_SAMPLES,
    PRETRIGGER_SAMPLES, ProbeCapabilities, ProbeRequest, ProbeTimingCalibration,
)
from backend.app.models.domain import Experiment


@dataclass(frozen=True)
class AcquisitionTimingAssessment:
    supported: bool = False
    reason: str = "unknown_excitation_time_origin"
    evidence_status: str = "unsupported"
    detail: str | None = None
    source_sample_rate_hz: int | None = None
    source_sample_count: int | None = None
    experiment_sha256: str | None = None
    reference_sha256: str | None = None
    operator: str | None = None
    calibrated_at_utc: str | None = None
    max_trigger_alignment_error_us: float | None = None
    max_clock_error_ppm: float | None = None
    sensor_authenticity_verified: bool = False
    physical_bench_validation_performed_by_host: bool = False

    def to_dict(self) -> dict:
        """Bounded public summary; raw arrays belong in separate retained evidence."""
        return asdict(self)


def canonical_experiment_sha256(experiment: Experiment) -> str:
    payload = json.dumps(experiment.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _integer(value, name: str, lower: int, upper: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not lower <= value <= upper:
        raise ValueError(f"{name} requires a bounded integer")
    return value


def _number(value, name: str, lower: float, upper: float, *, positive: bool = False) -> float:
    if (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
            or value < lower or value > upper or positive and value <= 0):
        raise ValueError(f"{name} exceeds the finite supported timing bounds")
    return float(value)


def _sha(value, name: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"{name} requires a lowercase SHA-256 digest")
    return value


def _operator(value) -> str:
    if (not isinstance(value, str) or not 3 <= len(value.strip()) <= 128
            or any(ord(c) < 32 or ord(c) == 127 for c in value)):
        raise ValueError("A bounded named operator is required")
    return value.strip()


def _calibration_time(value) -> str:
    if not isinstance(value, str) or not 10 <= len(value) <= 64:
        raise ValueError("Calibration timestamp must be aware ISO-8601")
    try:
        observed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Calibration timestamp must be aware ISO-8601") from exc
    if observed.tzinfo is None:
        raise ValueError("Calibration timestamp must include a timezone")
    observed = observed.astimezone(timezone.utc)
    now = datetime.now(timezone.utc)
    if not now-timedelta(days=MAX_CALIBRATION_AGE_DAYS) <= observed <= now+timedelta(minutes=5):
        raise ValueError("Calibration is stale or dated in the future under the 90-day operator policy")
    return observed.isoformat()


def _source_contract(experiment: Experiment, source_rate: int, source_count: int) -> str:
    _integer(source_rate, "actual source rate", 1000, 384000)
    _integer(source_count, "actual source sample count", 8, 384000)
    if source_count != round(experiment.duration_s * source_rate):
        raise ValueError("Actual source sample count does not cover the declared experiment window")
    if experiment.sample_rate_hz is not None and experiment.sample_rate_hz != source_rate:
        raise ValueError("Actual source rate differs from the complete experiment")
    if experiment.frequency_end_hz >= source_rate / 2:
        raise ValueError("Experiment exceeds the actual source Nyquist bound")
    return canonical_experiment_sha256(experiment)


def _external_assessment(timing: Mapping, experiment: Experiment, source_rate: int,
                         source_count: int, experiment_hash: str) -> AcquisitionTimingAssessment:
    fields = {"kind", "sample_rate_hz", "trigger_sample_index", "max_trigger_alignment_error_us",
              "max_clock_error_ppm", "reference_sha256", "operator", "arrival_adapter_validated",
              "calibrated_at_utc", "experiment_sha256", "drive_adapter"}
    if set(timing) != fields:
        raise ValueError("External timing declaration requires exactly the supported evidence fields")
    if timing["kind"] != "trigger_aligned_recording":
        raise ValueError("Only explicitly trigger-aligned external recordings support arrival inference")
    if _integer(timing["sample_rate_hz"], "declared source rate", 1000, 384000) != source_rate:
        raise ValueError("Declared timing rate does not bind the actual source rate")
    _integer(timing["trigger_sample_index"], "trimmed trigger sample index", 0, 0)
    if timing["arrival_adapter_validated"] is not True or timing["drive_adapter"] != "validated_experiment_reference":
        raise ValueError("External timing requires explicit experiment-reference arrival/drive adapter attestation")
    if _sha(timing["experiment_sha256"], "experiment binding") != experiment_hash:
        raise ValueError("External recording does not bind the complete requested experiment")
    alignment = _number(timing["max_trigger_alignment_error_us"], "declared trigger alignment", 0,
                        min(20., 250000./source_rate), positive=True)
    clock = _number(timing["max_clock_error_ppm"], "declared clock error", 0, 1000, positive=True)
    reference = _sha(timing["reference_sha256"], "external timing reference")
    operator = _operator(timing["operator"])
    calibrated_at = _calibration_time(timing["calibrated_at_utc"])
    return AcquisitionTimingAssessment(True, "operator_declared_trigger_alignment", "operator_declared",
        source_sample_rate_hz=source_rate, source_sample_count=source_count,
        experiment_sha256=experiment_hash, reference_sha256=reference, operator=operator,
        calibrated_at_utc=calibrated_at, max_trigger_alignment_error_us=alignment, max_clock_error_ppm=clock)


def _frame_assessment(timing: Mapping, experiment: Experiment, source_rate: int,
                      source_count: int, experiment_hash: str) -> AcquisitionTimingAssessment:
    _integer(timing.get("protocol_version"), "server-checked frame version", 2, 2)
    device_id = timing.get("device_id")
    if not isinstance(device_id, str) or not re.fullmatch(DEVICE_ID_PREFIX+r"[0-9a-f]{12}", device_id):
        raise ValueError("V2 timing does not bind a supported acquisition chip")
    capabilities = ProbeCapabilities(device_id, 16000, MAX_FRAME_SAMPLES, 12, DRIVE_FAMILY,
                                     ("CHIRP", "TONE_BURST"), PRETRIGGER_SAMPLES)
    calibration = ProbeTimingCalibration.from_metadata(timing.get("operator_timing_calibration"), capabilities)
    # This validates current calibration, complete experiment/rate envelope,
    # and expected counts only. It does not parse the retained sample frame.
    request = ProbeRequest.build(experiment, source_rate, capabilities, calibration, timing.get("request_id"))
    if (_sha(timing.get("experiment_sha256"), "frame experiment binding") != experiment_hash
            or request.experiment_hash != experiment_hash):
        raise ValueError("Frame timing does not bind the complete requested experiment")
    if (_integer(timing.get("sample_rate_hz"), "frame source rate", 1000, 16000) != source_rate
            or _integer(timing.get("used_sample_count"), "frame used count", 8, MAX_FRAME_SAMPLES) != source_count
            or source_count != request.posttrigger_samples
            or _integer(timing.get("raw_sample_count"), "frame raw count", 8, MAX_FRAME_SAMPLES) != request.total_samples
            or _integer(timing.get("pretrigger_sample_count"), "frame pretrigger count", PRETRIGGER_SAMPLES, PRETRIGGER_SAMPLES) != request.pretrigger_samples):
        raise ValueError("Frame counts or rate do not bind the actual trigger-relative source samples")
    _sha(timing.get("raw_frame_sha256"), "retained frame digest")
    if not isinstance(timing.get("frame_fnv1a32"), str) or not re.fullmatch(r"[0-9a-f]{8}", timing["frame_fnv1a32"]):
        raise ValueError("Frame integrity marker is missing")
    if (timing.get("evidence_status") != "frame_contract_checked_with_operator_attestation"
            or timing.get("sensor_authenticity_verified") is not False
            or timing.get("physical_bench_validation_performed_by_host") is not False):
        raise ValueError("Frame metadata cannot claim unperformed authenticity or host bench validation")
    for name in ("sample_timestamps_us", "recorded_drive_codes", "raw_adc_samples"):
        values = timing.get(name)
        if not isinstance(values, (list, tuple)) or len(values) != request.total_samples:
            raise ValueError("Retained raw frame arrays do not match the checked acquisition count")
    timestamps = timing["sample_timestamps_us"]
    first = _integer(timestamps[0], "frame first timestamp", 0, 0)
    trigger_timestamp = _integer(timestamps[request.pretrigger_samples], "frame trigger sample time", 0, 1000000)
    last = _integer(timestamps[-1], "frame last timestamp", 1, 1000000)
    trigger = _integer(timing.get("trigger_time_us"), "frame trigger time", 0, 1000000)
    drive_start = _integer(timing.get("drive_start_us"), "frame drive start", 0, 1000000)
    drive_end = _integer(timing.get("drive_end_us"), "frame drive end", 1, 1000000)
    period = 1000000./source_rate
    quantization_ppm = 1000000./((request.total_samples-1)*period)
    clock = _number(timing.get("observed_clock_error_ppm"), "actual frame clock error", 0,
                    calibration.max_clock_error_ppm+quantization_ppm)
    jitter = _number(timing.get("maximum_sample_jitter_us"), "actual frame jitter", 0,
                     calibration.max_sample_jitter_us+1)
    alignment = _number(timing.get("trigger_alignment_error_us"), "actual frame alignment", 0,
                        calibration.max_trigger_alignment_error_us+1)
    _integer(timing.get("maximum_drive_code_error"), "actual drive-reference error", 0, calibration.max_drive_code_error)
    expected_clock = abs((last-first)/((request.total_samples-1)*period)-1)*1000000
    if not math.isclose(clock, expected_clock, rel_tol=1e-8, abs_tol=1e-6):
        raise ValueError("Reported frame clock error is inconsistent with retained timestamps")
    if (not math.isclose(alignment, abs(trigger_timestamp-trigger), abs_tol=1e-9)
            or abs(drive_start-trigger) > calibration.max_trigger_alignment_error_us+1
            or drive_end <= drive_start or drive_end > last
            or abs((drive_end-drive_start)-request.burst_us) > calibration.max_sample_jitter_us+period+1
            or last-trigger < (source_count-1)*period-calibration.max_sample_jitter_us-calibration.max_trigger_alignment_error_us-1):
        raise ValueError("Frame drive, trigger, and source coverage metadata are inconsistent")
    if jitter < max(abs(first), abs(trigger_timestamp-request.pretrigger_samples*period),
                    abs(last-(request.total_samples-1)*period)) - 1e-9:
        raise ValueError("Reported maximum sample jitter is inconsistent with retained endpoint timing")
    return AcquisitionTimingAssessment(True, "server_frame_checked_with_operator_timing_attestation", "framechecked_operatorattested",
        source_sample_rate_hz=source_rate, source_sample_count=source_count,
        experiment_sha256=experiment_hash, reference_sha256=calibration.reference_sha256,
        operator=_operator(calibration.operator), calibrated_at_utc=_calibration_time(calibration.calibrated_at_utc),
        max_trigger_alignment_error_us=calibration.max_trigger_alignment_error_us,
        max_clock_error_ppm=calibration.max_clock_error_ppm)


def assess_physical_timing(sensor_metadata: Mapping | None, experiment: Experiment,
                           source_rate: int, source_count: int, *,
                           hardware_frame_checked: bool = False) -> AcquisitionTimingAssessment:
    """Assess timing; only server code can supply the frame-checked keyword.

    A similarly named value inside user metadata never changes this keyword or
    elevates an operator declaration into frame-checked evidence.
    """
    if not isinstance(sensor_metadata, Mapping) or "acquisition_timing" not in sensor_metadata:
        return AcquisitionTimingAssessment()
    if not isinstance(hardware_frame_checked, bool):
        return AcquisitionTimingAssessment(reason="invalid_server_frame_flag")
    timing = sensor_metadata.get("acquisition_timing")
    if not isinstance(timing, Mapping):
        return AcquisitionTimingAssessment(reason="invalid_acquisition_timing_contract", detail="Nested timing evidence must be an object")
    try:
        experiment_hash = _source_contract(experiment, source_rate, source_count)
        if hardware_frame_checked:
            return _frame_assessment(timing, experiment, source_rate, source_count, experiment_hash)
        if timing.get("protocol_version") is not None or timing.get("evidence_status") is not None:
            return AcquisitionTimingAssessment(reason="untrusted_frame_metadata",
                detail="Public frame claims lack a server-controlled successful frame check")
        return _external_assessment(timing, experiment, source_rate, source_count, experiment_hash)
    except (ValueError, TypeError, AttributeError, OverflowError) as exc:
        return AcquisitionTimingAssessment(reason="invalid_acquisition_timing_contract", detail=str(exc)[:256])
