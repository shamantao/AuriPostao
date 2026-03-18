#!/usr/bin/env bash
set -euo pipefail

OWNER="${1:-shamantao}"
REPO="${2:-AuriPostao}"
VISIBILITY="${3:-private}"   # private | public
BACKLOG_FILE="${4:-DOCS/backlog_epic_us_v1.md}"

if [[ "$VISIBILITY" != "private" && "$VISIBILITY" != "public" ]]; then
  echo "ERROR: visibility must be private or public" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI is required." >&2
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "ERROR: current folder is not a git repository." >&2
  exit 1
fi

if ! gh auth status >/dev/null 2>&1; then
  echo "ERROR: GitHub auth is not ready. Run: gh auth login -h github.com" >&2
  exit 1
fi

FULL_REPO="${OWNER}/${REPO}"

# Create remote repository if it does not exist.
if gh repo view "$FULL_REPO" >/dev/null 2>&1; then
  echo "Repository already exists: $FULL_REPO"
else
  gh repo create "$FULL_REPO" --"$VISIBILITY" --source=. --remote=origin --push
  echo "Repository created: $FULL_REPO"
fi

# Ensure remote origin exists.
if ! git remote get-url origin >/dev/null 2>&1; then
  git remote add origin "https://github.com/${FULL_REPO}.git"
fi

# Ensure there is at least one commit.
if ! git rev-parse HEAD >/dev/null 2>&1; then
  git add .
  git commit -m "chore(epic-0): initialize local foundation" || true
fi

# Push main.
git push -u origin main

# Labels (idempotent via --force)
gh label create "type:socle" --repo "$FULL_REPO" --color 1f6feb --description "Backend, API, DB, orchestration" --force
gh label create "type:interface" --repo "$FULL_REPO" --color 0e8a16 --description "Tauri user interface work" --force
gh label create "type:delivery" --repo "$FULL_REPO" --color fbca04 --description "Delivery, repo, workflow automation" --force
gh label create "type:quality" --repo "$FULL_REPO" --color 5319e7 --description "Quality gates, tests, checks" --force
gh label create "priority:high" --repo "$FULL_REPO" --color b60205 --description "Highest implementation priority" --force
gh label create "priority:medium" --repo "$FULL_REPO" --color d93f0b --description "Medium implementation priority" --force
gh label create "priority:low" --repo "$FULL_REPO" --color 0e8a16 --description "Lower implementation priority" --force

for n in 0 1 2 3 4 5 6 7 8 9; do
  gh label create "epic:${n}" --repo "$FULL_REPO" --color 0052cc --description "Epic ${n}" --force
done

# Seed issues from backlog.
bash core/scripts/seed_github_issues_from_backlog.sh "$BACKLOG_FILE" apply "$FULL_REPO"

echo "Done: repository, labels, and US issues are ready on ${FULL_REPO}."
