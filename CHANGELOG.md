# Changelog

All notable changes to ContextOS are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [1.0.0] — 2026-05-28

🚀 **First production release.** Phase 1 through Phase 4 deliverables —
the full agent-family toolchain: parse, lint, compile across six target
formats, semantic diff, repo-level audit, and corpus-wide stats. The
public docs site is live at <https://jonathanlight.github.io/context_os/>.

601 tests, mypy --strict clean on 84 source files, 94 % coverage.

### Added

#### Phase 2 — Lint rules (15 codes across six categories)

- **Ambiguity (A)** — `A001` vague directive, `A002` subjective
  adjective, `A003` vague quantifier, `A004` hedging cadence.
- **Contradiction (C)** — `C001` antonym overlap heuristic (~80 %
  precision; NLI-based detection lands post-MVP).
- **LLM-friendliness (F)** — `F001` excessive ALL CAPS, `F002` rule
  title too long, `F003` duplicate rule.
- **Completeness (K)** — `K001` no rules declared, `K002` must-rule
  without rationale, `K003` must-rule without examples (INFO).
- **Anti-pattern (X)** — `X001` placeholder marker (TODO/FIXME),
  `X002` unfilled template placeholder, `X003` question instead of
  directive.
- **Platform (P)** — `P001` personal absolute path, `P002` email
  address in title, `P003` bare URL in title.
- **Cross-artifact (XA)** — `XA001` rule id collision across files
  (audit only).

Each rule ships a `docs/rules/<code>.md` reference page with trigger,
why-it-matters, suggested fix, and tuning knobs.

#### Phase 3 — Multi-target emitters

- `codex` → `AGENTS.md` (parse + emit + lint).
- `cursor` → `.cursor/rules/agent.mdc` (emit only — `.mdc` parser is
  Phase 5+).
- `copilot` → `.github/copilot-instructions.md` (emit only).
- `cline` → `.clinerules` (emit only).
- `windsurf` → `.windsurfrules` (emit only).

A private `_agent_base.py` exports the shared flat-Markdown emit logic
the codex / copilot / cline / windsurf wrappers reuse. `claude_code`
keeps its own H3-sub-section layout under Stack / Tools.

#### Phase 3 — Semantic diff

- `ctx diff <a> <b>` — structured AST-level diff between two
  Documents. Reports project / identity / stack-bucket / rule
  added-removed-modified / style / forbidden_patterns / tools changes.
- Rule diffs cover title, severity, rationale, applies_to, and tags
  changes per rule, matched by `Rule.id`.
- `--json` flag for CI consumption (Pydantic model_dump_json, sort_keys).

#### Phase 3 — Repo audit

- `ctx audit <root>` — walks a repository, parses every recognized
  agent file, runs per-file analyzers + cross-artifact rules.
- `ProjectInferred` data model aggregates every artifact found.
- Skipped files (`.cursorrules`, `.clinerules`, `.windsurfrules`,
  `.github/copilot-instructions.md`) listed explicitly so coverage
  gaps stay visible.
- `--json` shape for downstream dashboards / Markdown-to-HTML
  generators.
- XA001 fires when the same `Rule.id` appears in multiple files with
  conflicting (title, severity) signatures.

#### Phase 4 — Corpus stats

- `ctx stats <root>` — rolls an audit report into per-severity counts,
  top diagnostic codes (sorted by frequency, ties lexicographic), per-
  file rule counts, and target coverage.
- `--top N` flag for the top-codes count (default 10).
- `--json` for machine consumption.

#### Phase 4 — Documentation site

- MkDocs Material site auto-deployed by `.github/workflows/docs.yml`
  on push to `develop` or `main`.
- Landing page, five-minute getting-started tutorial, rules catalog
  with one page per code, and the five spec pages (Vision, Spec,
  Architecture, Roadmap, Research) all wired into the navigation.
- New `docs` optional-dependencies extra (`mkdocs>=1.5`,
  `mkdocs-material>=9.0`) — opt-in, doesn't bloat the runtime install.

#### Phase 4 — README launch polish

- CI / Docs / PyPI / Python / MIT badges.
- "Why ContextOS" framing with the three-families problem.
- Five-minute tour with verbatim CLI output for `lint`, `diff`,
  `audit`, and `stats`.
- Phase status matrix and supported-targets parse/emit table.

### Changed

- `Development Status` classifier moves from `3 - Alpha` to
  `5 - Production/Stable`.
- CLI surface is now seven commands: `parse`, `compile`, `lint`,
  `diff`, `audit`, `stats`, `--version`.
- Severity contract: every command exits 1 only when an error-severity
  diagnostic fires. Warnings and info do not break CI by default.

### Notable design decisions

- Function-form emitters (not a class hierarchy) for the agent family.
  `_agent_base.emit_flat_agent_markdown` is the canonical shared
  implementation; each target's named function is a thin wrapper for
  CLI dispatch.
- Rule severity is preserved across a Markdown round-trip by
  prefixing the title with `Must` / `Should` / `May` when the original
  title's leading word doesn't already imply the severity.
- Cross-artifact rules live in the audit, not in the per-file lint.
  Stats aggregates over the audit so neither the scanner nor the
  analyzer pipeline runs twice.

### Documented limitations (rolled to Phase 5+)

- Anthropic Skills (`SKILL.md` parsing + emit + lint) — Phase 5.
- RAG corpora (`rag_config.*` parsing + audit + manifest emit) —
  Phase 6.
- Parsers for cursor / copilot / cline / windsurf — Phase 5+ (formats
  are structurally different enough from `CLAUDE.md` to warrant
  per-target walkers).
- HTML audit report — JSON renderer is the bridge today; a downstream
  Markdown-to-HTML converter consumes the JSON.
- NLI-based contradiction detector (planned upgrade path for C001).

## [0.1.0] — 2026-05-27

Phase 1 deliverable. ContextOS now parses a `.ctx` source, walks an
existing `CLAUDE.md`, and compiles either back to a stable `CLAUDE.md`
through a strict-typed Pydantic AST. The full pipeline is covered by
1000 hypothesis-generated round-trip examples and is exposed through
the `ctx` CLI.

### Added

- **AST** — Pydantic v2 models for the context family: `Severity` enum
  (must / should / may), `Position` (frozen, file/line/column), `ProseBlock`,
  and the context-family submodels `Identity`, `Stack`, `Style`, `Tools`,
  `Rule` (regex-validated `id` matching `^[A-Z]+-\d{3,}$`), and the
  composing `AgentDocument` and root `Document`. All models are strict
  (`extra="forbid"`), JSON round-trippable, and 100 % covered.
- **`.ctx` parser** (`contextos.parsers.parse_ctx_file` /
  `parse_ctx_string`) — TOML source via `tomlkit`, builds a `Document` and
  preserves per-rule line positions. Did-you-mean hints via `difflib` on
  unknown root, section, and rule fields; type-aware messages
  (`"languages" expected array, got int`); typed `ContextOSParseError`
  with optional `Position` and `suggestion`.
- **`.ctx` dumper** (`contextos.parsers.dump_ctx_string`) — round-trips
  the AST back to canonical TOML. Not byte-stable (drops defaults +
  empty lists) but semantic-stable for parse → dump → parse.
- **11 `.ctx` fixtures** in `tests/fixtures/ctx/` (4 valid + 7 invalid)
  exercising the happy path and every diagnostic shape.
- **Diagnostics infrastructure** — `DiagSeverity` (error / warning / info,
  distinct from rule severity), `Diagnostic` frozen + hashable Pydantic
  model with regex-validated codes (e.g. `S001`, `XA001`),
  `DiagnosticBag` mutable collector with `add` / `extend` / `count` /
  `has_errors` / `sorted` / iteration. Rustc-style CLI renderer with ANSI
  colors gated by a caller-supplied flag; optional source-text preview
  with column caret. JSON renderer matching SPEC.md §3 shape.
- **Markdown parser** (`contextos.parsers.parse_markdown_file` /
  `parse_markdown_string`) — generic walk over `mistletoe` AST driven by
  per-target TOML mappings under `src/contextos/parsers/targets/mappings/`.
  Ships the `claude_code` mapping; six recognised sections with H3
  sub-sections on stack and tools; severity inferred lexically from
  leading words. Six representative `CLAUDE.md` fixtures.
- **CLAUDE.md emitter** (`contextos.emitters.emit_claude_markdown`) —
  byte-stable Markdown emission with `Must` / `Should` / `May` prefixing
  so the parser recovers the original severity. Empty sub-models
  collapse silently for round-trip stability.
- **Round-trip property tests** under `tests/integration/` — 1000
  hypothesis examples verifying `parse_markdown(emit(doc))` preserves
  the semantic shape; 200 examples verifying `emit` is idempotent after
  one parse round-trip.
- **CLI** (`contextos.cli`, exposed as the `ctx` console script):
  - `ctx parse <file>` — JSON or `.ctx` via `--to-ctx`; auto-detects
    `.ctx` vs Markdown; Markdown requires `--target`. `--output`
    redirects to a file.
  - `ctx compile <file.ctx> --target claude_code` — stdout by default;
    `--output-dir` writes `CLAUDE.md` (parents auto-created);
    `--dry-run` previews without touching the filesystem.
  - `ctx --version` / `-V`.
- **Project tooling** — `pyproject.toml` with hatchling build, strict
  ruff config, `mypy --strict`, pytest + hypothesis + coverage floor 85 %.
  Pre-commit hooks for ruff + mypy. CI on GitHub Actions for lint /
  typecheck / test across Python 3.12 and 3.13.

### Lossy fields (documented limitations)

The bullet-rule Markdown format cannot carry `Rule.id`, `rationale`,
`detail`, `example_good`, `example_bad`, `tags`, `links`, `position`,
`applies_to`. Document-level: `ctx_version`, `languages`, `authors`,
`version`. `AgentDocument.prose` is not emitted. A round-trip preserves
project name, identity role, stack / style / tools / forbidden_patterns
buckets, and the sequence of rule severities. A richer target with
H3-per-rule emission can land later if needed.

### Not yet covered

- Targets other than `claude_code` (Phase 3).
- Lint rules (Phase 2 ships 30+ across A / C / K / X / F / P / S / R / XA).
- Skills (Phase 5) and RAG (Phase 6) families.
- Live LLM evaluation (Phase 7+).

[Unreleased]: https://github.com/Jonathanlight/context_os/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Jonathanlight/context_os/releases/tag/v0.1.0
