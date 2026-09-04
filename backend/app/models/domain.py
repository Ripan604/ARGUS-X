from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

import numpy as np

Waveform = Literal[
    "impulse",
    "sine",
    "chirp",
    "tone_burst",
    "ricker",
    "multisine",
    "phase_coded",
    "complementary_coded",
    "spectrally_notched",
]
DefectType = Literal["cavity", "loose_region", "delamination", "dense_inclusion"]
WAVEFORMS = {
    "impulse", "sine", "chirp", "tone_burst", "ricker", "multisine",
    "phase_coded", "complementary_coded", "spectrally_notched",
}
DEFECT_TYPES = {"cavity", "loose_region", "delamination", "dense_inclusion"}


@dataclass(frozen=True)
class Panel:
    width_m: float = 0.60
    height_m: float = 0.40
    material: str = "composite"

    def __post_init__(self) -> None:
        if not np.isfinite(self.width_m) or not np.isfinite(self.height_m):
            raise ValueError("Panel dimensions must be finite")
        if self.width_m <= 0 or self.height_m <= 0:
            raise ValueError("Panel dimensions must be positive")
        if not isinstance(self.material, str) or not self.material.strip():
            raise ValueError("Panel material must be a non-empty string")

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

    def __post_init__(self) -> None:
        values = (
            self.wave_velocity, self.attenuation, self.resonance_hz,
            self.damping, self.noise_std, self.system_delay_s,
        )
        if any(not np.isfinite(value) for value in values):
            raise ValueError("Material values must be finite")
        if self.wave_velocity <= 0 or self.resonance_hz <= 0:
            raise ValueError("Wave velocity and resonance must be positive")
        if self.attenuation < 0 or self.damping < 0 or self.noise_std < 0 or self.system_delay_s < 0:
            raise ValueError("Attenuation, damping, noise, and system delay cannot be negative")

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
        if self.defect_type not in DEFECT_TYPES:
            raise ValueError(f"Unsupported defect type: {self.defect_type}")

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
    phase_code: str | None = None
    code_length: int = 0
    sample_rate_hz: int | None = None
    spectral_notches_hz: tuple[tuple[float, float], ...] = ()

    def __post_init__(self) -> None:
        coordinates = (self.source_x, self.source_y, self.receiver_x, self.receiver_y)
        if any(not np.isfinite(v) or v < 0 or v > 1 for v in coordinates):
            raise ValueError("Probe coordinates must be finite and in [0, 1]")
        numeric_values = (self.frequency_start_hz, self.frequency_end_hz, self.amplitude, self.duration_s)
        if any(not np.isfinite(value) for value in numeric_values):
            raise ValueError("Experiment frequencies, amplitude, and duration must be finite")
        if self.frequency_start_hz <= 0 or self.frequency_end_hz <= 0:
            raise ValueError("Frequencies must be positive")
        if not (0 < self.amplitude <= 1):
            raise ValueError("Amplitude must be in (0, 1]")
        if self.duration_s <= 0:
            raise ValueError("Duration must be positive")
        if self.frequency_end_hz < self.frequency_start_hz:
            raise ValueError("frequency_end_hz must be at least frequency_start_hz")
        if self.code_length < 0:
            raise ValueError("code_length cannot be negative")
        if self.sample_rate_hz is not None and self.sample_rate_hz < 1_000:
            raise ValueError("sample_rate_hz must be at least 1000 when supplied")
        if self.waveform not in WAVEFORMS:
            raise ValueError(f"Unsupported waveform: {self.waveform}")
        for notch in self.spectral_notches_hz:
            if len(notch) != 2 or any(not np.isfinite(value) for value in notch) or notch[0] < 0 or notch[1] <= notch[0]:
                raise ValueError("spectral notches must be increasing frequency pairs")

    @property
    def center_frequency_hz(self) -> float:
        return (self.frequency_start_hz + self.frequency_end_hz) / 2

    @property
    def bandwidth_hz(self) -> float:
        return self.frequency_end_hz - self.frequency_start_hz

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
