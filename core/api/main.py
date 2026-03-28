from __future__ import annotations

import os
import sqlite3
import urllib.request  # noqa: F401 — tests patch "core.api.main.urllib.request.urlopen"
from contextlib import contextmanager
from typing import Generator

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from core.api.database import APP_VERSION, init_db

DB_PATH = os.getenv("AURIPOSTAO_DB_PATH", "./core/data/auripostao.db")

app = FastAPI(title="AuriPostao Local API", version=APP_VERSION)


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


# ---------------------------------------------------------------------------
# Include routers (after _connect is defined — route modules import it lazily)
# ---------------------------------------------------------------------------
from core.api.routes_workflows import router as _wf_router  # noqa: E402
from core.api.routes_generation import router as _gen_router  # noqa: E402

app.include_router(_wf_router)
app.include_router(_gen_router)


@app.on_event("startup")
def startup() -> None:
    init_db(DB_PATH)


# ---------------------------------------------------------------------------
# Backward-compat re-exports (tests use `import core.api.main as api_main`)
# ---------------------------------------------------------------------------
from core.api.ai_provider import _call_ai_provider, _call_openai_compat  # noqa: E402, F401
from core.api.scheduling import _compute_next_slots  # noqa: E402, F401
from core.api.models import WorkflowForbiddenWordEntry  # noqa: E402, F401
from core.api.confidentiality import (  # noqa: E402, F401
    _check_confidentiality,
    _save_draft,
    _set_global_forbidden_words,
    _set_workflow_forbidden_words,
)

