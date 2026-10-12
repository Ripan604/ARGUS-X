from __future__ import annotations

import shutil
import argparse
import os
import secrets
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
    if sys.platform == "win32":
        result = subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"],
                                capture_output=True, timeout=8, check=False)
        if result.returncode == 0:
            process.wait(timeout=5)
            return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> None:
    parser = argparse.ArgumentParser(description="Start ARGUS locally, or explicitly share it on a trusted LAN")
    parser.add_argument("--lan", action="store_true", help="Enable authenticated LAN access and print a per-run access key")
    args = parser.parse_args()
    frontend_env = ROOT / "frontend" / ".env.local"
    local_port = "8000"
    if frontend_env.exists():
        for line in frontend_env.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("NEXT_PUBLIC_ARGUS_API_PORT="):
                local_port = line.split("=", 1)[1].strip().strip('"\'')
    port_text = os.getenv("ARGUS_API_PORT", local_port)
    if not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
        raise SystemExit("ARGUS_API_PORT must be an integer from 1 to 65535")
    api_port = int(port_text)
    child_environment = {**os.environ, "ARGUS_API_PORT": str(api_port), "NEXT_PUBLIC_ARGUS_API_PORT": str(api_port)}
    network_mode = "lan" if args.lan else os.getenv("ARGUS_NETWORK_MODE", "local")
    if network_mode not in {"local", "lan"}:
        raise SystemExit("ARGUS_NETWORK_MODE must be local or lan")
    bind_host = "127.0.0.1"
    lan_address = None
    access_key = None
    child_environment["ARGUS_NETWORK_MODE"] = network_mode
    if network_mode == "lan":
        lan_address = local_network_address()
        if lan_address in {"<this-laptop-ip>", "127.0.0.1", "0.0.0.0"}:
            raise SystemExit("Could not identify a LAN address; use local mode or configure the backend explicitly")
        access_key = os.getenv("ARGUS_API_TOKEN") or secrets.token_urlsafe(32)
        child_environment.update({
            "ARGUS_API_TOKEN": access_key,
            "ARGUS_ALLOWED_HOSTS": os.getenv("ARGUS_ALLOWED_HOSTS", f"localhost,127.0.0.1,{lan_address}"),
            "ARGUS_ALLOWED_ORIGINS": os.getenv("ARGUS_ALLOWED_ORIGINS", f"http://localhost:5173,http://127.0.0.1:5173,http://{lan_address}:5173"),
        })
        bind_host = "0.0.0.0"
    child_environment["ARGUS_BIND_HOST"] = bind_host
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
        venv_python = ROOT / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        backend_python = str(venv_python) if venv_python.exists() else sys.executable
        backend = subprocess.Popen([backend_python, str(ROOT / "backend" / "run_backend.py")], cwd=ROOT, env=child_environment)
        frontend_environment = dict(child_environment)
        frontend_environment.pop("ARGUS_API_TOKEN", None)
        frontend = subprocess.Popen(
            [npm, "run", "dev", "--", "--hostname", bind_host, "--port", "5173"],
            cwd=ROOT / "frontend",
            env=frontend_environment,
        )
        print("\nARGUS is starting locally:")
        print("  Instrument: http://localhost:5173")
        print(f"  API:        http://localhost:{api_port}")
        print(f"  API docs:   http://localhost:{api_port}/docs" + (" (requires an authorized API client in LAN mode)" if network_mode == "lan" else ""))
        if network_mode == "lan":
            print(f"  Phone probe: http://{lan_address}:5173/probe")
            print(f"  Edge API:    http://{lan_address}:{api_port}")
            print(f"  Access key:  {access_key}")
            print("  Enter this key under Shared engine access. Keep devices on a trusted LAN; HTTP does not encrypt traffic.")
        else:
            print("  Local-only mode. Use python run_argus.py --lan for authenticated phone/edge access.")
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
