from __future__ import annotations

import json
import re
import sqlite3
from datetime import datetime, timezone
from typing import Any

from core.api.database import _utc_now
from core.api.models import WorkflowForbiddenWordEntry
from core.api.scheduling import _compute_next_slots, _get_schedule


def _get_global_forbidden_words(conn: sqlite3.Connection) -> list[str]:
    rows = conn.execute(
        "SELECT word FROM forbidden_words ORDER BY word COLLATE NOCASE"
    ).fetchall()
    return [r["word"] for r in rows]


def _set_global_forbidden_words(conn: sqlite3.Connection, words: list[str]) -> list[str]:
    conn.execute("DELETE FROM forbidden_words")
    now = _utc_now()
    seen: set[str] = set()
    for w in words:
        cleaned = w.strip().lower()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            conn.execute(
                "INSERT INTO forbidden_words(word, created_at) VALUES (?, ?)",
                (cleaned, now),
            )
    return _get_global_forbidden_words(conn)


def _get_workflow_forbidden_words(
    conn: sqlite3.Connection, workflow_id: int
) -> list[dict[str, str]]:
    rows = conn.execute(
        "SELECT word, action FROM workflow_forbidden_words WHERE workflow_id = ? ORDER BY word COLLATE NOCASE",
        (workflow_id,),
    ).fetchall()
    return [{"word": r["word"], "action": r["action"]} for r in rows]


def _set_workflow_forbidden_words(
    conn: sqlite3.Connection, workflow_id: int, entries: list[WorkflowForbiddenWordEntry]
) -> list[dict[str, str]]:
    conn.execute(
        "DELETE FROM workflow_forbidden_words WHERE workflow_id = ?", (workflow_id,)
    )
    now = _utc_now()
    seen: set[str] = set()
    for e in entries:
        w = e.word.strip().lower()
        if w and w not in seen:
            seen.add(w)
            conn.execute(
                """
                INSERT INTO workflow_forbidden_words(workflow_id, word, action, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (workflow_id, w, e.action, now),
            )
    return _get_workflow_forbidden_words(conn, workflow_id)


def _check_confidentiality(
    journal: str, post: str, conn: sqlite3.Connection, workflow_id: int
) -> list[str]:
    """Return sorted list of forbidden words found in journal or post (word-boundary match).
    Effective word list = (global + workflow 'add') - workflow 'remove'."""
    effective: set[str] = {w.lower() for w in _get_global_forbidden_words(conn)}
    for entry in _get_workflow_forbidden_words(conn, workflow_id):
        w = entry["word"].lower()
        if entry["action"] == "add":
            effective.add(w)
        elif entry["action"] == "remove":
            effective.discard(w)
    if not effective:
        return []
    text = (journal + " " + post).lower()
    return sorted(w for w in effective if re.search(r"\b" + re.escape(w) + r"\b", text))


def _save_draft(
    conn: sqlite3.Connection,
    workflow_id: int,
    journal: str,
    post: str,
    status: str,
    forbidden_words_matched: list[str],
    slot_iso: str | None = None,
) -> int:
    now = _utc_now()
    cursor = conn.execute(
        """
        INSERT INTO workflow_drafts
            (workflow_id, slot_iso, journal, post, status, forbidden_words_matched, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (workflow_id, slot_iso, journal, post, status, json.dumps(forbidden_words_matched), now, now),
    )
    assert cursor.lastrowid is not None
    return int(cursor.lastrowid)


def _list_drafts(conn: sqlite3.Connection, workflow_id: int) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT id, workflow_id, slot_iso, journal, post, status,
               forbidden_words_matched, created_at, updated_at
        FROM workflow_drafts
        WHERE workflow_id = ?
        ORDER BY created_at DESC
        """,
        (workflow_id,),
    ).fetchall()
    return [
        {
            "id": r["id"],
            "workflow_id": r["workflow_id"],
            "slot_iso": r["slot_iso"],
            "journal": r["journal"],
            "post": r["post"],
            "status": r["status"],
            "forbidden_words_matched": json.loads(r["forbidden_words_matched"] or "[]"),
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]


def _update_draft_status(
    conn: sqlite3.Connection, workflow_id: int, draft_id: int, status: str
) -> dict[str, Any] | None:
    now = _utc_now()
    conn.execute(
        "UPDATE workflow_drafts SET status = ?, updated_at = ? WHERE id = ? AND workflow_id = ?",
        (status, now, draft_id, workflow_id),
    )
    row = conn.execute(
        """
        SELECT id, workflow_id, slot_iso, journal, post, status,
               forbidden_words_matched, created_at, updated_at
        FROM workflow_drafts WHERE id = ? AND workflow_id = ?
        """,
        (draft_id, workflow_id),
    ).fetchone()
    if row is None:
        return None
    return {
        "id": row["id"],
        "workflow_id": row["workflow_id"],
        "slot_iso": row["slot_iso"],
        "journal": row["journal"],
        "post": row["post"],
        "status": row["status"],
        "forbidden_words_matched": json.loads(row["forbidden_words_matched"] or "[]"),
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _abandon_stale_drafts(conn: sqlite3.Connection, workflow_id: int) -> int:
    """Mark pending_approval drafts as abandoned when the next scheduled slot has passed.
    Returns number of drafts abandoned."""
    now = datetime.now(timezone.utc)
    schedule = _get_schedule(conn, workflow_id)
    pending = conn.execute(
        """
        SELECT id, slot_iso, created_at FROM workflow_drafts
        WHERE workflow_id = ? AND status = 'pending_approval'
        """,
        (workflow_id,),
    ).fetchall()
    abandoned_ids: list[int] = []
    for row in pending:
        slot_iso = row["slot_iso"]
        ref_str = slot_iso if slot_iso else row["created_at"]
        try:
            ref_dt = datetime.fromisoformat(ref_str)
            if ref_dt.tzinfo is None:
                ref_dt = ref_dt.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
        next_slots = _compute_next_slots(schedule, from_dt=ref_dt, n=1)
        if next_slots:
            try:
                next_dt = datetime.fromisoformat(next_slots[0])
                if next_dt.tzinfo is None:
                    next_dt = next_dt.replace(tzinfo=timezone.utc)
                if now >= next_dt:
                    abandoned_ids.append(int(row["id"]))
            except ValueError:
                pass
        else:
            if ref_dt < now:
                abandoned_ids.append(int(row["id"]))
    if abandoned_ids:
        placeholders = ",".join("?" * len(abandoned_ids))
        now_iso = now.isoformat()
        conn.execute(
            f"UPDATE workflow_drafts SET status = 'abandoned', updated_at = ? WHERE id IN ({placeholders})",
            [now_iso, *abandoned_ids],
        )
    return len(abandoned_ids)
