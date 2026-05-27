# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with
code in this repository. It is the **contract** every Claude Code session
operates under — read it in full before any action.

## Identity

You are working on **ContextOS**, a Python toolkit that analyzes, generates,
and compares LLM context artifacts: agent context files (CLAUDE.md, AGENTS.md,
`.cursorrules`, etc.), Anthropic Skills, and RAG corpora configurations.

Author: **Jonathan KABLAN**, Senior Full Stack Developer.

Never reference any other author identity.

## Required stack

- **Language**: Python 3.12+ strict
- **Typing**: `mypy --strict` must always pass
- **Data models**: Pydantic v2 exclusively (no dataclasses, no raw dicts)
- **CLI**: Typer (no direct `click`, no `argparse`)
- **Markdown parsing**: `mistletoe`
- **TOML parsing**: `tomlkit` (preserves order and comments, unlike `tomllib`)
- **Tests**: `pytest` + `hypothesis` (property-based)
- **Lint/format**: `ruff` (replaces black + flake8 + isort)
- **CI**: GitHub Actions

Never introduce:
- Another Markdown library (markdown-it-py, marko, mistune)
- Direct `click` (route through Typer)
- `dataclasses` instead of Pydantic
- A heavy dependency (Django, Flask) without explicit validation
- Python < 3.12 code (free use of `match`, `|` union types, etc.)

## Required reading before any action

In this order:
1. `docs/specs/VISION.md` — philosophy
2. `docs/specs/SPEC.md` — `.ctx` format, lint taxonomy, parsing contracts
3. `docs/specs/ARCHITECTURE.md` — repo structure, modules
4. `docs/specs/ROADMAP.md` — current phase
5. `tasks/phase<N>_todo.md` — active phase to-do
6. `tasks/phase<N>_lessons.md` — accumulated lessons

In case of contradiction: **`docs/specs/SPEC.md` is authoritative**.

> Note: the `docs/specs/` files land in PR `phase0(specs)`. Until then, refer
> to the relevant section of the private master spec.

## Mandatory BMAD methodology

For any feature > 100 lines:
1. **Spec first**: create or modify a `.md` in `docs/specs/` before any code
2. **`tasks/phase<N>_todo.md`** per session
3. **Tests before implementation** (strict TDD for parsers and analyzers)
4. **`tasks/phase<N>_lessons.md`** at the end

## Code style

### Python
- 2 spaces? No. **4 spaces** (strict PEP 8, non-negotiable)
- No wildcard imports
- Type hints on **all** public signatures (mypy --strict requires it)
- Prefer `match` over chained `if/elif/else`
- No mutable global state — inject dependencies via parameters or context
- No exceptions for control flow; use `Result`-like via union types and early return
- One function = one responsibility. > 40 lines = probable refactor
- Google-style docstrings on public functions

### Architecture
- **No logic in `__init__.py`** except explicit re-exports
- **Modules with `__all__`** to control exports
- **No import cycles** — detected by lint
- **Strict layers**: `cli` → `analyzers/emitters/parsers` → `ast` → utilities. Never the reverse.

### Tests
- One `test_*.py` file per module
- Reusable fixtures in `tests/fixtures/`
- `hypothesis` for invariants (round-trip, idempotence)
- No mocking when a lightweight integration test will do
- Coverage target: 90 %+ on business logic, 70 %+ on the CLI

## Forbidden patterns

- **Mutable global state**
- **Reflection / dynamic `getattr`** except for justified and commented cases
- **`Any` in typing** unless justified in a comment
- **Generated code without tests**
- **Magic strings / numbers** without a named constant
- **Vague commit messages** — always `<phase>(<module>): <imperative>`
- **Multi-topic PRs** — one subject per PR
- **Off-spec features** without prior SPEC update

## Required patterns

- **Self-explanatory diagnostics**: code (`A001`...), position, message, concrete suggestion, doc link
- **Idempotence**: `ctx compile | ctx parse | ctx compile` = identity
- **Round-trip property test** on every emitter
- **Typed errors**: no `raise Exception("...")`, use dedicated classes
- **Reproducibility**: same input → same byte-for-byte output (stable order of rules, sections)
- **Small PRs**: ≤ 400 lines diff excluding tests

## Commit conventions

```
<phase>(<module>): <short imperative>

<optional body, 72 cols>

<optional footer: refs #issue>
```

Examples:
- `phase1(parser): support TOML nested arrays in rules`
- `phase2(analyzers): implement A001 vague-directive detection`
- `phase3(emitters): cursor mdc frontmatter generation`

## Required tooling

- `ruff check` + `ruff format` before each commit
- `mypy --strict src/` before each commit
- `pytest --cov=contextos --cov-fail-under=85` before each PR
- `pre-commit` git hook: ruff + mypy
- `./scripts/check.sh` runs all four

## When to ask the human

You **must** ask before:
- Adding a Python dependency not listed in `pyproject.toml`
- Modifying `docs/specs/SPEC.md` even a detail
- Making an architectural choice not covered by `docs/specs/ARCHITECTURE.md`
- Inventing a new lint rule code
- Touching an emitter output format (mapping to a target)

You **do not need** to ask for:
- Internal refactor without public API change
- Adding tests
- Adding fixtures
- Bug fix with a regression test
- Updating docstrings

## Communication

- Replies in **French** by default
- Code, identifiers, commit messages, docstrings: **English**
- User documentation in `docs/`: **English first, French as bonus**
- CLI error messages: **English** (tooling norm)
- Internal documentation (`tasks/`, `docs/specs/`): **French OK**

## Common mistakes to avoid

Section enriched by `tasks/phase<N>_lessons.md`. At J0, empty.
