from __future__ import annotations

import json
import os
import sqlite3
import urllib.error
import urllib.request
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Generator


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


class IngestionPreviewRequest(BaseModel):
    file_paths: list[str] = []
    directory_path: str | None = None
    recursive: bool = False
    max_file_size_bytes: int = Field(default=1_000_000, ge=1)


class WorkflowSourcesUpdate(BaseModel):
    file_paths: list[str] = []
    directory_path: str | None = None
    recursive: bool = False
    max_file_size_bytes: int = Field(default=1_000_000, ge=1)


# ---------------------------------------------------------------------------
# US-3.1 — AI adapter
# ---------------------------------------------------------------------------

VOICE_PRESETS: dict[str, str] = {
    "professional_concise": "Write in a clear, professional tone. Be concise and factual.",
    "professional_detailed": "Write in a professional, thorough tone. Include context and nuance.",
    "casual": "Write in a friendly, conversational tone. Natural and warm.",
    "storytelling": "Write as an engaging narrative. Use vivid, concrete language.",
    "technical": "Write for a technical audience. Be precise and use correct terminology.",
}


class AIConfigUpdate(BaseModel):
    provider: str = Field(default="ollama", pattern="^(ollama|openai_compat)$")
    base_url: str = Field(default="http://localhost:11434")
    model: str = Field(default="llama3.2", min_length=1)
    timeout_seconds: int = Field(default=30, ge=5, le=300)


# ---------------------------------------------------------------------------
# US-3.2 — Voice criteria
# ---------------------------------------------------------------------------


class VoiceCriteriaUpdate(BaseModel):
    preset: str = Field(default="professional_concise")
    custom_instructions: str = ""
    min_length: int = Field(default=100, ge=10, le=2000)
    max_length: int = Field(default=500, ge=50, le=5000)


TEXT_EXTENSIONS = {".txt", ".md"}


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _api_error(status_code: int, code: str, message: str) -> None:
    raise HTTPException(status_code=status_code, detail={"code": code, "message": message})


@contextmanager
def _connect() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


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


def _decode_text(data: bytes) -> tuple[str, str]:
    try:
        return data.decode("utf-8"), "utf-8"
    except UnicodeDecodeError:
        # MVP fallback for legacy local files.
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


def _workflow_exists(conn: sqlite3.Connection, workflow_id: int) -> bool:
    return (
        conn.execute("SELECT 1 FROM workflows WHERE id = ?", (workflow_id,)).fetchone() is not None
    )


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


# ---------------------------------------------------------------------------
# US-3.1 — AI config helpers
# ---------------------------------------------------------------------------

def _get_ai_config(conn: sqlite3.Connection, workflow_id: int) -> dict[str, Any]:
    row = conn.execute(
        "SELECT provider, base_url, model, timeout_seconds FROM workflow_ai_configs WHERE workflow_id = ?",
        (workflow_id,),
    ).fetchone()
    if row is None:
        return {
            "workflow_id": workflow_id,
            "provider": "ollama",
            "base_url": "http://localhost:11434",
            "model": "llama3.2",
            "timeout_seconds": 30,
        }
    return {
        "workflow_id": workflow_id,
        "provider": row["provider"],
        "base_url": row["base_url"],
        "model": row["model"],
        "timeout_seconds": row["timeout_seconds"],
    }


def _set_ai_config(conn: sqlite3.Connection, workflow_id: int, payload: AIConfigUpdate) -> dict[str, Any]:
    now = _utc_now()
    conn.execute(
        """
        INSERT INTO workflow_ai_configs(workflow_id, provider, base_url, model, timeout_seconds, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(workflow_id)
        DO UPDATE SET
            provider = excluded.provider,
            base_url = excluded.base_url,
            model = excluded.model,
            timeout_seconds = excluded.timeout_seconds,
            updated_at = excluded.updated_at
        """,
        (workflow_id, payload.provider, payload.base_url.strip(), payload.model.strip(), payload.timeout_seconds, now),
    )
    return {
        "workflow_id": workflow_id,
        "provider": payload.provider,
        "base_url": payload.base_url.strip(),
        "model": payload.model.strip(),
        "timeout_seconds": payload.timeout_seconds,
    }


# ---------------------------------------------------------------------------
# US-3.2 — Voice criteria helpers
# ---------------------------------------------------------------------------

def _get_voice_criteria(conn: sqlite3.Connection, workflow_id: int) -> dict[str, Any]:
    row = conn.execute(
        "SELECT preset, custom_instructions, min_length, max_length FROM workflow_voice_criteria WHERE workflow_id = ?",
        (workflow_id,),
    ).fetchone()
    if row is None:
        return {
            "workflow_id": workflow_id,
            "preset": "professional_concise",
            "custom_instructions": "",
            "min_length": 100,
            "max_length": 500,
        }
    return {
        "workflow_id": workflow_id,
        "preset": row["preset"],
        "custom_instructions": row["custom_instructions"] or "",
        "min_length": row["min_length"],
        "max_length": row["max_length"],
    }


def _set_voice_criteria(conn: sqlite3.Connection, workflow_id: int, payload: VoiceCriteriaUpdate) -> dict[str, Any]:
    if payload.preset not in VOICE_PRESETS and payload.preset != "custom":
        _api_error(422, "invalid_preset", f"preset must be one of: {', '.join(VOICE_PRESETS)} or 'custom'")
    if payload.min_length >= payload.max_length:
        _api_error(422, "invalid_length", "min_length must be less than max_length")
    now = _utc_now()
    conn.execute(
        """
        INSERT INTO workflow_voice_criteria(workflow_id, preset, custom_instructions, min_length, max_length, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(workflow_id)
        DO UPDATE SET
            preset = excluded.preset,
            custom_instructions = excluded.custom_instructions,
            min_length = excluded.min_length,
            max_length = excluded.max_length,
            updated_at = excluded.updated_at
        """,
        (workflow_id, payload.preset, payload.custom_instructions, payload.min_length, payload.max_length, now),
    )
    return {
        "workflow_id": workflow_id,
        "preset": payload.preset,
        "custom_instructions": payload.custom_instructions,
        "min_length": payload.min_length,
        "max_length": payload.max_length,
    }


# ---------------------------------------------------------------------------
# US-3.1 — AI provider adapter
# ---------------------------------------------------------------------------

def _call_ollama(base_url: str, model: str, prompt: str, timeout: int) -> str:
    url = base_url.rstrip("/") + "/api/generate"
    data = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read())
    return str(result.get("response", ""))


def _call_openai_compat(base_url: str, model: str, prompt: str, timeout: int) -> str:
    url = base_url.rstrip("/") + "/v1/chat/completions"
    data = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read())
    return str(result["choices"][0]["message"]["content"])


def _call_ai_provider(
    provider: str, base_url: str, model: str, prompt: str, timeout: int
) -> tuple[str | None, str | None, str | None]:
    """Call AI provider. Returns (response_text, error_type, error_message).
    error_type is None on success, 'transient' or 'permanent' on failure."""
    try:
        if provider == "openai_compat":
            text = _call_openai_compat(base_url, model, prompt, timeout)
        else:
            text = _call_ollama(base_url, model, prompt, timeout)
        return text, None, None
    except TimeoutError:
        return None, "transient", "Request timed out"
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return None, "permanent", f"Authentication failed (HTTP {exc.code})"
        if exc.code == 404:
            return None, "permanent", "Model or endpoint not found (HTTP 404)"
        return None, "transient", f"Provider error (HTTP {exc.code})"
    except urllib.error.URLError as exc:
        return None, "transient", f"Cannot connect to provider: {exc.reason}"
    except (json.JSONDecodeError, KeyError) as exc:
        return None, "permanent", f"Invalid response from provider: {exc}"
    except Exception as exc:
        return None, "transient", f"Unexpected error: {exc}"


def _build_prompt(criteria: dict[str, Any], content_summary: str) -> str:
    preset = criteria.get("preset", "professional_concise")
    if preset == "custom" and criteria.get("custom_instructions"):
        style_desc = criteria["custom_instructions"]
    else:
        style_desc = VOICE_PRESETS.get(preset, VOICE_PRESETS["professional_concise"])
    min_len = criteria.get("min_length", 100)
    max_len = criteria.get("max_length", 500)
    return (
        "You are an editorial assistant generating two outputs from source content.\n\n"
        f"Voice style: {style_desc}\n"
        f"Length: between {min_len} and {max_len} words per output.\n\n"
        "Source content:\n"
        f"{content_summary}\n\n"
        "Generate:\n"
        "1. JOURNAL — a private, detailed, reflective entry\n"
        "2. POST — a public-facing message in the voice style above\n\n"
        'Respond ONLY with valid JSON in this exact format: {"journal": "...", "post": "..."}'
    )


def _parse_generation_response(text: str) -> tuple[str | None, str | None, str | None, str | None]:
    """Extract journal and post from model response.
    Returns (journal, post, error_type, error_message)."""
    text = text.strip()
    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[1:end]).strip()
    try:
        data = json.loads(text)
        journal = str(data.get("journal", "")).strip()
        post = str(data.get("post", "")).strip()
        if not journal or not post:
            return None, None, "permanent", "Model returned empty journal or post"
        return journal, post, None, None
    except (json.JSONDecodeError, KeyError) as exc:
        return None, None, "permanent", f"Could not parse model output as JSON: {exc}"


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


@app.post("/ingestion/preview")
def ingestion_preview(payload: IngestionPreviewRequest) -> dict[str, Any]:
    return _ingestion_preview(payload)


@app.get("/workflows/{workflow_id}/sources")
def get_workflow_sources(workflow_id: int) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        return _get_workflow_sources(conn, workflow_id)


@app.put("/workflows/{workflow_id}/sources")
def set_workflow_sources(workflow_id: int, payload: WorkflowSourcesUpdate) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        return _set_workflow_sources(conn, workflow_id, payload)


@app.post("/workflows/{workflow_id}/ingestion/preview")
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


# ---------------------------------------------------------------------------
# US-3.1 — AI config endpoints
# ---------------------------------------------------------------------------


@app.get("/workflows/{workflow_id}/ai-config")
def get_ai_config(workflow_id: int) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        return _get_ai_config(conn, workflow_id)


@app.put("/workflows/{workflow_id}/ai-config")
def set_ai_config(workflow_id: int, payload: AIConfigUpdate) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        return _set_ai_config(conn, workflow_id, payload)


# ---------------------------------------------------------------------------
# US-3.2 — Voice criteria endpoints
# ---------------------------------------------------------------------------


@app.get("/workflows/{workflow_id}/voice-criteria")
def get_voice_criteria(workflow_id: int) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        return _get_voice_criteria(conn, workflow_id)


@app.put("/workflows/{workflow_id}/voice-criteria")
def set_voice_criteria(workflow_id: int, payload: VoiceCriteriaUpdate) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        return _set_voice_criteria(conn, workflow_id, payload)


# ---------------------------------------------------------------------------
# US-3.1 — Generation endpoint
# ---------------------------------------------------------------------------


@app.post("/workflows/{workflow_id}/generate")
def generate(workflow_id: int) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        ai_config = _get_ai_config(conn, workflow_id)
        voice_criteria = _get_voice_criteria(conn, workflow_id)
        sources = _get_workflow_sources(conn, workflow_id)

    ingestion = _ingestion_preview(IngestionPreviewRequest(
        file_paths=sources["file_paths"],
        directory_path=sources["directory_path"],
        recursive=bool(sources["recursive"]),
        max_file_size_bytes=int(sources["max_file_size_bytes"]),
    ))

    accepted = ingestion["accepted_files"]
    if not accepted:
        content_summary = "(no source content available)"
    else:
        parts = [f"--- {Path(f['path']).name} ---\n{f['preview']}" for f in accepted[:10]]
        content_summary = "\n\n".join(parts)

    prompt = _build_prompt(voice_criteria, content_summary)

    response_text, err_type, err_msg = _call_ai_provider(
        provider=ai_config["provider"],
        base_url=ai_config["base_url"],
        model=ai_config["model"],
        prompt=prompt,
        timeout=ai_config["timeout_seconds"],
    )

    if err_type is not None:
        return {
            "workflow_id": workflow_id,
            "journal": None,
            "post": None,
            "provider": ai_config["provider"],
            "model": ai_config["model"],
            "error_type": err_type,
            "error_message": err_msg,
        }

    journal, post, parse_err_type, parse_err_msg = _parse_generation_response(response_text)
    return {
        "workflow_id": workflow_id,
        "journal": journal,
        "post": post,
        "provider": ai_config["provider"],
        "model": ai_config["model"],
        "error_type": parse_err_type,
        "error_message": parse_err_msg,
    }

