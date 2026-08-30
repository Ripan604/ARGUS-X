from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.evaluation.calibration_study import run_calibration_study, write_calibration_artifacts


def main() -> None:
    parser = argparse.ArgumentParser(description="ARGUS NEO simulation-based calibration study")
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--quick", action="store_true")
    modes.add_argument("--standard", action="store_true")
    modes.add_argument("--research", action="store_true")
    parser.add_argument("--seed", type=int, default=200)
    parser.add_argument("--output", default="research_results/calibration.json")
    args = parser.parse_args()
    mode = "research" if args.research else "standard" if args.standard else "quick"
    result = run_calibration_study(mode, args.seed)
    destination = Path(args.output); destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2), encoding="utf-8")
    artifacts = write_calibration_artifacts(result, destination.parent / "calibration_artifacts")
    print(json.dumps({"output": str(destination.resolve()), "artifacts": artifacts, **result["metadata"], "coverage": result["coverage"], "expected_calibration_error": result["expected_calibration_error"]}, indent=2))


if __name__ == "__main__":
    main()
