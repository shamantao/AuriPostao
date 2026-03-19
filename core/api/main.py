from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


APP_VERSION = "0.1.0-epic0"
DB_PATH = os.getenv("AURIPOSTAO_DB_PATH", "./core/data/auripostao.db")

app = FastAPI(title="AuriPostao Local API", version=APP_VERSION)


class WorkflowCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    is_active: bool = True
    channels: list[str] = Field(min_length=1)


class WorkflowUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    is_active: bool | None = None


class WorkflowOut(BaseModel):
    id: int
    local_user: str
    name: str
    description: str
    is_active: bool
    created_at: str
    updated_at: str
    channels: list[str] = []


class WorkflowChannelsUpdate(BaseModel):
    channels: list[str] = Field(min_length=1)


class ChannelDummyUpdate(BaseModel):
    enabled: bool


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _api_error(status_code: int, code: str, message: str) -> None:
    raise HTTPException(status_code=status_code, detail={"code": code, "message": message})


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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


@app.exception_handler(HTTPException)
async def handle_http_exception(_: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    if isinstance(detail, dict) and "code" in detail and "message" in detail:
        payload = detail
    else:
        payload = {"code": "http_error", "message": str(detail)}
    return JSONResponse(status_code=exc.status_code, content=payload)


@app.exception_handler(RequestValidationError)
async def handle_validation_exception(_: Request, exc: RequestValidationError) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {"loc": ["body"], "msg": "invalid payload"}
    path = ".".join(str(part) for part in first.get("loc", []))
    message = f"{path}: {first.get('msg', 'invalid payload')}"
    return JSONResponse(
        status_code=422,
        content={"code": "validation_error", "message": message},
    )


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


@app.get("/channels/status")
def channels_status() -> dict[str, Any]:
    with _connect() as conn:
        valid_channels = _enabled_channels(conn)
    return {
        "has_valid_channel": len(valid_channels) > 0,
        "valid_channels": valid_channels,
        "config_url": "#channels-config",
    }


@app.put("/channels/dummy")
def set_dummy_channel(payload: ChannelDummyUpdate) -> dict[str, Any]:
    now = _utc_now()
    with _connect() as conn:
        conn.execute(
            """
            INSERT INTO channel_configs(channel_name, is_enabled, config_json, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(channel_name)
            DO UPDATE SET is_enabled = excluded.is_enabled, updated_at = excluded.updated_at
            """,
            ("dummy", int(payload.enabled), "{}", now),
        )
        valid_channels = _enabled_channels(conn)

    return {
        "has_valid_channel": len(valid_channels) > 0,
        "valid_channels": valid_channels,
        "config_url": "#channels-config",
    }


@app.get("/workflows")
def list_workflows() -> dict[str, list[WorkflowOut]]:
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT id, local_user, name, description, is_active, created_at, updated_at
            FROM workflows
            ORDER BY updated_at DESC, id DESC
            """
        ).fetchall()
        ch_rows = conn.execute(
            "SELECT workflow_id, channel_name FROM workflow_channels ORDER BY channel_name"
        ).fetchall()
    channels_map: dict[int, list[str]] = {}
    for ch in ch_rows:
        channels_map.setdefault(ch["workflow_id"], []).append(ch["channel_name"])
    return {"items": [_row_to_workflow(r, channels_map.get(r["id"], [])) for r in rows]}


@app.post("/workflows", status_code=201)
def create_workflow(payload: WorkflowCreate) -> WorkflowOut:
    name = payload.name.strip()
    if not name:
        _api_error(422, "validation_error", "name is required")

    now = _utc_now()
    try:
        with _connect() as conn:
            if not _has_valid_channel(conn):
                _api_error(
                    403,
                    "no_valid_channel",
                    "configure at least one valid channel before creating a workflow",
                )
            for ch in payload.channels:
                if not conn.execute(
                    "SELECT 1 FROM channel_configs WHERE channel_name = ?", (ch,)
                ).fetchone():
                    _api_error(422, "channel_not_found", f"channel '{ch}' does not exist")
            cursor = conn.execute(
                """
                INSERT INTO workflows(local_user, name, description, is_active, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                ("local", name, payload.description, int(payload.is_active), now, now),
            )
            workflow_id = cursor.lastrowid
            for ch in payload.channels:
                conn.execute(
                    "INSERT INTO workflow_channels(workflow_id, channel_name, created_at) VALUES (?, ?, ?)",
                    (workflow_id, ch, now),
                )
            row = conn.execute(
                """
                SELECT id, local_user, name, description, is_active, created_at, updated_at
                FROM workflows WHERE id = ?
                """,
                (workflow_id,),
            ).fetchone()
    except sqlite3.IntegrityError as exc:
        if "UNIQUE constraint failed: workflows.local_user, workflows.name" in str(exc):
            _api_error(409, "workflow_name_conflict", "workflow name already exists for local user")
        _api_error(400, "db_integrity_error", str(exc))

    return _row_to_workflow(row, list(payload.channels))


@app.put("/workflows/{workflow_id}")
def update_workflow(workflow_id: int, payload: WorkflowUpdate) -> WorkflowOut:
    with _connect() as conn:
        existing = conn.execute(
            """
            SELECT id, local_user, name, description, is_active, created_at, updated_at
            FROM workflows WHERE id = ?
            """,
            (workflow_id,),
        ).fetchone()
        if existing is None:
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")

        new_name = existing["name"] if payload.name is None else payload.name.strip()
        if not new_name:
            _api_error(422, "validation_error", "name cannot be empty")

        new_description = existing["description"] if payload.description is None else payload.description
        new_is_active = existing["is_active"] if payload.is_active is None else int(payload.is_active)
        now = _utc_now()

        try:
            conn.execute(
                """
                UPDATE workflows
                SET name = ?, description = ?, is_active = ?, updated_at = ?
                WHERE id = ?
                """,
                (new_name, new_description, new_is_active, now, workflow_id),
            )
        except sqlite3.IntegrityError as exc:
            if "UNIQUE constraint failed: workflows.local_user, workflows.name" in str(exc):
                _api_error(409, "workflow_name_conflict", "workflow name already exists for local user")
            _api_error(400, "db_integrity_error", str(exc))

        row = conn.execute(
            """
            SELECT id, local_user, name, description, is_active, created_at, updated_at
            FROM workflows WHERE id = ?
            """,
            (workflow_id,),
        ).fetchone()

    return _row_to_workflow(row)


@app.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: int) -> dict[str, Any]:
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
    if cursor.rowcount == 0:
        _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
    return {"deleted": True, "id": workflow_id}


@app.get("/workflows/{workflow_id}/channels")
def get_workflow_channels(workflow_id: int) -> dict[str, list[str]]:
    with _connect() as conn:
        if conn.execute("SELECT 1 FROM workflows WHERE id = ?", (workflow_id,)).fetchone() is None:
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        rows = conn.execute(
            "SELECT channel_name FROM workflow_channels WHERE workflow_id = ? ORDER BY channel_name",
            (workflow_id,),
        ).fetchall()
    return {"channels": [r["channel_name"] for r in rows]}


@app.put("/workflows/{workflow_id}/channels")
def set_workflow_channels(workflow_id: int, payload: WorkflowChannelsUpdate) -> dict[str, list[str]]:
    with _connect() as conn:
        if conn.execute("SELECT 1 FROM workflows WHERE id = ?", (workflow_id,)).fetchone() is None:
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        for ch in payload.channels:
            if not conn.execute(
                "SELECT 1 FROM channel_configs WHERE channel_name = ?", (ch,)
            ).fetchone():
                _api_error(422, "channel_not_found", f"channel '{ch}' does not exist")
        now = _utc_now()
        conn.execute("DELETE FROM workflow_channels WHERE workflow_id = ?", (workflow_id,))
        for ch in payload.channels:
            conn.execute(
                "INSERT INTO workflow_channels(workflow_id, channel_name, created_at) VALUES (?, ?, ?)",
                (workflow_id, ch, now),
            )
        rows = conn.execute(
            "SELECT channel_name FROM workflow_channels WHERE workflow_id = ? ORDER BY channel_name",
            (workflow_id,),
        ).fetchall()
    return {"channels": [r["channel_name"] for r in rows]}
