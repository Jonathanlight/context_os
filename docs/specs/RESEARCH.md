# Research — Phase 0 corpus study

This is a working document. It collects observations from a manual audit of
real artifacts in the wild, across the three families. The goal is to ground
the lint rules and emitter mappings in reality, not in opinions.

> **Status:** stub. Five fixtures land in PR `phase0(corpus)`. The full
> Phase 0 audit will reach 40–60 artifacts total (see `ROADMAP.md` Phase 0).

## 1. The three families of artifacts

### 1.1 Agent — instruction files

Per-project files that are always in the LLM's context. Tend to be:

- 500–5000 words
- Markdown with H2 sections (Identity, Stack, Rules, Style, Tools)
- Authored by a single human or a small team
- Updated weekly to monthly
- Read by the LLM at every session start

Canonical examples: `CLAUDE.md`, `AGENTS.md`, `.cursorrules`,
`.github/copilot-instructions.md`, `.clinerules`, `.windsurfrules`.

### 1.2 RAG — pipeline configurations

YAML / JSON / Python files that wire up:

- Embeddings (provider, model, dimensions)
- Vector store (Qdrant, Pinecone, Chroma, pgvector...)
- Chunking strategy (fixed, semantic, recursive)
- Knowledge bases (sources, filters, priorities)
- Retrieval (top_k, score threshold, hybrid)
- Reranking (optional)
- Citation format

Canonical sources: LlamaIndex `RagWorkflow`, LangChain `RetrievalQA`,
Haystack `Pipeline`, raw YAML.

### 1.3 Skill — modular capabilities

Folders containing:

- `SKILL.md` (Markdown body + YAML frontmatter with `name`, `description`)
- Scripts, examples, templates referenced by the body

Activated by the LLM only when the description matches user intent.
Anthropic's canonical format; Cursor commands and GPT custom instructions
are emerging variants.

## 2. Patterns to validate (Phase 0 audit)

### Agent patterns (to be confirmed by audit)

- H2 sections in fixed order: identity, stack, rules, style, tools
- Rules expressed as bullet lists or numbered sections
- Inline severity ("must", "should", "may") sometimes implicit
- Forbidden patterns often in a dedicated `## Forbidden` section

### RAG patterns (to be confirmed)

- Pipeline config in a single YAML file
- Documents organized in `docs/`, `kb/`, or `knowledge-base/`
- Chunk sizes typically 200–800 tokens
- Top-k between 3 and 10
- Reranker absent below ~500 documents

### Skill patterns (to be confirmed)

- Description starts with a verb
- 50–500 words body
- "When to use" + "Files" + "Example invocation" + "Expected output" sections
- Triggers via description match, not explicit keywords

## 2.5 Patterns confirmed by initial fixtures (5 artifacts)

The first audit pass landed 5 fixtures in `tests/fixtures/` (see PR
`phase0(corpus)`). Each was authored from scratch but structurally
informed by a real public reference. Findings:

### Agent family (3 fixtures)

- **Multiple coexisting structural conventions.** A "monorepo" CLAUDE.md
  (LangChain-flavored) uses many H2/H3 sections (Architecture, Tools, PR
  conventions, Core principles, CI/CD), while a "single-maintainer" AGENTS.md
  uses 5–6 short H2 sections (Identity, Stack, Rules, Style, Forbidden).
  Both are legitimate. The parser must heuristic the type, not assume one
  layout.
- **Severity language is inconsistent.** Observed across fixtures:
  - Explicit: "must follow", "CRITICAL", "MUST", "Never"
  - Implicit imperative: "Don't apologize", "Always backtest"
  - Soft: "Prefer", "Use"
  The mapping to `severity ∈ {must, should, may}` requires lexical rules
  (must / never → `must`; should / prefer → `should`; may / can → `may`;
  imperative without modal → `must` by default).
- **Cursor `.mdc` is structurally different.** YAML frontmatter (description,
  globs, alwaysApply) + ALL-CAPS section markers + dense bullet lists. No
  H1/H2. The parser needs a dedicated mapping for `.mdc`.
- **PR conventions live in CLAUDE.md.** Conventional Commits, branching,
  commit titles. These are project-level rules, not code-level. The `[[rules]]`
  schema must accept `applies_to: ["workflow", "vcs"]` cleanly.

### Skill family (1 fixture)

- **Frontmatter is the activation contract.** `name` + `description` drive
  trigger matching; everything in the body is documentation for the LLM
  once activated. The S001 (vague description) and S002 (too generic)
  rules are the most consequential.
- **Body sections converge** around `Overview`, `When to use this skill`,
  `Do NOT use this skill for`, `Workflow` (numbered steps in imperative),
  `Files in this skill` (bullet list referencing real files), `Example
  invocation` (single user prompt), `Expected output` (JSON or template).
- **Anti-pattern: "compatibility" field.** The official Anthropic format
  does not standardize a `compatibility:` field in the frontmatter; this
  fixture pins one to flag the future S-rule. Body-resident runtime
  declarations (e.g. in `Overview`) are the convention.

### RAG family (1 fixture)

- **LlamaIndex is code-configured.** The Python `Settings` singleton sets
  `llm`, `embed_model`, `chunk_size`, `chunk_overlap`, `context_window`,
  `transformations`. There is no canonical YAML/JSON. ContextOS therefore
  defines its **own** portable manifest format (the fixture
  `llamaindex_style_manifest.yaml`), which the `rag_corpus` emitter will
  produce.
- **Embeddings provider lock-in is real.** Voyage / Cohere / OpenAI /
  Anthropic each pin dimensions and API contracts. The manifest captures
  `embedding_dimensions` explicitly to detect mismatches with the vector
  store config.
- **Knowledge base granularity.** A single corpus often has 2–5 distinct
  KBs (leave policy, expenses, onboarding…) with different `when_to_use`
  hints. The manifest supports a list of `knowledge_bases`, each with its
  own glob, refresh frequency, and priority.

### Calibration impact

These observations suggest:

- **S007 threshold** (SKILL.md too long > 200 lines): the fixture lands at
  ~70 lines body. The 200-line ceiling is comfortably above typical good
  skills.
- **Cursor `.mdc` parser is a Phase 3 priority** — it shares no structural
  DNA with the H2-based agent files.
- **Cross-artifact rules** (XA001–XA004) need a richer model than initially
  scoped: the cursor `.mdc` may contradict the CLAUDE.md not literally but
  in spirit (e.g. CLAUDE.md says "use type hints", `.mdc` says "TypeScript
  strict mode" — same intent, different vocabulary). NLI-based detection
  is realistic, lexical-only is not.

## 3. Phase 0 audit methodology

### Sample composition (target: 40–60 artifacts)

#### Agent (30 files)

- 10 from public OSS repos (anthropic/claude-code itself, ray-project, langchain, etc.)
- 10 from awesome lists (`awesome-claude-md`, `awesome-cursorrules`)
- 5 from blog post examples
- 5 from the author's own projects (anonymized)

#### RAG (15 configs)

- 5 LlamaIndex `RagWorkflow` examples
- 5 LangChain `RetrievalQA` examples
- 5 raw YAML manifests from real projects

#### Skill (15 folders)

- 5 official Anthropic Skills examples
- 5 from `awesome-anthropic-skills` (if exists)
- 5 from author's own work

### Per-artifact grid

For each artifact, record:

- URL or path
- Length (words / lines)
- Sections present (vs. expected)
- Rules count and severity distribution
- Top 3 ambiguities found by hand
- Top 3 anti-patterns found by hand
- Notes on emitter mapping (what the format expects)
- License (must be MIT-compatible to ship as fixture)

### Expected output

A spreadsheet `phase0-audit.csv` + a synthesis section in this file,
populated as fixtures land in `tests/fixtures/`.

## 4. Public sources to mine

### Agent

- `awesome-claude-md` (GitHub)
- `awesome-cursorrules` (GitHub)
- `awesome-agents.md` (GitHub)
- Discord servers (Anthropic, OpenAI, Cursor)

### RAG

- LlamaIndex `examples/` directory
- LangChain `cookbook/` directory
- Haystack tutorials
- Public knowledge base examples (Pinecone, Weaviate)

### Skill

- Anthropic Skills GitHub repo
- `awesome-anthropic-skills` (if exists by Phase 0)
- Hacker News "Show HN" posts mentioning skills

## 5. Open questions for Phase 0

- Is there a stable canonical order of sections in `CLAUDE.md`?
- Do real RAG configs declare `freshness_policy`? If not, R006 may need to be `should` instead of `must`.
- What is the median length of a `SKILL.md`? S007 threshold is currently set at 200 lines — to be calibrated.
- How often do real skills include an `example_invocation`? S003 severity depends on this.
- Are there hybrid artifacts (e.g. an `AGENTS.md` that bundles agent context + RAG references)? If yes, parser heuristics must detect.

## 6. Identified risks

1. **Sample bias** — public repos may not reflect production usage.
   Mitigation: weight the audit toward author's own artifacts and explicitly
   note "public-skewed" in the synthesis.
2. **License pollution** — some public artifacts have no license. Cannot
   ship as fixtures. Mitigation: contact authors or rewrite a paraphrase
   that captures the structure without copying.
3. **Tooling drift** — Cursor and Anthropic update their formats faster than
   any spec. Mitigation: pin fixtures to a specific date and source revision.

## 7. Phase 0 checklist

- [ ] 5 fixtures landed in `tests/fixtures/` (PR `phase0(corpus)`)
- [ ] 30 agent files audited and noted in `phase0-audit.csv`
- [ ] 15 RAG configs audited
- [ ] 15 Skills folders audited
- [ ] Synthesis section in this file updated
- [ ] Open questions resolved (or moved to Phase 7+)
- [ ] License compliance verified per fixture
