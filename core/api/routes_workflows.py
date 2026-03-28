from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from core.api.database import (
    APP_VERSION,
    _api_error,
    _enabled_channels,
    _has_valid_channel,
    _row_to_workflow,
    _utc_now,
    _workflow_exists,
)
from core.api.ingestion import (
    _get_workflow_sources,
    _ingestion_preview,
    _set_workflow_sources,
)
from core.api.models import (
    ChannelDummyUpdate,
    IngestionPreviewRequest,
    WorkflowChannelsUpdate,
    WorkflowCreate,
    WorkflowSourcesUpdate,
    WorkflowUpdate,
)

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "service": "auripostao-api",
        "version": APP_VERSION,
        "time_utc": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/bootstrap")
def bootstrap_status() -> dict[str, str]:
    return {
        "api": "connected",
        "db_path": _get_db_path(),
        "mode": os.getenv("AURIPOSTAO_MODE", "debug"),
    }


@router.get("/channels/status")
def channels_status() -> dict[str, Any]:
    with _connect() as conn:
        valid_channels = _enabled_channels(conn)
    return {
        "has_valid_channel": len(valid_channels) > 0,
        "valid_channels": valid_channels,
        "config_url": "#channels-config",
    }


@router.put("/channels/dummy")
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


@router.post("/ingestion/preview")
def ingestion_preview(payload: IngestionPreviewRequest) -> dict[str, Any]:
    return _ingestion_preview(payload)


@router.get("/workflows/{workflow_id}/sources")
def get_workflow_sources(workflow_id: int) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        return _get_workflow_sources(conn, workflow_id)


@router.put("/workflows/{workflow_id}/sources")
def set_workflow_sources(workflow_id: int, payload: WorkflowSourcesUpdate) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        return _set_workflow_sources(conn, workflow_id, payload)


@router.post("/workflows/{workflow_id}/ingestion/preview")
def workflow_ingestion_preview(workflow_id: int) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        sources = _get_workflow_sources(conn, workflow_id)

    payload = IngestionPreviewRequest(
        file_paths=sources["file_paths"],
        directory_path=sources["directory_path"],
        recursive=bool(sources["recursive"]),
        max_file_size_bytes=int(sources["max_file_size_bytes"]),
    )
    return _ingestion_preview(payload)


@router.get("/workflows")
def list_workflows() -> dict[str, list]:
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


@router.post("/workflows", status_code=201)
def create_workflow(payload: WorkflowCreate) -> dict[str, Any]:
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


@router.put("/workflows/{workflow_id}")
def update_workflow(workflow_id: int, payload: WorkflowUpdate) -> dict[str, Any]:
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


@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: int) -> dict[str, Any]:
    with _connect() as conn:
        cursor = conn.execute("DELETE FROM workflows WHERE id = ?", (workflow_id,))
    if cursor.rowcount == 0:
        _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
    return {"deleted": True, "id": workflow_id}


@router.get("/workflows/{workflow_id}/channels")
def get_workflow_channels(workflow_id: int) -> dict[str, list[str]]:
    with _connect() as conn:
        if conn.execute("SELECT 1 FROM workflows WHERE id = ?", (workflow_id,)).fetchone() is None:
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        rows = conn.execute(
            "SELECT channel_name FROM workflow_channels WHERE workflow_id = ? ORDER BY channel_name",
            (workflow_id,),
        ).fetchall()
    return {"channels": [r["channel_name"] for r in rows]}


@router.put("/workflows/{workflow_id}/channels")
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


def _connect():
    """Lazy accessor — returns the _connect context manager from main module."""
    import core.api.main as _main
    return _main._connect()


def _get_db_path() -> str:
    import core.api.main as _main
    return _main.DB_PATH
