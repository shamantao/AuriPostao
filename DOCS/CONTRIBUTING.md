# Contributing

## Branching model
- Default protected branch: `main`
- Working branches follow this convention:
	- `feat/<scope>` for features
	- `fix/<scope>` for bug fixes
	- `chore/<scope>` for maintenance

## Pull requests
- Direct push to `main` is blocked by branch protection.
- At least 1 approving review is required before merge.
- Conversation resolution is required before merge.

## Code style
- Follow conventions documented in `DOCS/`.
- Keep modules with single responsibilities.

## Commits
- Use Conventional Commits (examples: `feat:`, `fix:`, `docs:`, `chore:`).
- Reference issue numbers when applicable.

## Testing
- Install local hooks once per clone:
  - `npm run hooks:install`
- Run baseline checks before committing:
  - `npm run check:baseline`
- Project-specific unit/integration/E2E tests are defined by each project team.

## Security checks
- Run `scripts/check-secrets.sh` before opening a pull request.
- Never commit credentials, tokens, or private keys.
