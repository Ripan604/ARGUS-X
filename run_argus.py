from __future__ import annotations

import shutil
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def local_network_address() -> str:
    """Best-effort LAN address discovery without sending application data."""
    probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        probe.connect(("8.8.8.8", 80))
        return str(probe.getsockname()[0])
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return "<this-laptop-ip>"
    finally:
        probe.close()


def terminate(process: subprocess.Popen | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> None:
    npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
    if npm is None:
        raise SystemExit("npm was not found. Install Node 22+, then run npm install in frontend/.")
    if not (ROOT / "frontend" / "node_modules").exists():
        raise SystemExit("Frontend dependencies are missing. Run: cd frontend && npm install")

    backend: subprocess.Popen | None = None
    frontend: subprocess.Popen | None = None
    stop_requested = False

    def stop_services(*_: object) -> None:
        nonlocal stop_requested
        stop_requested = True
        terminate(frontend)
        terminate(backend)

    signal.signal(signal.SIGINT, stop_services)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, stop_services)

    try:
        backend = subprocess.Popen([sys.executable, str(ROOT / "backend" / "run_backend.py")], cwd=ROOT)
        frontend = subprocess.Popen(
            [npm, "run", "dev", "--", "--hostname", "0.0.0.0", "--port", "5173"],
            cwd=ROOT / "frontend",
        )
        print("\nARGUS is starting locally:")
        print("  Instrument: http://localhost:5173")
        print("  API:        http://localhost:8000")
        print("  API docs:   http://localhost:8000/docs")
        lan_address = local_network_address()
        print(f"  Phone probe: http://{lan_address}:5173/probe")
        print(f"  Edge API:    http://{lan_address}:8000")
        print("  Keep all devices on the same trusted local network.")
        print("Press Ctrl+C to stop both services.\n")
        while backend.poll() is None and frontend.poll() is None:
            time.sleep(0.5)
        if stop_requested:
            print("ARGUS stopped cleanly.")
            return
        failed = backend if backend.poll() is not None else frontend
        raise SystemExit(f"A service stopped unexpectedly with code {failed.returncode}.")
    finally:
        stop_services()


if __name__ == "__main__":
    main()
