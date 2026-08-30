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

## ARGUS NEO routes

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/materials` | Synthetic material-prior profiles and disclaimers |
| GET | `/api/planner/recommend` | Current action, fidelity, objective, horizon, and scores |
| GET | `/api/planner/explain` | Structured quantity-derived rationale |
| GET | `/api/planner/alternatives` | Ranked auditable alternative actions |
| GET | `/api/planner/status` | Candidate progress/timing/cache diagnostics |
| GET | `/api/inference/state` | Versioned joint structural/nuisance state |
| GET | `/api/inference/uncertainty` | Structural, metrology, discrepancy, and OOD summaries |
| GET | `/api/calibration/status` | Reference profile and nuisance update state |
| GET | `/api/model/trust` | Discrepancy, cache, and selected-fidelity evidence |
| GET | `/api/ood/status` | Method scores, status, confidence cap, recommendation |
| PUT | `/api/sessions/{id}/no-go-regions` | Replace virtual inaccessible areas |
| POST | `/api/sessions/{id}/human-decision` | Accept/modify/reject and audit a recommendation |
| POST | `/api/sessions/{id}/emergency-stop` | Persistently latch all acquisition paths with an operator reason |
| POST | `/api/sessions/{id}/emergency-stop/release` | Release the latch only with explicit human acknowledgement |
| GET | `/api/assurance/status` | Integrity state, sensor reliability, drift, failure taxonomy, and safety latch |
| GET | `/api/ledger/{id}` | Linked evidence records |
| GET | `/api/ledger/{id}/verify` | Verify canonical hashes and predecessor links |
| GET | `/api/events/{id}` | Human/import/constraint event history |
| GET | `/api/export/{id}` | Integrity-manifested research ZIP |
| POST | `/api/import` | Verify and import a research ZIP |
| POST/GET | `/api/research/jobs*` | Submit, observe, list, or cancel local jobs |
| POST | `/api/benchmark/run` | Queue nine-policy paired benchmark |
| POST | `/api/ablation/run` | Queue controlled mechanism ablation |
| POST | `/api/calibration/run` | Queue simulation-based calibration study |
| GET | `/api/models` | Local model registry |
| GET | `/api/demo/scenarios` | Built-in honest demo definitions |
| POST | `/api/demo/run` | Queue a deterministic demo scenario |
| POST/GET | `/api/probe/*` | Register/list nodes and submit observations |
| WS | `/ws/probe/{node}` | Phone/edge heartbeat and session state |
| WS | `/ws/session/{id}` | Dashboard state/planner status protocol |

All query endpoints taking a session use `?session_id=<id>`. OpenAPI is the authoritative validation schema. Research jobs support `benchmark`, `calibration`, `ablation`, `dataset_generation`, `surrogate_training`, and `demo_scenario` and return `queued`, `running`, `completed`, `failed`, or `cancelled`.
