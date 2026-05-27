# Phase 1 — Parser + AST + Emitter Claude

**Goal:** ship `ctx parse` and `ctx compile --target claude_code` with a
round-trip property test that passes on 1000 hypothesis iterations. Release
`context-os v0.1.0` on PyPI.

**Estimated duration:** 3 weeks (semaines 2-4).

**Reference:** `docs/specs/ROADMAP.md` Phase 1 section.

---

## Milestone 1.1 — AST models (2 days)

- [ ] `src/contextos/ast/nodes.py` — Pydantic v2 models for `Severity`, `Position`, `Rule`, `Identity`, `Stack`, `Style`, `Tools`, `ProseBlock`, `Document`
- [ ] All fields strictly typed
- [ ] Pydantic validators for constraints (e.g. `id` matches `^[A-Z]+-\d{3,}$`)
- [ ] `model_config = ConfigDict(extra="forbid")` on all models
- [ ] `tests/ast/test_nodes.py` — 20+ tests (valid creation, unknown field rejection, JSON round-trip, ID/severity validators)
- [ ] PR: `phase1(ast): pydantic v2 models for ContextOS AST`

## Milestone 1.2 — `.ctx` parser (4 days, split in 2 PRs)

### 1.2a — Core
- [ ] `src/contextos/parsers/ctx_parser.py` API: `parse_ctx_file(path: Path) -> Document`, `parse_ctx_string(content: str, source: str) -> Document`
- [ ] Use `tomlkit` to preserve order + comments
- [ ] Build `Document` Pydantic with `Position` for each `[[rules]]`
- [ ] `ContextOSParseError` class with position + suggestion
- [ ] PR: `phase1(parsers): ctx TOML parser core`

### 1.2b — Errors + fixtures
- [ ] Error messages for: invalid TOML, missing required field, unknown field (with `did you mean`), incorrect type
- [ ] `tests/fixtures/ctx/` — 10 representative `.ctx` files
- [ ] 30+ test cases: valid files, schema errors, round-trip TOML → AST → TOML
- [ ] PR: `phase1(parsers): ctx parser errors + fixtures`

## Milestone 1.3 — Diagnostics infrastructure (2 days)

- [ ] `src/contextos/diagnostics/diagnostic.py` — `DiagSeverity` enum, `Diagnostic` Pydantic model, `DiagnosticBag` collector
- [ ] `src/contextos/diagnostics/renderer_cli.py` — `rustc`-style with rich colors and underlining
- [ ] `src/contextos/diagnostics/renderer_json.py` — machine-readable output
- [ ] 15+ tests (creation, serialization, golden file rendering)
- [ ] PR: `phase1(diagnostics): infrastructure for typed errors`

## Milestone 1.4 — Generic Markdown parser (3 days)

- [ ] `src/contextos/parsers/markdown_parser.py` API: `parse_markdown_file(path: Path, target: str) -> Document`
- [ ] Use `mistletoe` for Markdown
- [ ] Identify H2 sections by title heuristic per target
- [ ] Target mappings in YAML: `src/contextos/parsers/targets/mappings/claude.yaml`
- [ ] `tests/fixtures/claude/` — 25+ real fixtures
- [ ] Tests: identity extraction, stack extraction, rules extraction, absence detection, false positives
- [ ] PR: `phase1(parsers): markdown parser with target-specific mappings`

## Milestone 1.5 — Claude emitter (3 days)

- [ ] `src/contextos/emitters/claude.py` — `ClaudeMdEmitter.emit(doc: Document) -> str`
- [ ] Sections: `# CLAUDE.md — {project}`, `## Identity`, `## Stack`, `## Rules`, `## Style`, `## Forbidden patterns`, `## Tools`
- [ ] Stable output: same AST → same Markdown byte-for-byte
- [ ] Tests: snapshots on 10 `.ctx` fixtures, section order, empty/minimal cases
- [ ] PR: `phase1(emitters): CLAUDE.md emitter with stable output`

## Milestone 1.6 — Round-trip property tests (2 days)

- [ ] `tests/integration/test_roundtrip_claude.py`
- [ ] `hypothesis` strategy `arbitrary_document()` generating varied `Document`s
- [ ] `semantically_equivalent()` comparing two `Document`s modulo stable order
- [ ] `@given(arbitrary_document()) @settings(max_examples=1000)` passes
- [ ] PR: `phase1(tests): round-trip property tests with hypothesis`

## Milestone 1.7 — CLI (2 days)

- [ ] `src/contextos/cli/__init__.py` with Typer subcommands:
  - [ ] `ctx parse <file>` — parse + display AST in JSON or TOML
  - [ ] `ctx parse <file> --to-ctx` — rewrite as `.ctx`
  - [ ] `ctx compile <file.ctx> --target claude_code` — emit `CLAUDE.md`
  - [ ] `ctx compile <file.ctx> --target claude_code --output-dir ./out`
  - [ ] `ctx compile <file.ctx> --target claude_code --dry-run`
  - [ ] `ctx --version`
- [ ] 15+ CLI tests via `typer.testing.CliRunner`
- [ ] PR: `phase1(cli): basic CLI for parse and compile`

## Milestone 1.8 — Release v0.1.0 (1 day)

- [ ] Bump version in `pyproject.toml`
- [ ] `CHANGELOG.md` first entry
- [ ] Git tag `v0.1.0` on `main`
- [ ] Build wheel + sdist
- [ ] Upload to PyPI (requires `PYPI_API_TOKEN` GitHub secret)
- [ ] GitHub Release with notes
- [ ] PR: `phase1(release): v0.1.0`

---

## Done-of-phase

- [ ] `ctx compile project.ctx --target claude_code` produces a valid `CLAUDE.md`
- [ ] `ctx parse CLAUDE.md --to-ctx` produces an exploitable `.ctx`
- [ ] Round-trip property test passes on 1000 hypothesis iterations
- [ ] `context-os v0.1.0` published on PyPI
- [ ] Coverage ≥ 85 %
- [ ] All 8 milestones merged
