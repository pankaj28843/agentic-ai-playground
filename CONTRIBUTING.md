# Contributing

Thanks for taking a look. This project is an experimental playground, but we still aim for clean, reviewable changes.

## Before you start
- Search existing issues and discussions.
- If you plan a larger change, open an issue first.

## Development setup

```bash
uv sync --all-packages
pnpm -C frontend install
cp .env.example .env
```

## Style and tests

```bash
# Python lint + format
uv run ruff check . --fix
uv run ruff format .

# Python tests
uv run pytest packages/ -x -q

# Frontend lint + build
pnpm -C frontend lint
pnpm -C frontend build

# E2E tests (requires running stack)
source .env && uv run python scripts/e2e_tests.py
pnpm -C frontend exec playwright test --reporter=list
```

## Pull request guidelines
- Keep changes focused and explain the intent in the PR description.
- Add or update tests when behavior changes.
- Do not commit secrets, credentials, or local machine artifacts.
- Avoid hardcoding internal hostnames, private URLs, or machine-specific paths.
