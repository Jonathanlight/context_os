# ContextOS

> Lint, unify, and study everything you give to an LLM.

[![CI](https://github.com/Jonathanlight/context_os/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/Jonathanlight/context_os/actions/workflows/ci.yml)
[![Docs](https://github.com/Jonathanlight/context_os/actions/workflows/docs.yml/badge.svg?branch=develop)](https://jonathanlight.github.io/context_os/)
[![PyPI](https://img.shields.io/pypi/v/context-os.svg)](https://pypi.org/project/context-os/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

ContextOS is a Python toolkit for the three families of artifacts that
drive modern LLMs — and that today live in five incompatible formats:

- **Agent context files** — `CLAUDE.md`, `AGENTS.md`, `.cursorrules`,
  `.cursor/rules/*.mdc`, `.clinerules`, `.windsurfrules`,
  `.github/copilot-instructions.md`.
- **Anthropic Skills** (Phase 5).
- **RAG corpora configurations** (Phase 6).

Write your project context **once** in a `.ctx` file. ContextOS compiles
it to every target format you need, **lints** the result, **diffs** two
versions semantically, and **audits** a whole repository at once.

## Why ContextOS

A developer working seriously with LLMs in 2026 maintains 5–10 context
files spread across formats. They drift. They contradict. Nobody catches
the rule that says `Always use type hints` in `CLAUDE.md` while
`.cursorrules` says `Never use type hints in benchmarks`. The model
sees both; one of them wins; the choice is invisible to the author.

ContextOS treats the context as **source code**: parsed into a typed
AST, validated against 14+ lint rules, kept in sync across targets,
diffed semantically, audited at the repo level. The CLI ships
production-shaped errors with `file:line:column` locations and concrete
suggestions, not vibes.

## Five-minute tour

```bash
pipx install context-os
ctx --version
```

Write your project context once:

```toml
# project.ctx
project = "MyApp"
artifacts = ["context"]

[stack]
required = ["python>=3.12", "fastapi"]
forbidden = ["django"]

[[rules]]
id = "TDD-001"
title = "Write a failing test before any production code change"
severity = "must"
rationale = "Catches regressions before they reach the PR review."

[[rules]]
id = "SEC-042"
title = "Sanitize every input crossing a trust boundary"
severity = "must"
rationale = "Prevents path-traversal and injection attacks."
example_good = "bleach.clean(user_html)"
```

Compile to any agent target:

```bash
ctx compile project.ctx --target claude_code --output-dir .
# wrote ./CLAUDE.md

ctx compile project.ctx --target codex   --output-dir .
ctx compile project.ctx --target cursor  --output-dir .
ctx compile project.ctx --target copilot --output-dir .
```

Lint an existing context file:

```bash
$ ctx lint CLAUDE.md --target claude_code
warning[A001]: vague directive: 'Be concise'
  --> CLAUDE.md:42:1
   = help: rephrase with a measurable criterion (e.g. 'public functions
     <= 40 lines' instead of 'be concise')
   = doc:  https://contextos.dev/rules/A001

warning[K002]: must-severity rule 'TDD-001' has no rationale
  --> CLAUDE.md:14:1
   = help: add `rationale = "..."` explaining why this rule is mandatory
```

Diff two versions:

```bash
$ ctx diff project.ctx project.ctx.new
project: 'MyApp' -> 'MyApp-v2'

stack:
  required:
    + pydantic

rules:
  + DOC-001: Every public function has a docstring
  ~ TDD-001:
      severity: should -> must
      tags +: ['discipline']
```

Audit a whole repo:

```bash
$ ctx audit .

--- ./CLAUDE.md
warning[F002]: rule title is 145 characters long (limit: 120)
  --> ./CLAUDE.md:12:1

--- ./AGENTS.md
no diagnostics

--- Cross-artifact
warning[XA001]: rule id 'TDD-001' collides across 2 files with different
content: ['./AGENTS.md', './CLAUDE.md']

--- Skipped files (no parser yet)
  ./.cursorrules  [cursor]  no parser yet for target 'cursor'

summary: 2 diagnostic(s)
```

Aggregate stats across a corpus:

```bash
$ ctx stats path/to/projects

corpus stats: path/to/projects

files audited:  18
files skipped:  4
diagnostics:    72

by severity:
  error    0
  warning  61
  info     11

top codes:
  A001   18
  K002   12
  F002    9
  K003    8
  XA001   3

target coverage:
  claude_code   12
  codex          6
  cursor         4
```

## Status

🚀 **Phase 4 in progress.** v0.1.0 shipped; v1.0 launch tracks the
[roadmap](docs/specs/ROADMAP.md).

| Phase | What                                          | Status     |
|-------|-----------------------------------------------|------------|
| 1     | Parser + AST + Claude emitter                 | ✅ shipped |
| 2     | 14 lint rules (A / C / F / K / P / X)          | ✅ shipped |
| 3     | 5 more emitters + diff + audit                | ✅ shipped |
| 4     | Corpus study + docs site + launch v1.0         | 🟢 active  |
| 5     | Anthropic Skills (`SKILL.md`)                  | ⏳ planned |
| 6     | RAG corpora                                    | ⏳ planned |

## Supported targets

| Target         | Parse | Emit | Output filename                         |
|----------------|-------|------|-----------------------------------------|
| `claude_code`  | ✅    | ✅   | `CLAUDE.md`                             |
| `codex`        | ✅    | ✅   | `AGENTS.md`                             |
| `cursor`       | ⏳    | ✅   | `.cursor/rules/agent.mdc`               |
| `copilot`      | ⏳    | ✅   | `.github/copilot-instructions.md`       |
| `cline`        | ⏳    | ✅   | `.clinerules`                           |
| `windsurf`     | ⏳    | ✅   | `.windsurfrules`                        |

Parsers for cursor / copilot / cline / windsurf are Phase 5+ work — the
formats are different enough from `CLAUDE.md` that they each need their
own walker.

## CLI surface

| Command       | What it does                                          |
|---------------|-------------------------------------------------------|
| `ctx parse`   | `.ctx` or Markdown → AST as JSON or TOML              |
| `ctx compile` | `.ctx` → target file (Markdown or `.mdc`)             |
| `ctx lint`    | Run analyzers on a single file                         |
| `ctx diff`    | Semantic diff of two Documents                        |
| `ctx audit`   | Walk a repo, lint every file, run cross-artifact rules |
| `ctx stats`   | Aggregate corpus-wide statistics from an audit        |
| `ctx --version` | Print version                                       |

Every command has `--json` for machine-readable output and exits 1 only
when an error-severity diagnostic fires.

## Docs

- 📚 [Documentation site](https://jonathanlight.github.io/context_os/)
- 🛠 [Getting started](docs/getting-started.md)
- 📋 [Rules catalog](docs/rules/index.md)
- 🏛 [Specs](docs/specs/) (Vision, Spec, Architecture, Roadmap)

## Stack

- Python 3.12+, `mypy --strict`
- [Pydantic v2](https://docs.pydantic.dev) — strict-typed AST
- [Typer](https://typer.tiangolo.com) — the `ctx` CLI
- [mistletoe](https://github.com/miyuchina/mistletoe) — Markdown parser
- [tomlkit](https://github.com/python-poetry/tomlkit) — TOML with comments preserved
- pytest + [hypothesis](https://hypothesis.readthedocs.io) — 600+ tests, 1000-example property tests on the round-trip
- [ruff](https://docs.astral.sh/ruff/) — lint + format

## Install for development

```bash
git clone git@github.com:Jonathanlight/context_os.git
cd context_os
pip install -e ".[dev]"
pre-commit install
./scripts/check.sh   # ruff + mypy --strict + pytest
```

For the docs site:

```bash
pip install -e ".[docs]"
mkdocs serve   # http://127.0.0.1:8000/
```

## Contributing

Pull requests welcome. Read [`tasks/CONTRIBUTING.md`](tasks/CONTRIBUTING.md)
first — ContextOS enforces strict PR discipline (one subject per PR,
≤ 400 lines diff excluding tests, conventional commits prefixed by phase).

## License

MIT — see [LICENSE](LICENSE).

## Author

[Jonathan KABLAN](https://github.com/Jonathanlight) — Senior Full Stack Developer.
