from __future__ import annotations

import json
import sqlite3
import time
import urllib.error
import urllib.request
from typing import Any

from core.api.database import _api_error, _utc_now
from core.api.models import AIConfigUpdate, VoiceCriteriaUpdate, VOICE_PRESETS


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


def _call_ollama(base_url: str, model: str, prompt: str, timeout: int) -> str:
    url = base_url.rstrip("/") + "/api/generate"
    data = json.dumps({"model": model, "prompt": prompt, "stream": False}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read())
    return str(result.get("response", ""))


def _call_openai_compat(base_url: str, model: str, prompt: str, timeout: int) -> str:
    base = base_url.rstrip("/")
    if not base.endswith("/v1"):
        base = base + "/v1"
    url = base + "/chat/completions"
    data = json.dumps({"model": model, "messages": [{"role": "user", "content": prompt}]}).encode()
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        result = json.loads(resp.read())
    return str(result["choices"][0]["message"]["content"])


def _call_ai_provider(
    provider: str, base_url: str, model: str, prompt: str, timeout: int
) -> tuple[str | None, str | None, str | None]:
    """Call AI provider with up to 3 attempts on transient errors (5xx, timeout, connection).
    Returns (response_text, error_type, error_message).
    error_type is None on success, 'transient' or 'permanent' on failure."""
    max_attempts = 3
    last_err_type: str | None = None
    last_err_msg: str | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            if provider == "openai_compat":
                text = _call_openai_compat(base_url, model, prompt, timeout)
            else:
                text = _call_ollama(base_url, model, prompt, timeout)
            return text, None, None
        except TimeoutError:
            last_err_type, last_err_msg = "transient", "Request timed out"
        except urllib.error.HTTPError as exc:
            if exc.code in (401, 403):
                return None, "permanent", f"Authentication failed (HTTP {exc.code})"
            if exc.code == 404:
                return None, "permanent", "Model or endpoint not found (HTTP 404)"
            last_err_type, last_err_msg = "transient", f"Provider error (HTTP {exc.code})"
        except urllib.error.URLError as exc:
            last_err_type, last_err_msg = "transient", f"Cannot connect to provider: {exc.reason}"
        except (json.JSONDecodeError, KeyError) as exc:
            return None, "permanent", f"Invalid response from provider: {exc}"
        except Exception as exc:
            last_err_type, last_err_msg = "transient", f"Unexpected error: {exc}"

        if attempt < max_attempts:
            wait = 5 * attempt
            time.sleep(wait)

    return None, last_err_type, last_err_msg


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


def _extract_json_object(text: str) -> str:
    """Find the first top-level JSON object {...} in text, handling nested braces."""
    start = text.find("{")
    if start == -1:
        return text
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return text[start:]


def _parse_generation_response(text: str) -> tuple[str | None, str | None, str | None, str | None]:
    """Extract journal and post from model response.
    Returns (journal, post, error_type, error_message)."""
    text = text.strip()
    # Strip markdown code-block wrappers
    if text.startswith("```"):
        lines = text.split("\n")
        end = len(lines)
        for i in range(len(lines) - 1, 0, -1):
            if lines[i].strip() == "```":
                end = i
                break
        text = "\n".join(lines[1:end]).strip()
    # Try direct parse first, then extract the first JSON object
    for candidate in (text, _extract_json_object(text)):
        try:
            data = json.loads(candidate)
            journal = str(data.get("journal", "")).strip()
            post = str(data.get("post", "")).strip()
            if not journal or not post:
                continue
            return journal, post, None, None
        except (json.JSONDecodeError, KeyError, AttributeError):
            continue
    return None, None, "permanent", f"Could not parse model output as JSON (raw start: {text[:120]!r})"
