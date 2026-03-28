#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${ROOT_DIR}/scripts/cleanup-dev-ports.sh"
cleanup_auripostao_dev_ports

cd "${ROOT_DIR}"

# Ensure the Python venv + deps are ready (silent if already up to date)
VENV_DIR="${ROOT_DIR}/.venv"
if [[ ! -d "$VENV_DIR" ]]; then
  python3 -m venv "$VENV_DIR"
fi
"${VENV_DIR}/bin/pip" install -q -r "${ROOT_DIR}/core/api/requirements.txt" 2>/dev/null

# Launch Tauri (which auto-spawns the Python API sidecar)
exec npx tauri dev
npm run tauri dev