from __future__ import annotations

import os
from datetime import datetime, timezone

from fastapi import FastAPI


APP_VERSION = "0.1.0-epic0"
DB_PATH = os.getenv("AURIPOSTAO_DB_PATH", "./core/data/auripostao.db")

app = FastAPI(title="AuriPostao Local API", version=APP_VERSION)


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
