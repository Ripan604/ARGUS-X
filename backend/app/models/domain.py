from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

import numpy as np

Waveform = Literal["impulse", "sine", "chirp"]
DefectType = Literal["cavity", "loose_region", "delamination", "dense_inclusion"]


@dataclass(frozen=True)
class Panel:
    width_m: float = 0.60
    height_m: float = 0.40
    material: str = "composite"

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Material:
    wave_velocity: float = 180.0
    attenuation: float = 1.65
    resonance_hz: float = 3_100.0
    damping: float = 95.0
    noise_std: float = 0.007
    system_delay_s: float = 0.0008

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Defect:
    center_x: float
    center_y: float
    radius_x: float = 0.09
    radius_y: float = 0.07
    severity: float = 0.72
    defect_type: DefectType = "cavity"

    def __post_init__(self) -> None:
        for value in (self.center_x, self.center_y, self.radius_x, self.radius_y, self.severity):
            if not np.isfinite(value):
                raise ValueError("Defect values must be finite")
        if not (0 <= self.center_x <= 1 and 0 <= self.center_y <= 1):
            raise ValueError("Defect center must be within the normalized panel")
        if self.radius_x <= 0 or self.radius_y <= 0 or not (0 < self.severity <= 1):
            raise ValueError("Defect radii and severity must be positive")

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Experiment:
    source_x: float
    source_y: float
    receiver_x: float
    receiver_y: float
    frequency_start_hz: float = 1_800.0
    frequency_end_hz: float = 4_200.0
    amplitude: float = 0.45
    duration_s: float = 0.12
    waveform: Waveform = "chirp"

    def __post_init__(self) -> None:
        coordinates = (self.source_x, self.source_y, self.receiver_x, self.receiver_y)
        if any(not np.isfinite(v) or v < 0 or v > 1 for v in coordinates):
            raise ValueError("Probe coordinates must be finite and in [0, 1]")
        if self.frequency_start_hz <= 0 or self.frequency_end_hz <= 0:
            raise ValueError("Frequencies must be positive")
        if not (0 < self.amplitude <= 1):
            raise ValueError("Amplitude must be in (0, 1]")
        if self.duration_s <= 0:
            raise ValueError("Duration must be positive")

    @property
    def center_frequency_hz(self) -> float:
        return (self.frequency_start_hz + self.frequency_end_hz) / 2

    def to_dict(self) -> dict:
        return asdict(self)


def normalized_to_meters(x: np.ndarray | float, y: np.ndarray | float, panel: Panel):
    return np.asarray(x) * panel.width_m, np.asarray(y) * panel.height_m


def physical_distance(
    ax: np.ndarray | float,
    ay: np.ndarray | float,
    bx: np.ndarray | float,
    by: np.ndarray | float,
    panel: Panel,
) -> np.ndarray:
    return np.hypot((np.asarray(ax) - np.asarray(bx)) * panel.width_m, (np.asarray(ay) - np.asarray(by)) * panel.height_m)
