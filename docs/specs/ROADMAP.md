# Roadmap

ContextOS is built in incremental releases. The first release (`v1.0`) ships
context files only, in 13 weeks; Skills and RAG follow as `v1.1` and `v1.2`.

| Release | Goal      | Families covered                       | Target week |
|---------|-----------|----------------------------------------|-------------|
| v1.0    | launch HN | Context files (6 targets)              | 13          |
| v1.1    | iteration | + Skills (Anthropic format)            | 17          |
| v1.2    | iteration | + RAG (audit + manifest)               | 21          |

Total: **~5 months** for the full v1.2. The **launch stays at week 13** —
audience compounds while Skills and RAG land.

Effort: ~12–15 h/week × 21 weeks = **~270 h total**.

---

## Phase 0 — Foundation (Week 1)

Audit 30 agent context files, 10 public Skills folders, and 5 public RAG
corpora. Produce `docs/specs/RESEARCH.md` with patterns observed.

Output:

- `docs/specs/{VISION,SPEC,ARCHITECTURE,ROADMAP,RESEARCH}.md`
- `pyproject.toml`, project skeleton, CI workflow
- `CLAUDE.md` contract at repo root
- 5+ real fixtures across the three families

## Phase 1 — Parser + AST + Claude emitter (Weeks 2–4)

Context family only. The AST already includes Skills and RAG submodels —
just not implemented in parser/emitter yet.

8 milestones (see `tasks/phase1_todo.md`):

1.1 Pydantic v2 AST models
1.2 `.ctx` parser (TOML via tomlkit)
1.3 Diagnostics infrastructure
1.4 Generic Markdown parser with per-target mappings
1.5 Claude emitter with byte-stable output
1.6 Round-trip property tests (`hypothesis`, 1000 examples)
1.7 CLI surface (`ctx parse`, `ctx compile --target claude_code`)
1.8 Release `v0.1.0` on PyPI

**DoD:** `ctx compile project.ctx --target claude_code` produces a valid
`CLAUDE.md`; `ctx parse CLAUDE.md --to-ctx` produces a usable `.ctx`;
round-trip passes 1000 iterations.

## Phase 2 — Context analyzers (Weeks 5–7)

30+ rules across categories A/C/K/X/F/P on the context family. Each rule has:

- Detection logic
- Concrete suggestion
- Documentation page in `docs/rules/<code>.md`
- ≥ 3 unit tests
- ≥ 1 real-fixture regression test

## Phase 3 — Multi-target + diff + audit (Weeks 8–10)

All six agent emitter targets (Claude, Codex, Cursor, Copilot, Cline,
Windsurf). Semantic diff. Repo-level audit with HTML report.

## Phase 4 — Corpus, docs, launch v1.0 (Weeks 11–13)

Public corpus study (40+ artifacts), docs site, launch posts.

**The HN pitch stays focused on context files.** Skills and RAG are
mentioned as "coming next" without diluting attention.

## Phase 5 — Skills (✅ shipped)

**Goal achieved:** `ctx parse SKILL.md`, `ctx lint SKILL.md`,
`ctx compile skill.ctx --target anthropic_skill`, `ctx audit .`
walks `SKILL.md` files, `ctx stats .` reports `anthropic_skill`
coverage.

**Shipped (PRs #44 – #49):**

- AST: `SkillDocument` Pydantic model mirroring SPEC §1.3 verbatim;
  `Document.type` widened to `Literal["agent", "skill"]` with a
  family-slot validator that rejects cross-family payloads (PR #44).
- `.ctx` parser extended: `[[skill]]` blocks validated;
  `SUPPORTED_ARTIFACTS` widened to `{'context', 'skills'}`; `dump_ctx_string`
  honors `type='skill'` (PR #48).
- `SKILL.md` parser: ruamel.yaml frontmatter + mistletoe body;
  title fallback from body H1 for Anthropic-flavored files; verbatim
  body preservation; `ContextOSParseError` with `file:line:column` +
  suggestions on every failure mode (PR #45).
- `SKILL.md` emitter: ruamel `typ='rt'` for key-order preservation;
  byte-stability + idempotence contracts; 200-example hypothesis
  round-trip property test (PR #46).
- Skill analyzers S001–S006:
  - **Description quality** — S001 missing trigger, S002 too short,
    S003 nearing hard cap.
  - **Body / metadata coherence** — S004 missing `example_invocation`,
    S005 body H1 missing or mismatched, S006 redundant
    `trigger_keywords` (PR #47).
- CLI integration across `parse`, `lint`, `compile`, `audit`, `stats`
  (PR #48).
- Docs: one page per S*** rule, getting-started skill example,
  `anthropic_skill` target in the supported-targets table (this PR).

**Deferred to a follow-up phase:**

- 25+ real Skills fixtures (currently 3 fixtures + 200 hypothesis
  examples).
- TF-IDF for S006 overlap (current heuristic is lexical-only).
- tiktoken-aware length warnings (S003 uses character counts).
- 3 ready-made skill templates (data-extraction, code-generation,
  document-conversion).
- Skill cross-artifact rules (audit's XA001 only operates on agent
  files today).

**Anti-goals (unchanged):** no live skill evaluation, no Cursor
commands / GPT custom instructions support.

**DoD met:** full pipeline (parse → lint → emit → re-parse) verified
on 3 fixtures + 200 hypothesis-generated skills; self-audit of the
ContextOS repo produces zero S-rule errors; PRs #44–#49 merge cleanly
to develop.

## Phase 6 — RAG (✅ shipped)

**Goal achieved:** `ctx parse rag.ctx`, `ctx lint rag.ctx`,
`ctx compile rag.ctx --target rag_manifest`, `ctx audit .` walks
`.ctx` files and routes them by family, `ctx stats .` reports `.ctx`
coverage.

**Shipped (PRs #50 – #55):**

- AST: `RagConfig` + `DocumentEntry` + `RagDocument` mirroring SPEC
  §1.4 verbatim; `Document.type` widened to
  `Literal["agent", "skill", "rag"]` with a four-family-ready
  validator. Two AST-level validators enforce
  `chunk_min ≤ target ≤ max` and `reranking_top_k ≤ retrieval_top_k`
  (PR #50).
- `.ctx` parser extended: `SUPPORTED_ARTIFACTS` widened to
  `{context, skills, rag}`; `[rag]` + `[[document]]` blocks
  validated; `dump_ctx_string` honors `type='rag'` (PR #51).
- RAG manifest emitter: `rag.manifest.json` with stable byte output;
  fixed canonical field order matching SPEC; `MANIFEST_VERSION = 1.0`
  pinned (PR #52).
- RAG analyzers R001–R006:
  - **Chunking sanity** — R001 overlap > 50% of target, R002 tight
    headroom under 20%, R006 large source without `header_aware`.
  - **Pipeline completeness** — R003 no freshness_policy, R004 no
    embedding_model, R005 `header_aware` override without anchors
    (PR #53).
- CLI integration across `parse`, `lint`, `compile`, `audit`,
  `stats` (PR #54). Scanner now picks up any `.ctx` file and routes
  by family.
- Docs: one page per R*** rule, getting-started RAG example,
  ROADMAP closed (this PR).
- v2.0.0 release — RAG closes the agent + skill + RAG trio (this PR).

**Deferred to a follow-up phase (Phase 7+):**

- HTML audit report (the JSON renderer is the bridge today).
- Document scanner with MinHash fingerprint + tiktoken-aware chunk
  estimation.
- `chunks.jsonl` estimate output alongside the manifest.
- Similarity heatmap / length distribution visualizations.
- Per-language R*** specializations (current R-rules treat all
  languages identically).
- R007–R017 (the extended R-rule set from the original ROADMAP) —
  the six shipped today cover the highest-impact failure modes.

**Anti-goals (unchanged):** no real embedding, no indexing, no live
retrieval, no PDF support.

**DoD met:** parse → lint → emit → audit pipeline runs end-to-end on
`rag.ctx`; the generated manifest is valid JSON consumers can read in
five lines of Python (`json.load(open("rag.manifest.json"))`).

## Phase 7A — Editor integration (✅ shipped)

**Goal achieved:** ContextOS speaks LSP. Diagnostics, completion,
hover, and quick-fix code actions surface inline in any LSP-aware
editor. CI gets a composite GitHub Action that posts audit reports
as sticky PR comments.

**Shipped (PRs #56 – #61):**

- LSP server skeleton on pygls 2.x with `ctx lsp` CLI entry point;
  optional `[lsp]` extras keep CLI-only users at the baseline
  ~5 MB install. Reuses the existing parsers + analyzers — zero
  parallel implementation that could drift (PR #56).
- LSP completion + hover. Top-level `.ctx` keys, section names,
  value enums (severity / chunking strategies / output formats),
  SKILL.md frontmatter keys. Hover on rule codes (`A001` … `XA001`)
  opens a Markdown blob with doc link (PR #57).
- LSP code actions. Every diagnostic with a suggestion surfaces as
  a quickfix; X003 ships a structured fix that strips the trailing
  `?` from rule titles. Future structured fixes (F001 / X001 / S005
  / C001) layer in via single-branch dispatcher (PR #58).
- VSCode extension. Thin TypeScript wrapper spawning `ctx lsp`
  over stdio. New `contextos-ctx` language ID for `.ctx`;
  `**/SKILL.md` matched by glob so the user's normal Markdown
  workflow stays intact elsewhere. `contextos.command` setting
  for virtualenv pinning. CI step compiles the extension on every
  PR (PR #59).
- `contextos/lint-action` composite Action. yaml-only — no Docker,
  no JavaScript runtime. Runs `ctx audit --json` and posts a
  sticky PR comment via the hidden-marker pattern (one comment
  per PR, updated in place on re-runs). Inputs cover version
  pinning, subpath audit, non-blocking mode, custom token (PR #60).
- Docs (this PR): `docs/editor.md` covering LSP install +
  configuration for VSCode / Neovim / Helix / Sublime; ROADMAP
  closed; v2.1.0 release.

**Deferred to Phase 7B (live evaluation):**

- Live Skills evaluation via Anthropic API (was already deferred).
- Live RAG evaluation via embedding providers (was already deferred).

**Deferred long-tail (no phase planned):**

- Marketplace publication for the VSCode extension (manual
  publisher account + PAT — same model as PyPI trusted publishing
  blocks the v2.0 PyPI publish).
- Marketplace listing for `contextos/lint-action` (manual Action
  publishing UI).
- Additional structured code-action fixes (F001 lowercase, X001
  strip TODO, S005 prepend H1, C001 contradiction rephrase).
- LSP `textDocument/definition` and `documentSymbol` for jump-to-rule.
- `nvim-lspconfig` upstream registration.

**DoD met:** ContextOS is consumable as a CLI, as a Python library,
as a language server, as a VSCode extension, and as a GitHub
Action. All shapes share the same Python core; a diagnostic that
fires in one surfaces identically in all.

## Phase 7B — Live evaluation (✅ shipped)

**Goal achieved:** move from validating **structure** to validating
**functionality**. ContextOS now runs eval suites against the
Anthropic Skills routing API (via tool-use emulation) and against
in-process cosine retrieval over user-supplied embeddings, with a
CI-grade diff command that classifies every case transition.

**Shipped (PRs #62 – #67):**

- `.eval.toml` format + AST: `EvalSuite` (target literal), `SkillCase`
  (prompt + expected_skill), `RagCase` (query + expected_sources +
  top_k). Cross-target validators reject mismatched case lists. Parser
  reuses `ContextOSParseError` so eval-suite mistakes get the same
  `file:line:column` shape as `.ctx` errors (PR #62).
- Anthropic Skills evaluator: `SkillRoutingProvider` Protocol +
  Mock + Anthropic-backed implementation. Tool-use API emulates
  Skills routing — each `SkillDocument` becomes a tool definition
  whose description is the trigger signal; the model's tool choice
  maps to the picked skill slug. Per-case error capture so a
  flaky provider doesn't waste the whole run (PR #63).
- RAG retrieval evaluator: `RagRetrievalProvider` Protocol + Mock
  + `EmbeddingRagProvider` with eager-stacked, row-normalized cosine
  matrix. User supplies the embedding callable + pre-indexed Chunks;
  ContextOS does not ship an embedding service or an indexer.
  OR-semantics over `expected_sources` (PR #64).
- `ctx eval` CLI with dispatch on `suite.target`, `--dry-run`
  Mock providers, JSON / file output, OpenAI-backed query embedding
  via `--rag-embed-model` (PR #65).
- `ctx eval-diff` with five-bucket classification (regression /
  improvement / new_failure / new_pass / removed) and sticky exit
  semantics: regressions always break CI, new failures only with
  `--fail-on-new-failure` (PR #66).
- Docs (this PR): full `docs/eval.md` covering architecture, AST
  shape, dry-run quick start, live Skills + RAG setup, BYO embedding
  service via the Python API, CI flow with eval-diff, troubleshooting.
- v3.0.0 release — Phase 7B closes; ContextOS now ships **structural
  validation + functional evaluation + editor integration**.

**Deferred to Phase 8+:**

- Multi-provider Skills (OpenAI tools, local models) — Anthropic is
  the only Skills backend today.
- Embedding-provider helpers (Voyage / Cohere wrappers in the CLI).
  Users plug their own via the Python API today.
- Eval-set growth tooling (case generation, prompt expansion).
- HTML eval report (the JSON renderer is the bridge today).
- Cost dashboard integration (token totals are exposed; rendering
  them as a series chart is downstream tooling).

**Anti-goals (unchanged):** no live indexing, no PDF support, no
fine-tuning loops.

**DoD met:** `ctx eval suite.toml --dry-run` works on the shipped
fixtures (3/3 pass); live providers ship behind an `[eval]` extras
gate with a clear install message when missing; `ctx eval-diff`
reports regressions and exits 1 on the gate-relevant transitions.

## Phase 8 — Adoption & visualization (✅ shipped)

**Goal achieved:** ContextOS shippable as PyPI + VSCode Marketplace
packages, with HTML reports for audit and eval runs and a
``ctx fix`` command that auto-applies the four structured
code-actions across a repo.

**Shipped (PRs #68 – #73):**

- PyPI publish unblock + release docs: ``release.yml`` documents
  the two supported paths (API token vs trusted publishing), prints
  a workflow notice naming the path it will take, and ships a
  manual ``scripts/publish-to-pypi.sh`` escape hatch for hotfixes
  (PR #68).
- VSCode Marketplace publish workflow: ``vscode-publish.yml``
  triggered on the same ``v*`` tags as ``release.yml``; bumps
  ``package.json`` to match the tag, builds, runs ``vsce publish``
  when ``VSCE_PAT`` is set, degrades to build-only otherwise
  (PR #69).
- HTML audit report: ``ctx audit --html`` renders a self-contained
  page with severity filters, per-file sections, cross-artifact
  + skipped blocks, summary footer. Hand-rolled with
  ``html.escape`` at every interpolation — no jinja2 dep — and
  inline CSS+JS so the output is one drop-in file (PR #70).
- HTML eval report: ``ctx eval --html`` renders cases as a
  filterable table with PASS / FAIL chips, pass-rate progress
  bar, token total badge, drill-down expected/actual per case,
  inline error notes for provider failures (PR #71).
- ``ctx fix`` + structured fixes: F001 (sentence-case ALL CAPS),
  X001 (strip TODO/FIXME markers at title start), X003 (strip
  trailing ?), S005 (prepend ``# <title>`` to SKILL.md body
  lacking H1). Dry-run by default; ``--apply`` writes the new
  content. Walks directories via the audit scanner (PR #72).
- Docs (this PR): ``docs/dashboard.md`` covering both HTML
  reports + the ``ctx fix`` workflow with safety properties and
  a pre-commit hook example.
- v4.0.0 release — Phase 8 closes; ContextOS shipments now span
  PyPI, VSCode Marketplace, GitHub Marketplace (lint-action), and
  self-contained HTML artifacts for downstream consumers.

**Deferred to Phase 9+:**

- Multi-provider Skills (OpenAI tools, local models) — Anthropic
  remains the only Skills backend.
- Embedding-provider CLI helpers (Voyage / Cohere shortcuts) —
  OpenAI is the only built-in.
- LSP code_actions.py / fix.structured.py unification (currently
  X003 has two parallel implementations).
- Additional structured fixes (C001 contradiction rephrase,
  multi-edit refactors like moving URLs out of titles).
- HTML report customization (themes, embeddable widgets).

## Phase 9+ — Post-MVP

- PDF support in RAG.
- Cursor commands, GPT custom instructions.
- LSP definition / documentSymbol for jump-to-rule.
- Web app on `contextos.dev/app`.
- `contextos/scaffold-action` for `ctx compile` in CI.
- Multi-provider Skills (OpenAI tools, local models).
- Embedding-provider CLI helpers.
- LSP/fix de-dup.

---

## Effort estimate

| Phase     | Duration | Python lines | Test lines | Doc lines |
|-----------|----------|--------------|------------|-----------|
| 0         | 1 week   | ~500         | ~100       | ~1700     |
| 1         | 3 weeks  | ~2500        | ~1500      | +500      |
| 2         | 3 weeks  | ~2500        | ~2000      | +1500     |
| 3         | 3 weeks  | ~2500        | ~1500      | +800      |
| 4         | 3 weeks  | ~500         | ~300       | +3000     |
| **v1.0**  | —        | —            | —          | —         |
| 5 Skills  | 4 weeks  | ~2500        | ~1800      | +1200     |
| **v1.1**  | —        | —            | —          | —         |
| 6 RAG     | 4 weeks  | ~3500        | ~2500      | +1800     |
| **v1.2**  | —        | —            | —          | —         |
| **Total** | 21 weeks | ~14500       | ~9700      | ~10500    |

## Communication

| Moment           | Action                                                        |
|------------------|---------------------------------------------------------------|
| Week 13 (v1.0)   | Launch HN, Reddit, X, awesome lists. Pitch = unified context  |
| Weeks 14–17      | Iterate on user feedback + build Skills in parallel           |
| Week 17 (v1.1)   | Skills launch post on Anthropic Discord, share in r/ClaudeAI  |
| Weeks 18–21      | Iterate + build RAG                                           |
| Week 21 (v1.2)   | RAG audit post — data-engineering angle, r/LocalLLaMA / r/LangChain |
| Week 22+         | Conferences, talks (BDX I/O, ParisPHP, FOSDEM)                |

Three moments of visibility, spaced, each coherent with its angle. Audience
compounds across releases instead of being diluted in one launch.
