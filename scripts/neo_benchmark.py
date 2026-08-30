from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.evaluation.neo_benchmark import run_ablation_study, run_benchmark_matrix


def main() -> None:
    parser = argparse.ArgumentParser(description="ARGUS NEO paired benchmark/ablation runner")
    parser.add_argument("--ablation", action="store_true")
    parser.add_argument("--cases", type=int, default=2)
    parser.add_argument("--max-experiments", type=int, default=5)
    parser.add_argument("--seed", type=int, default=100)
    parser.add_argument("--output", default="research_results/neo_benchmark.json")
    args = parser.parse_args()
    result = run_ablation_study(args.cases, args.seed) if args.ablation else run_benchmark_matrix(args.cases, args.max_experiments, args.seed)
    destination = Path(args.output); destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Wrote observed simulated results to {destination.resolve()}")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
