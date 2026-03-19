# AuriPostao

MVP local-first app to generate and publish short content using a local AI engine.

## Current status
- EPIC-0 started
- Local Python API bootstrap available (`/health`, `/bootstrap`)
- GitHub issue seeding automation available

## Run local API bootstrap

bash core/scripts/run_api.sh

In another terminal:

bash core/scripts/check_bootstrap.sh

## Run local app stack (UI + API)

npm run tauri dev

This command now starts Vite and the local Python API together.

## Install local Git hooks

npm run hooks:install

This configures Git to use the versioned hooks in .githooks/.

The local gates are:
- pre-commit: lint + fast unit tests
- pre-push: baseline checks + full unit tests + light integration

## GitHub bootstrap and US issue seeding

1. Authenticate GitHub CLI:

gh auth login -h github.com

2. Create repository + labels + issues from backlog:

bash core/scripts/bootstrap_github_and_seed_issues.sh shamantao AuriPostao private DOCS/backlog_epic_us_v1.md

## Backlog
- See DOCS/backlog_epic_us_v1.md
- Seeding guide: DOCS/github_issue_seeding.md
