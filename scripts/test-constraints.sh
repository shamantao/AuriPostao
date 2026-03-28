#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

echo "== Code Constraints Test =="
PYTHONWARNINGS="error::ResourceWarning" python3 -m pytest \
  "$PROJECT_DIR/tests/test_code_constraints.py" \
  -v \
  --tb=short \
  "${@:-}"

echo "✓ All code constraints validated"
