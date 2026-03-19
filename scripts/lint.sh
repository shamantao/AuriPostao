#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "== Lint =="
cargo fmt --manifest-path "$PROJECT_DIR/src-tauri/Cargo.toml" --all -- --check