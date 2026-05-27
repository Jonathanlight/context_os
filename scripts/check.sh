#!/usr/bin/env bash
# Run all local quality gates. Mirrors what CI runs on every PR.
# Exit on first failure so the first broken check is the one a developer sees.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "→ ruff check"
ruff check src tests

echo "→ ruff format --check"
ruff format --check src tests

echo "→ mypy --strict"
mypy --strict src tests

echo "→ pytest"
pytest --cov-fail-under=85

echo "✓ all checks passed"
