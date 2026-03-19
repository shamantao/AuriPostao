#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "== Fast unit tests =="
cargo test --manifest-path "$PROJECT_DIR/src-tauri/Cargo.toml" --lib --bins --quiet
python3 -m unittest discover -s "$PROJECT_DIR/tests" -p 'test_*.py' -q