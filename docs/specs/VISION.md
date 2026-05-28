# Vision

> Lint, unify, and study everything you give to an LLM: **agent context files, skills, and RAG corpora.**

## The problem

A developer working seriously with LLMs in 2026 maintains **three families
of artifacts**, each with its own conventions, and no single tool covers all
three.

### Family 1 — Agent context files

Per-project, per-agent instructions:

- `CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `.github/copilot-instructions.md`,
  `.clinerules`, `.windsurfrules`, `.aider.conf.yml`

### Family 2 — Skills

Modular capabilities, activated on demand:

- Anthropic Skills: `<skill-name>/SKILL.md` folders with YAML frontmatter (`name`, `description`)
- Cursor commands, GPT custom instructions, agent marketplaces (emerging)

### Family 3 — RAG corpora

Knowledge bases injected through retrieval:

- Source documents (`.md`, `.txt`, `.pdf` chunked)
- Pipeline config (chunking, embedding, reranker, top-k)
- Retrieval and reranking prompts

### Shared symptoms

1. **No standard** — every tool invents its own format
2. **No linter** — nothing flags ambiguity, contradiction, redundancy
3. **Duplication** — the same intent rewritten across 3–5 desynchronized formats
4. **No comparative analysis** — no way to measure whether your `CLAUDE.md` or skill is more effective than the average

## What ContextOS does

For each of the three families, ContextOS:

1. **Analyzes** an existing artifact and flags anti-patterns, ambiguities, contradictions, gaps
2. **Compiles** a single `.ctx` source file to the target-specific format of each platform
3. **Compares** two artifacts at the semantic level (not byte-level)
4. **Audits** an entire repository, aggregating diagnostics across the three families
5. **Studies** a public corpus to produce usage statistics (Phase 4)

## The five principles

1. **One format, many outputs** — one `.ctx` source compiles to 6+ synchronized target formats
2. **Strict lint, actionable advice** — every diagnostic carries a concrete suggestion
3. **Semantic, not textual** — common AST, normalized comparison
4. **Vendor-independent** — no LLM calls in the core
5. **MIT open source** — `pipx install context-os-ctx`

## The three families in `.ctx`

A single `.ctx` file can cover one, two, or all three families. Sections are
optional; the `artifacts` field selects which sections the parser expects:

```toml
project = "MyApp"
artifacts = ["context", "skills", "rag"]
targets = ["claude_code", "cursor", "anthropic_skills"]

# Family 1 — context
[identity]   ...
[[rules]]    ...

# Family 2 — skills
[[skill]]    ...

# Family 3 — RAG
[rag]        ...
[[document]] ...
```

Technical details in [`SPEC.md`](./SPEC.md).

## Canonical use cases

### Case 1 — Audit a repo, all families

```bash
$ ctx audit .
─── Agent context ─────────────────────────────────────────
CLAUDE.md:42:1   A001  vague directive "be concise"
AGENTS.md:88:5   C001  contradicts CLAUDE.md rule TDD-001

─── Skills ───────────────────────────────────────────────
skills/pdf-extract/SKILL.md:3:14  S001  description too vague
skills/pdf-extract/SKILL.md:8:1   S004  referenced file missing
skills/pdf-extract/SKILL.md       S006  overlaps with skills/invoice-parse

─── RAG corpus ──────────────────────────────────────────
docs/policies/leave.md           R002  chunk too short (38 tokens)
docs/policies/expenses.md        R005  87% similar to docs/policies/finance.md

Total: 8 issues (3 must-fix, 5 warnings)
```

### Case 2 — Compile to an Anthropic Skill

```bash
$ ctx compile pdf-skill.ctx --target anthropic_skills
✓ wrote skills/pdf-extract/SKILL.md (frontmatter + body)
✓ verified description triggers on: ["pdf", "extract", "invoice"]
```

### Case 3 — Semantic diff of a SKILL.md

```bash
$ ctx diff SKILL.md@v1 SKILL.md@HEAD
~ description: 312 → 187 chars (tighter, improves trigger precision)
+ added 2 usage examples
- removed reference to obsolete file scripts/old.py
```

### Case 4 — Audit a RAG corpus

```bash
$ ctx audit-rag docs/knowledge-base/
Chunking estimate: 412 chunks @ target 500 tokens
Quality issues:
  12 documents under 100 tokens (poor retrieval context)
  3 document pairs > 85% similarity (redundancy)
  47 chunks without H1/H2 anchor (weak retrieval signal)
Suggested actions:
  - merge docs/leave-policy.md + docs/leave-procedure.md
  - add H2 anchors to docs/onboarding-{1..7}.md
```

## Target audience

- Solo devs maintaining `CLAUDE.md` + `AGENTS.md` + `.cursorrules` in parallel
- Teams shipping Anthropic Skills (marketplace, GPT Store, Cursor commands)
- Data / RAG teams auditing their knowledge bases
- Prompt-engineering auditors and consultants

## Non-target

ContextOS does **not** do:

- **LLM hosting or inference** — bring your own platform
- **Retrieval execution** — LangChain, LlamaIndex, Haystack already do this
- **Skill hosting** — marketplaces handle distribution
- **Live skill/RAG evaluation** — post-launch, optional

## The bet

The three families of artifacts proliferate in 2026–2027. Any serious LLM
developer already maintains 5–10 files spread across the families. Without a
unified tool: manual synchronization or abandonment. The unification is the
opportunity.

## License

MIT — Jonathan KABLAN, 2026.
