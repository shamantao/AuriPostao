#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
VENV_DIR="${ROOT_DIR}/.venv"

if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi

source "${VENV_DIR}/bin/activate"
pip install -r "${ROOT_DIR}/core/api/requirements.txt" >/dev/null

mkdir -p "${ROOT_DIR}/core/data"
export AURIPOSTAO_DB_PATH="${ROOT_DIR}/core/data/auripostao.db"

uvicorn core.api.main:app --host 127.0.0.1 --port 8787
