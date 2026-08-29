from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.config import ArgusConfig
from backend.app.services.engine import ArgusEngine


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the ARGUS active physical interrogation loop")
    parser.add_argument("--preset", choices=["easy", "medium", "hard"], default="medium")
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--experiments", type=int, default=10)
    args = parser.parse_args()

    config = ArgusConfig(max_experiments=args.experiments, seed=args.seed)
    engine = ArgusEngine(config=config, seed=args.seed, preset=args.preset)
    print("ARGUS — Adaptive Recursive Guided Uncertainty Sensing")
    print(f"Secret {args.preset} defect generated. Ground truth remains hidden during interrogation.")
    print(" idx | source -> receiver    | band (Hz)   | entropy | confidence | EIG proxy")
    print("-----+-----------------------+-------------+---------+------------+----------")
    while not engine.status()["should_stop"]:
        recommendation = engine.current_recommendation
        result = engine.run_recommended()
        status = engine.status()
        e = result.parameters
        print(
            f" {result.index:>3} | ({e.source_x:.2f},{e.source_y:.2f}) -> ({e.receiver_x:.2f},{e.receiver_y:.2f})"
            f" | {e.frequency_start_hz:4.0f}-{e.frequency_end_hz:4.0f} | {status['normalized_entropy']:.3f}"
            f"   | {status['confidence']:.3f}      | {recommendation.selected.expected_information_gain:.3f}"
        )
    estimate = engine.belief.estimate()
    print(f"\nStopped: {engine.status()['stop_reason']}")
    print(f"Estimated defect (MAP): ({estimate['map_x']:.3f}, {estimate['map_y']:.3f})")
    print(f"Ground truth:           ({engine.truth.center_x:.3f}, {engine.truth.center_y:.3f})")
    print(f"Physical localization error: {engine.localization_error() * 1000:.1f} mm")
    print(f"Entropy reduction: {(1 - estimate['normalized_entropy']) * 100:.1f}%")


if __name__ == "__main__":
    main()
