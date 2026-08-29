from __future__ import annotations

import importlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.config import ArgusConfig
from backend.app.database.repository import SessionRepository
from backend.app.services.engine import ArgusEngine


def main() -> None:
    checks: list[dict[str, str | bool]] = []

    def record(name: str, ok: bool, detail: str) -> None:
        checks.append({"check": name, "ok": ok, "detail": detail})

    version = sys.version_info
    record("python", version >= (3, 10), f"{version.major}.{version.minor}.{version.micro}; 3.11+ recommended")
    for module in ("numpy", "scipy", "fastapi", "pydantic", "serial", "torch"):
        try:
            loaded = importlib.import_module(module)
            record(f"import:{module}", True, str(getattr(loaded, "__version__", "available")))
        except Exception as exc:
            record(f"import:{module}", False, str(exc))

    try:
        engine = ArgusEngine(config=ArgusConfig(max_experiments=3), seed=17, preset="easy")
        engine.run_recommended()
        record("closed_loop", abs(float(engine.belief.posterior.sum()) - 1.0) < 1e-8, "one active experiment completed")
    except Exception as exc:
        record("closed_loop", False, str(exc))

    try:
        with tempfile.TemporaryDirectory(prefix="argus-doctor-") as directory:
            repository = SessionRepository(Path(directory) / "doctor.db")
            with repository.connection() as connection:
                mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
            record("sqlite", True, f"temporary database initialized; journal={mode}")
    except Exception as exc:
        record("sqlite", False, str(exc))

    node = shutil.which("node")
    npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
    if node:
        node_version = subprocess.run([node, "--version"], capture_output=True, text=True, timeout=5).stdout.strip()
        record("node", True, node_version)
    else:
        record("node", False, "node not found")
    record("npm", npm is not None, npm or "npm not found")
    record("frontend_dependencies", (ROOT / "frontend" / "node_modules").exists(), "frontend/node_modules")
    record("benchmark_artifact", (ROOT / "benchmark_results" / "benchmark.json").exists(), "benchmark_results/benchmark.json")

    print("ARGUS readiness report")
    for check in checks:
        print(f"[{'PASS' if check['ok'] else 'FAIL'}] {check['check']}: {check['detail']}")
    print("\nMachine-readable summary:")
    print(json.dumps({"ready": all(bool(check["ok"]) for check in checks), "checks": checks}, indent=2))
    raise SystemExit(0 if all(bool(check["ok"]) for check in checks) else 1)


if __name__ == "__main__":
    main()
