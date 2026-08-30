from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import socket
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def request_json(server: str, path: str, method: str = "GET", payload: dict | None = None) -> dict:
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        f"{server.rstrip('/')}{path}", data=body, method=method,
        headers={"Content-Type": "application/json"} if body is not None else {},
    )
    with urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def capture_microphone(duration: float, sample_rate: int) -> list[float]:
    try:
        import sounddevice as sd
    except ImportError as exc:
        raise RuntimeError("sounddevice is unavailable; install backend requirements or run without --auto-capture") from exc
    recording = sd.rec(max(8, int(duration * sample_rate)), samplerate=sample_rate, channels=1, dtype="float32")
    sd.wait()
    return recording[:, 0].tolist()


def main() -> None:
    parser = argparse.ArgumentParser(description="ARGUS Laptop-B acquisition/edge node")
    parser.add_argument("--server", required=True, help="Laptop-A API, e.g. http://192.168.1.20:8000")
    parser.add_argument("--session", required=True, help="ARGUS physical-session ID")
    parser.add_argument("--node-id", default=f"edge-{socket.gethostname().lower()}")
    parser.add_argument("--sample-rate", type=int, default=16_000)
    parser.add_argument("--auto-capture", action="store_true", help="Capture once for each newly observed recommendation")
    parser.add_argument("--poll-seconds", type=float, default=2.0)
    args = parser.parse_args()
    capabilities = {
        "microphone": True, "sample_rate": args.sample_rate, "transport": "local_http",
        "automatic_acquisition": args.auto_capture, "platform": sys.platform,
    }
    last_experiment = -1
    delay = max(0.5, args.poll_seconds)
    print(f"ARGUS edge node {args.node_id} connecting to {args.server}; Ctrl+C stops it.")
    while True:
        try:
            request_json(args.server, "/api/probe/register", "POST", {
                "node_id": args.node_id, "node_type": "edge_laptop", "capabilities": capabilities,
            })
            state = request_json(args.server, f"/sessions/{args.session}")
            count = int(state["status"]["experiment_count"])
            experiment = state["recommendation"]["experiment"]
            print(
                f"heartbeat {datetime.now(timezone.utc).isoformat()} | experiment={count} | "
                f"action={state['recommendation']['action_type']} | "
                f"TX=({experiment['source_x']:.3f},{experiment['source_y']:.3f}) "
                f"RX=({experiment['receiver_x']:.3f},{experiment['receiver_y']:.3f})"
            )
            if args.auto_capture and count != last_experiment and not state["status"]["should_stop"]:
                samples = capture_microphone(max(0.12, float(experiment["duration_s"])), args.sample_rate)
                result = request_json(args.server, "/api/probe/measurement", "POST", {
                    "session_id": args.session, "node_id": args.node_id, "sample_rate": args.sample_rate,
                    "samples": samples, "experiment": experiment,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "sensor_metadata": {"node_type": "edge_laptop", "hostname": socket.gethostname()},
                })
                last_experiment = int(result["state"]["status"]["experiment_count"])
                print(f"measurement accepted | quality={json.dumps(result['quality'], sort_keys=True)}")
            else:
                last_experiment = count
            delay = max(0.5, args.poll_seconds)
        except (HTTPError, URLError, TimeoutError, RuntimeError, KeyError, ValueError) as exc:
            print(f"edge connection/acquisition warning: {exc}; retrying in {delay:.1f}s", file=sys.stderr)
            delay = min(20.0, delay * 1.7)
        try:
            time.sleep(delay)
        except KeyboardInterrupt:
            print("ARGUS edge node stopped.")
            return


if __name__ == "__main__":
    main()
