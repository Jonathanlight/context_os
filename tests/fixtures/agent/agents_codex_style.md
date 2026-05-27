# AGENTS.md — Example Trading Bot

> Synthetic fixture inspired by Codex's `AGENTS.md` convention. See
> `tests/fixtures/README.md` for inspiration sources.

## Identity

You are working on **example-trader**, a small Python trading bot that
consumes a websocket price feed and produces trade signals.

Author: Example Author. Single maintainer.

## Stack

- Python 3.11+
- `asyncio` for the websocket loop
- `numpy` + `pandas` for indicators
- `pytest` for tests

## Rules

- Never hard-code API keys. Read them from env.
- Never make synchronous HTTP calls inside the websocket loop — they block the event loop.
- Always backtest a new strategy on at least 6 months of data before live deployment.
- Prefer pure functions for indicator logic so backtests are deterministic.

## Style

- 4 spaces, no tabs.
- `snake_case` for functions and variables, `PascalCase` for classes.
- Use `typing` annotations on every public function.

## Forbidden patterns

- `time.sleep()` in async code
- `print()` in production paths — use `logging`
- Global mutable state for trader configuration
