"""Bounded, trigger-referenced serial frames; integrity is not authentication.

An operator's external timing/transfer calibration is required independently of
wire version. Parsing a frame does not validate the specimen or the apparatus.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import re
from typing import Iterable, Mapping

import numpy as np
from scipy.signal import windows

from backend.app.models.domain import Experiment


MAX_LINE_BYTES = 512
MAX_FRAME_SAMPLES = 4096
PRETRIGGER_SAMPLES = 16
DRIVE_FAMILY = "DAC8_SAMPLED_SINE"
DEVICE_ID_PREFIX = "ESP32_DAC25_ADC34_"
PONG_V2 = b"PONG,ARGUS_PROBE,2"
PONG_LEGACY = b"PONG,ARGUS_PROBE,1"
MAX_CALIBRATION_AGE_DAYS = 90  # Conservative operator-policy heuristic, not a metrology standard.


def _integer(value: str, name: str, minimum: int, maximum: int) -> int:
    if not re.fullmatch(r"[0-9]{1,10}", value):
        raise ValueError(f"Invalid integer {name}")
    number = int(value)
    if not minimum <= number <= maximum:
        raise ValueError(f"{name} outside supported bounds")
    return number


def _finite(value: str, name: str) -> float:
    try:
        number = float(value)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"Invalid {name}") from exc
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def wire_line(raw: bytes) -> str:
    if not isinstance(raw, bytes) or len(raw) > MAX_LINE_BYTES or not raw.endswith(b"\n"):
        raise ValueError("Oversized or incomplete serial line")
    try:
        line = raw[:-1].removesuffix(b"\r").decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("Serial frame must be ASCII") from exc
    if not line or any(ord(character) < 32 or ord(character) > 126 for character in line):
        raise ValueError("Invalid serial control characters")
    return line


@dataclass(frozen=True)
class ProbeCapabilities:
    device_id: str
    max_sample_rate_hz: int
    max_samples: int
    adc_bits: int
    drive_family: str
    waveforms: tuple[str, ...]
    pretrigger_samples: int

    @classmethod
    def parse(cls, raw: bytes) -> ProbeCapabilities:
        fields = wire_line(raw).split(",")
        if len(fields) != 10 or fields[:2] != ["CAPS", "2"] or fields[6] != "concurrent_triggered":
            raise ValueError("Unsupported v2 acquisition capabilities")
        if (not re.fullmatch(DEVICE_ID_PREFIX + r"[0-9a-f]{12}", fields[2])
                or fields[7] != DRIVE_FAMILY or fields[8] != "CHIRP|TONE_BURST"):
            raise ValueError("Unsupported device, drive transfer, or waveform adapter")
        return cls(fields[2], _integer(fields[3], "maximum rate", 1000, 16000),
                   _integer(fields[4], "maximum samples", 48, MAX_FRAME_SAMPLES),
                   _integer(fields[5], "ADC bits", 12, 12), fields[7], tuple(fields[8].split("|")),
                   _integer(fields[9], "pretrigger samples", PRETRIGGER_SAMPLES, PRETRIGGER_SAMPLES))


@dataclass(frozen=True)
class ProbeTimingCalibration:
    device_id: str
    sample_rate_hz: int
    calibration_id: str
    calibrated_at_utc: str
    reference_sha256: str
    operator: str
    drive_family: str
    max_sample_jitter_us: float
    max_clock_error_ppm: float
    max_trigger_alignment_error_us: float
    max_drive_code_error: int
    arrival_adapter_validated: bool

    @classmethod
    def from_metadata(cls, metadata: Mapping, capabilities: ProbeCapabilities) -> ProbeTimingCalibration:
        if not isinstance(metadata, Mapping) or set(metadata) != set(cls.__dataclass_fields__):
            raise ValueError("Timing calibration requires the complete, supported operator evidence fields")
        calibration = cls(**dict(metadata))
        calibration.validate(capabilities)
        return calibration

    def validate(self, capabilities: ProbeCapabilities) -> None:
        if self.device_id != capabilities.device_id or self.drive_family != capabilities.drive_family:
            raise ValueError("Calibration does not bind this device/drive adapter")
        if (isinstance(self.sample_rate_hz, bool) or not isinstance(self.sample_rate_hz, int)
                or not 1000 <= self.sample_rate_hz <= capabilities.max_sample_rate_hz):
            raise ValueError("Calibration must bind a supported sample rate")
        if not isinstance(self.calibration_id, str) or not re.fullmatch(r"[A-Za-z0-9_.:-]{3,128}", self.calibration_id):
            raise ValueError("Calibration ID must be a bounded identifier")
        if not isinstance(self.operator, str) or not 3 <= len(self.operator.strip()) <= 128:
            raise ValueError("Calibration requires a named operator")
        if not isinstance(self.reference_sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", self.reference_sha256):
            raise ValueError("Calibration requires an external reference evidence SHA256")
        if self.arrival_adapter_validated is not True:
            raise ValueError("Operator must explicitly attest the device-specific arrival/drive adapter validation")
        try:
            observed = datetime.fromisoformat(self.calibrated_at_utc.replace("Z", "+00:00"))
        except (ValueError, TypeError, AttributeError) as exc:
            raise ValueError("Calibration time must be aware ISO-8601") from exc
        if observed.tzinfo is None:
            raise ValueError("Calibration time must include a timezone")
        now = datetime.now(timezone.utc)
        if not now - timedelta(days=MAX_CALIBRATION_AGE_DAYS) <= observed.astimezone(timezone.utc) <= now + timedelta(minutes=5):
            raise ValueError("Calibration is expired or dated in the future")
        quarter_period_us = 250000.0 / self.sample_rate_hz
        limits = {"max_sample_jitter_us": min(20.0, quarter_period_us),
                  "max_clock_error_ppm": 1000.0,
                  "max_trigger_alignment_error_us": min(20.0, quarter_period_us)}
        for name, maximum in limits.items():
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 < value <= maximum:
                raise ValueError(f"Calibration {name} must be positive and at most {maximum:g}")
        if isinstance(self.max_drive_code_error, bool) or not isinstance(self.max_drive_code_error, int) or not 0 <= self.max_drive_code_error <= 2:
            raise ValueError("DAC reference tolerance must be between zero and two codes")


@dataclass(frozen=True)
class ProbeRequest:
    request_id: str
    experiment_hash: str
    experiment: Experiment
    sample_rate_hz: int
    window_us: int
    posttrigger_samples: int
    pretrigger_samples: int
    wire_waveform: str
    burst_samples: int

    @classmethod
    def build(cls, experiment: Experiment, sample_rate: int, capabilities: ProbeCapabilities,
              calibration: ProbeTimingCalibration, request_id: str) -> ProbeRequest:
        calibration.validate(capabilities)
        if not isinstance(request_id, str) or not re.fullmatch(r"[0-9a-f]{32}", request_id):
            raise ValueError("A fresh 128-bit request ID is required")
        if isinstance(sample_rate, bool) or not isinstance(sample_rate, int) or sample_rate != calibration.sample_rate_hz:
            raise ValueError("Requested rate differs from the calibrated acquisition rate")
        if experiment.sample_rate_hz is not None and experiment.sample_rate_hz != sample_rate:
            raise ValueError("Experiment sample rate differs from the acquisition rate")
        if experiment.phase_code or experiment.code_length or experiment.spectral_notches_hz:
            raise ValueError("Coded/notched drive parameters are not implemented by this adapter")
        if experiment.waveform not in {"chirp", "sine", "tone_burst"}:
            raise ValueError("The v2 DAC adapter supports only chirp and sine/tone burst")
        if experiment.waveform != "chirp" and experiment.frequency_start_hz != experiment.frequency_end_hz:
            raise ValueError("Tone-burst endpoints must be equal")
        if (experiment.frequency_start_hz < 100 or experiment.frequency_end_hz > min(6000, sample_rate * 0.40)
                or experiment.amplitude > 0.60 or not 0.02 <= experiment.duration_s <= 0.25):
            raise ValueError("Experiment exceeds the calibrated DAC/ADC acquisition envelope")
        window_us = round(experiment.duration_s * 1000000)
        count = round(experiment.duration_s * sample_rate)
        if count < 32 or count != round(window_us * sample_rate / 1000000) or count + capabilities.pretrigger_samples > capabilities.max_samples:
            raise ValueError("Declared acquisition window cannot be represented within the frame sample bound")
        payload = json.dumps(experiment.to_dict(), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
        return cls(request_id, hashlib.sha256(payload).hexdigest(), experiment, sample_rate, window_us, count,
                   capabilities.pretrigger_samples, "CHIRP" if experiment.waveform == "chirp" else "TONE_BURST",
                   max(16, round(min(0.010, experiment.duration_s * 0.22) * sample_rate)))

    @property
    def total_samples(self) -> int:
        return self.posttrigger_samples + self.pretrigger_samples

    @property
    def burst_us(self) -> int:
        return round(self.burst_samples * 1000000 / self.sample_rate_hz)

    def command(self) -> bytes:
        experiment = self.experiment
        return (f"EXPERIMENT2 {self.request_id} {self.experiment_hash} {experiment.frequency_start_hz:.9g} "
                f"{experiment.frequency_end_hz:.9g} {experiment.amplitude:.9g} {self.window_us} "
                f"{self.wire_waveform} {self.sample_rate_hz} {self.pretrigger_samples}\n").encode("ascii")

    def expected_drive_codes(self) -> np.ndarray:
        t = np.arange(self.burst_samples, dtype=np.float64) / self.sample_rate_hz
        experiment = self.experiment
        if self.wire_waveform == "CHIRP":
            slope = (experiment.frequency_end_hz - experiment.frequency_start_hz) / max(t[-1], 1 / self.sample_rate_hz)
            wave = np.cos(2 * np.pi * (experiment.frequency_start_hz * t + 0.5 * slope * t**2))
        else:
            wave = np.sin(2 * np.pi * experiment.frequency_start_hz * t)
        wave *= windows.tukey(self.burst_samples, alpha=0.45)
        wave /= max(1.0, float(np.max(np.abs(wave))))
        values = np.floor(128 + 127 * experiment.amplitude * wave + 0.5).astype(np.int16)
        result = np.full(self.total_samples, 128, dtype=np.int16)
        result[self.pretrigger_samples:self.pretrigger_samples + self.burst_samples] = values
        return result


def fnv1a32(payload: bytes, initial: int = 2166136261) -> int:
    value = initial
    for byte in payload:
        value = ((value ^ byte) * 16777619) & 0xffffffff
    return value


@dataclass(frozen=True)
class ProbeFrame:
    samples: np.ndarray
    metadata: dict


def parse_frame(lines: Iterable[bytes], request: ProbeRequest, capabilities: ProbeCapabilities,
                calibration: ProbeTimingCalibration) -> ProbeFrame:
    calibration.validate(capabilities)
    iterator = iter(lines)
    try:
        header = wire_line(next(iterator)).split(",")
    except StopIteration as exc:
        raise ValueError("Missing BEGIN2 frame") from exc
    if len(header) != 17 or header[0] != "BEGIN2":
        raise ValueError("Malformed BEGIN2 frame")
    if header[1:3] != [request.request_id, request.experiment_hash]:
        raise ValueError("Frame does not bind the requested experiment/nonce")
    count = _integer(header[3], "sample count", 8, capabilities.max_samples)
    rate = _integer(header[4], "sample rate", 1000, capabilities.max_sample_rate_hz)
    bits = _integer(header[5], "ADC bits", 12, 12)
    trigger_index = _integer(header[8], "trigger index", 1, count - 1)
    trigger_us = _integer(header[9], "trigger timestamp", 0, 1000000)
    window_us = _integer(header[13], "window duration", 20000, 250000)
    burst_us = _integer(header[14], "burst duration", 1, 20000)
    drive_start_us = _integer(header[15], "drive start", 0, 1000000)
    drive_end_us = _integer(header[16], "drive end", 1, 1000000)
    if (count != request.total_samples or rate != request.sample_rate_hz or bits != capabilities.adc_bits
            or header[6] != capabilities.drive_family or header[7] != request.wire_waveform
            or trigger_index != request.pretrigger_samples or window_us != request.window_us
            or abs(burst_us - request.burst_us) > 1):
        raise ValueError("Frame acquisition/drive metadata differs from the complete requested experiment")
    for index, expected, name in ((10, request.experiment.frequency_start_hz, "start frequency"),
                                  (11, request.experiment.frequency_end_hz, "end frequency"),
                                  (12, request.experiment.amplitude, "amplitude")):
        if not math.isclose(_finite(header[index], name), expected, rel_tol=1e-6, abs_tol=1e-6):
            raise ValueError(f"Frame {name} differs from the requested experiment")
    timestamps = np.empty(count, dtype=np.int64)
    raw_values = np.empty(count, dtype=np.int16)
    drive_codes = np.empty(count, dtype=np.int16)
    checksum = 2166136261
    raw_digest = hashlib.sha256()
    for index in range(count):
        try:
            fields = wire_line(next(iterator)).split(",")
        except StopIteration as exc:
            raise ValueError("Incomplete sample frame") from exc
        if len(fields) != 5 or fields[0] != "DATA2" or _integer(fields[1], "sample index", 0, count - 1) != index:
            raise ValueError("Sample indices must be contiguous and complete")
        timestamp = _integer(fields[2], "sample timestamp", 0, 1000000)
        raw = _integer(fields[3], "ADC value", 0, (1 << bits) - 1)
        code = _integer(fields[4], "DAC value", 0, 255)
        canonical = f"{index},{timestamp},{raw},{code}\n".encode("ascii")
        if fields[1:] != [str(index), str(timestamp), str(raw), str(code)]:
            raise ValueError("Non-canonical sample representation")
        checksum = fnv1a32(canonical, checksum)
        raw_digest.update(canonical)
        timestamps[index], raw_values[index], drive_codes[index] = timestamp, raw, code
    try:
        trailer = wire_line(next(iterator)).split(",")
    except StopIteration as exc:
        raise ValueError("Missing complete END2 marker") from exc
    if (len(trailer) != 6 or trailer[0] != "END2" or trailer[1] != request.request_id
            or _integer(trailer[2], "end count", 8, capabilities.max_samples) != count
            or not re.fullmatch(r"[0-9a-fA-F]{8}", trailer[3]) or int(trailer[3], 16) != checksum
            or trailer[4] != "OK"):
        raise ValueError("Frame checksum/count/status failed; no samples may be ingested")
    late_us = _integer(trailer[5], "reported maximum lateness", 0, 1000000)
    if next(iterator, None) is not None:
        raise ValueError("Unexpected trailing frame data")
    period_us = 1000000.0 / rate
    if timestamps[0] != 0 or np.any(np.diff(timestamps) <= 0):
        raise ValueError("Sample timestamps must start at zero and increase strictly")
    average_period = float(timestamps[-1]) / (count - 1)
    clock_error_ppm = abs(average_period / period_us - 1) * 1000000
    # One-microsecond timestamp quantization is permitted explicitly; it cannot
    # excuse missing/deadline-late samples or a wrong capture-window duration.
    clock_quantization_ppm = 1000000.0 / ((count - 1) * period_us)
    if clock_error_ppm > calibration.max_clock_error_ppm + clock_quantization_ppm:
        raise ValueError("Observed sample clock differs from the calibrated rate")
    deviations = timestamps.astype(np.float64) - np.arange(count) * period_us
    maximum_jitter_us = float(np.max(np.abs(deviations)))
    if maximum_jitter_us > calibration.max_sample_jitter_us + 1 or late_us > calibration.max_sample_jitter_us + 1:
        raise ValueError("Sample timing jitter/deadline lateness exceeds operator calibration")
    alignment_error_us = abs(float(timestamps[trigger_index]) - trigger_us)
    if (alignment_error_us > calibration.max_trigger_alignment_error_us + 1
            or abs(drive_start_us - trigger_us) > calibration.max_trigger_alignment_error_us + 1
            or abs((drive_end_us - drive_start_us) - burst_us) > calibration.max_sample_jitter_us + period_us + 1
            or drive_end_us <= drive_start_us or drive_end_us > timestamps[-1]):
        raise ValueError("Drive/trigger timing is not aligned inside the captured window")
    minimum_coverage = (request.posttrigger_samples - 1) * period_us
    if timestamps[-1] - trigger_us < minimum_coverage - calibration.max_sample_jitter_us - calibration.max_trigger_alignment_error_us - 1:
        raise ValueError("Samples do not cover the declared trigger-relative observation window")
    code_error = int(np.max(np.abs(drive_codes - request.expected_drive_codes())))
    if code_error > calibration.max_drive_code_error:
        raise ValueError("Recorded DAC command sequence differs from the requested reference waveform")
    samples = ((raw_values[trigger_index:].astype(np.float64) - (1 << (bits - 1))) / (1 << (bits - 1))).astype(np.float32)
    metadata = {
        "protocol_version": 2, "device_id": capabilities.device_id,
        "sample_rate_hz": rate, "raw_sample_count": count, "used_sample_count": len(samples),
        "pretrigger_sample_count": trigger_index, "trigger_time_us": trigger_us,
        "drive_start_us": drive_start_us, "drive_end_us": drive_end_us,
        "observed_clock_error_ppm": clock_error_ppm, "maximum_sample_jitter_us": maximum_jitter_us,
        "trigger_alignment_error_us": alignment_error_us, "maximum_drive_code_error": code_error,
        "request_id": request.request_id, "experiment_sha256": request.experiment_hash,
        "raw_frame_sha256": raw_digest.hexdigest(), "frame_fnv1a32": f"{checksum:08x}",
        "sample_timestamps_us": timestamps.tolist(), "recorded_drive_codes": drive_codes.tolist(),
        "raw_adc_samples": raw_values.tolist(),
        "units": "normalized", "normalization": "(ADC_raw - 2048) / 2048; pretrigger removed",
        "operator_timing_calibration": asdict(calibration),
        "evidence_status": "frame_contract_checked_with_operator_attestation",
        "sensor_authenticity_verified": False, "physical_bench_validation_performed_by_host": False,
    }
    return ProbeFrame(samples, metadata)
