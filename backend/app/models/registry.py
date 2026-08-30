from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path

from backend.app.database.repository import SessionRepository


class ModelRegistry:
    def __init__(self, repository: SessionRepository) -> None:
        self.repository = repository

    def register(
        self,
        model_id: str,
        architecture: str,
        *,
        training_dataset_hash: str | None = None,
        metrics: dict | None = None,
        calibration_metrics: dict | None = None,
        supported_domain: dict | None = None,
        artifact_path: str | None = None,
    ) -> dict:
        artifact_hash = None
        if artifact_path and Path(artifact_path).is_file():
            artifact_hash = sha256(Path(artifact_path).read_bytes()).hexdigest()
        record = {
            "model_id": model_id, "architecture": architecture,
            "training_dataset_hash": training_dataset_hash,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "metrics": metrics or {}, "calibration_metrics": calibration_metrics or {},
            "supported_domain": supported_domain or {}, "artifact_path": artifact_path,
            "artifact_hash": artifact_hash,
        }
        self.repository.register_model(record)
        return record

    def list(self) -> list[dict]:
        return self.repository.list_models()

