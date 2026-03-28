#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
export CARGO_TARGET_DIR="$PROJECT_DIR/src-tauri/target/test-cache"

echo "== Code Constraints =="
PYTHONWARNINGS="error::ResourceWarning" python3 -m pytest \
  "$PROJECT_DIR/tests/test_code_constraints.py" \
  -q

echo ""
echo "== Fast unit tests =="
cargo test --manifest-path "$PROJECT_DIR/src-tauri/Cargo.toml" --lib --bins --quiet
PYTHONWARNINGS="error::ResourceWarning" \
	python3 -m unittest discover -s "$PROJECT_DIR/tests" -p 'test_*.py' -q