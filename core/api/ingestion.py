from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from core.api.database import _api_error, _utc_now
from core.api.models import (
    IngestionPreviewRequest,
    TEXT_EXTENSIONS,
    WorkflowSourcesUpdate,
)


def _decode_text(data: bytes) -> tuple[str, str]:
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        return data.decode("latin-1"), "latin-1"


def _ingestion_preview(payload: IngestionPreviewRequest) -> dict[str, Any]:
    accepted: list[dict[str, Any]] = []
    ignored: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    candidates: list[Path] = []

    for raw in payload.file_paths:
        p = Path(raw).expanduser()
        if not p.exists():
            errors.append({"path": str(p), "reason": "not_found"})
            continue
        if p.is_dir():
            ignored.append({"path": str(p), "reason": "is_directory"})
            continue
        candidates.append(p)

    if payload.directory_path:
        root = Path(payload.directory_path).expanduser()
        if not root.exists():
            errors.append({"path": str(root), "reason": "directory_not_found"})
        elif not root.is_dir():
            errors.append({"path": str(root), "reason": "not_a_directory"})
        else:
            iterator = root.rglob("*") if payload.recursive else root.glob("*")
            for p in iterator:
                if p.is_file():
                    candidates.append(p)

    seen: set[str] = set()
    unique_candidates: list[Path] = []
    for p in candidates:
        key = str(p.resolve()) if p.exists() else str(p)
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(p)

    for p in unique_candidates:
        suffix = p.suffix.lower()
        if suffix not in TEXT_EXTENSIONS:
            ignored.append({"path": str(p), "reason": "non_text_extension"})
            continue
        try:
            size = p.stat().st_size
        except OSError as exc:
            errors.append({"path": str(p), "reason": f"stat_error: {exc}"})
            continue
        if size > payload.max_file_size_bytes:
            ignored.append({"path": str(p), "reason": "file_too_large"})
            continue
        try:
            raw_data = p.read_bytes()
            text, encoding = _decode_text(raw_data)
            accepted.append(
                {
                    "path": str(p),
                    "size_bytes": size,
                    "encoding": encoding,
                    "preview": text[:400],
                }
            )
        except OSError as exc:
            errors.append({"path": str(p), "reason": f"read_error: {exc}"})

    return {
        "accepted_files": accepted,
        "ignored_files": ignored,
        "errors": errors,
        "summary": {
            "accepted": len(accepted),
            "ignored": len(ignored),
            "errors": len(errors),
            "total_candidates": len(unique_candidates),
            "total_size_bytes": sum(item["size_bytes"] for item in accepted),
        },
    }


def _normalize_file_paths(paths: list[str]) -> list[str]:
    unique: list[str] = []
    seen: set[str] = set()
    for raw in paths:
        value = raw.strip()
        if not value:
            continue
        if value in seen:
            continue
        seen.add(value)
        unique.append(value)
    return unique


def _get_workflow_sources(conn: sqlite3.Connection, workflow_id: int) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT file_paths_json, directory_path, recursive, max_file_size_bytes
        FROM workflow_source_configs
        WHERE workflow_id = ?
        """,
        (workflow_id,),
    ).fetchone()
    if row is None:
        return {
            "file_paths": [],
            "directory_path": None,
            "recursive": False,
            "max_file_size_bytes": 1_000_000,
        }

    try:
        file_paths = json.loads(row["file_paths_json"])
        if not isinstance(file_paths, list):
            file_paths = []
    except (json.JSONDecodeError, TypeError):
        file_paths = []

    return {
        "file_paths": _normalize_file_paths([str(v) for v in file_paths]),
        "directory_path": row["directory_path"],
        "recursive": bool(row["recursive"]),
        "max_file_size_bytes": int(row["max_file_size_bytes"]),
    }


def _set_workflow_sources(
    conn: sqlite3.Connection, workflow_id: int, payload: WorkflowSourcesUpdate
) -> dict[str, Any]:
    file_paths = _normalize_file_paths(payload.file_paths)
    directory_path = payload.directory_path.strip() if payload.directory_path else None
    now = _utc_now()
    conn.execute(
        """
        INSERT INTO workflow_source_configs(
            workflow_id, file_paths_json, directory_path, recursive, max_file_size_bytes, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(workflow_id)
        DO UPDATE SET
            file_paths_json = excluded.file_paths_json,
            directory_path = excluded.directory_path,
            recursive = excluded.recursive,
            max_file_size_bytes = excluded.max_file_size_bytes,
            updated_at = excluded.updated_at
        """,
        (
            workflow_id,
            json.dumps(file_paths),
            directory_path,
            int(payload.recursive),
            payload.max_file_size_bytes,
            now,
        ),
    )
    return {
        "file_paths": file_paths,
        "directory_path": directory_path,
        "recursive": payload.recursive,
        "max_file_size_bytes": payload.max_file_size_bytes,
    }
