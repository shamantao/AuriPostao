#!/usr/bin/env bash
set -euo pipefail

# Seed GitHub issues from backlog markdown.
# Extrait user story, acceptance criteria et scenario EPIC depuis le backlog.
# Requires: gh CLI authenticated, python3 available.
#
# Usage:
#   bash seed_github_issues_from_backlog.sh <backlog.md> <dry-run|apply|update> [owner/repo]
#
# Modes:
#   dry-run  - print plans only, no GitHub calls
#   apply    - create new issues (skip existing)
#   update   - update body of existing issues; create if missing

BACKLOG_FILE="${1:-DOCS/backlog_epic_us_v1.md}"
MODE="${2:-dry-run}"
TARGET_REPO="${3:-}"

if [[ ! -f "$BACKLOG_FILE" ]]; then
  echo "ERROR: backlog file not found: $BACKLOG_FILE" >&2; exit 1
fi
if ! command -v gh >/dev/null 2>&1; then
  echo "ERROR: gh CLI not found." >&2; exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 not found." >&2; exit 1
fi
if [[ "$MODE" != "dry-run" && "$MODE" != "apply" && "$MODE" != "update" ]]; then
  echo "ERROR: mode must be dry-run | apply | update" >&2; exit 1
fi

repo_full_name="$TARGET_REPO"
if [[ -z "$repo_full_name" ]]; then
  repo_full_name="$(gh repo view --json nameWithOwner -q .nameWithOwner 2>/dev/null || true)"
fi
if [[ "$MODE" != "dry-run" && -z "$repo_full_name" ]]; then
  echo "ERROR: apply/update mode requires a repository context." >&2; exit 1
fi

# Python parser: parses backlog, writes body files to WORKDIR,
# outputs TSV: issue_title<TAB>epic_label<TAB>type_label<TAB>priority_label<TAB>body_path
WORKDIR="$(mktemp -d /tmp/seed_issues_XXXXX)"
PYPARSE="$(mktemp /tmp/parse_backlog_XXXXX.py)"
trap "rm -rf '$WORKDIR' '$PYPARSE'" EXIT

python3 - "$PYPARSE" << 'WRITE_PARSER'
import sys

parser_code = r"""
import sys, re, os

backlog_path = sys.argv[1]
workdir      = sys.argv[2]

with open(backlog_path, encoding="utf-8") as f:
    lines = f.readlines()

# Pass 1: scenario lines per EPIC id
epic_scenarios = {}
cur_epic = ""
in_scenario = False
for line in lines:
    s = line.rstrip("\n")
    m = re.match(r"^## EPIC-(\d+)", s)
    if m:
        cur_epic = m.group(1); in_scenario = False; continue
    if re.match(r"^Scenario test humain EPIC-\d+:", s):
        in_scenario = True; epic_scenarios.setdefault(cur_epic, []); continue
    if in_scenario:
        if not s.strip() or s.startswith("##") or s.startswith("Template"):
            in_scenario = False
        elif s.strip():
            epic_scenarios.setdefault(cur_epic, []).append(s.strip())

# Pass 2: US with story + criteria
current_epic = {"id": "", "title": ""}
current_us = None
in_acceptance = False
counter = 0

def priority(epic_id):
    n = int(epic_id)
    if n <= 2:  return "priority:high"
    if n <= 6:  return "priority:medium"
    return "priority:low"

def tlabel(kind):
    return {"Socle":"type:socle","Interface":"type:interface",
            "Delivery":"type:delivery","Qualite":"type:quality"}.get(kind,"type:other")

def emit(us):
    global counter
    if not us: return
    eid      = us["epic_id"]
    scenario = epic_scenarios.get(eid, [])
    criteria = us["criteria"] if us["criteria"] else ["1. A definir."]
    story_ln = f"- **User story:** {us['story']}\n" if us["story"] else ""
    body = (
        f"## 1. Contexte\n"
        f"- **EPIC:** EPIC-{eid} -- {us['epic_title']}\n"
        f"{story_ln}"
        f"\n## 2. Scope\n- Inclus dans cette US.\n"
        f"\n## 3. Hors-scope\n- Non traite dans cette US.\n"
        f"\n## 4. Acceptance Criteria\n"
        + "\n".join(criteria) + "\n"
        + f"\n## 5. Tests\n**Scenario test humain EPIC-{eid}:**\n"
        + ("\n".join(scenario) if scenario else "Voir backlog.") + "\n"
        + "\n- Tests auto : unitaires et/ou integration selon scope.\n"
        + "\n## 6. Definition of Done\n"
        + "- [ ] Code merge\n- [ ] Tests verts\n- [ ] Documentation mise a jour\n"
    )
    body_path = os.path.join(workdir, f"{counter:03d}.body")
    with open(body_path, "w", encoding="utf-8") as f:
        f.write(body)
    issue_title = f"[EPIC-{eid}][US-{us['us_id']}][{us['kind']}] {us['title']}"
    print(f"{issue_title}\t{'epic:'+eid}\t{tlabel(us['kind'])}\t{priority(eid)}\t{body_path}")
    counter += 1

for line in lines:
    s = line.rstrip("\n")
    m = re.match(r"^## EPIC-(\d+) - (.+)$", s)
    if m:
        emit(current_us); current_us = None; in_acceptance = False
        current_epic = {"id": m.group(1), "title": m.group(2)}; continue
    if re.match(r"^Scenario test humain|^Template issue|^## Ordre|^## Definition", s):
        emit(current_us); current_us = None; in_acceptance = False; continue
    m = re.match(r"^- US-(\d+\.\d+) \(([^)]+)\) - (.+)$", s)
    if m:
        emit(current_us); in_acceptance = False
        current_us = {"epic_id": current_epic["id"], "epic_title": current_epic["title"],
                      "us_id": m.group(1), "kind": m.group(2), "title": m.group(3),
                      "story": "", "criteria": []}
        continue
    if current_us is None: continue
    m = re.match(r"^  - (En tant qu?.+)$", s)
    if m: current_us["story"] = m.group(1); continue
    if re.match(r"^  - Acceptance:", s): in_acceptance = True; continue
    if in_acceptance:
        m = re.match(r"^    (\d+\. .+)$", s)
        if m: current_us["criteria"].append(m.group(1)); continue
        if s.strip() and not s.startswith("    "): in_acceptance = False

emit(current_us)
"""

with open(sys.argv[1], "w") as f:
    f.write(parser_code.lstrip())
WRITE_PARSER

# Process TSV manifest: TITLE<TAB>epic_label<TAB>type_label<TAB>priority_label<TAB>body_path
while IFS=$'\t' read -r issue_title epic_label type_label priority_label body_file; do
  echo "PLAN: $issue_title"
  echo "  labels: $epic_label, $type_label, $priority_label"

  if [[ "$MODE" == "apply" ]]; then
    existing="$(gh issue list --repo "$repo_full_name" --state all \
      --search "in:title \"$issue_title\"" --json number -q '.[0].number // empty')"
    if [[ -n "$existing" ]]; then
      echo "SKIP existing #${existing}: $issue_title"
    else
      gh issue create --repo "$repo_full_name" --title "$issue_title" \
        --body-file "$body_file" \
        --label "$epic_label" --label "$type_label" --label "$priority_label" >/dev/null
      echo "CREATED: $issue_title"
    fi

  elif [[ "$MODE" == "update" ]]; then
    existing="$(gh issue list --repo "$repo_full_name" --state all \
      --search "in:title \"$issue_title\"" --json number -q '.[0].number // empty')"
    if [[ -n "$existing" ]]; then
      gh issue edit "$existing" --repo "$repo_full_name" --body-file "$body_file" >/dev/null
      echo "UPDATED #${existing}: $issue_title"
    else
      gh issue create --repo "$repo_full_name" --title "$issue_title" \
        --body-file "$body_file" \
        --label "$epic_label" --label "$type_label" --label "$priority_label" >/dev/null
      echo "CREATED: $issue_title"
    fi
  fi

done < <(python3 "$PYPARSE" "$BACKLOG_FILE" "$WORKDIR")

if [[ -z "$repo_full_name" ]]; then
  echo "Done. Mode: $MODE (no repository context)."
else
  echo "Done. Mode: $MODE (repo: $repo_full_name)."
fi
