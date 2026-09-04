from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sqlite3
import threading
from typing import Iterator
import zlib

import numpy as np

from backend.app.database.migrations import apply_migrations


class SessionRepository:
    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    preset TEXT NOT NULL,
                    state_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS experiments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
                    experiment_index INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    parameters_json TEXT NOT NULL,
                    features_json TEXT NOT NULL,
                    posterior_before_json TEXT NOT NULL,
                    posterior_after_json TEXT NOT NULL,
                    likelihood_json TEXT NOT NULL,
                    planner_json TEXT NOT NULL,
                    diagnostics_json TEXT NOT NULL,
                    raw_signal BLOB NOT NULL,
                    UNIQUE(session_id, experiment_index)
                );
                DROP INDEX IF EXISTS idx_experiments_session;
                CREATE INDEX IF NOT EXISTS idx_sessions_updated_at ON sessions(updated_at DESC);
                PRAGMA optimize;
                """
            )
            apply_migrations(connection)

    def create_session(self, session_id: str, mode: str, preset: str, state: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self.connection() as connection:
            connection.execute(
                "INSERT INTO sessions(id, created_at, updated_at, mode, preset, state_json) VALUES(?,?,?,?,?,?)",
                (session_id, now, now, mode, preset, json.dumps(state)),
            )

    def delete_session(self, session_id: str) -> None:
        """Remove one exact session, used to roll back a failed bundle import."""

        with self._lock, self.connection() as connection:
            connection.execute("DELETE FROM sessions WHERE id=?", (session_id,))

    def update_session(self, session_id: str, state: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self.connection() as connection:
            cursor = connection.execute(
                "UPDATE sessions SET updated_at=?, state_json=? WHERE id=?", (now, json.dumps(state), session_id)
            )
            if cursor.rowcount == 0:
                raise KeyError(session_id)

    def get_session(self, session_id: str) -> dict | None:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM sessions WHERE id=?", (session_id,)).fetchone()
        if row is None:
            return None
        return {**dict(row), "state": json.loads(row["state_json"])}

    def list_sessions(self, limit: int = 50) -> list[dict]:
        safe_limit = max(1, min(int(limit), 200))
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT id, created_at, updated_at, mode, preset, state_json FROM sessions ORDER BY updated_at DESC LIMIT ?",
                (safe_limit,),
            ).fetchall()
        result = []
        for row in rows:
            state = json.loads(row["state_json"])
            result.append(
                {
                    "id": row["id"],
                    "created_at": row["created_at"],
                    "updated_at": row["updated_at"],
                    "mode": row["mode"],
                    "preset": row["preset"],
                    "experiment_count": len(state.get("experiments", [])),
                    "revealed": bool(state.get("revealed", False)),
                }
            )
        return result

    def add_experiment(self, session_id: str, result) -> None:
        raw = zlib.compress(np.asarray(result.signal, dtype=np.float32).tobytes(), level=6)
        with self._lock, self.connection() as connection:
            connection.execute(
                """INSERT INTO experiments(
                    session_id, experiment_index, created_at, parameters_json, features_json,
                    posterior_before_json, posterior_after_json, likelihood_json, planner_json,
                    diagnostics_json, raw_signal
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    session_id, result.index, datetime.now(timezone.utc).isoformat(),
                    json.dumps(result.parameters.to_dict()), json.dumps(result.analysis),
                    json.dumps(result.posterior_before.tolist()), json.dumps(result.posterior_after.tolist()),
                    json.dumps(result.likelihood.tolist()), json.dumps(result.recommendation.to_dict()),
                    json.dumps({
                        **result.diagnostics,
                        "quality": result.quality,
                        "calibration_result": result.calibration_result,
                        "action_type": result.action_type,
                    }), raw,
                ),
            )

    def list_experiments(self, session_id: str, include_signal: bool = False) -> list[dict]:
        columns = "*" if include_signal else "id,session_id,experiment_index,created_at,parameters_json,features_json,posterior_before_json,posterior_after_json,likelihood_json,planner_json,diagnostics_json"
        with self.connection() as connection:
            rows = connection.execute(
                f"SELECT {columns} FROM experiments WHERE session_id=? ORDER BY experiment_index", (session_id,)
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            for key in ("parameters_json", "features_json", "posterior_before_json", "posterior_after_json", "likelihood_json", "planner_json", "diagnostics_json"):
                item[key.removesuffix("_json")] = json.loads(item.pop(key))
            if include_signal:
                item["signal"] = np.frombuffer(zlib.decompress(item.pop("raw_signal")), dtype=np.float32)
            result.append(item)
        return result

    def import_experiment(self, session_id: str, item: dict, signal: np.ndarray) -> None:
        raw = zlib.compress(np.asarray(signal, dtype=np.float32).tobytes(), level=6)
        with self._lock, self.connection() as connection:
            connection.execute(
                """INSERT INTO experiments(
                    session_id, experiment_index, created_at, parameters_json, features_json,
                    posterior_before_json, posterior_after_json, likelihood_json, planner_json,
                    diagnostics_json, raw_signal
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    session_id, int(item["experiment_index"]), item["created_at"],
                    json.dumps(item["parameters"]), json.dumps(item["features"]),
                    json.dumps(item["posterior_before"]), json.dumps(item["posterior_after"]),
                    json.dumps(item["likelihood"]), json.dumps(item["planner"]),
                    json.dumps(item["diagnostics"]), raw,
                ),
            )

    def append_ledger_entry(
        self,
        session_id: str,
        experiment_index: int,
        previous_hash: str,
        entry: dict,
        entry_hash: str,
    ) -> None:
        with self._lock, self.connection() as connection:
            connection.execute(
                """INSERT INTO ledger_entries(
                    session_id, experiment_index, created_at, previous_hash, entry_json, entry_hash
                ) VALUES(?,?,?,?,?,?)""",
                (
                    session_id,
                    experiment_index,
                    datetime.now(timezone.utc).isoformat(),
                    previous_hash,
                    json.dumps(entry, sort_keys=True, separators=(",", ":")),
                    entry_hash,
                ),
            )

    def list_ledger_entries(self, session_id: str) -> list[dict]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM ledger_entries WHERE session_id=? ORDER BY experiment_index", (session_id,)
            ).fetchall()
        return [
            {
                **dict(row),
                "entry": json.loads(row["entry_json"]),
            }
            for row in rows
        ]

    def create_job(self, job_id: str, job_type: str, request: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self.connection() as connection:
            connection.execute(
                """INSERT INTO research_jobs(
                    id, job_type, status, created_at, updated_at, progress, request_json
                ) VALUES(?,?,?,?,?,?,?)""",
                (job_id, job_type, "queued", now, now, 0.0, json.dumps(request)),
            )

    def update_job(
        self,
        job_id: str,
        *,
        status: str | None = None,
        progress: float | None = None,
        result: dict | None = None,
        error: str | None = None,
        cancellation_requested: bool | None = None,
    ) -> None:
        assignments, values = ["updated_at=?"], [datetime.now(timezone.utc).isoformat()]
        for name, value in (
            ("status", status), ("progress", progress),
            ("result_json", json.dumps(result) if result is not None else None),
            ("error", error),
            ("cancellation_requested", int(cancellation_requested) if cancellation_requested is not None else None),
        ):
            if value is not None:
                assignments.append(f"{name}=?")
                values.append(value)
        values.append(job_id)
        with self._lock, self.connection() as connection:
            connection.execute(f"UPDATE research_jobs SET {', '.join(assignments)} WHERE id=?", values)

    def get_job(self, job_id: str) -> dict | None:
        with self.connection() as connection:
            row = connection.execute("SELECT * FROM research_jobs WHERE id=?", (job_id,)).fetchone()
        return self._job_row(row) if row else None

    def list_jobs(self, limit: int = 50) -> list[dict]:
        with self.connection() as connection:
            rows = connection.execute(
                "SELECT * FROM research_jobs ORDER BY updated_at DESC LIMIT ?", (max(1, min(limit, 200)),)
            ).fetchall()
        return [self._job_row(row) for row in rows]

    def count_active_jobs(self) -> int:
        with self.connection() as connection:
            row = connection.execute(
                "SELECT COUNT(*) FROM research_jobs WHERE status IN ('queued', 'running')"
            ).fetchone()
        return int(row[0])

    @staticmethod
    def _job_row(row) -> dict:
        item = dict(row)
        item["request"] = json.loads(item.pop("request_json"))
        item["result"] = json.loads(item.pop("result_json")) if item.get("result_json") else None
        item.pop("result_json", None)
        item["cancellation_requested"] = bool(item["cancellation_requested"])
        return item

    def recover_interrupted_jobs(self) -> int:
        with self._lock, self.connection() as connection:
            cursor = connection.execute(
                """UPDATE research_jobs SET status='failed',
                   error='Process restarted before the queued or running job completed',
                   updated_at=? WHERE status IN ('queued', 'running')""",
                (datetime.now(timezone.utc).isoformat(),),
            )
            return int(cursor.rowcount)

    def register_model(self, record: dict) -> None:
        with self._lock, self.connection() as connection:
            connection.execute(
                """INSERT INTO model_registry(
                    model_id, architecture, training_dataset_hash, created_at, metrics_json,
                    calibration_json, supported_domain_json, artifact_path, artifact_hash
                ) VALUES(?,?,?,?,?,?,?,?,?)
                ON CONFLICT(model_id) DO UPDATE SET
                    architecture=excluded.architecture,
                    training_dataset_hash=excluded.training_dataset_hash,
                    metrics_json=excluded.metrics_json,
                    calibration_json=excluded.calibration_json,
                    supported_domain_json=excluded.supported_domain_json,
                    artifact_path=excluded.artifact_path,
                    artifact_hash=excluded.artifact_hash""",
                (
                    record["model_id"], record["architecture"], record.get("training_dataset_hash"),
                    record.get("created_at", datetime.now(timezone.utc).isoformat()),
                    json.dumps(record.get("metrics", {})), json.dumps(record.get("calibration_metrics", {})),
                    json.dumps(record.get("supported_domain", {})), record.get("artifact_path"), record.get("artifact_hash"),
                ),
            )

    def list_models(self) -> list[dict]:
        with self.connection() as connection:
            rows = connection.execute("SELECT * FROM model_registry ORDER BY created_at DESC").fetchall()
        result = []
        for row in rows:
            item = dict(row)
            for column in ("metrics_json", "calibration_json", "supported_domain_json"):
                item[column.removesuffix("_json") + ("_metrics" if column == "calibration_json" else "")] = json.loads(item.pop(column))
            result.append(item)
        return result

    def add_event(self, session_id: str, event_type: str, payload: dict) -> int:
        with self._lock, self.connection() as connection:
            cursor = connection.execute(
                "INSERT INTO session_events(session_id, created_at, event_type, payload_json) VALUES(?,?,?,?)",
                (session_id, datetime.now(timezone.utc).isoformat(), event_type, json.dumps(payload)),
            )
            return int(cursor.lastrowid)

    def import_event(self, session_id: str, created_at: str, event_type: str, payload: dict) -> int:
        with self._lock, self.connection() as connection:
            cursor = connection.execute(
                "INSERT INTO session_events(session_id, created_at, event_type, payload_json) VALUES(?,?,?,?)",
                (session_id, created_at, event_type, json.dumps(payload)),
            )
            return int(cursor.lastrowid)

    def list_events(self, session_id: str) -> list[dict]:
        with self.connection() as connection:
            rows = connection.execute("SELECT * FROM session_events WHERE session_id=? ORDER BY id", (session_id,)).fetchall()
        return [{**dict(row), "payload": json.loads(row["payload_json"])} for row in rows]

    def upsert_probe_node(self, node_id: str, node_type: str, capabilities: dict, state: dict) -> dict:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self.connection() as connection:
            connection.execute(
                """INSERT INTO probe_nodes(node_id, node_type, capabilities_json, state_json, last_seen_at)
                VALUES(?,?,?,?,?) ON CONFLICT(node_id) DO UPDATE SET
                    node_type=excluded.node_type,
                    capabilities_json=excluded.capabilities_json,
                    state_json=excluded.state_json,
                    last_seen_at=excluded.last_seen_at""",
                (node_id, node_type, json.dumps(capabilities), json.dumps(state), now),
            )
        return {"node_id": node_id, "node_type": node_type, "capabilities": capabilities, "state": state, "last_seen_at": now}

    def list_probe_nodes(self) -> list[dict]:
        with self.connection() as connection:
            rows = connection.execute("SELECT * FROM probe_nodes ORDER BY last_seen_at DESC").fetchall()
        return [
            {
                "node_id": row["node_id"], "node_type": row["node_type"],
                "capabilities": json.loads(row["capabilities_json"]),
                "state": json.loads(row["state_json"]), "last_seen_at": row["last_seen_at"],
            }
            for row in rows
        ]
