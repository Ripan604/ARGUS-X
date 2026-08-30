from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import chirp, windows

from backend.app.models.domain import Defect, Experiment, Material, Panel, physical_distance


@dataclass(frozen=True)
class SimulationPreset:
    name: str
    radius_range: tuple[float, float]
    severity_range: tuple[float, float]
    noise_multiplier: float


PRESETS = {
    "easy": SimulationPreset("easy", (0.10, 0.15), (0.78, 0.95), 0.55),
    "medium": SimulationPreset("medium", (0.065, 0.11), (0.58, 0.82), 1.0),
    "hard": SimulationPreset("hard", (0.04, 0.075), (0.38, 0.64), 1.55),
}


class AcousticSimulator:
    """Small deterministic wave-scattering digital twin.

    This intentionally stays interpretable: a direct, attenuated plate wave is
    combined with a delayed defect-scattered response and damped local ringing.
    It is not a finite-element solver, but every generated sample follows a
    physical path-length and propagation-delay model.
    """

    _reflection = {
        "cavity": 1.0,
        "loose_region": 0.72,
        "delamination": 0.86,
        "dense_inclusion": -0.64,
    }

    def __init__(
        self,
        panel: Panel | None = None,
        material: Material | None = None,
        sample_rate: int = 16_000,
        seed: int = 7,
    ) -> None:
        self.panel = panel or Panel()
        self.material = material or Material()
        self.sample_rate = sample_rate
        self.rng = np.random.default_rng(seed)

    def random_defect(self, preset: str = "medium") -> Defect:
        if preset not in PRESETS:
            raise ValueError(f"Unknown preset: {preset}")
        spec = PRESETS[preset]
        radius_x = float(self.rng.uniform(*spec.radius_range))
        radius_y = float(self.rng.uniform(*spec.radius_range))
        margin_x, margin_y = radius_x + 0.04, radius_y + 0.04
        material_noise = self.material.noise_std * spec.noise_multiplier
        self.material = Material(**{**self.material.to_dict(), "noise_std": material_noise})
        return Defect(
            center_x=float(self.rng.uniform(margin_x, 1 - margin_x)),
            center_y=float(self.rng.uniform(margin_y, 1 - margin_y)),
            radius_x=radius_x,
            radius_y=radius_y,
            severity=float(self.rng.uniform(*spec.severity_range)),
            defect_type=str(self.rng.choice(["cavity", "loose_region", "delamination", "dense_inclusion"])),
        )

    def excitation(self, experiment: Experiment) -> np.ndarray:
        total_samples = max(32, int(round(experiment.duration_s * self.sample_rate)))
        burst_duration = min(0.010, experiment.duration_s * 0.22)
        burst_samples = max(16, int(round(burst_duration * self.sample_rate)))
        t = np.arange(burst_samples) / self.sample_rate
        if experiment.waveform in {"impulse", "ricker"}:
            center = burst_duration * 0.28
            width = max(1 / experiment.center_frequency_hz, 0.00022)
            phase = np.pi * (t - center) / width
            wave = (1 - 2 * phase**2) * np.exp(-(phase**2))
        elif experiment.waveform in {"sine", "tone_burst"}:
            wave = np.sin(2 * np.pi * experiment.frequency_start_hz * t)
        elif experiment.waveform == "multisine":
            frequencies = np.linspace(experiment.frequency_start_hz, experiment.frequency_end_hz, 5)
            wave = sum(np.sin(2 * np.pi * frequency * t + index * np.pi / 7) for index, frequency in enumerate(frequencies)) / len(frequencies)
        elif experiment.waveform in {"phase_coded", "complementary_coded"}:
            primary = np.asarray([1, 1, 1, -1, -1, 1, -1], dtype=np.float64)
            secondary = np.asarray([1, 1, 1, -1, 1, -1, 1], dtype=np.float64)
            code = np.concatenate((primary, secondary)) if experiment.waveform == "complementary_coded" else primary
            if experiment.phase_code:
                parsed = [1.0 if token in {"1", "+"} else -1.0 for token in experiment.phase_code if token in {"1", "0", "+", "-"}]
                if parsed:
                    code = np.asarray(parsed, dtype=np.float64)
            chip = max(2, burst_samples // len(code))
            phases = np.repeat(code, chip)[:burst_samples]
            phases = np.pad(phases, (0, max(0, burst_samples - len(phases))), mode="edge")
            wave = phases * np.sin(2 * np.pi * experiment.center_frequency_hz * t)
        else:
            wave = chirp(
                t,
                f0=experiment.frequency_start_hz,
                f1=experiment.frequency_end_hz,
                t1=max(t[-1], 1 / self.sample_rate),
                method="linear",
            )
            if experiment.waveform == "spectrally_notched":
                spectrum = np.fft.rfft(wave)
                frequencies = np.fft.rfftfreq(len(wave), 1 / self.sample_rate)
                notches = experiment.spectral_notches_hz or ((2_800.0, 3_300.0),)
                for low, high in notches:
                    spectrum[(frequencies >= low) & (frequencies <= high)] = 0
                wave = np.fft.irfft(spectrum, n=len(wave))
        wave *= windows.tukey(burst_samples, alpha=0.45)
        # FFT notching and coded summation can introduce modest overshoot. The
        # experiment amplitude is a hard actuator bound, so normalize after all
        # waveform transforms rather than assuming every family is unit peak.
        wave /= max(1.0, float(np.max(np.abs(wave))))
        wave *= experiment.amplitude
        result = np.zeros(total_samples, dtype=np.float64)
        result[:burst_samples] = wave
        return result

    def path_properties(self, defect: Defect, experiment: Experiment) -> tuple[float, float, float]:
        direct_distance = float(
            physical_distance(
                experiment.source_x,
                experiment.source_y,
                experiment.receiver_x,
                experiment.receiver_y,
                self.panel,
            )
        )
        source_defect = float(
            physical_distance(experiment.source_x, experiment.source_y, defect.center_x, defect.center_y, self.panel)
        )
        defect_receiver = float(
            physical_distance(defect.center_x, defect.center_y, experiment.receiver_x, experiment.receiver_y, self.panel)
        )
        return direct_distance, source_defect, defect_receiver

    def simulate_baseline(self, experiment: Experiment) -> np.ndarray:
        excitation = self.excitation(experiment)
        direct_distance = float(
            physical_distance(
                experiment.source_x,
                experiment.source_y,
                experiment.receiver_x,
                experiment.receiver_y,
                self.panel,
            )
        )
        delay = self.material.system_delay_s + direct_distance / self.material.wave_velocity
        gain = np.exp(-self.material.attenuation * direct_distance) / (1.0 + 4.0 * direct_distance)
        response = self._fractional_delay(excitation, delay) * gain
        return response

    def simulate(
        self,
        defect: Defect,
        experiment: Experiment,
        *,
        add_noise: bool = True,
        rng: np.random.Generator | None = None,
    ) -> np.ndarray:
        excitation = self.excitation(experiment)
        response = self.simulate_baseline(experiment)
        _, source_defect, defect_receiver = self.path_properties(defect, experiment)
        scatter_distance = source_defect + defect_receiver
        delay = self.material.system_delay_s + scatter_distance / self.material.wave_velocity
        area_scale = np.sqrt(defect.radius_x * defect.radius_y) / 0.085
        attenuation = np.exp(-self.material.attenuation * scatter_distance)
        geometric = 1.0 / (1.0 + 5.0 * scatter_distance)
        frequency = experiment.center_frequency_hz
        defect_resonance = self.material.resonance_hz * (1.05 - 0.32 * defect.severity)
        resonance_gain = 0.72 + 0.72 * np.exp(-0.5 * ((frequency - defect_resonance) / 1_250.0) ** 2)
        scatter_gain = (
            self._reflection[defect.defect_type]
            * defect.severity
            * area_scale
            * attenuation
            * geometric
            * resonance_gain
            * 0.43
        )
        response = response + self._fractional_delay(excitation, delay) * scatter_gain

        ring_start = int(round(delay * self.sample_rate))
        if ring_start < len(response):
            ring_t = np.arange(len(response) - ring_start) / self.sample_rate
            ring_frequency = defect_resonance * (1.12 if defect.defect_type == "dense_inclusion" else 1.0)
            ring = np.sin(2 * np.pi * ring_frequency * ring_t) * np.exp(-self.material.damping * ring_t)
            response[ring_start:] += ring * scatter_gain * experiment.amplitude * 0.11

        if add_noise:
            noise_rng = rng or self.rng
            noise = noise_rng.normal(0.0, self.material.noise_std, len(response))
            # Low-frequency environmental drift makes preprocessing meaningful.
            drift = np.cumsum(noise_rng.normal(0.0, self.material.noise_std * 0.012, len(response)))
            response = response + noise + drift
        return response.astype(np.float32)

    def predicted_signature(
        self,
        x: np.ndarray,
        y: np.ndarray,
        experiment: Experiment,
        severity: float = 0.65,
    ) -> np.ndarray:
        source_distance = physical_distance(experiment.source_x, experiment.source_y, x, y, self.panel)
        receiver_distance = physical_distance(x, y, experiment.receiver_x, experiment.receiver_y, self.panel)
        total_distance = source_distance + receiver_distance
        delay = self.material.system_delay_s + total_distance / self.material.wave_velocity
        gain = severity * np.exp(-self.material.attenuation * total_distance) / (1.0 + 5.0 * total_distance)
        phase = 2 * np.pi * experiment.center_frequency_hz * delay
        return np.column_stack((delay, np.log(gain + 1e-8), np.sin(phase), np.cos(phase)))

    def _fractional_delay(self, values: np.ndarray, delay_s: float) -> np.ndarray:
        sample_positions = np.arange(len(values), dtype=np.float64) - delay_s * self.sample_rate
        return np.interp(sample_positions, np.arange(len(values)), values, left=0.0, right=0.0)
