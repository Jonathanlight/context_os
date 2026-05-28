# Changelog

All notable changes to ContextOS are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

Nothing yet.

## [4.0.2] — 2026-05-29

README-only re-publish to refresh the PyPI project page.

### Fixed

- README logo now resolves on PyPI. v4.0.1 was uploaded with the
  logo referenced as ``logo.png`` (relative path); PyPI's Camo proxy
  cached that as a dead URL because PyPI doesn't serve repo assets.
  v4.0.1's PyPI README was frozen at upload time so the absolute
  ``raw.githubusercontent.com`` URL that landed on develop after the
  publish couldn't reach PyPI without a fresh version bump. This
  release pushes the corrected README so the logo renders inline on
  the project page.
- No code changes vs v4.0.1.

## [4.0.1] — 2026-05-28

Hotfix release. The shipped feature set is identical to v4.0.0 — this
bump exists so the freshly-renamed distribution can land on PyPI
under `context-os-ctx` without colliding with the v4.0.0 git tag
(which was cut before the rename and would carry the wrong `name:`
in `pyproject.toml`).

### Changed

- **PyPI distribution name renamed** from `context-os` to
  `context-os-ctx`. The `context-os` name on PyPI was already
  reserved by an unrelated project; `context-os-ctx` is free and is
  now the distribution name shipped from this repository.
  - **Import name is unchanged** (`import contextos`).
  - **CLI binary is unchanged** (`ctx`).
  - Install commands across the README, getting-started guide,
    editor / eval docs, the lint-action default, and the local
    publish script all reference the new name.

### Fixed

- `release.yml` (PyPI publish): now uses a `Detect publish mode`
  step that prints which credential path will be attempted.
- `vscode-publish.yml`: dropped `environment: vscode` (which
  required manual setup on the repo) and replaced
  `if: secrets.VSCE_PAT != ''` with the env-indirection pattern
  via `steps.detect.outputs.should_publish`, which is the canonical
  way to use secrets in step-level conditionals. Added
  `workflow_dispatch` for manual runs; non-`v*` ref names skip
  the version-sync step cleanly.
- `docs.yml`: the GitHub Pages deploy steps now `continue-on-error`
  when Pages isn't enabled on the repo. The build still verifies
  on every push; the deploy is best-effort until the operator
  enables Pages in **Settings → Pages → Source = GitHub Actions**.
- Repo-wide `ruff format` pass.

## [4.0.0] — 2026-05-28

📦 **Adoption & visualization.** ContextOS ships to PyPI and the
VSCode Marketplace via configurable release workflows, surfaces
audit and eval results as self-contained HTML pages, and includes
`ctx fix` for auto-applying the four structured code-actions across
a repository.

Major version bump because the conceptual surface expands again —
from "lint + evaluate" to "lint + evaluate + auto-fix + ship." No
backwards-incompatible API changes; every v3.x consumer keeps
working unchanged.

### Added

#### Phase 8 — Adoption & visualization (PRs #68–#73)

- **PyPI publish unblock** (PR #68) — `release.yml` documents the
  two supported paths (API token vs trusted publishing), prints a
  workflow notice naming which path runs, falls through from one
  to the other when only one is configured. New
  `scripts/publish-to-pypi.sh` manual escape hatch.
- **VSCode Marketplace workflow** (PR #69) — `vscode-publish.yml`
  triggered on the same `v*` tags; bumps `package.json` to match
  the tag, builds, runs `vsce publish` when `VSCE_PAT` secret is
  present, degrades to build-only otherwise.
- **HTML audit report** (PR #70) — `ctx audit --html` renders a
  self-contained page with severity filter buttons, per-file
  accordion sections (sorted by path), cross-artifact + skipped
  blocks, summary footer. Hand-rolled with `html.escape` at every
  interpolation — no jinja2 dep — and inline CSS+JS so the output
  is one drop-in file. `--json` and `--html` are mutually
  exclusive.
- **HTML eval report** (PR #71) — `ctx eval --html` renders cases
  as a filterable table with PASS / FAIL chips, pass-rate progress
  bar, token total badge, expected/actual columns, inline error
  notes for provider exceptions.
- **`ctx fix` command + structured fixes F001 / X001 / S005**
  (PR #72) — new fix module with `compute_fix(text, diag) →
  TextEdit | None` dispatcher routing by `diag.code`. Four
  fixes ship today: X003 (strip trailing `?`), F001 (sentence-
  case ALL CAPS title), X001 (strip TODO/FIXME markers at title
  start), S005 (prepend `# <title>` to SKILL.md body lacking H1).
  Dry-run by default; `--apply` writes the new content. Walks
  directories via the audit scanner so the set of fixed files
  matches what `ctx audit` would lint.
- **Docs** (this PR) — `docs/dashboard.md` covering both HTML
  reports + the `ctx fix` workflow with safety properties and a
  pre-commit hook example. `docs/release.md` covers the PyPI +
  VSCode Marketplace setup walkthroughs.

### New CLI subcommands

| Command | What it does |
| --- | --- |
| `ctx fix <target>` | Auto-apply structured fixes; dry-run by default, `--apply` writes |

### Extended CLI

| Command | New flag | Purpose |
| --- | --- | --- |
| `ctx audit` | `--html`, `--output` | Self-contained HTML report; `--json` and `--html` mutually exclusive |
| `ctx eval` | `--html` | Self-contained HTML report; same mutual exclusion |

### New workflows

- `.github/workflows/vscode-publish.yml` — Marketplace publication
  on `v*` tag push.

### Documented limitations

- The LSP `code_actions.py` module still has its own X003
  implementation. A subsequent PR will unify both paths on
  `contextos.fix.structured`. Documented in the fix package
  docstring.
- PyPI publishing still requires a manual one-time setup step
  (either create the `PYPI_API_TOKEN` secret OR configure a
  Trusted Publisher on pypi.org). Documented in `docs/release.md`.
- VSCode Marketplace publishing requires a Marketplace publisher
  account + a Personal Access Token in the `VSCE_PAT` secret.
  Documented in `docs/release.md`.
- No multi-edit fixes today — each diagnostic gets at most one
  `TextEdit`. Multi-step refactors (e.g. moving a URL out of a
  title into `links`) need additional plumbing.

## [3.0.0] — 2026-05-28

🎯 **Functional evaluation.** ContextOS no longer only validates
*structure* (does the skill have trigger phrasing, does the RAG
config have a freshness policy) — it now validates *behavior*. Run
your skills against real Anthropic models and your RAG corpus
against real OpenAI embeddings, score the results, gate CI on
regressions.

Major version bump because the conceptual surface widens: the same
toolchain you use to lint a `CLAUDE.md` now scores whether your
skills actually fire. No backwards-incompatible API changes — every
v2.x consumer keeps working.

### Added

#### Phase 7B — Live evaluation (PRs #62–#67)

- **`.eval.toml` format + AST** (PR #62) — `EvalSuite` with target
  literal (`anthropic_skill` | `rag`), `SkillCase` (prompt +
  expected_skill + tags), `RagCase` (query + expected_sources +
  top_k bounded 1–100). Cross-target model validator rejects
  mismatched case lists. Parser reuses `ContextOSParseError` so
  eval-suite mistakes carry `file:line:column` + suggestion.
- **Anthropic Skills evaluator** (PR #63) — `SkillRoutingProvider`
  Protocol + `MockSkillProvider` (deterministic for tests) +
  `AnthropicSkillProvider` (lazy SDK import, Haiku 4.5 default
  model). Skills routing emulated via the Messages API tool-use
  feature: each `SkillDocument` → tool definition with description
  = trigger signal; tool-use block's name = picked skill slug.
  `SkillEvalRunner` captures per-case errors so a flaky provider
  doesn't waste the whole run.
- **RAG retrieval evaluator** (PR #64) — `RagRetrievalProvider`
  Protocol + `MockRagProvider` + `EmbeddingRagProvider` with
  eager-stacked, row-normalized cosine matrix (each `retrieve()`
  is one matmul). User supplies the embedding callable
  (`EmbedQueryFn = Callable[[str], list[float]]`) and pre-indexed
  `Chunk` list. ContextOS does **not** ship an embedding service
  or an indexer. Pass criterion = OR semantics on
  `expected_sources`.
- **`ctx eval` CLI** (PR #65) — dispatches on `suite.target`,
  `--dry-run` uses Mock providers (every case passes by
  construction), `--json` / `--output` for CI consumption,
  `--skills-dir` walks SKILL.md recursively (sorted-path order for
  deterministic tool ordering), `--rag-chunks` loads pre-indexed
  chunks from JSON, `--rag-embed-model` selects the OpenAI
  embedding model. All eval-side imports lazy so `[eval]` extras
  don't slow down `ctx --version`.
- **`ctx eval-diff` for regression detection** (PR #66) — compare
  two eval result JSON files; classify case transitions into five
  buckets (regression / improvement / new_failure / new_pass /
  removed). Default CI gate: exit 1 on regression only;
  `--fail-on-new-failure` flag opt-in for stricter gating. Sticky
  comment shape compatible with PR review workflows.
- **Docs page** (this PR) — `docs/eval.md` covering architecture,
  `.eval.toml` grammar, dry-run quick start, live Skills + RAG
  setup, BYO embedding service via Python API, CI workflow with
  `eval-diff`, troubleshooting table.

### New CLI subcommands

| Command | What it does |
| --- | --- |
| `ctx eval <suite.eval.toml>` | Run an eval suite; `--dry-run` for mock-driven smoke |
| `ctx eval-diff <baseline> <current>` | Compare two eval JSON outputs; exit 1 on regression |

### New optional-dependencies group

- `[eval] = ["anthropic>=0.40", "numpy>=1.26", "openai>=1.0"]`.

### Documented limitations

- **Skills routing** is emulated via the Messages API tool-use
  feature, not the actual Skills product (which lives in Claude app
  / Claude Code, not the public API). Tool selection is the closest
  approximation; the gap is documented in
  `anthropic_provider.py:9`.
- **OpenAI is the only built-in embedding provider in the CLI**.
  Voyage / Cohere / local-model users drop down to the Python API
  (one `EmbeddingRagProvider(chunks, embed_query)` call). Documented
  in `docs/eval.md`.
- **No indexer ships with ContextOS** — users feed pre-indexed
  chunks via `--rag-chunks chunks.json`. The chunks file is
  whatever the user's pipeline produces; we validate the shape and
  cosine over what's there.
- **No HTML eval report**; the JSON renderer is the bridge today.

## [2.1.0] — 2026-05-28

🛠️ **Editor integration.** ContextOS now ships as a language server
(`ctx lsp`), a VSCode extension wrapping it, and a composite GitHub
Action that posts audit reports as sticky PR comments. The 27 lint
rules and the underlying parsers / analyzers are unchanged — this
release is purely about getting them where authors actually work.

### Added

#### Phase 7A — Editor integration (PRs #56–#61)

- **LSP server** on pygls 2.x (`src/contextos/lsp/`). Reacts to
  `didOpen` / `didChange` / `didSave`; dispatches `.ctx` →
  `parse_ctx_string` (which itself routes by `artifacts` family —
  agent / skill / rag all work) and `SKILL.md` → `parse_skill_string`.
  ContextOS Position (1-indexed) ↔ LSP Position (0-indexed)
  conversion centralized in `diagnostics_adapter`. `ContextOSParseError`
  surfaces as `E0001` so parse failures shape identically to analyzer
  diagnostics.
- **LSP completion** for `.ctx` top-level keys, section names
  (`[rag]`, `[[skill]]`, `[[document]]`, …), and value enums (severity
  / chunking strategies / output formats), plus `SKILL.md` YAML
  frontmatter keys. Value enums and field names derive from the AST
  Literals so a SPEC change ripples through completion without manual
  sync.
- **LSP hover** on any rule code in the file (`A001`, `S005`, `XA001`,
  …) opens a Markdown blob linking to the docs page. The conservative
  regex (`^[A-Z]{1,2}\d{3,}$`) covers all 27 shipped codes.
- **LSP code actions**. Two tiers: an info-only quickfix for every
  diagnostic with a suggestion (title surfaces in the lightbulb
  menu), plus a structured fix for **X003** (strip the trailing `?`
  from rule titles). Future structured fixes layer in via the
  single-branch dispatcher (F001 / X001 / S005 / C001 are listed in
  the code-actions module docstring).
- **`ctx lsp` CLI subcommand**. Lazy `pygls` import with a clear
  recovery message (`pipx install context-os[lsp]`) when the extras
  aren't installed.
- **New optional-dependencies group**: `[lsp]` (currently `pygls>=2.0`).
  `dev` extras gains `pygls` so the test suite runs.
- **VSCode extension** at `extensions/vscode/`. TypeScript wrapper
  spawning `ctx lsp` over stdio. New `contextos-ctx` language ID for
  `.ctx`; `**/SKILL.md` matched via glob so the user's normal
  Markdown workflow stays authoritative elsewhere. Settings:
  `contextos.command`, `contextos.trace.server`. Command:
  `contextos.restartServer`. CI step compiles the extension on every
  PR (new `vscode-extension` job in `.github/workflows/ci.yml`).
- **`contextos/lint-action`** composite GitHub Action at
  `actions/lint/`. yaml-only: `setup-python` + `pip install` +
  `ctx audit --json` + `github-script` for the PR comment. **Sticky
  comment** pattern via hidden HTML marker so re-runs of the same
  PR update the existing comment in place — no comment spam.
  Inputs cover `path`, `python-version`, `context-os-spec` (overridable
  for version pins / editable installs / git URLs), `fail-on-error`,
  `comment-on-pr`, `github-token`. Outputs `exit-code`,
  `diagnostic-count`, `audit-json-path`.

### Docs

- New `docs/editor.md` page covering LSP install, VSCode setup,
  Neovim lspconfig snippet, Helix `languages.toml` config, Sublime
  LSP config, what-you-get summary, and a troubleshooting table.
- ROADMAP closes Phase 7A and pencils in Phase 7B (live evaluation).

### Documented limitations

- VSCode Marketplace publication for the extension stays a manual
  step out of CI (publisher account + `VSCE_PAT` token — same model
  as the PyPI trusted-publishing flow that gates the v2.0 PyPI
  publish).
- `contextos/lint-action` Marketplace listing stays manual until the
  Action publishing UI is run.
- `nvim-lspconfig` upstream registration not yet submitted; users
  configure via the `lspconfig.configs` table for now.
- Additional structured code-action fixes (F001 / X001 / S005 / C001)
  enumerated in `code_actions.py` for future PRs.

## [2.0.0] — 2026-05-28

🚀 **The full trio shipped.** ContextOS v2.0 covers all three families
of LLM context artifacts: **agent files**, **Anthropic Skills**, and
**RAG corpora**. The CLI surface, AST, parsers, emitters, and 27 lint
rules treat them uniformly under one toolchain.

This release stacks on top of v1.0 (Phase 1–4 deliverable, see below)
with everything that landed in Phase 5 (Skills) and Phase 6 (RAG).

### Added

#### Phase 5 — Anthropic Skills (PRs #44–#49)

- AST: `SkillDocument` Pydantic model mirroring SPEC §1.3 verbatim;
  `Document.type` widened to admit `"skill"` with a family-slot
  validator rejecting cross-family payloads.
- `.ctx` parser supports `[[skill]]` blocks; `dump_ctx_string` honors
  `type='skill'`.
- `SKILL.md` parser using ruamel.yaml frontmatter + mistletoe body;
  body title fallback from first H1; verbatim body preservation.
- `SKILL.md` emitter with byte stability + parse → emit → parse
  idempotence; 200-example hypothesis round-trip test.
- Skill analyzers S001–S006: description trigger phrasing, length
  floor / ceiling, missing example_invocation, body H1 mismatch,
  redundant trigger_keywords.
- CLI integration: `parse`, `lint`, `compile --target anthropic_skill`,
  `audit`, `stats` all dispatch SKILL.md files.
- Six rule docs pages + getting-started skill example + mkdocs nav.

#### Phase 6 — RAG corpora (PRs #50–#55)

- AST: `RagConfig` (chunking, embedding, reranking, freshness),
  `DocumentEntry` (source glob + tags + anchors), `RagDocument`.
  `Document.type` widens to admit `"rag"`.
- Two AST-level invariants enforced: `chunk_min ≤ target ≤ max` and
  `reranking_top_k ≤ retrieval_top_k`.
- `.ctx` parser supports `[rag]` + `[[document]]` blocks.
- RAG manifest emitter — `rag.manifest.json` consumed by external
  indexers (Qdrant, Pinecone, custom). `MANIFEST_VERSION` is `"1.0"`
  pinned.
- RAG analyzers R001–R006: excessive chunk overlap, tight target/max
  headroom, missing freshness_policy, missing embedding_model,
  header_aware override without anchors, large source without
  override.
- CLI integration: `parse`, `lint`, `compile --target rag_manifest`,
  `audit`, `stats`. Audit scanner picks up any `.ctx` file and
  routes by family.
- Six rule docs pages + getting-started RAG example + mkdocs nav.

### Changed

- CLI now supports **eight** targets (`claude_code`, `codex`,
  `cursor`, `copilot`, `cline`, `windsurf`, `anthropic_skill`,
  `rag_manifest`).
- Lint surface grows to **27 rules** across **seven categories**:
  Ambiguity (A), Contradiction (C), LLM-friendliness (F),
  Completeness (K), Platform (P), RAG (R), Skill (S), plus
  cross-artifact XA001.

### Documented limitations

- HTML audit report (JSON renderer is the bridge today).
- Document scanner with MinHash fingerprint + tiktoken-aware chunk
  estimation.
- `chunks.jsonl` estimate alongside the RAG manifest.
- 25+ real Skills fixtures (currently 3 + 200 hypothesis examples).
- Per-language R*** specializations.
- Skill / RAG cross-artifact rules (XA001 still only covers agent
  files).
- Live evaluation, indexing, retrieval (anti-goals — Phase 7+).

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
  `AgentDocument` aggregate. All models are `extra="forbid"` so a typo
  surfaces as a parse error rather than silently dropping.
- **`.ctx` parser** (`contextos.parsers.ctx_parser`) using `tomlkit` so
  comment-preserving round-trips are possible. `parse_ctx_file` /
  `parse_ctx_string` / `dump_ctx_string`. `ContextOSParseError` carries
  a `Position` + a free-form `suggestion` so the CLI prints
  rustc-style diagnostics (`file:line:col`, did-you-mean hints on
  unknown root fields).
- **Generic Markdown parser** (`contextos.parsers.markdown_parser`)
  using `mistletoe` + per-target TOML mappings under
  `parsers/targets/mappings/`. Adding a new agent target is a TOML
  drop-in — no code change. `claude_code` and `codex` mappings ship
  by default.
- **Diagnostics** (`contextos.diagnostics`) — `Diagnostic`,
  `DiagnosticBag`, `DiagSeverity` enum (`error`, `warning`, `info`).
  CLI renderer with optional ANSI colors and a JSON renderer for CI
  consumption.
- **`emit_claude_markdown`** (`contextos.emitters.claude`) —
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
