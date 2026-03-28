from __future__ import annotations

import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import HTTPException

from core.api.models import WorkflowOut


APP_VERSION = "0.1.0-epic0"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _api_error(status_code: int, code: str, message: str) -> None:
    raise HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _row_to_workflow(row: sqlite3.Row, channels: list[str] | None = None) -> dict[str, Any]:
    return {
        "id": row["id"],
        "local_user": row["local_user"],
        "name": row["name"],
        "description": row["description"],
        "is_active": bool(row["is_active"]),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "channels": channels if channels is not None else [],
    }


def _enabled_channels(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT channel_name FROM channel_configs WHERE is_enabled = 1 ORDER BY channel_name"
    ).fetchall()
    return [str(row["channel_name"]) for row in rows]


def _has_valid_channel(conn: sqlite3.Connection) -> bool:
    row = conn.execute(
        "SELECT COUNT(1) AS total FROM channel_configs WHERE is_enabled = 1"
    ).fetchone()
    return bool(row["total"])


def _workflow_exists(conn: sqlite3.Connection, workflow_id: int) -> bool:
    return (
        conn.execute("SELECT 1 FROM workflows WHERE id = ?", (workflow_id,)).fetchone() is not None
    )


def init_db(db_path: str) -> int:
    """Create/update local SQLite schema and return current migration version."""
    db_file = Path(db_path)
    db_file.parent.mkdir(parents=True, exist_ok=True)

    with closing(sqlite3.connect(db_file)) as conn:
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

        migration_v2_applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version = 2"
        ).fetchone()

        if not migration_v2_applied:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS channel_configs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    channel_name TEXT NOT NULL UNIQUE,
                    is_enabled INTEGER NOT NULL DEFAULT 0 CHECK (is_enabled IN (0, 1)),
                    config_json TEXT NOT NULL DEFAULT '{}',
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                INSERT OR IGNORE INTO channel_configs(channel_name, is_enabled, config_json, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                ("dummy", 0, "{}", _utc_now()),
            )
            conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (2, _utc_now()),
            )

        migration_v3_applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version = 3"
        ).fetchone()

        if not migration_v3_applied:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_channels (
                    workflow_id INTEGER NOT NULL,
                    channel_name TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (workflow_id, channel_name),
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE,
                    FOREIGN KEY (channel_name) REFERENCES channel_configs(channel_name) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (3, _utc_now()),
            )

        migration_v4_applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version = 4"
        ).fetchone()

        if not migration_v4_applied:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_source_configs (
                    workflow_id INTEGER PRIMARY KEY,
                    file_paths_json TEXT NOT NULL DEFAULT '[]',
                    directory_path TEXT,
                    recursive INTEGER NOT NULL DEFAULT 0 CHECK (recursive IN (0, 1)),
                    max_file_size_bytes INTEGER NOT NULL DEFAULT 1000000,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (4, _utc_now()),
            )

        migration_v5_applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version = 5"
        ).fetchone()

        if not migration_v5_applied:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_ai_configs (
                    workflow_id INTEGER PRIMARY KEY,
                    provider TEXT NOT NULL DEFAULT 'ollama',
                    base_url TEXT NOT NULL DEFAULT 'http://localhost:11434',
                    model TEXT NOT NULL DEFAULT 'llama3.2',
                    timeout_seconds INTEGER NOT NULL DEFAULT 30,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (5, _utc_now()),
            )

        migration_v6_applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version = 6"
        ).fetchone()

        if not migration_v6_applied:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_voice_criteria (
                    workflow_id INTEGER PRIMARY KEY,
                    preset TEXT NOT NULL DEFAULT 'professional_concise',
                    custom_instructions TEXT NOT NULL DEFAULT '',
                    min_length INTEGER NOT NULL DEFAULT 100,
                    max_length INTEGER NOT NULL DEFAULT 500,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (6, _utc_now()),
            )

        migration_v7_applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version = 7"
        ).fetchone()

        if not migration_v7_applied:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_schedules (
                    workflow_id INTEGER PRIMARY KEY,
                    schedule_type TEXT NOT NULL DEFAULT 'none',
                    timezone TEXT NOT NULL DEFAULT 'UTC',
                    run_at TEXT,
                    times_json TEXT NOT NULL DEFAULT '[]',
                    weekdays_json TEXT NOT NULL DEFAULT '[]',
                    monthdays_json TEXT NOT NULL DEFAULT '[]',
                    catchup_enabled INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS schedule_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id INTEGER NOT NULL,
                    slot_iso TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TEXT NOT NULL,
                    UNIQUE(workflow_id, slot_iso),
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (7, _utc_now()),
            )

        migration_v8_applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version = 8"
        ).fetchone()

        if not migration_v8_applied:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS forbidden_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    word TEXT NOT NULL UNIQUE COLLATE NOCASE,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_forbidden_words (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id INTEGER NOT NULL,
                    word TEXT NOT NULL COLLATE NOCASE,
                    action TEXT NOT NULL DEFAULT 'add' CHECK (action IN ('add', 'remove')),
                    created_at TEXT NOT NULL,
                    UNIQUE(workflow_id, word),
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS workflow_drafts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    workflow_id INTEGER NOT NULL,
                    slot_iso TEXT,
                    journal TEXT NOT NULL DEFAULT '',
                    post TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL DEFAULT 'pending_approval'
                        CHECK (status IN ('pending_approval','approved','rejected','abandoned','blocked_confidentiality')),
                    forbidden_words_matched TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (workflow_id) REFERENCES workflows(id) ON DELETE CASCADE
                )
                """
            )
            conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (8, _utc_now()),
            )

        migration_v9_applied = conn.execute(
            "SELECT 1 FROM schema_migrations WHERE version = 9"
        ).fetchone()

        if not migration_v9_applied:
            conn.execute(
                "ALTER TABLE workflow_schedules ADD COLUMN require_approval INTEGER NOT NULL DEFAULT 0"
            )
            conn.execute(
                "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                (9, _utc_now()),
            )

        current_version = conn.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        ).fetchone()[0]
        conn.commit()

    return int(current_version)
