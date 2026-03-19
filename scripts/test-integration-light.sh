#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
BASE_URL="${1:-http://127.0.0.1:8787}"
API_PID=""

cleanup() {
  if [[ -n "$API_PID" ]] && kill -0 "$API_PID" >/dev/null 2>&1; then
    kill "$API_PID" >/dev/null 2>&1 || true
    wait "$API_PID" >/dev/null 2>&1 || true
  fi
}

trap cleanup EXIT

echo "== Light integration =="

if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
  echo "API already running on ${BASE_URL}; reusing it"
else
  echo "Starting local API for integration check"
  bash "$PROJECT_DIR/core/scripts/run_api.sh" > /tmp/auripostao-api.log 2>&1 &
  API_PID=$!

  for _ in $(seq 1 30); do
    if curl -fsS "${BASE_URL}/health" >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi

curl -fsS "${BASE_URL}/health" >/dev/null
bash "$PROJECT_DIR/core/scripts/check_bootstrap.sh" "$BASE_URL" >/dev/null

echo "Light integration checks passed"