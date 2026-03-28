from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from core.api.ai_provider import (
    _build_prompt,
    _get_ai_config,
    _get_voice_criteria,
    _parse_generation_response,
    _set_ai_config,
    _set_voice_criteria,
)
from core.api.confidentiality import (
    _abandon_stale_drafts,
    _check_confidentiality,
    _get_global_forbidden_words,
    _get_workflow_forbidden_words,
    _list_drafts,
    _save_draft,
    _set_global_forbidden_words,
    _set_workflow_forbidden_words,
    _update_draft_status,
)
from core.api.database import _api_error, _workflow_exists
from core.api.ingestion import _get_workflow_sources, _ingestion_preview
from core.api.models import (
    AIConfigUpdate,
    ForbiddenWordsUpdate,
    IngestionPreviewRequest,
    ScheduleRunMark,
    ScheduleUpdate,
    VoiceCriteriaUpdate,
    WorkflowForbiddenWordsUpdate,
)
from core.api.scheduling import (
    _compute_missed_slots,
    _compute_next_slots,
    _get_schedule,
    _set_schedule,
)

router = APIRouter()


@router.get("/workflows/{workflow_id}/ai-config")
def get_ai_config(workflow_id: int) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        return _get_ai_config(conn, workflow_id)


@router.put("/workflows/{workflow_id}/ai-config")
def set_ai_config(workflow_id: int, payload: AIConfigUpdate) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        return _set_ai_config(conn, workflow_id, payload)


@router.get("/workflows/{workflow_id}/voice-criteria")
def get_voice_criteria(workflow_id: int) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        return _get_voice_criteria(conn, workflow_id)


@router.put("/workflows/{workflow_id}/voice-criteria")
def set_voice_criteria(workflow_id: int, payload: VoiceCriteriaUpdate) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        return _set_voice_criteria(conn, workflow_id, payload)


@router.get("/workflows/{workflow_id}/schedule")
def get_schedule(workflow_id: int) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "not_found", f"workflow {workflow_id} not found")
        return _get_schedule(conn, workflow_id)


@router.put("/workflows/{workflow_id}/schedule")
def set_schedule(workflow_id: int, payload: ScheduleUpdate) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "not_found", f"workflow {workflow_id} not found")
        return _set_schedule(conn, workflow_id, payload)


@router.get("/workflows/{workflow_id}/schedule/next-slots")
def get_next_slots(workflow_id: int) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "not_found", f"workflow {workflow_id} not found")
        schedule = _get_schedule(conn, workflow_id)
    next_slots = _compute_next_slots(schedule)
    return {"workflow_id": workflow_id, "next_slots": next_slots}


@router.get("/workflows/{workflow_id}/schedule/missed-slots")
def get_missed_slots(workflow_id: int, since: str | None = None) -> dict[str, Any]:
    """Return missed slots since the given ISO datetime (defaults to 24 h ago)."""
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            if since_dt.tzinfo is None:
                since_dt = since_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            _api_error(422, "invalid_since", f"since must be a valid ISO datetime, got: {since}")
            return {}
    else:
        since_dt = datetime.now(timezone.utc) - timedelta(hours=24)
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "not_found", f"workflow {workflow_id} not found")
        schedule = _get_schedule(conn, workflow_id)
        missed = _compute_missed_slots(conn, workflow_id, schedule, since_dt)
    return {"workflow_id": workflow_id, "missed_slots": missed}


@router.post("/workflows/{workflow_id}/schedule/mark-run")
def mark_schedule_run(workflow_id: int, payload: ScheduleRunMark) -> dict[str, Any]:
    """Record the execution status of a slot to prevent re-execution (dedup)."""
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "not_found", f"workflow {workflow_id} not found")
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            conn.execute(
                "INSERT INTO schedule_runs(workflow_id, slot_iso, status, created_at) VALUES (?, ?, ?, ?)",
                (workflow_id, payload.slot_iso, payload.status, now_iso),
            )
        except sqlite3.IntegrityError:
            _api_error(
                409,
                "slot_already_recorded",
                f"slot {payload.slot_iso} already recorded for workflow {workflow_id}",
            )
    return {"workflow_id": workflow_id, "slot_iso": payload.slot_iso, "status": payload.status}


@router.post("/workflows/{workflow_id}/generate")
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

    import core.api.main as _main
    response_text, err_type, err_msg = _main._call_ai_provider(
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
            "draft_id": None,
        }

    journal, post, parse_err_type, parse_err_msg = _parse_generation_response(response_text)
    if parse_err_type is not None:
        return {
            "workflow_id": workflow_id,
            "journal": journal,
            "post": post,
            "provider": ai_config["provider"],
            "model": ai_config["model"],
            "error_type": parse_err_type,
            "error_message": parse_err_msg,
            "draft_id": None,
        }

    with _connect() as conn:
        schedule = _get_schedule(conn, workflow_id)
        require_approval = bool(schedule.get("require_approval", False))
        matched = _check_confidentiality(journal or "", post or "", conn, workflow_id)
        if matched:
            final_err_type: str | None = "blocked_confidentiality"
            final_err_msg: str | None = f"blocked: {', '.join(matched)}"
            draft_status = "blocked_confidentiality"
        elif require_approval:
            final_err_type = None
            final_err_msg = None
            draft_status = "pending_approval"
        else:
            final_err_type = None
            final_err_msg = None
            draft_status = "approved"
        draft_id = _save_draft(conn, workflow_id, journal or "", post or "", draft_status, matched)

    return {
        "workflow_id": workflow_id,
        "journal": journal,
        "post": post,
        "provider": ai_config["provider"],
        "model": ai_config["model"],
        "error_type": final_err_type,
        "error_message": final_err_msg,
        "draft_id": draft_id,
        "draft_status": draft_status,
        "require_approval": require_approval,
    }


@router.get("/confidentiality/forbidden-words")
def get_global_forbidden_words() -> dict[str, Any]:
    with _connect() as conn:
        words = _get_global_forbidden_words(conn)
    return {"words": words}


@router.put("/confidentiality/forbidden-words")
def set_global_forbidden_words(payload: ForbiddenWordsUpdate) -> dict[str, Any]:
    with _connect() as conn:
        words = _set_global_forbidden_words(conn, payload.words)
    return {"words": words}


@router.get("/workflows/{workflow_id}/forbidden-words")
def get_workflow_forbidden_words(workflow_id: int) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        entries = _get_workflow_forbidden_words(conn, workflow_id)
    return {"workflow_id": workflow_id, "entries": entries}


@router.put("/workflows/{workflow_id}/forbidden-words")
def set_workflow_forbidden_words(
    workflow_id: int, payload: WorkflowForbiddenWordsUpdate
) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        entries = _set_workflow_forbidden_words(conn, workflow_id, payload.entries)
    return {"workflow_id": workflow_id, "entries": entries}


@router.get("/workflows/{workflow_id}/drafts")
def list_drafts(workflow_id: int) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        items = _list_drafts(conn, workflow_id)
    return {"workflow_id": workflow_id, "items": items}


@router.post("/workflows/{workflow_id}/drafts/{draft_id}/approve")
def approve_draft(workflow_id: int, draft_id: int) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        result = _update_draft_status(conn, workflow_id, draft_id, "approved")
    if result is None:
        _api_error(404, "draft_not_found", f"draft {draft_id} not found for workflow {workflow_id}")
    return result  # type: ignore[return-value]


@router.post("/workflows/{workflow_id}/drafts/{draft_id}/reject")
def reject_draft(workflow_id: int, draft_id: int) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        result = _update_draft_status(conn, workflow_id, draft_id, "rejected")
    if result is None:
        _api_error(404, "draft_not_found", f"draft {draft_id} not found for workflow {workflow_id}")
    return result  # type: ignore[return-value]


@router.post("/workflows/{workflow_id}/drafts/abandon-stale")
def abandon_stale_drafts(workflow_id: int) -> dict[str, Any]:
    with _connect() as conn:
        if not _workflow_exists(conn, workflow_id):
            _api_error(404, "workflow_not_found", f"workflow {workflow_id} not found")
        count = _abandon_stale_drafts(conn, workflow_id)
    return {"workflow_id": workflow_id, "abandoned_count": count}


def _connect():
    """Lazy accessor — returns the _connect context manager from main module."""
    import core.api.main as _main
    return _main._connect()
