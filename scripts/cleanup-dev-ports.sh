#!/usr/bin/env bash
set -euo pipefail

stop_listener_on_port() {
  local port="$1"
  local label="$2"
  local pids=""

  if ! command -v lsof >/dev/null 2>&1; then
    return 0
  fi

  pids="$(lsof -tiTCP:"${port}" -sTCP:LISTEN -n -P || true)"
  if [[ -z "${pids}" ]]; then
    return 0
  fi

  echo "Stopping previous ${label} on port ${port}: ${pids}"
  kill ${pids} >/dev/null 2>&1 || true
  sleep 0.5

  pids="$(lsof -tiTCP:"${port}" -sTCP:LISTEN -n -P || true)"
  if [[ -n "${pids}" ]]; then
    echo "Force stopping previous ${label} on port ${port}: ${pids}"
    kill -9 ${pids} >/dev/null 2>&1 || true
    sleep 0.2
  fi
}

cleanup_auripostao_dev_ports() {
  stop_listener_on_port 8787 "local API"
  stop_listener_on_port 5173 "Vite dev server"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  cleanup_auripostao_dev_ports
fi