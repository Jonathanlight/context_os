# ContextOS

> Lint, unify, and study everything you give to an LLM.

ContextOS is a Python toolkit for analyzing, generating, and comparing the
context artifacts that drive LLMs: agent context files (`CLAUDE.md`,
`AGENTS.md`, `.cursorrules`, `.cursor/rules/*.mdc`, `.clinerules`,
`.windsurfrules`, `.github/copilot-instructions.md`), Anthropic Skills, and
RAG corpora configurations.

## What it does

| Surface | Command | Phase |
|---|---|---|
| Parse a `.ctx` source | `ctx parse foo.ctx` | 1 |
| Compile to a target | `ctx compile foo.ctx --target claude_code` | 1 / 3 |
| Lint a file | `ctx lint CLAUDE.md --target claude_code` | 2 |
| Diff two Documents | `ctx diff a.ctx b.ctx` | 3 |
| Audit a repo | `ctx audit .` | 3 |
| Aggregate corpus stats | `ctx stats path/to/corpus` | 4 |

## The five principles

1. **One format, many outputs.** A single `.ctx` source compiles to six target
   formats that stay in sync.
2. **Strict lint, actionable advice.** Every diagnostic carries a concrete
   suggestion and a doc URL.
3. **Semantic, not textual.** A common AST means diffs and audits look at
   intent, not whitespace.
4. **Vendor-independent.** No LLM calls in the core. Heuristics are
   deterministic.
5. **Open source.** MIT.

## Quick example

```bash
pipx install context-os
ctx compile project.ctx --target claude_code --output-dir .
ctx lint CLAUDE.md --target claude_code
ctx audit .
```

See [Getting started](getting-started.md) for the full walk-through, or jump
straight to the [rules catalog](rules/index.md) to see what ContextOS
checks for today.

## Status

🚀 **v1.0.0 shipped.** Phase 1 → Phase 4 deliverables — parser, six
target emitters, 14 single-file lint rules across A / C / F / K / P / X
categories, the XA001 cross-artifact collision rule, semantic diff,
repo audit, corpus stats, and this docs site — are all live. See the
[roadmap](specs/ROADMAP.md) for Phase 5 (Skills) and Phase 6 (RAG).

## Supported targets

- `claude_code` → `CLAUDE.md` (parse + emit + lint)
- `codex` → `AGENTS.md` (parse + emit + lint)
- `cursor` → `.cursor/rules/agent.mdc` (emit only)
- `copilot` → `.github/copilot-instructions.md` (emit only)
- `cline` → `.clinerules` (emit only)
- `windsurf` → `.windsurfrules` (emit only)
- `anthropic_skill` → `SKILL.md` (parse + emit + lint, Phase 5)

RAG support lands in Phase 6.

## License

[MIT](https://github.com/Jonathanlight/context_os/blob/develop/LICENSE) — Jonathan KABLAN, 2026.
