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

## Phase 5 — Skills (Weeks 14–17, NEW)

**Goal:** `ctx lint skill.md`, `ctx compile skill.ctx --target anthropic_skills`,
`ctx audit skills/`.

Deliverables:

- AST extension: `Skill` Pydantic models
- `.ctx` parser extended: `[[skill]]` section validated
- `SKILL.md` parser: mistletoe + YAML frontmatter; "Files" section detection; "Example invocation" detection; 25+ real Skills fixtures
- Skills analyzer: S001–S010 (TF-IDF for S006 overlap, tiktoken for lengths)
- `anthropic_skills` emitter: creates `skills/<name>/`, generates `SKILL.md` with frontmatter, copies referenced files, verifies existence before copy
- CLI: `ctx lint-skill <path>`, `ctx compile <file.ctx> --target anthropic_skills`, `ctx audit-skills <dir>`
- 3 templates (data-extraction, code-generation, document-conversion)
- Docs: one page per S*** rule, emitter page, "Create a skill with ContextOS" tutorial
- Release `v1.1.0`
- Blog post + share on Anthropic Discord, r/ClaudeAI

**Anti-goals:** no live skill evaluation (Phase 7+), no Cursor commands / GPT
custom instructions support (Phase 7+).

**DoD:** full pipeline on 10 real skills (parse → lint → rewrite); round-trip
property test on skills; self-audit of the ContextOS repo produces ≥ 0
critical issues.

## Phase 6 — RAG (Weeks 18–21, NEW)

**Goal:** `ctx audit-rag <dir>`, `ctx compile <file.ctx> --target rag_corpus`,
portable manifest.

Deliverables:

- AST extension: `RagConfig`, `Document` Pydantic models
- `.ctx` parser extended: `[rag]` and `[[document]]` sections
- Document scanner: directory walk; `[[document]]` glob filtering; `.md` / `.txt` reading (PDF in Phase 7+); MinHash fingerprint; chunk estimation with tiktoken per strategy
- RAG analyzer: R001–R017 (documents R001–R012, config R013–R017)
- `rag_corpus` emitter: `manifest.yaml`, cleaned `docs/`, `chunks.jsonl` estimate, `audit.md` report
- HTML report with similarity heatmap, length distribution, actionable fix list
- CLI: `ctx lint-rag`, `ctx audit-rag`, `ctx compile --target rag_corpus`
- Docs: one page per R*** rule, emitter page, "Prepare a RAG corpus with ContextOS" tutorial
- Release `v1.2.0`
- Blog post + share on r/LocalLLaMA, r/LangChain
- Demo PRs: one LangChain + one LlamaIndex consuming a ContextOS manifest

**Anti-goals:** no real embedding (token estimation only); no indexing; no
live retrieval; no PDF support (Phase 7+).

**DoD:** audit of a real corpus (ContextOS docs + 2 public corpora) produces
an actionable report; generated manifest loadable in LangChain in ≤ 5 lines
of Python.

## Phase 7+ — Post-MVP

- Live Skills evaluation (Anthropic API)
- Live RAG evaluation (eval-set + measured recall)
- PDF support in RAG
- Cursor commands, GPT custom instructions
- LSP server for `.ctx`
- VSCode extension
- GitHub Action `contextos/lint-action@v1`
- Web app on `contextos.dev/app`

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
