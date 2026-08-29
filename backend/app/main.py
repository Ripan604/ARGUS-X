from __future__ import annotations

import json
import logging
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from backend.app.database.repository import SessionRepository
from backend.app.evaluation.benchmark import run_benchmark
from backend.app.hardware.devices import MicrophoneDevice, SerialProbeDevice, discover_devices
from backend.app.models.domain import Experiment
from backend.app.schemas.api import CreateSessionRequest, DeviceConnectRequest, DeviceExperimentRequest, ExperimentParameters, RunExperimentRequest
from backend.app.services.session_manager import SessionManager
from backend.app.utils.logging import configure_logging

configure_logging()
logger = logging.getLogger("argus.api")


def create_app(database_path: str | Path | None = None) -> FastAPI:
    db_path = database_path or os.getenv("ARGUS_DB_PATH", "backend/data/argus.db")
    repository = SessionRepository(db_path)
    manager = SessionManager(repository)
    devices = {"serial_probe": SerialProbeDevice(), "microphone": MicrophoneDevice()}
    app = FastAPI(
        title="ARGUS API",
        version="0.1.0",
        description="Adaptive Recursive Guided Uncertainty Sensing closed-loop experiment API",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.manager = manager
    app.state.repository = repository
    app.state.devices = devices

    def runtime_or_404(session_id: str):
        try:
            return manager.get(session_id)
        except KeyError:
            raise HTTPException(404, "Session not found")

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok", "service": "argus", "version": "0.1.0", "physics_inference": True}

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
            result = manager.process_samples(session_id, samples, runtime.engine.config.sample_rate, experiment)
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

    return app


app = create_app()
