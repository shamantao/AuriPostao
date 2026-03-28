from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from core.api.database import _api_error, _utc_now
from core.api.models import ScheduleUpdate


def _is_valid_timezone(tz_name: str) -> bool:
    try:
        ZoneInfo(tz_name)
        return True
    except (ZoneInfoNotFoundError, KeyError):
        return False


def _parse_hm_pairs(times: list[str]) -> list[tuple[int, int]]:
    """Parse ['HH:MM', ...] into (hour, minute) tuples, skip malformed entries."""
    pairs: list[tuple[int, int]] = []
    for t in times:
        try:
            parts = t.split(":")
            h, m = int(parts[0]), int(parts[1])
            if 0 <= h <= 23 and 0 <= m <= 59:
                pairs.append((h, m))
        except (ValueError, IndexError):
            continue
    return pairs


def _get_schedule(conn: sqlite3.Connection, workflow_id: int) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT schedule_type, timezone, run_at, times_json, weekdays_json, monthdays_json,
               catchup_enabled, require_approval
        FROM workflow_schedules WHERE workflow_id = ?
        """,
        (workflow_id,),
    ).fetchone()
    if row is None:
        return {
            "workflow_id": workflow_id,
            "schedule_type": "none",
            "timezone": "UTC",
            "run_at": None,
            "times": [],
            "weekdays": [],
            "monthdays": [],
            "catchup_enabled": False,
            "require_approval": False,
        }
    try:
        times = json.loads(row["times_json"])
        if not isinstance(times, list):
            times = []
    except (json.JSONDecodeError, TypeError):
        times = []
    try:
        weekdays = json.loads(row["weekdays_json"])
        if not isinstance(weekdays, list):
            weekdays = []
    except (json.JSONDecodeError, TypeError):
        weekdays = []
    try:
        monthdays = json.loads(row["monthdays_json"])
        if not isinstance(monthdays, list):
            monthdays = []
    except (json.JSONDecodeError, TypeError):
        monthdays = []
    return {
        "workflow_id": workflow_id,
        "schedule_type": row["schedule_type"],
        "timezone": row["timezone"],
        "run_at": row["run_at"],
        "times": times,
        "weekdays": weekdays,
        "monthdays": monthdays,
        "catchup_enabled": bool(row["catchup_enabled"]),
        "require_approval": bool(row["require_approval"]),
    }


def _set_schedule(
    conn: sqlite3.Connection, workflow_id: int, payload: ScheduleUpdate
) -> dict[str, Any]:
    if not _is_valid_timezone(payload.timezone):
        _api_error(422, "invalid_timezone", f"Unknown timezone: {payload.timezone}")
    for t in payload.times:
        parts = t.split(":")
        try:
            if len(parts) != 2:
                raise ValueError
            h, m = int(parts[0]), int(parts[1])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError
        except ValueError:
            _api_error(422, "invalid_time_format", f"times must be 'HH:MM' (00-23:00-59), got: {t}")
    for wd in payload.weekdays:
        if not (0 <= wd <= 6):
            _api_error(422, "invalid_weekday", f"weekdays must be 0-6 (Mon-Sun), got: {wd}")
    for md in payload.monthdays:
        if not (1 <= md <= 31):
            _api_error(422, "invalid_monthday", f"monthdays must be 1-31, got: {md}")
    if payload.schedule_type == "one_shot":
        if not payload.run_at:
            _api_error(422, "missing_run_at", "run_at is required for one_shot schedule type")
        try:
            datetime.fromisoformat(str(payload.run_at))
        except ValueError:
            _api_error(422, "invalid_run_at", f"run_at must be a valid ISO datetime: {payload.run_at}")
    now = _utc_now()
    conn.execute(
        """
        INSERT INTO workflow_schedules(
            workflow_id, schedule_type, timezone, run_at,
            times_json, weekdays_json, monthdays_json, catchup_enabled, require_approval, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(workflow_id)
        DO UPDATE SET
            schedule_type = excluded.schedule_type,
            timezone = excluded.timezone,
            run_at = excluded.run_at,
            times_json = excluded.times_json,
            weekdays_json = excluded.weekdays_json,
            monthdays_json = excluded.monthdays_json,
            catchup_enabled = excluded.catchup_enabled,
            require_approval = excluded.require_approval,
            updated_at = excluded.updated_at
        """,
        (
            workflow_id,
            payload.schedule_type,
            payload.timezone,
            payload.run_at,
            json.dumps(payload.times),
            json.dumps(payload.weekdays),
            json.dumps(payload.monthdays),
            int(payload.catchup_enabled),
            int(payload.require_approval),
            now,
        ),
    )
    return {
        "workflow_id": workflow_id,
        "schedule_type": payload.schedule_type,
        "timezone": payload.timezone,
        "run_at": payload.run_at,
        "times": payload.times,
        "weekdays": payload.weekdays,
        "monthdays": payload.monthdays,
        "catchup_enabled": payload.catchup_enabled,
        "require_approval": payload.require_approval,
    }


def _compute_next_slots(
    schedule: dict[str, Any], from_dt: datetime | None = None, n: int = 5
) -> list[str]:
    """Return the next n UTC ISO slot datetimes strictly after from_dt (defaults to now)."""
    if from_dt is None:
        from_dt = datetime.now(timezone.utc)
    stype = schedule.get("schedule_type", "none")
    if stype == "none":
        return []
    tz_name = schedule.get("timezone", "UTC")
    try:
        tz: Any = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError):
        tz = timezone.utc

    if stype == "one_shot":
        run_at = schedule.get("run_at")
        if not run_at:
            return []
        try:
            dt = datetime.fromisoformat(str(run_at))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=tz)
            dt_utc = dt.astimezone(timezone.utc)
            return [dt_utc.isoformat()] if dt_utc > from_dt else []
        except (ValueError, OverflowError):
            return []

    hm_pairs = _parse_hm_pairs(schedule.get("times", []))
    if not hm_pairs:
        return []
    weekdays: list[int] = [int(w) for w in schedule.get("weekdays", []) if 0 <= int(w) <= 6]
    monthdays: list[int] = [int(d) for d in schedule.get("monthdays", []) if 1 <= int(d) <= 31]

    slots: list[datetime] = []
    local_from = from_dt.astimezone(tz)
    current_date = local_from.date()
    limit_date = current_date + timedelta(days=400)

    while len(slots) < n and current_date <= limit_date:
        include = False
        if stype == "daily":
            include = True
        elif stype == "weekly":
            include = current_date.weekday() in weekdays
        elif stype == "monthly":
            include = current_date.day in monthdays
        if include:
            for h, m in hm_pairs:
                try:
                    local_dt = datetime(
                        current_date.year, current_date.month, current_date.day, h, m, tzinfo=tz
                    )
                    utc_dt = local_dt.astimezone(timezone.utc)
                    if utc_dt > from_dt:
                        slots.append(utc_dt)
                except (ValueError, OverflowError):
                    continue
        current_date += timedelta(days=1)

    slots.sort()
    return [dt.isoformat() for dt in slots[:n]]


def _compute_missed_slots(
    conn: sqlite3.Connection,
    workflow_id: int,
    schedule: dict[str, Any],
    since_dt: datetime,
) -> list[str]:
    """Return slots in (since_dt, now] that haven't been recorded as done/skipped."""
    now = datetime.now(timezone.utc)
    if since_dt >= now:
        return []
    stype = schedule.get("schedule_type", "none")
    if stype == "none":
        return []
    tz_name = schedule.get("timezone", "UTC")
    try:
        tz: Any = ZoneInfo(tz_name)
    except (ZoneInfoNotFoundError, KeyError):
        tz = timezone.utc

    all_slots: list[datetime] = []

    if stype == "one_shot":
        run_at = schedule.get("run_at")
        if run_at:
            try:
                dt = datetime.fromisoformat(str(run_at))
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz)
                dt_utc = dt.astimezone(timezone.utc)
                if since_dt < dt_utc <= now:
                    all_slots.append(dt_utc)
            except (ValueError, OverflowError):
                pass
    else:
        hm_pairs = _parse_hm_pairs(schedule.get("times", []))
        weekdays: list[int] = [int(w) for w in schedule.get("weekdays", []) if 0 <= int(w) <= 6]
        monthdays: list[int] = [int(d) for d in schedule.get("monthdays", []) if 1 <= int(d) <= 31]
        if hm_pairs:
            current_date = since_dt.astimezone(tz).date()
            end_date = now.astimezone(tz).date() + timedelta(days=1)
            while current_date <= end_date:
                include = False
                if stype == "daily":
                    include = True
                elif stype == "weekly":
                    include = current_date.weekday() in weekdays
                elif stype == "monthly":
                    include = current_date.day in monthdays
                if include:
                    for h, m in hm_pairs:
                        try:
                            local_dt = datetime(
                                current_date.year, current_date.month, current_date.day, h, m, tzinfo=tz
                            )
                            utc_dt = local_dt.astimezone(timezone.utc)
                            if since_dt < utc_dt <= now:
                                all_slots.append(utc_dt)
                        except (ValueError, OverflowError):
                            continue
                current_date += timedelta(days=1)

    all_slots.sort()
    all_slot_isos = [dt.isoformat() for dt in all_slots]
    if not all_slot_isos:
        return []
    placeholders = ",".join("?" * len(all_slot_isos))
    executed_rows = conn.execute(
        f"SELECT slot_iso FROM schedule_runs WHERE workflow_id = ? AND slot_iso IN ({placeholders}) AND status IN ('done', 'skipped')",  # noqa: S608
        [workflow_id, *all_slot_isos],
    ).fetchall()
    executed_isos = {row["slot_iso"] for row in executed_rows}
    return [iso for iso in all_slot_isos if iso not in executed_isos]
