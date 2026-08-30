from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.models.active_learning import run_active_learning_study


def main() -> None:
    parser = argparse.ArgumentParser(description="CPU-only active learning for the ARGUS MLP surrogate")
    parser.add_argument("--samples", type=int, default=240)
    parser.add_argument("--query-count", type=int, default=24)
    parser.add_argument("--seed", type=int, default=431)
    parser.add_argument("--output", default="research_results/active_surrogate.json")
    args = parser.parse_args()
    result = run_active_learning_study(seed=args.seed, samples=args.samples, query_count=args.query_count)
    destination = Path(args.output); destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(destination.resolve()), **result}, indent=2))


if __name__ == "__main__":
    main()
