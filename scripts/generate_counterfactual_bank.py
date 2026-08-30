from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.research.bank import generate_counterfactual_bank


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a deterministic chunked ARGUS counterfactual response bank")
    parser.add_argument("--scale", choices=("tiny", "demo", "research"), default="tiny")
    parser.add_argument("--seed", type=int, default=71)
    parser.add_argument("--destination", default="datasets/generated/counterfactual_bank")
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()
    result = generate_counterfactual_bank(args.destination, scale=args.scale, seed=args.seed, resume=not args.no_resume)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
