from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
from scipy.signal import correlate, correlation_lags

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.models.domain import Experiment
from backend.app.simulation.physics import AcousticSimulator


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an object-specific ARGUS reference profile")
    parser.add_argument("--seed", type=int, default=31)
    parser.add_argument("--output", default="datasets/samples/calibration.json")
    args = parser.parse_args()
    simulator = AcousticSimulator(seed=args.seed)
    experiments = [
        Experiment(0.05, 0.08, 0.95, 0.08, 1_200, 3_000, 0.42, 0.12, "chirp"),
        Experiment(0.05, 0.92, 0.95, 0.92, 2_200, 4_400, 0.42, 0.12, "chirp"),
        Experiment(0.08, 0.05, 0.08, 0.95, 3_400, 6_200, 0.42, 0.12, "chirp"),
    ]
    estimates = []
    for experiment in experiments:
        baseline = simulator.simulate_baseline(experiment)
        noisy = baseline + simulator.rng.normal(0, simulator.material.noise_std, len(baseline))
        corr = correlate(noisy, simulator.excitation(experiment), mode="full")
        lags = correlation_lags(len(noisy), len(noisy), mode="full")
        lag = lags[np.argmax(np.abs(corr))] / simulator.sample_rate
        distance, _, _ = simulator.path_properties(
            simulator.random_defect("medium"), experiment
        )
        estimates.append(distance / max(lag - simulator.material.system_delay_s, 1e-6))
    profile = {
        "wave_velocity_m_s": float(np.median(estimates)),
        "noise_std": simulator.material.noise_std,
        "attenuation": simulator.material.attenuation,
        "resonance_hz": simulator.material.resonance_hz,
        "reference_experiments": [experiment.to_dict() for experiment in experiments],
    }
    output = Path(args.output); output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(profile, indent=2), encoding="utf-8")
    print(json.dumps(profile, indent=2))


if __name__ == "__main__":
    main()
