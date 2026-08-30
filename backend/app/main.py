from __future__ import annotations

import json
import logging
import os
from pathlib import Path
import io
from datetime import datetime, timezone

import numpy as np

from fastapi import FastAPI, File, Form, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from backend.app.database.repository import SessionRepository
from backend.app.demo.scenarios import SCENARIOS
from backend.app.evaluation.benchmark import run_benchmark
from backend.app.evidence.bundles import export_research_bundle, import_research_bundle
from backend.app.hardware.devices import MicrophoneDevice, SerialProbeDevice, discover_devices
from backend.app.models.registry import ModelRegistry
from backend.app.core.materials import MATERIAL_PROFILES
from backend.app.models.domain import Experiment
from backend.app.research.jobs import ResearchJobManager
from backend.app.schemas.api import (
    CreateSessionRequest, DeviceConnectRequest, DeviceExperimentRequest, ExperimentParameters,
    HumanDecisionRequest, NoGoRegionsRequest, ProbeMeasurementRequest, ProbeRegistrationRequest,
    ResearchJobRequest, RunExperimentRequest,
)
from backend.app.services.session_manager import SessionManager
from backend.app.utils.logging import configure_logging

configure_logging()
logger = logging.getLogger("argus.api")


def create_app(database_path: str | Path | None = None) -> FastAPI:
    db_path = database_path or os.getenv("ARGUS_DB_PATH", "backend/data/argus.db")
    repository = SessionRepository(db_path)
    manager = SessionManager(repository)
    jobs = ResearchJobManager(repository)
    model_registry = ModelRegistry(repository)
    devices = {"serial_probe": SerialProbeDevice(), "microphone": MicrophoneDevice()}
    app = FastAPI(
        title="ARGUS API",
        version="0.1.0",
        description="Adaptive Recursive Guided Uncertainty Sensing closed-loop experiment API",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_origin_regex=r"https?://(localhost|127\.0\.0\.1|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[01])\.\d+\.\d+)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.manager = manager
    app.state.repository = repository
    app.state.devices = devices
    app.state.jobs = jobs
    app.state.model_registry = model_registry

    def runtime_or_404(session_id: str):
        try:
            return manager.get(session_id)
        except KeyError:
            raise HTTPException(404, "Session not found")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "argus", "version": "0.1.0", "physics_inference": True}

    @app.get("/api/materials")
    def material_profiles() -> dict:
        return {"profiles": [profile.to_dict() for profile in MATERIAL_PROFILES.values()]}

    @app.get("/api/demo/scenarios")
    def demo_scenarios() -> dict:
        return {"scenarios": SCENARIOS}

    @app.post("/api/demo/run", status_code=202)
    def start_demo_scenario(parameters: dict | None = None) -> dict:
        return jobs.submit("demo_scenario", parameters or {"scenario": "rival_hypotheses"})

    @app.post("/sessions", status_code=201)
    def create_session(request: CreateSessionRequest) -> dict:
        runtime = manager.create(request)
        logger.info("session_created id=%s mode=%s preset=%s", runtime.id, runtime.mode, runtime.preset)
        return manager.public_state(runtime)

    @app.get("/sessions")
    def list_sessions(limit: int = 50) -> dict:
        return {"sessions": repository.list_sessions(limit)}

    @app.get("/sessions/{session_id}")
    def get_session(session_id: str) -> dict:
        return manager.public_state(runtime_or_404(session_id))

    @app.post("/sessions/{session_id}/calibrate")
    def calibrate(session_id: str) -> dict:
        runtime_or_404(session_id)
        return manager.calibrate(session_id)

    @app.get("/sessions/{session_id}/recommendation")
    def recommendation(session_id: str) -> dict:
        return runtime_or_404(session_id).engine.current_recommendation.to_dict()

    @app.post("/sessions/{session_id}/experiments/run")
    def run_experiment(session_id: str, request: RunExperimentRequest | None = None) -> dict:
        runtime_or_404(session_id)
        parameters = Experiment(**request.experiment.model_dump()) if request and request.experiment else None
        try:
            result = manager.run(session_id, parameters)
        except RuntimeError as exc:
            raise HTTPException(409, str(exc))
        logger.info("experiment_completed session=%s index=%s", session_id, result.index)
        return {"experiment": result.index, "state": manager.public_state(manager.get(session_id)), "measurement": result.analysis, "diagnostics": result.diagnostics}

    @app.post("/sessions/{session_id}/experiments/upload")
    async def upload_experiment(
        session_id: str,
        file: UploadFile = File(...),
        experiment_json: str | None = Form(None),
    ) -> dict:
        runtime_or_404(session_id)
        if file.content_type not in {"audio/wav", "audio/x-wav", "audio/wave", "application/octet-stream"}:
            raise HTTPException(415, "Only WAV audio is accepted")
        parameters = None
        if experiment_json:
            try:
                parameters = Experiment(**ExperimentParameters.model_validate(json.loads(experiment_json)).model_dump())
            except Exception as exc:
                raise HTTPException(422, f"Invalid experiment_json: {exc}")
        payload = await file.read(10 * 1024 * 1024 + 1)
        try:
            result = manager.process_wav(session_id, payload, parameters)
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        return {"experiment": result.index, "state": manager.public_state(manager.get(session_id)), "measurement": result.analysis, "diagnostics": result.diagnostics}

    @app.post("/sessions/{session_id}/experiments/device")
    def acquire_device_experiment(session_id: str, request: DeviceExperimentRequest) -> dict:
        runtime = runtime_or_404(session_id)
        device = devices[request.device]
        if not device.connected:
            raise HTTPException(409, f"{request.device} is not connected")
        experiment = Experiment(**request.experiment.model_dump()) if request.experiment else runtime.engine.current_recommendation.selected.experiment
        try:
            samples = device.acquire(experiment, runtime.engine.config.sample_rate)
            result = manager.process_samples(
                session_id, samples, runtime.engine.config.sample_rate, experiment, acquisition_source=request.device
            )
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(400, str(exc))
        logger.info("device_experiment_completed session=%s device=%s index=%s", session_id, request.device, result.index)
        return {"experiment": result.index, "state": manager.public_state(manager.get(session_id)), "measurement": result.analysis, "diagnostics": result.diagnostics}

    @app.get("/sessions/{session_id}/posterior")
    def posterior(session_id: str) -> dict:
        runtime = runtime_or_404(session_id)
        return {"posterior": runtime.engine.belief.to_list(), "estimate": runtime.engine.belief.estimate()}

    @app.get("/sessions/{session_id}/history")
    def history(session_id: str) -> dict:
        runtime_or_404(session_id)
        return {"experiments": repository.list_experiments(session_id)}

    @app.post("/sessions/{session_id}/reveal")
    def reveal(session_id: str) -> dict:
        runtime_or_404(session_id)
        try:
            return manager.reveal(session_id)
        except RuntimeError as exc:
            raise HTTPException(409, str(exc))

    @app.get("/devices")
    def list_devices() -> dict:
        status = discover_devices()
        status.update({name: device.status() for name, device in devices.items()})
        return status

    @app.post("/devices/connect")
    def connect_device(request: DeviceConnectRequest) -> dict:
        return devices[request.device].connect(port=request.port, baudrate=request.baudrate)

    @app.post("/devices/disconnect")
    def disconnect_device(request: DeviceConnectRequest) -> dict:
        return devices[request.device].disconnect()

    @app.get("/benchmarks")
    def benchmarks() -> dict:
        path = Path("benchmark_results/benchmark.json")
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return run_benchmark(cases=4, max_experiments=8)

    @app.get("/api/planner/recommend")
    def planner_recommend(session_id: str) -> dict:
        return runtime_or_404(session_id).engine.current_recommendation.to_dict()

    @app.get("/api/planner/explain")
    def planner_explain(session_id: str) -> dict:
        recommendation = runtime_or_404(session_id).engine.current_recommendation
        return recommendation.structured_explanation or {"primary_reason": recommendation.explanation}

    @app.get("/api/planner/alternatives")
    def planner_alternatives(session_id: str) -> dict:
        recommendation = runtime_or_404(session_id).engine.current_recommendation
        return {"selected": recommendation.selected.to_dict(), "alternatives": [item.to_dict() for item in recommendation.top_candidates[1:]]}

    @app.get("/api/planner/status")
    def planner_status(session_id: str) -> dict:
        engine = runtime_or_404(session_id).engine
        return {"status": "completed", **engine.neo_planner.last_diagnostics}

    @app.get("/api/inference/state")
    def inference_state(session_id: str) -> dict:
        return runtime_or_404(session_id).engine.joint_state.to_dict()

    @app.get("/api/inference/uncertainty")
    def inference_uncertainty(session_id: str) -> dict:
        return runtime_or_404(session_id).engine.joint_state.uncertainty_summary()

    @app.get("/api/calibration/status")
    def calibration_status(session_id: str) -> dict:
        runtime = runtime_or_404(session_id)
        return {
            "profile": runtime.calibration,
            "last_calibration": runtime.engine.joint_state.last_calibration,
            "metrology": runtime.engine.joint_state.nuisance.uncertainty_summary(),
        }

    @app.get("/api/model/trust")
    def model_trust(session_id: str) -> dict:
        engine = runtime_or_404(session_id).engine
        return {
            **engine.joint_state.discrepancy_state,
            "cache": {str(level): model.cache.stats() for level, model in engine.neo_planner.models.items()},
            "last_planner_fidelity": engine.current_recommendation.chosen_model_fidelity,
            "reason_for_fidelity": engine.current_recommendation.reason_for_fidelity,
        }

    @app.get("/api/ood/status")
    def ood_status(session_id: str) -> dict:
        return runtime_or_404(session_id).engine.joint_state.ood_state

    @app.put("/api/sessions/{session_id}/no-go-regions")
    def set_no_go_regions(session_id: str, request: NoGoRegionsRequest) -> dict:
        runtime_or_404(session_id)
        return manager.set_no_go_regions(session_id, [item.model_dump() for item in request.regions])

    @app.post("/api/sessions/{session_id}/human-decision")
    def human_decision(session_id: str, request: HumanDecisionRequest) -> dict:
        runtime_or_404(session_id)
        return manager.human_decision(
            session_id, request.decision, request.reason,
            request.experiment.model_dump() if request.experiment else None,
        )

    @app.get("/api/ledger/{session_id}")
    def ledger_entries(session_id: str) -> dict:
        runtime_or_404(session_id)
        return {"entries": repository.list_ledger_entries(session_id)}

    @app.get("/api/ledger/{session_id}/verify")
    def verify_ledger(session_id: str) -> dict:
        runtime_or_404(session_id)
        return manager.ledger.verify(session_id)

    @app.get("/api/events/{session_id}")
    def session_events(session_id: str) -> dict:
        runtime_or_404(session_id)
        return {"events": repository.list_events(session_id)}

    @app.get("/api/export/{session_id}")
    def export_bundle(session_id: str):
        runtime_or_404(session_id)
        payload = export_research_bundle(repository, session_id)
        return StreamingResponse(
            io.BytesIO(payload), media_type="application/zip",
            headers={"Content-Disposition": f'attachment; filename="argus_session_{session_id}.zip"'},
        )

    @app.post("/api/import", status_code=201)
    async def import_bundle(file: UploadFile = File(...)) -> dict:
        if file.content_type not in {"application/zip", "application/octet-stream", "application/x-zip-compressed"}:
            raise HTTPException(415, "Only an ARGUS ZIP research bundle is accepted")
        payload = await file.read(100 * 1024 * 1024 + 1)
        try:
            result = import_research_bundle(repository, payload)
            manager.get(result["session_id"])
            return result
        except (ValueError, KeyError, OSError) as exc:
            raise HTTPException(400, str(exc))

    @app.post("/api/research/jobs", status_code=202)
    def create_research_job(request: ResearchJobRequest) -> dict:
        try:
            return jobs.submit(request.job_type, request.parameters)
        except ValueError as exc:
            raise HTTPException(422, str(exc))

    @app.get("/api/research/jobs")
    def list_research_jobs(limit: int = 50) -> dict:
        return {"jobs": repository.list_jobs(limit)}

    @app.get("/api/research/jobs/{job_id}")
    def get_research_job(job_id: str) -> dict:
        job = repository.get_job(job_id)
        if job is None:
            raise HTTPException(404, "Research job not found")
        return job

    @app.post("/api/research/jobs/{job_id}/cancel")
    def cancel_research_job(job_id: str) -> dict:
        try:
            return jobs.cancel(job_id)
        except KeyError:
            raise HTTPException(404, "Research job not found")

    @app.post("/api/benchmark/run", status_code=202)
    def start_benchmark(parameters: dict | None = None) -> dict:
        return jobs.submit("benchmark", parameters or {})

    @app.post("/api/ablation/run", status_code=202)
    def start_ablation(parameters: dict | None = None) -> dict:
        return jobs.submit("ablation", parameters or {})

    @app.post("/api/calibration/run", status_code=202)
    def start_calibration_study(parameters: dict | None = None) -> dict:
        return jobs.submit("calibration", parameters or {})

    @app.get("/api/models")
    def list_models() -> dict:
        return {"models": model_registry.list()}

    @app.post("/api/probe/register", status_code=201)
    def register_probe(request: ProbeRegistrationRequest) -> dict:
        return repository.upsert_probe_node(request.node_id, request.node_type, request.capabilities, {"status": "connected"})

    @app.get("/api/probe/nodes")
    def probe_nodes() -> dict:
        return {"nodes": repository.list_probe_nodes()}

    @app.post("/api/probe/measurement")
    def probe_measurement(request: ProbeMeasurementRequest) -> dict:
        runtime = runtime_or_404(request.session_id)
        if request.timestamp:
            try:
                observed_at = datetime.fromisoformat(request.timestamp.replace("Z", "+00:00"))
                if observed_at.tzinfo is None:
                    observed_at = observed_at.replace(tzinfo=timezone.utc)
                skew_seconds = abs((datetime.now(timezone.utc) - observed_at.astimezone(timezone.utc)).total_seconds())
            except ValueError as exc:
                repository.add_event(request.session_id, "measurement_rejected", {"reason": "invalid_timestamp", "node_id": request.node_id})
                raise HTTPException(400, "Probe timestamp is not valid ISO-8601") from exc
            if skew_seconds > 300:
                repository.add_event(request.session_id, "measurement_rejected", {"reason": "timestamp_skew", "skew_seconds": skew_seconds, "node_id": request.node_id})
                raise HTTPException(400, "Probe timestamp differs from server time by more than five minutes")
        experiment = Experiment(**request.experiment.model_dump()) if request.experiment else runtime.engine.current_recommendation.selected.experiment
        try:
            result = manager.process_samples(
                request.session_id, np.asarray(request.samples, dtype=np.float32), request.sample_rate,
                experiment, acquisition_source=f"probe:{request.node_id}", sensor_metadata=request.sensor_metadata,
            )
        except ValueError as exc:
            raise HTTPException(400, str(exc))
        repository.upsert_probe_node(request.node_id, "browser", request.sensor_metadata, {"status": "streaming", "session_id": request.session_id})
        return {"experiment": result.index, "state": manager.public_state(runtime), "quality": result.quality, "diagnostics": result.diagnostics}

    @app.websocket("/ws/probe/{node_id}")
    async def probe_socket(websocket: WebSocket, node_id: str) -> None:
        await websocket.accept()
        try:
            while True:
                message = await websocket.receive_json()
                message_type = message.get("type")
                if message_type in {"hello", "heartbeat"}:
                    node = repository.upsert_probe_node(
                        node_id, message.get("node_type", "browser"), message.get("capabilities", {}),
                        {"status": "connected", "session_id": message.get("session_id")},
                    )
                    await websocket.send_json({"type": "ack", "node": node})
                elif message_type == "state" and message.get("session_id"):
                    await websocket.send_json({"type": "session_state", "state": manager.public_state(runtime_or_404(message["session_id"]))})
                else:
                    await websocket.send_json({"type": "error", "message": "Unsupported probe message"})
        except WebSocketDisconnect:
            repository.upsert_probe_node(node_id, "browser", {}, {"status": "disconnected"})

    @app.websocket("/ws/session/{session_id}")
    async def session_socket(websocket: WebSocket, session_id: str) -> None:
        runtime = runtime_or_404(session_id)
        await websocket.accept()
        try:
            while True:
                message = await websocket.receive_json()
                if message.get("type") == "state":
                    await websocket.send_json({"type": "state", "state": manager.public_state(runtime)})
                elif message.get("type") == "planner_status":
                    await websocket.send_json({"type": "planner_status", "status": runtime.engine.neo_planner.last_diagnostics})
                else:
                    await websocket.send_json({"type": "error", "message": "Unsupported session message"})
        except WebSocketDisconnect:
            return

    return app


app = create_app()
