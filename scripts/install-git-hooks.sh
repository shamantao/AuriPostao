#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"

git -C "$PROJECT_DIR" config core.hooksPath .githooks
chmod +x "$PROJECT_DIR"/.githooks/pre-commit "$PROJECT_DIR"/.githooks/pre-push "$PROJECT_DIR"/scripts/*.sh "$PROJECT_DIR"/core/scripts/*.sh

echo "Git hooks installed from .githooks/"