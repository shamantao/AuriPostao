#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${1:-http://127.0.0.1:8787}"

printf "Checking %s/health\n" "$BASE_URL"
curl -fsS "${BASE_URL}/health" | cat
printf "\n\nChecking %s/bootstrap\n" "$BASE_URL"
curl -fsS "${BASE_URL}/bootstrap" | cat
printf "\n"
