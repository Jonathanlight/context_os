# FullExample

Comprehensive context file covering every section the parser knows.

## Identity

Senior backend engineer working on the trading-bot monorepo.

## Stack

### Required

- python>=3.12
- pydantic>=2.7

### Forbidden

- django
- flask

### Preferred

- fastapi
- starlette

## Rules

- Never commit secrets to the repository.
- Always run the test suite before opening a PR.
- Should prefer composition over inheritance.
- May add module-level docstrings for context.
- Run linting before each commit.

## Style

- 4 spaces, no tabs.
- snake_case for functions and variables.
- PascalCase for classes.

## Forbidden patterns

- Wildcard imports.
- Raw SQL string concatenation.
- Global mutable state.

## Tools

### Required

- ruff
- mypy
- pytest

### Forbidden

- black
- flake8
