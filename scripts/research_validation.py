from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.app.evaluation.research_validation import run_validation


def main():
    parser = argparse.ArgumentParser(description="Controlled paired ARGUS synthetic validation")
    parser.add_argument("--seed", type=int, default=41000)
    parser.add_argument("--cases", type=int, default=20)
    parser.add_argument("--steps", type=int, default=8)
    parser.add_argument("--candidates", type=int, default=24)
    parser.add_argument("--variants", nargs="+", default=["legacy_proxy", "nuisance_aware"])
    parser.add_argument("--output", default="research_results/nuisance_design_validation.json")
    args = parser.parse_args()
    paths = ["scripts/research_validation.py"] + sorted(
        str(p.relative_to(ROOT)).replace("\\", "/") for p in (ROOT / "backend/app").rglob("*.py"))
    fingerprints = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    result = run_validation(range(args.seed, args.seed + args.cases), args.steps, args.candidates,
                            variants=args.variants,
                            progress=lambda r: print(json.dumps({k: r[k] for k in
                                ("seed", "context", "variant", "completed", "localization_error_mm", "execution_error") if k in r}), flush=True))
    result["metadata"]["source_sha256"] = fingerprints
    result["metadata"]["git_head"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    result["metadata"]["source_changed_during_run"] = any(hashlib.sha256((ROOT / p).read_bytes()).hexdigest() != digest for p, digest in fingerprints.items())
    result["metadata"]["command"] = "python scripts/research_validation.py " + " ".join(sys.argv[1:])
    destination = ROOT / args.output
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(result["paired_comparisons"], indent=2))
    print(f"Wrote {destination}")


if __name__ == "__main__":
    main()
