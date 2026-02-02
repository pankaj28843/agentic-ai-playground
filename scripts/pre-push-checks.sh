#!/usr/bin/env bash
# Pre-push validation script
# Run this before pushing to ensure all checks pass.
# Usage: ./scripts/pre-push-checks.sh
#
# This script runs:
# 1. Python lint (ruff)
# 2. Python tests (pytest)
# 3. Frontend lint (eslint)
# 4. Frontend build (pnpm build)
#
# E2E tests are NOT included here (they cost money via Bedrock).
# Run E2E manually when needed: source .env && uv run python scripts/debug_tui_runtime.py --preflight

set -e

echo "=== Pre-push validation ==="

echo ""
echo "1/4 Ruff lint & format..."
uv run ruff check . --fix
uv run ruff format .

echo ""
echo "2/4 Pytest..."
uv run pytest packages/ -x -q

echo ""
echo "3/4 Frontend lint..."
pnpm -C frontend lint

echo ""
echo "4/4 Frontend build..."
pnpm -C frontend build

echo ""
echo "=== All checks passed ==="
