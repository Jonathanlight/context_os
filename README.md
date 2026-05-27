# ContextOS

> The Operating System for LLM Context.

ContextOS is a Python toolkit for analyzing, generating, and comparing the
context artifacts that drive LLMs:

- agent context files (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.windsurfrules`, etc.)
- Anthropic Skills (`SKILL.md` folders)
- RAG corpora configurations (LlamaIndex, LangChain, Haystack, raw YAML)

The CLI is `ctx`. A `.ctx` source file declares your project, stack, rules,
skills, and RAG pipeline; ContextOS compiles it to every target format you
need, lints existing artifacts, diffs them semantically, and audits a whole
repo at once.

## Status

🚧 **Phase 0 — Foundation.** No usable release yet. The first release `v0.1.0`
will ship the parser, AST, and Claude emitter. See
[`docs/specs/ROADMAP.md`](docs/specs/ROADMAP.md) once it lands.

## Stack

- Python 3.12+, `mypy --strict`
- [Pydantic v2](https://docs.pydantic.dev) — the AST
- [Typer](https://typer.tiangolo.com) — the `ctx` CLI
- [mistletoe](https://github.com/miyuchina/mistletoe) — Markdown parsing
- [tomlkit](https://github.com/python-poetry/tomlkit) — TOML parsing (preserves order + comments)
- pytest + [hypothesis](https://hypothesis.readthedocs.io) — tests + property-based
- [ruff](https://docs.astral.sh/ruff/) — lint + format

## Development

```bash
git clone git@github.com:Jonathanlight/context_os.git
cd context_os
pip install -e ".[dev]"
pre-commit install
./scripts/check.sh   # ruff + mypy --strict + pytest
```

## Contributing

Pull requests are welcome. Read [`tasks/CONTRIBUTING.md`](tasks/CONTRIBUTING.md)
first — ContextOS enforces strict PR discipline (one subject per PR, ≤ 400
lines diff hors tests, conventional commits prefixed by phase).

## License

MIT — see [LICENSE](LICENSE).

## Author

[Jonathan KABLAN](https://github.com/Jonathanlight) — Senior Full Stack Developer.
