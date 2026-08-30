from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.demo.scenarios import SCENARIOS, run_demo_scenario


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a deterministic ARGUS NEO blind demonstration")
    parser.add_argument("scenario", choices=tuple(SCENARIOS))
    parser.add_argument("--seed", type=int)
    parser.add_argument("--cases", type=int, default=4)
    parser.add_argument("--output", default="")
    args = parser.parse_args()
    result = run_demo_scenario(args.scenario, seed=args.seed, cases=args.cases)
    text = json.dumps(result, indent=2)
    if args.output:
        destination = Path(args.output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text, encoding="utf-8")
        print(f"Wrote observed simulated demo report to {destination.resolve()}")
    else:
        print(text)


if __name__ == "__main__":
    main()
