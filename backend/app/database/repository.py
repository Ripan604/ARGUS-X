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

    def create_session(self, session_id: str, mode: str, preset: str, state: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._lock, self.connection() as connection:
            connection.execute(
                "INSERT INTO sessions(id, created_at, updated_at, mode, preset, state_json) VALUES(?,?,?,?,?,?)",
                (session_id, now, now, mode, preset, json.dumps(state)),
            )

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
                    json.dumps(result.diagnostics), raw,
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
