<div align="center">

<img src="logo.png" alt="ContextOS — The Operating System for AI Context" width="420">

# ContextOS

**The complete toolchain for LLM context engineering — lint, compile, audit, evaluate, auto-fix, and ship.**

**English** · [Français](README.fr.md)

[![CI](https://github.com/Jonathanlight/context_os/actions/workflows/ci.yml/badge.svg?branch=develop)](https://github.com/Jonathanlight/context_os/actions/workflows/ci.yml)
[![Docs](https://github.com/Jonathanlight/context_os/actions/workflows/docs.yml/badge.svg?branch=develop)](https://jonathanlight.github.io/context_os/)
[![PyPI](https://img.shields.io/pypi/v/context-os.svg)](https://pypi.org/project/context-os/)
[![Python](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

</div>

---

## The problem

A developer working seriously with LLMs in 2026 maintains **5–10 context files** scattered across incompatible formats:

```
your-repo/
├── CLAUDE.md                          ← Claude Code
├── AGENTS.md                          ← Codex / Aider
├── .cursorrules                       ← Cursor
├── .cursor/rules/*.mdc                ← Cursor (new format)
├── .clinerules                        ← Cline
├── .windsurfrules                     ← Windsurf
├── .github/copilot-instructions.md    ← GitHub Copilot
├── skills/<name>/SKILL.md             ← Anthropic Skills
└── rag.ctx                            ← RAG corpus config
```

They **drift**. They **contradict**. Nobody catches the rule that says `Always use type hints` in `CLAUDE.md` while `.cursorrules` says `Never use type hints in benchmarks`. The model sees both; one wins; the choice is invisible to the author.

## The solution

ContextOS treats LLM context as **source code**: parsed into a typed AST, validated against 27 lint rules, kept in sync across targets, evaluated against real LLMs, auto-fixed where unambiguous.

```
   ┌─────────────────┐
   │  project.ctx    │   ← write once
   └────────┬────────┘
            │
   ┌────────▼─────────┐
   │   ContextOS      │   ← parse · lint · evaluate · fix
   └────────┬─────────┘
            │
   ┌────────┼────────┬────────┬────────┬─────────┐
   ▼        ▼        ▼        ▼        ▼         ▼
CLAUDE.md AGENTS.md cursor copilot windsurf  SKILL.md
                                              rag.manifest.json
```

## What's in the box

|     | Capability | One-liner |
| --- | --- | --- |
| 📝 | **`ctx compile`** | One `.ctx` source → eight target formats |
| 🔎 | **`ctx lint`** | 27 rules across A / C / F / K / P / R / S / X / XA categories |
| 🌳 | **`ctx audit`** | Walk a repo, lint every file, surface cross-artifact collisions |
| 📊 | **`ctx stats`** | Aggregate corpus-wide diagnostics + top rule codes |
| 🔀 | **`ctx diff`** | Semantic diff between two context versions |
| 🧪 | **`ctx eval`** | Functional evaluation against Anthropic Skills + RAG retrieval |
| 📉 | **`ctx eval-diff`** | Compare runs, gate CI on regressions |
| 🛠 | **`ctx fix`** | Auto-apply structured fixes (X003, F001, X001, S005) |
| 🧠 | **`ctx lsp`** | LSP server for VSCode / Neovim / Helix / Sublime |
| 📺 | **`--html`** | Self-contained HTML reports for audit + eval |

## Install

```bash
# Core CLI
pipx install context-os

# With editor (LSP) support
pipx install 'context-os[lsp]'

# With evaluation (Anthropic + OpenAI + numpy)
pipx install 'context-os[eval]'
```

Verify:

```bash
ctx --version
# contextos 4.0.0
```

## Five-minute tour

### 1 — Write your project context once

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
rationale = "Catches regressions before they reach PR review."

[[rules]]
id = "SEC-042"
title = "Sanitize every input crossing a trust boundary"
severity = "must"
rationale = "Prevents path-traversal and injection attacks."
example_good = "bleach.clean(user_html)"
```

### 2 — Compile to every target

```bash
ctx compile project.ctx --target claude_code --output-dir .   # → ./CLAUDE.md
ctx compile project.ctx --target codex       --output-dir .   # → ./AGENTS.md
ctx compile project.ctx --target cursor      --output-dir .   # → ./.cursor/rules/agent.mdc
ctx compile project.ctx --target copilot     --output-dir .   # → ./.github/copilot-instructions.md
```

### 3 — Lint existing files

```text
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

### 4 — Audit a whole repo

```text
$ ctx audit .

--- ./CLAUDE.md
warning[F002]: rule title is 145 characters long (limit: 120)
  --> ./CLAUDE.md:12:1

--- ./AGENTS.md
no diagnostics

--- Cross-artifact
warning[XA001]: rule id 'TDD-001' collides across 2 files with different
content: ['./AGENTS.md', './CLAUDE.md']

summary: 2 diagnostic(s)
```

### 5 — Evaluate your skills functionally

```bash
ctx eval skills.eval.toml --skills-dir skills/ --json --output current.json
ctx eval-diff baseline.json current.json
# exit 1 if a previously-passing case now fails
```

### 6 — Auto-fix what we can

```bash
ctx fix CLAUDE.md           # dry-run: prints a unified diff
ctx fix CLAUDE.md --apply   # writes the fix back
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                       ContextOS v4.0                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  AST (Pydantic v2, mypy --strict)                      │     │
│  │  Agent · Skill · RAG · Eval                            │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                 │
│  ┌────────────┬─────────────┬────────────┬────────────────┐     │
│  │  Parsers   │  Analyzers  │  Emitters  │  Eval runners  │     │
│  │  .ctx      │  27 rules   │  8 targets │  Anthropic     │     │
│  │  CLAUDE.md │  A/C/F/K/P/ │  Markdown  │  OpenAI        │     │
│  │  SKILL.md  │  R/S/X/XA   │  JSON      │  Mock          │     │
│  └────────────┴─────────────┴────────────┴────────────────┘     │
│                                                                 │
│  ┌────────────────────────────────────────────────────────┐     │
│  │  Surfaces                                              │     │
│  │  CLI · Python library · LSP server · VSCode extension  │     │
│  │      · GitHub Action · HTML reports                    │     │
│  └────────────────────────────────────────────────────────┘     │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

Three artifact families: **agent context files** · **Anthropic Skills** · **RAG corpora**.
Three operating modes: **structural lint** · **functional eval** · **auto-fix**.
Five consumption surfaces: **CLI** · **Python library** · **LSP** · **VSCode extension** · **GitHub Action**.

## Supported targets

| Target            | Parse | Emit | Filename                              |
|-------------------|:-----:|:----:|---------------------------------------|
| `claude_code`     |  ✅   |  ✅  | `CLAUDE.md`                           |
| `codex`           |  ✅   |  ✅  | `AGENTS.md`                           |
| `cursor`          |  ⏳   |  ✅  | `.cursor/rules/agent.mdc`             |
| `copilot`         |  ⏳   |  ✅  | `.github/copilot-instructions.md`     |
| `cline`           |  ⏳   |  ✅  | `.clinerules`                         |
| `windsurf`        |  ⏳   |  ✅  | `.windsurfrules`                      |
| `anthropic_skill` |  ✅   |  ✅  | `SKILL.md`                            |
| `rag_manifest`    |  N/A  |  ✅  | `rag.manifest.json`                   |

## CLI reference

| Command              | Purpose                                                              |
|----------------------|----------------------------------------------------------------------|
| `ctx parse`          | `.ctx` / Markdown / SKILL.md → AST as JSON or TOML                   |
| `ctx compile`        | `.ctx` → target file (8 supported targets)                           |
| `ctx lint`           | Run the 27 analyzers on a single file                                |
| `ctx diff`           | Semantic AST-level diff of two Documents                             |
| `ctx audit`          | Walk a repo, lint everything, run cross-artifact rules               |
| `ctx stats`          | Aggregate corpus-wide statistics from an audit                       |
| `ctx lsp`            | Language server over stdio (requires `[lsp]` extras)                 |
| `ctx eval`           | Run a `.eval.toml` against a real or mock provider                   |
| `ctx eval-diff`      | Compare two `ctx eval --json` outputs; exit 1 on regression          |
| `ctx fix`            | Auto-apply structured fixes; `--dry-run` default, `--apply` to write |

**Universal flags:** every command has `--json` for machine-readable output.
**HTML reports:** `ctx audit --html` and `ctx eval --html` emit self-contained HTML pages.
**Exit codes:** 0 on success, 1 only when an error-severity diagnostic fires (or a structured failure occurs).

## Project status

| Phase | What                                                          | Status     |
|-------|---------------------------------------------------------------|------------|
| 1     | Parser + AST + Claude emitter                                 | ✅ shipped |
| 2     | 15 lint rules (A / C / F / K / P / X / XA)                    | ✅ shipped |
| 3     | 5 more emitters + diff + audit                                | ✅ shipped |
| 4     | Corpus stats + docs site + **v1.0** launch                    | ✅ shipped |
| 5     | Anthropic Skills (`SKILL.md`) + 6 skill rules                 | ✅ shipped |
| 6     | RAG corpora + 6 RAG rules + **v2.0** launch                   | ✅ shipped |
| 7A    | LSP server + VSCode extension + GitHub Action + **v2.1**      | ✅ shipped |
| 7B    | Live evaluation (Skills + RAG) + **v3.0** launch              | ✅ shipped |
| 8     | PyPI/Marketplace + HTML reports + `ctx fix` + **v4.0** launch | ✅ shipped |
| 9+    | Multi-provider Skills, embedding helpers, PDF in RAG, …       | ⏳ planned |

## Editor integration

ContextOS speaks LSP and ships a VSCode extension wrapping it.

```bash
pipx install 'context-os[lsp]'
```

- **VSCode** — extension at [`extensions/vscode/`](extensions/vscode).
- **Neovim / Helix / Sublime** — three-line LSP client configs in [`docs/editor.md`](docs/editor.md).
- **GitHub CI** — composite Action at [`actions/lint/`](actions/lint):
  ```yaml
  - uses: Jonathanlight/context_os/actions/lint@v4.0.0
  ```
  Posts a sticky audit report as a PR comment.

The 27 lint rules, completion, hover, and quick-fix code actions surface identically in every shape — the editor is just an alternate window onto the same Python core.

## Live evaluation

Move from validating **structure** to validating **behavior**: does the skill actually fire on the right prompts? Does RAG retrieval actually find the expected sources?

```bash
pipx install 'context-os[eval]'

ctx eval skills.eval.toml --dry-run             # mock smoke, no API calls
ctx eval skills.eval.toml --skills-dir skills/  # real Anthropic run
ctx eval-diff baseline.json current.json        # exit 1 on regression
```

- **Skills routing** via the Anthropic Messages API tool-use feature (`ANTHROPIC_API_KEY`).
- **RAG retrieval** via in-process cosine over pre-indexed embeddings (`OPENAI_API_KEY` for query embeddings; bring your own for other vendors via the Python API).
- **Mock providers** drive every test in CI without spending tokens.

See [`docs/eval.md`](docs/eval.md) for the full workflow.

## Visualization & auto-fix

```bash
ctx audit . --html --output audit.html
ctx eval skills.eval.toml --dry-run --html --output eval.html
ctx fix CLAUDE.md          # dry-run unified diff
ctx fix CLAUDE.md --apply  # write fixes
```

See [`docs/dashboard.md`](docs/dashboard.md).

## Docs

- 📚 [Documentation site](https://jonathanlight.github.io/context_os/)
- 🛠 [Getting started](docs/getting-started.md)
- 🧠 [Editor integration](docs/editor.md)
- 🧪 [Live evaluation](docs/eval.md)
- 📺 [Visualization & auto-fix](docs/dashboard.md)
- 📦 [Releasing](docs/release.md)
- 📋 [Rules catalog](docs/rules/index.md)
- 🏛 [Specs](docs/specs/) (Vision · Spec · Architecture · Roadmap)

## Stack

- **Python 3.12+**, `mypy --strict` clean on every file.
- [Pydantic v2](https://docs.pydantic.dev) — strict-typed AST.
- [Typer](https://typer.tiangolo.com) — the `ctx` CLI.
- [mistletoe](https://github.com/miyuchina/mistletoe) — Markdown parser.
- [tomlkit](https://github.com/python-poetry/tomlkit) — TOML preserving comments + order.
- [ruamel.yaml](https://yaml.readthedocs.io) — YAML preserving comments + order (SKILL.md frontmatter).
- [pygls](https://github.com/openlawlibrary/pygls) (optional) — LSP server.
- [anthropic](https://docs.anthropic.com), [openai](https://platform.openai.com), [numpy](https://numpy.org) (optional) — eval runtime.
- pytest + [hypothesis](https://hypothesis.readthedocs.io) — **1129 tests**, 94 % coverage, 1000-example property tests on the round-trip.
- [ruff](https://docs.astral.sh/ruff/) — lint + format.

## Install for development

```bash
git clone git@github.com:Jonathanlight/context_os.git
cd context_os
pip install -e ".[dev]"
pre-commit install
./scripts/check.sh    # ruff + mypy --strict + pytest
```

For the docs site:

```bash
pip install -e ".[docs]"
mkdocs serve   # http://127.0.0.1:8000/
```

## Contributing

Pull requests welcome. Read [`tasks/CONTRIBUTING.md`](tasks/CONTRIBUTING.md) first — ContextOS enforces strict PR discipline (one subject per PR, ≤ 400 lines diff excluding tests, conventional commits prefixed by phase).

## License

MIT — see [LICENSE](LICENSE).

## Author

[Jonathan KABLAN](https://github.com/Jonathanlight) — Senior Full Stack Developer.
