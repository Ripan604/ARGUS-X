from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.evaluation.benchmark import run_benchmark


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark active ARGUS probing against non-adaptive baselines")
    parser.add_argument("--cases", type=int, default=12)
    parser.add_argument("--preset", choices=["easy", "medium", "hard"], default="medium")
    parser.add_argument("--experiments", type=int, default=10)
    parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--output", default="benchmark_results")
    args = parser.parse_args()
    result = run_benchmark(args.cases, args.preset, args.experiments, args.seed, args.output)
    print(json.dumps(result["summary"], indent=2))
    print("\nPaired ARGUS advantages (positive values favor ARGUS):")
    print(json.dumps(result["paired_comparisons"], indent=2))
    print(f"\nSaved actual per-run data to {Path(args.output).resolve()}")


if __name__ == "__main__":
    main()
