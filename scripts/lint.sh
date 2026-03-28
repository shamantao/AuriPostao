#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export CARGO_TARGET_DIR="$PROJECT_DIR/src-tauri/target/test-cache"

echo "== Lint =="
cargo fmt --manifest-path "$PROJECT_DIR/src-tauri/Cargo.toml" --all -- --check