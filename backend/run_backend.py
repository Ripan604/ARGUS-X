from __future__ import annotations

from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn
from backend.app.security import SecuritySettings
from backend.app.security.network import MAX_WEBSOCKET_BYTES


def server_configuration() -> dict:
    """Fail closed before listening when LAN authentication is incomplete."""
    SecuritySettings.from_environment()
    port_text = os.getenv("ARGUS_API_PORT", "8000")
    if not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
        raise ValueError("ARGUS_API_PORT must be an integer from 1 to 65535")
    return {"host": os.getenv("ARGUS_BIND_HOST", "127.0.0.1"), "port": int(port_text),
            "reload": False, "proxy_headers": False, "ws_max_size": MAX_WEBSOCKET_BYTES,
            "ws_max_queue": 8, "limit_concurrency": 64, "timeout_keep_alive": 5}


if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", **server_configuration())
