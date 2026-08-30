from __future__ import annotations

from pathlib import Path
import os
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import uvicorn


if __name__ == "__main__":
    uvicorn.run("backend.app.main:app", host=os.getenv("ARGUS_BIND_HOST", "0.0.0.0"), port=8000, reload=False)
