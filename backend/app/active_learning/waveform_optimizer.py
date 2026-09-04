from __future__ import annotations

from dataclasses import replace

import numpy as np

from backend.app.models.domain import Experiment


class WaveformGeometryOptimizer:
    """Bounded seeded coarse search plus optional successive refinement."""

    FAST_WAVEFORMS = ("chirp", "tone_burst", "ricker", "multisine", "phase_coded")
    RESEARCH_WAVEFORMS = FAST_WAVEFORMS + ("complementary_coded", "spectrally_notched")

    def __init__(self, seed: int = 71) -> None:
        self.rng = np.random.default_rng(seed)

    def expand(self, candidates: list[Experiment], mode: str = "fast", maximum: int = 72) -> list[Experiment]:
        # Treat waveform as an actual decision variable: retain several
        # alternatives for each geometry so the downstream planner can compare
        # their excitation quality. The prior implementation assigned one
        # waveform by list index, which was deterministic but not optimization.
        waveforms = (
            ("chirp", "complementary_coded", "spectrally_notched")
            if mode == "research"
            else ("chirp", "phase_coded", "multisine")
        )
        result: list[Experiment] = []
        for index, candidate in enumerate(candidates):
            for waveform in waveforms:
                phase_code = "1110010" if waveform == "phase_coded" else None
                notches = ((2_800.0, 3_300.0),) if waveform == "spectrally_notched" else ()
                result.append(replace(candidate, waveform=waveform, phase_code=phase_code, code_length=7 if phase_code else 0, spectral_notches_hz=notches))
                if len(result) >= maximum:
                    return result
            if mode == "research" and len(result) < maximum and index % 3 == 0:
                center = candidate.center_frequency_hz * float(self.rng.uniform(0.90, 1.10))
                bandwidth = max(400.0, candidate.bandwidth_hz * float(self.rng.uniform(0.75, 1.18)))
                result.append(
                    replace(
                        candidate,
                        frequency_start_hz=max(200.0, center - bandwidth / 2),
                        frequency_end_hz=min(7_000.0, center + bandwidth / 2),
                        amplitude=float(np.clip(candidate.amplitude * self.rng.uniform(0.82, 1.08), 0.12, 0.72)),
                        waveform="chirp",
                        phase_code=None,
                        code_length=0,
                        spectral_notches_hz=(),
                    )
                )
        return result[:maximum]

    def refine(self, experiment: Experiment, score_function, iterations: int = 10) -> Experiment:
        best, best_score = experiment, float(score_function(experiment))
        for _ in range(max(1, iterations)):
            center = best.center_frequency_hz + float(self.rng.normal(0, 220))
            bandwidth = max(350.0, best.bandwidth_hz * float(self.rng.uniform(0.84, 1.16)))
            trial = replace(
                best,
                frequency_start_hz=float(np.clip(center - bandwidth / 2, 200, 6_500)),
                frequency_end_hz=float(np.clip(center + bandwidth / 2, 500, 7_000)),
                amplitude=float(np.clip(best.amplitude + self.rng.normal(0, 0.035), 0.12, 0.72)),
            )
            if trial.frequency_end_hz < trial.frequency_start_hz:
                continue
            score = float(score_function(trial))
            if score > best_score:
                best, best_score = trial, score
        return best
