#!/usr/bin/env bash
set -euo pipefail

# Seed GitHub issues from backlog markdown (US lines).
# Requires: gh CLI authenticated on target repository.

BACKLOG_FILE="${1:-DOCS/backlog_epic_us_v1.md}"
MODE="${2:-dry-run}" # dry-run | apply
TARGET_REPO="${3:-}"   # optional: owner/repo

if [[ ! -f "$BACKLOG_FILE" ]]; then
  echo "ERROR: backlog file not found: $BACKLOG_FILE" >&2
  exit 1
fi

if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI not found. Install GitHub CLI first." >&2
  exit 1
fi

if [[ "$MODE" != "dry-run" && "$MODE" != "apply" ]]; then
  echo "ERROR: mode must be dry-run or apply" >&2
  exit 1
fi

repo_full_name="$TARGET_REPO"
if [[ -z "$repo_full_name" ]]; then
  repo_full_name="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
fi

if [[ "$MODE" == "apply" && -z "$repo_full_name" ]]; then
  echo "ERROR: apply mode requires a repository context." >&2
  echo "Hint: run inside a cloned repo or pass owner/repo as 3rd argument." >&2
  exit 1
fi

issue_exists() {
  local title="$1"
  if [[ -z "$repo_full_name" ]]; then
    return 1
  fi
  local count
  count="$(gh issue list --repo "$repo_full_name" --state all --search "in:title \"$title\"" --json number -q 'length')"
  [[ "$count" -gt 0 ]]
}

map_type_label() {
  local us_kind="$1"
  case "$us_kind" in
    Socle) echo "type:socle" ;;
    Interface) echo "type:interface" ;;
    Delivery) echo "type:delivery" ;;
    Qualite) echo "type:quality" ;;
    *) echo "type:other" ;;
  esac
}

map_priority_label() {
  local epic_id="$1"
  if [[ "$epic_id" -le 2 ]]; then
    echo "priority:high"
  elif [[ "$epic_id" -le 6 ]]; then
    echo "priority:medium"
  else
    echo "priority:low"
  fi
}

current_epic=""
current_epic_id=""

# The parser expects lines like:
# - US-5.1 (Socle) - Connecteur SMTP
while IFS= read -r line; do
  if [[ "$line" =~ ^##[[:space:]]EPIC-([0-9]+)[[:space:]]-[[:space:]](.+)$ ]]; then
    current_epic_id="${BASH_REMATCH[1]}"
    current_epic="${BASH_REMATCH[2]}"
    continue
  fi

  if [[ "$line" =~ ^-[[:space:]]US-([0-9]+\.[0-9]+)[[:space:]]\(([^\)]+)\)[[:space:]]-[[:space:]](.+)$ ]]; then
    us_id="${BASH_REMATCH[1]}"
    us_kind="${BASH_REMATCH[2]}"
    us_title="${BASH_REMATCH[3]}"

    epic_from_us="${us_id%%.*}"
    epic_label="epic:${epic_from_us}"
    type_label="$(map_type_label "$us_kind")"
    priority_label="$(map_priority_label "$epic_from_us")"

    issue_title="[EPIC-${epic_from_us}][US-${us_id}][${us_kind}] ${us_title}"

    # Idempotent behavior: skip if title already exists.
    if issue_exists "$issue_title"; then
      echo "SKIP existing: $issue_title"
      continue
    fi

    body_file="$(mktemp)"
    cat > "$body_file" <<EOF
## 1. Context
- EPIC: EPIC-${current_epic_id} - ${current_epic}
- Source backlog: ${BACKLOG_FILE}
- Problem:
- User value:

## 2. Scope
- Included:
- Included:

## 3. Out of Scope
- Not included:

## 4. Acceptance Criteria
1. To be copied from backlog US section.
2. 
3. 

## 5. Tests
- Manual test:
- Automated tests:

## 6. Definition of Done
- Code merged
- Relevant tests green
- Documentation updated
EOF

    echo "PLAN: $issue_title"
    echo "  labels: $epic_label, $type_label, $priority_label"

    if [[ "$MODE" == "apply" ]]; then
      gh issue create \
        --repo "$repo_full_name" \
        --title "$issue_title" \
        --body-file "$body_file" \
        --label "$epic_label" \
        --label "$type_label" \
        --label "$priority_label" >/dev/null
      echo "CREATED: $issue_title"
    fi

    rm -f "$body_file"
  fi
done < "$BACKLOG_FILE"

if [[ -z "$repo_full_name" ]]; then
  echo "Done. Mode: $MODE (no repository context, planning output only)."
else
  echo "Done. Mode: $MODE (repo: $repo_full_name)."
fi
