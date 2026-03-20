#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Avoid reusing a stale uvicorn instance that may expose an older API schema.
if command -v lsof >/dev/null 2>&1; then
	PIDS="$(lsof -tiTCP:8787 -sTCP:LISTEN -n -P || true)"
	if [[ -n "${PIDS}" ]]; then
		echo "Stopping previous local API on port 8787: ${PIDS}"
		kill ${PIDS} || true
		sleep 0.4
	fi
fi

cd "${ROOT_DIR}"
npm run tauri dev