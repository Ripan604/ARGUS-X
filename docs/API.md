# HTTP API

Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Service and physics-engine readiness |
| POST | `/sessions` | Create secret simulation or physical session |
| GET | `/sessions` | List resumable local session summaries |
| GET | `/sessions/{id}` | Current public session state; truth is withheld |
| POST | `/sessions/{id}/calibrate` | Generate/store an object reference profile |
| GET | `/sessions/{id}/recommendation` | Selected and top-five candidate experiments |
| POST | `/sessions/{id}/experiments/run` | Execute simulation recommendation or custom parameters |
| POST | `/sessions/{id}/experiments/upload` | Validate/process a WAV measurement |
| POST | `/sessions/{id}/experiments/device` | Acquire from a connected microphone or serial probe |
| GET | `/sessions/{id}/posterior` | Current grid and estimates |
| GET | `/sessions/{id}/history` | Signals/features/plans/posterior transitions |
| POST | `/sessions/{id}/reveal` | Reveal simulation truth and physical error |
| GET | `/devices` | Microphone and serial availability |
| POST | `/devices/connect` | Connect microphone or serial probe |
| POST | `/devices/disconnect` | Disconnect device safely |
| GET | `/benchmarks` | Actual saved benchmark output, or a small generated run |

All probe coordinates are finite normalized values in `[0,1]`. Upload content type and size are checked, and no uploaded filename is used as a filesystem path.
