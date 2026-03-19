#!/usr/bin/env bash
# check-secrets.sh — lightweight secret detection helper.

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PATTERN="(api[_-]?key[[:space:]]*[:=]|secret(_key)?[[:space:]]*[:=]|token[[:space:]]*[:=]|password[[:space:]]*[:=]|BEGIN[[:space:]]+(RSA|EC|OPENSSH|DSA)[[:space:]]+PRIVATE[[:space:]]+KEY)"

echo ""
echo "=== Secret scan ==="
echo ""

if command -v gitleaks >/dev/null 2>&1; then
  echo "Using gitleaks..."
  gitleaks detect \
    --source "$PROJECT_DIR" \
    --config "$PROJECT_DIR/.gitleaks.toml" \
    --no-git
  echo "No secrets detected by gitleaks."
  exit 0
fi

echo "gitleaks not found; using fallback regex scan..."

if command -v rg >/dev/null 2>&1; then
  if rg -n -i \
    "$PATTERN" \
    "$PROJECT_DIR" \
    --glob '!.git/**' \
    --glob '!.venv/**' \
    --glob '!node_modules/**' \
    --glob '!dist/**' \
    --glob '!logs/**' \
    --glob '!.tmp/**' \
    --glob '!reports/**' \
    --glob '!src-tauri/target/**' \
    --glob '!tests/fixtures/**'; then
    echo "Potential secrets detected. Review before commit."
    exit 1
  fi
else
  if grep -RInE \
    "$PATTERN" \
    --exclude-dir=.git \
    --exclude-dir=.venv \
    --exclude-dir=node_modules \
    --exclude-dir=dist \
    --exclude-dir=logs \
    --exclude-dir=.tmp \
    --exclude-dir=reports \
    --exclude-dir=target \
    --exclude-dir=fixtures \
    "$PROJECT_DIR"; then
    echo "Potential secrets detected. Review before commit."
    exit 1
  fi
fi

echo "Fallback scan found no obvious secrets."
