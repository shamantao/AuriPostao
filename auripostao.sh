#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

source "${ROOT_DIR}/scripts/cleanup-dev-ports.sh"
cleanup_auripostao_dev_ports

cd "${ROOT_DIR}"
npm run tauri dev