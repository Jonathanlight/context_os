# Global development guidelines for the example monorepo

> Synthetic fixture inspired by the structure of a typical mid-sized OSS
> `CLAUDE.md`. See `tests/fixtures/README.md` for inspiration sources.

## Project architecture and context

This is a Python monorepo. The top-level layout:

```
.
├── packages/
│   ├── core/
│   ├── adapters/
│   └── cli/
├── docs/
├── examples/
└── tests/
```

Each package has its own `pyproject.toml` and is publishable to PyPI
independently.

### Key config files

- `pyproject.toml` (per package) — build, deps, lint config
- `Makefile` (root) — orchestration of dev tasks
- `.github/workflows/ci.yml` — CI pipeline

## Development tools and commands

```bash
make install       # install dev deps for every package
make test          # run pytest across all packages
make lint          # ruff check + ruff format --check
make build         # build wheels for every package
make docs          # render docs site locally
```

## PR and commit titles

You **must** follow Conventional Commits. Examples:

- `feat(core): add async streaming to runtime`
- `fix(adapters): handle empty response from openai`
- `chore(ci): bump python to 3.13`

PR titles mirror the squash commit. **Never** open a PR titled "WIP" or
"misc changes".

## Core development principles

### Maintain stable public interfaces

Public APIs (anything not prefixed with `_`) are **CRITICAL** to keep
stable across minor versions. Before changing a public signature, ask:
will this break a downstream user?

### Code quality standards

```python
def process(items: list[Item]) -> Result:
    """Process a batch of items and return a Result.

    Args:
        items: non-empty list of validated Item instances.

    Returns:
        Result with aggregated stats.
    """
    ...
```

- Type hints on every public function
- Google-style docstrings on every public function
- Be concise

### Testing requirements

Use `pytest` + `hypothesis`. Coverage floor is 85 %.

- [ ] Every new public function has a unit test
- [ ] Every bug fix has a regression test
- [ ] Property tests for parsing / serialization round-trips

### Security and risk assessment

- Never log secrets
- Never `eval` user input
- Sanitize all paths from untrusted sources
- Pin dependencies in `pyproject.toml`

## CI / CD infrastructure

CI runs `lint`, `typecheck`, and `test` on every PR. The `test` job is a
matrix across Python 3.12 and 3.13. PRs cannot merge until all three are
green.

## Additional resources

- Public docs: example.dev/docs
- Internal Slack: #example-monorepo-dev
