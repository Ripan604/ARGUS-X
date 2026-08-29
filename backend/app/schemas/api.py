from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class CreateSessionRequest(BaseModel):
    mode: Literal["simulation", "physical"] = "simulation"
    preset: Literal["easy", "medium", "hard"] = "medium"
    seed: int | None = None
    panel_width_mm: float = Field(600, ge=100, le=5_000)
    panel_height_mm: float = Field(400, ge=100, le=5_000)
    grid_size: int = Field(20, ge=10, le=40)
    max_experiments: int = Field(12, ge=3, le=30)


class ExperimentParameters(BaseModel):
    source_x: float = Field(ge=0, le=1)
    source_y: float = Field(ge=0, le=1)
    receiver_x: float = Field(ge=0, le=1)
    receiver_y: float = Field(ge=0, le=1)
    frequency_start_hz: float = Field(ge=100, le=20_000)
    frequency_end_hz: float = Field(ge=100, le=20_000)
    amplitude: float = Field(gt=0, le=1)
    duration_s: float = Field(ge=0.02, le=2)
    waveform: Literal["impulse", "sine", "chirp"]

    @model_validator(mode="after")
    def validate_band(self):
        if self.frequency_end_hz < self.frequency_start_hz:
            raise ValueError("frequency_end_hz must be greater than or equal to frequency_start_hz")
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
