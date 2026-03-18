# GitHub Issue Seeding from Backlog

This guide provides a ready-to-run flow for creating one GitHub issue per US from the backlog file.

## Files
- Template: DOCS/us_issue_template.md
- Script: core/scripts/seed_github_issues_from_backlog.sh
- Full bootstrap script: core/scripts/bootstrap_github_and_seed_issues.sh
- Backlog input: DOCS/backlog_epic_us_v1.md

## Prerequisites
- GitHub CLI installed
- Authenticated session: gh auth login
- Current folder is the target repository

## Label strategy
- epic label: epic:<id> from US id
- type label: type:socle | type:interface | type:delivery | type:quality | type:other
- priority label: priority:high (epic 0-2), priority:medium (epic 3-6), priority:low (epic 7+)

## Dry run
Run planning mode first to preview title and labels without writing issues:

bash core/scripts/seed_github_issues_from_backlog.sh DOCS/backlog_epic_us_v1.md dry-run

You can also target a repository explicitly:

bash core/scripts/seed_github_issues_from_backlog.sh DOCS/backlog_epic_us_v1.md dry-run owner/repo

## Apply
Create issues for real:

bash core/scripts/seed_github_issues_from_backlog.sh DOCS/backlog_epic_us_v1.md apply

If not running inside a cloned target repository, pass owner/repo:

bash core/scripts/seed_github_issues_from_backlog.sh DOCS/backlog_epic_us_v1.md apply owner/repo

## Idempotence
- The script skips creation when an issue with the same title already exists.

## Recommended workflow
1. Create labels once in repository settings.
2. Run dry-run and review output.
3. Run apply.
4. Manually copy exact acceptance criteria from backlog into each issue.

## One-shot full bootstrap
If you want to create repository, labels, and issues in one command:

bash core/scripts/bootstrap_github_and_seed_issues.sh shamantao AuriPostao private DOCS/backlog_epic_us_v1.md

## Notes
- This script currently seeds issue shell and labels. It does not yet copy all acceptance lines from markdown blocks.
- If needed, this can be extended to parse acceptance and scenario lines in a second iteration.
- Dry-run works even without repository context; apply mode requires repository context or explicit owner/repo.
