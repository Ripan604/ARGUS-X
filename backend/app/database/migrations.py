from __future__ import annotations

from datetime import datetime, timezone
import sqlite3


MIGRATIONS: tuple[tuple[int, str, str], ...] = (
    (
        1,
        "neo_research_infrastructure",
        """
        CREATE TABLE IF NOT EXISTS ledger_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            experiment_index INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            previous_hash TEXT NOT NULL,
            entry_json TEXT NOT NULL,
            entry_hash TEXT NOT NULL,
            UNIQUE(session_id, experiment_index),
            UNIQUE(session_id, entry_hash)
        );
        CREATE INDEX IF NOT EXISTS idx_ledger_session ON ledger_entries(session_id, experiment_index);

        CREATE TABLE IF NOT EXISTS research_jobs (
            id TEXT PRIMARY KEY,
            job_type TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            progress REAL NOT NULL DEFAULT 0,
            request_json TEXT NOT NULL,
            result_json TEXT,
            error TEXT,
            cancellation_requested INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_jobs_updated ON research_jobs(updated_at DESC);

        CREATE TABLE IF NOT EXISTS model_registry (
            model_id TEXT PRIMARY KEY,
            architecture TEXT NOT NULL,
            training_dataset_hash TEXT,
            created_at TEXT NOT NULL,
            metrics_json TEXT NOT NULL,
            calibration_json TEXT NOT NULL,
            supported_domain_json TEXT NOT NULL,
            artifact_path TEXT,
            artifact_hash TEXT
        );

        CREATE TABLE IF NOT EXISTS session_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL REFERENCES sessions(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL,
            event_type TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_events_session ON session_events(session_id, id);

        CREATE TABLE IF NOT EXISTS probe_nodes (
            node_id TEXT PRIMARY KEY,
            node_type TEXT NOT NULL,
            capabilities_json TEXT NOT NULL,
            state_json TEXT NOT NULL,
            last_seen_at TEXT NOT NULL
        );
        """,
    ),
)


def apply_migrations(connection: sqlite3.Connection) -> list[int]:
    connection.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TEXT NOT NULL
        )"""
    )
    applied = {int(row[0]) for row in connection.execute("SELECT version FROM schema_migrations")}
    completed: list[int] = []
    for version, name, sql in MIGRATIONS:
        if version in applied:
            continue
        connection.executescript(sql)
        connection.execute(
            "INSERT INTO schema_migrations(version, name, applied_at) VALUES(?,?,?)",
            (version, name, datetime.now(timezone.utc).isoformat()),
        )
        completed.append(version)
    return completed

