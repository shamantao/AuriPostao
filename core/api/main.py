from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI


APP_VERSION = "0.1.0-epic0"
DB_PATH = os.getenv("AURIPOSTAO_DB_PATH", "./core/data/auripostao.db")

app = FastAPI(title="AuriPostao Local API", version=APP_VERSION)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db(db_path: str) -> int:
    """Create/update local SQLite schema and return current migration version."""
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(db_file) as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version INTEGER PRIMARY KEY,
                applied_at TEXT NOT NULL
            )
            """
        )

        migration_v1_applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version = 1"
        ).fetchone()

        if not migration_v1_applied:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflows (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    local_user TEXT NOT NULL DEFAULT 'local',
                    name TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    is_active INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(local_user, name)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_revisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id INTEGER NOT NULL,
                    revision INTEGER NOT NULL,
                    prompt_private TEXT NOT NULL DEFAULT '',
                    prompt_public TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    FOREIGN KEY(workflow_id) REFERENCES workflows(id) ON DELETE CASCADE,
                    UNIQUE(workflow_id, revision)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    last_run_at TEXT,
                    error_message TEXT,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY(workflow_id) REFERENCES workflows(id) ON DELETE CASCADE,
                    UNIQUE(workflow_id)
                )
                """
            )
            conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (1, _utc_now()),
            )

        current_version = conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        ).fetchone()[0]

    return int(current_version)


@app.on_event("startup")
def startup() -> None:
    init_db(DB_PATH)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "auripostao-api",
        "version": APP_VERSION,
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {
        "api": "connected",
        "db_path": DB_PATH,
        "mode": os.getenv("AURIPOSTAO_MODE", "debug"),
    }
