# Changelog

All notable changes to ContextOS are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

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
