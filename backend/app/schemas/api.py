from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CreateSessionRequest(BaseModel):
    mode: Literal["simulation", "physical"] = "simulation"
    preset: Literal["easy", "medium", "hard"] = "medium"
    seed: int | None = Field(default=None, ge=0, le=2_147_483_647)
    panel_width_mm: float = Field(600, ge=100, le=5_000)
    panel_height_mm: float = Field(400, ge=100, le=5_000)
    grid_size: int = Field(20, ge=10, le=40)
    max_experiments: int = Field(12, ge=1, le=30)
    material_profile: Literal["generic_plate", "aluminum_demo", "cfrp_demo"] = "generic_plate"
    config_profile: Literal["demo", "research", "phone", "distributed", "benchmark"] = "demo"


class ExperimentParameters(BaseModel):
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


class RunExperimentRequest(BaseModel):
    experiment: ExperimentParameters | None = None


class DeviceConnectRequest(BaseModel):
    device: Literal["serial_probe", "microphone"]
    port: str | None = None
    baudrate: int = Field(115_200, ge=9_600, le=2_000_000)


class DeviceExperimentRequest(BaseModel):
    device: Literal["serial_probe", "microphone"]
    experiment: ExperimentParameters | None = None


class NoGoRegionRequest(BaseModel):
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


class NoGoRegionsRequest(BaseModel):
    regions: list[NoGoRegionRequest] = Field(default_factory=list, max_length=32)


class HumanDecisionRequest(BaseModel):
    decision: Literal["accept", "modify", "reject"]
    reason: Literal["inaccessible", "poor_contact", "unsafe", "user_preference", "hardware_limitation", "other"] | None = None
    experiment: ExperimentParameters | None = None

    @model_validator(mode="after")
    def validate_modification(self):
        if self.decision == "modify" and self.experiment is None:
            raise ValueError("A modified experiment is required when decision is modify")
        return self


class EmergencyStopRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)


class EmergencyReleaseRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    acknowledgement: bool


class ResearchJobRequest(BaseModel):
    job_type: Literal["benchmark", "calibration", "ablation", "dataset_generation", "surrogate_training", "demo_scenario"]
    parameters: dict = Field(default_factory=dict)


class ProbeRegistrationRequest(BaseModel):
    node_id: str = Field(min_length=3, max_length=128)
    node_type: Literal["phone", "edge_laptop", "browser", "serial_bridge"]
    capabilities: dict = Field(default_factory=dict)


class ProbeMeasurementRequest(BaseModel):
    session_id: str = Field(min_length=3, max_length=128)
    node_id: str = Field(min_length=3, max_length=128)
    sample_rate: int = Field(ge=1_000, le=384_000)
    samples: list[float] = Field(min_length=8, max_length=384_000)
    experiment: ExperimentParameters | None = None
    timestamp: str | None = None
    sensor_metadata: dict = Field(default_factory=dict)
    measurement_id: str | None = Field(default=None, min_length=3, max_length=128)
