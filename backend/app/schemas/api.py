from __future__ import annotations

from typing import Literal
import json
import math

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def bounded_metadata(value: dict) -> dict:
    """Bound metadata independently of the transport's much larger sample budget."""
    def visit(item, depth=0):
        if depth > 4:
            raise ValueError("Metadata nesting exceeds four levels")
        if isinstance(item, dict):
            if len(item) > 64:
                raise ValueError("Metadata has too many keys")
            for key, child in item.items():
                if not isinstance(key, str) or len(key) > 128:
                    raise ValueError("Metadata keys must be short strings")
                visit(child, depth + 1)
        elif isinstance(item, list):
            if len(item) > 128:
                raise ValueError("Metadata list is too long")
            for child in item:
                visit(child, depth + 1)
        elif isinstance(item, str):
            if len(item) > 1024:
                raise ValueError("Metadata string is too long")
        elif isinstance(item, (int, float)) and not isinstance(item, bool):
            try:
                finite = math.isfinite(item)
            except OverflowError:
                finite = False
            if not finite:
                raise ValueError("Metadata numbers must be finite")
        elif item is not None and not isinstance(item, bool):
            raise ValueError("Metadata must contain only JSON values")
    visit(value)
    if len(json.dumps(value, allow_nan=False, ensure_ascii=False).encode("utf-8")) > 16_384:
        raise ValueError("Metadata exceeds 16 KiB")
    return value


class APIRequest(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False, extra="forbid")


class CreateSessionRequest(APIRequest):
    mode: Literal["simulation", "physical"] = "simulation"
    preset: Literal["easy", "medium", "hard"] = "medium"
    seed: int | None = Field(default=None, ge=0, le=2_147_483_647)
    panel_width_mm: float = Field(600, ge=100, le=5_000)
    panel_height_mm: float = Field(400, ge=100, le=5_000)
    grid_size: int = Field(20, ge=10, le=40)
    max_experiments: int = Field(12, ge=1, le=30)
    material_profile: Literal["generic_plate", "aluminum_demo", "cfrp_demo"] = "generic_plate"
    config_profile: Literal["demo", "research", "phone", "distributed", "benchmark"] = "demo"
    enable_nuisance_aware_design: bool = Field(default=False, strict=True)
    enable_risk_calibration_design: bool = Field(default=False, strict=True)
    enable_task_conditioned_calibration: bool = Field(default=False, strict=True)


class ExperimentParameters(APIRequest):
    source_x: float = Field(ge=0, le=1)
    source_y: float = Field(ge=0, le=1)
    receiver_x: float = Field(ge=0, le=1)
    receiver_y: float = Field(ge=0, le=1)
    frequency_start_hz: float = Field(ge=100, le=20_000)
    frequency_end_hz: float = Field(ge=100, le=20_000)
    amplitude: float = Field(gt=0, le=1)
    duration_s: float = Field(ge=0.02, le=2)
    waveform: Literal[
        "impulse", "sine", "chirp", "tone_burst", "ricker", "multisine",
        "phase_coded", "complementary_coded", "spectrally_notched",
    ]
    phase_code: str | None = Field(default=None, max_length=128)
    code_length: int = Field(default=0, ge=0, le=256)
    sample_rate_hz: int | None = Field(default=None, ge=1_000, le=384_000)
    spectral_notches_hz: tuple[tuple[float, float], ...] = Field(default=(), max_length=16)

    @model_validator(mode="after")
    def validate_band(self):
        if self.frequency_end_hz < self.frequency_start_hz:
            raise ValueError("frequency_end_hz must be greater than or equal to frequency_start_hz")
        if any(low < 0 or high <= low or high > 20_000 for low, high in self.spectral_notches_hz):
            raise ValueError("spectral notches must be increasing pairs within 0 to 20 kHz")
        return self


class RunExperimentRequest(APIRequest):
    experiment: ExperimentParameters | None = None


class ProbeTimingCalibration(APIRequest):
    """Operator declaration referencing an external bench record, not certification."""

    device_id: str = Field(pattern=r"^ESP32_DAC25_ADC34_[0-9a-f]{12}$")
    sample_rate_hz: int = Field(ge=1000, le=16000, strict=True)
    calibration_id: str = Field(min_length=3, max_length=128, pattern=r"^[A-Za-z0-9_.:-]+$")
    calibrated_at_utc: str = Field(min_length=20, max_length=48)
    reference_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    operator: str = Field(min_length=3, max_length=128)
    drive_family: Literal["DAC8_SAMPLED_SINE"]
    max_sample_jitter_us: float = Field(gt=0, le=20, strict=True)
    max_clock_error_ppm: float = Field(gt=0, le=1000, strict=True)
    max_trigger_alignment_error_us: float = Field(gt=0, le=20, strict=True)
    max_drive_code_error: int = Field(ge=0, le=2, strict=True)
    arrival_adapter_validated: bool = Field(strict=True)

    @model_validator(mode="after")
    def validate_operator_record(self):
        from backend.app.hardware.protocol_v2 import ProbeCapabilities, ProbeTimingCalibration as OperatorCalibration

        capabilities = ProbeCapabilities(self.device_id, 16000, 4096, 12, self.drive_family, ("CHIRP", "TONE_BURST"), 16)
        OperatorCalibration.from_metadata(self.model_dump(), capabilities)
        return self


class DeviceConnectRequest(APIRequest):
    device: Literal["serial_probe", "microphone"]
    port: str | None = Field(default=None, max_length=256)
    baudrate: int = Field(115_200, ge=9_600, le=2_000_000)
    timing_calibration: ProbeTimingCalibration | None = None

    @model_validator(mode="after")
    def validate_calibration_device(self):
        if self.timing_calibration is not None:
            if self.device != "serial_probe":
                raise ValueError("Timing calibration is supported only for the serial v2 adapter")
            if self.baudrate < 115200:
                raise ValueError("Calibrated v2 acquisition requires at least 115200 baud")
        return self


class DeviceExperimentRequest(APIRequest):
    device: Literal["serial_probe", "microphone"]
    experiment: ExperimentParameters | None = None


class NoGoRegionRequest(APIRequest):
    x_min: float = Field(ge=0, le=1)
    y_min: float = Field(ge=0, le=1)
    x_max: float = Field(ge=0, le=1)
    y_max: float = Field(ge=0, le=1)
    label: str = Field(default="inaccessible", min_length=1, max_length=80)

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.x_max <= self.x_min or self.y_max <= self.y_min:
            raise ValueError("No-go region maxima must exceed minima")
        return self


class NoGoRegionsRequest(APIRequest):
    regions: list[NoGoRegionRequest] = Field(default_factory=list, max_length=32)


class HumanDecisionRequest(APIRequest):
    decision: Literal["accept", "modify", "reject"]
    reason: Literal["inaccessible", "poor_contact", "unsafe", "user_preference", "hardware_limitation", "other"] | None = None
    experiment: ExperimentParameters | None = None

    @model_validator(mode="after")
    def validate_modification(self):
        if self.decision == "modify" and self.experiment is None:
            raise ValueError("A modified experiment is required when decision is modify")
        return self


class EmergencyStopRequest(APIRequest):
    reason: str = Field(min_length=3, max_length=500)


class EmergencyReleaseRequest(APIRequest):
    reason: str = Field(min_length=3, max_length=500)
    acknowledgement: bool


class ResearchJobRequest(APIRequest):
    job_type: Literal["benchmark", "calibration", "ablation", "dataset_generation", "surrogate_training", "demo_scenario"]
    parameters: dict = Field(default_factory=dict)

    _bounded_parameters = field_validator("parameters")(bounded_metadata)


class ProbeRegistrationRequest(APIRequest):
    node_id: str = Field(min_length=3, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    node_type: Literal["phone", "edge_laptop", "browser", "serial_bridge"]
    capabilities: dict = Field(default_factory=dict)

    _bounded_capabilities = field_validator("capabilities")(bounded_metadata)


class ProbeMeasurementRequest(APIRequest):
    session_id: str = Field(min_length=3, max_length=128)
    node_id: str = Field(min_length=3, max_length=128, pattern=r"^[A-Za-z0-9_.-]+$")
    sample_rate: int = Field(ge=1_000, le=384_000)
    samples: list[float] = Field(min_length=8, max_length=384_000)
    experiment: ExperimentParameters | None = None
    timestamp: str | None = Field(default=None, max_length=64)
    sensor_metadata: dict = Field(default_factory=dict)
    measurement_id: str | None = Field(default=None, min_length=3, max_length=128)

    _bounded_sensor_metadata = field_validator("sensor_metadata")(bounded_metadata)
