#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TAURI_PID=""
TIMEOUT=20

source "$PROJECT_DIR/scripts/cleanup-dev-ports.sh"

cleanup() {
  if [[ -n "$TAURI_PID" ]] && kill -0 "$TAURI_PID" >/dev/null 2>&1; then
    echo "Stopping Tauri dev server (PID: $TAURI_PID)"
    kill "$TAURI_PID" >/dev/null 2>&1 || true
    wait "$TAURI_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

echo "== Tauri Startup Test =="
echo "Launching: cd $PROJECT_DIR && npm run tauri dev"

cd "$PROJECT_DIR"
cleanup_auripostao_dev_ports

# Start tauri dev in background
npm run tauri dev > /tmp/tauri-startup.log 2>&1 &
TAURI_PID=$!
echo "Tauri process started (PID: $TAURI_PID)"

# Wait for Vite to be ready
echo "Waiting for Vite dev server to be ready (timeout: ${TIMEOUT}s)..."
for i in $(seq 1 "$TIMEOUT"); do
  if curl -fsS http://localhost:5173/ >/dev/null 2>&1; then
    echo "✓ Vite dev server is ready"
    break
  fi
  if ! kill -0 "$TAURI_PID" >/dev/null 2>&1; then
    echo "✗ Tauri process crashed during startup"
    echo "--- Tauri startup log ---"
    cat /tmp/tauri-startup.log
    exit 1
  fi
  if [[ $i -eq "$TIMEOUT" ]]; then
    echo "✗ Timeout waiting for Vite dev server"
    echo "--- Tauri startup log ---"
    tail -50 /tmp/tauri-startup.log
    exit 1
  fi
  sleep 1
done

# Verify no build errors in the log
if grep -iE "error|failed to read|exit status" /tmp/tauri-startup.log; then
  echo "✗ Build errors detected in Tauri startup"
  exit 1
fi

echo "✓ Tauri startup test passed"
