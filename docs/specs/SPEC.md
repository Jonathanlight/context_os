# Specification — `.ctx` format and lint taxonomy

This is the authoritative specification. In case of contradiction with any
other document, **`SPEC.md` wins**.

## 0. Changelog

| Version | Date    | Change                                                   |
|---------|---------|----------------------------------------------------------|
| v0.1    | initial | `.ctx` format for agent context files                    |
| v0.2    | —       | 30+ lint rules, 6 emitter targets                        |
| **v0.3**| current | Add `[[skill]]`, `[rag]`, `[[document]]` sections        |

## 1. Source file format `.ctx`

A `.ctx` file is a **TOML + embedded Markdown** document, readable by both
humans and LLMs. It describes intent independently of the target platform.

### 1.1 Root fields

```toml
project       = "MyApp"
artifacts     = ["context", "skills", "rag"]   # one or more of the three families
languages     = ["PHP", "Symfony", "Twig"]
authors       = ["Jonathan KABLAN"]
targets       = ["claude_code", "cursor", "anthropic_skills"]
version       = "1.3.0"
ctx_version   = "0.3"
```

The `artifacts` field determines which sections are expected:

- `"context"` → `[identity]`, `[stack]`, `[[rules]]`, `[style]`, `[forbidden_patterns]`, `[tools]`
- `"skills"` → `[[skill]]`
- `"rag"` → `[rag]`, `[[document]]`

### 1.2 Family 1 — Context

Sections:

- `[identity]` — role, context, author
- `[stack]` — required, forbidden, preferred technologies
- `[[rules]]` — array of rules, each with `id`, `title`, `severity`, `applies_to`, `rationale`, `detail`, `example_good`, `example_bad`, `tags`, `links`
- `[style]` — code style conventions
- `[forbidden_patterns]` — anti-patterns to reject
- `[tools]` — required tooling

Rule `id` follows the regex `^[A-Z]+-\d{3,}$` (e.g. `TDD-001`, `SEC-042`).

`severity` ∈ `{must, should, may}`.

### 1.3 Family 2 — Skills

```toml
[[skill]]
name           = "pdf-extract"             # required, kebab-case
title          = "PDF invoice extraction"  # required, human-readable
description    = """
Extract structured data (vendor, total, tax, line items) from PDF invoices
in French or English. Triggers when the user asks to parse, extract, or
process an invoice PDF.
"""                                         # required, ≤ 1024 chars, starts with a verb
trigger_keywords    = ["pdf", "invoice", "extract", "facture"]
applies_to          = ["data-extraction"]
languages_supported = ["fr", "en"]
files          = [
  "scripts/extract.py",
  "examples/invoice_fr.pdf",
  "examples/invoice_en.pdf",
]
required_runtime       = "python>=3.10"
example_invocation     = "Extract the line items from this invoice.pdf"
expected_output_format = "json"
tags = ["data", "pdf", "extraction"]
```

Required fields: `name`, `title`, `description`.
Recommended for the `anthropic_skills` target: `trigger_keywords`, `files`,
`example_invocation`.

### 1.4 Family 3 — RAG

#### 1.4.1 `[rag]` — pipeline configuration

```toml
[rag]
chunking_strategy     = "semantic"        # "fixed" | "semantic" | "header_aware"
chunk_target_tokens   = 500
chunk_overlap_tokens  = 50
chunk_min_tokens      = 100
chunk_max_tokens      = 1500
embedding_model       = "voyage-3"
embedding_dimensions  = 1024
vector_store          = "qdrant"          # informational — not executed by ContextOS
reranker              = "cohere-rerank-3"
retrieval_top_k       = 10
reranking_top_k       = 3
freshness_policy      = "30d"             # documents older than 30d marked stale
language_default      = "fr"
```

#### 1.4.2 `[[document]]` — source declaration

```toml
[[document]]
source             = "docs/policies/**/*.md"  # glob
tags               = ["policy", "internal"]
freshness_required = "30d"
chunking_override  = "header_aware"
required_anchors   = ["##"]                   # requires H2 minimum for retrieval quality
max_size_kb        = 200
language           = "fr"

[[document]]
source           = "docs/api/*.md"
tags             = ["api", "public"]
required_anchors = ["#", "##", "###"]
```

### 1.5 Includes

```toml
includes = ["skills/*.ctx", "rag.ctx"]
```

A large project can split its config across multiple `.ctx` files. The
compiler merges before analysis.

## 2. Lint taxonomy

Codes are prefixed by category and suffixed by ordinal. IDs are never reused
within a family. Each rule has a page in `docs/rules/<code>.md`.

### 2.1 Common rules (Context family)

Categories:

- **A** — Ambiguity (vague directives, subjective adjectives, fuzzy quantifiers)
- **C** — Contradiction (rules that disagree)
- **K** — Completeness (missing sections, undocumented behaviour)
- **P** — Platform (target-specific gotchas)
- **X** — Anti-pattern (known bad)
- **F** — LLM-friendliness (formatting that hurts the model)

### 2.2 Skills rules (S***)

| Code | Rule                                                                        |
|------|------------------------------------------------------------------------------|
| S001 | Description too vague (activation will miss) — < 30 distinctive words        |
| S002 | Description too generic (activation too broad) — > 80% stop-words            |
| S003 | No usage example (`example_invocation` missing)                              |
| S004 | File referenced in `files` does not exist                                    |
| S005 | Non-standard name (spaces, inconsistent case) — kebab-case required          |
| S006 | Skills overlap (descriptions semantically close > 0.8)                       |
| S007 | SKILL.md too long (> 200 lines) — reduces activation efficiency              |
| S008 | Description without action verb at start                                     |
| S009 | `trigger_keywords` redundant with `description`                              |
| S010 | Skill bound to a runtime not declared in `required_runtime`                  |

### 2.3 RAG rules (R***)

#### Source documents

| Code | Rule                                                                        |
|------|------------------------------------------------------------------------------|
| R001 | Chunk too long (> `chunk_max_tokens`)                                        |
| R002 | Chunk too short (< `chunk_min_tokens`) — context loss                        |
| R003 | Section without H1/H2 title — weak retrieval signal                          |
| R004 | Unresolved external reference (URL, citation)                                |
| R005 | Cross-document duplication (similarity ≥ 80%)                                |
| R006 | Document without date — cannot evaluate freshness                            |
| R007 | Inconsistent tag taxonomy (`tag-a` and `tag_a` coexist)                      |
| R008 | Orphan document (not covered by any `[[document]]` glob)                     |
| R009 | Required anchor missing (`required_anchors` violated)                        |
| R010 | Mixed languages in one document (FR + EN without separation)                 |
| R011 | ASCII table (not cleanly parseable by standard embedders)                    |
| R012 | Image without alt text (information loss for retrieval)                      |

#### Retrieval config

| Code | Rule                                                                        |
|------|------------------------------------------------------------------------------|
| R013 | `chunk_target_tokens` < 100 or > 2000 (outside known-good range)             |
| R014 | `chunk_overlap_tokens` > 50% of `chunk_target_tokens` (excessive redundancy) |
| R015 | `reranking_top_k` > `retrieval_top_k` (inconsistent)                         |
| R016 | `embedding_model` not recognized                                             |
| R017 | No `reranker` for a corpus > 1000 documents                                  |

### 2.4 Cross-artifact rules (XA***)

Apply to a repo aggregating multiple artifacts.

| Code  | Rule                                                                       |
|-------|----------------------------------------------------------------------------|
| XA001 | Skill violates a rule declared in `CLAUDE.md`                              |
| XA002 | RAG document contradicts a rule in `CLAUDE.md` (rare but real)             |
| XA003 | Skill references a RAG document that does not exist                        |
| XA004 | RAG config mentioned in `CLAUDE.md` but absent from `.ctx`                 |

## 3. Diagnostic output

CLI format (default):

```
<file>:<line>:<col>  <CODE>  <message>
                     suggestion: <actionable hint>
                     doc: https://contextos.dev/rules/<code>
```

JSON format (`--json`):

```json
{
  "code": "S001",
  "severity": "must",
  "file": "skills/pdf-extract/SKILL.md",
  "line": 3,
  "column": 14,
  "message": "description too vague",
  "suggestion": "describe the input shape and the output shape concretely",
  "doc_url": "https://contextos.dev/rules/S001"
}
```

## 4. Compilation — `.ctx` → targets

### 4.1 Supported targets

**v0.1** (Phase 1):

- `claude_code` → `CLAUDE.md`

**v0.2** (Phase 3):

- `codex` → `AGENTS.md`
- `cursor` → `.cursorrules` + `.cursor/rules/*.mdc`
- `copilot` → `.github/copilot-instructions.md`
- `cline` → `.clinerules`
- `windsurf` → `.windsurfrules`

**v0.3** (Phase 5–6):

- `anthropic_skills` → `skills/<name>/SKILL.md` folder with YAML frontmatter
- `rag_corpus` → restructured source docs + manifest (not executed by ContextOS, delivered to a third-party tool)

### 4.2 Skills → `anthropic_skills` mapping

A `[[skill]]` section produces:

- A folder `skills/<name>/`
- A `skills/<name>/SKILL.md` file with YAML frontmatter:

  ```markdown
  ---
  name: pdf-extract
  description: Extract structured data (vendor, total, tax, line items) from PDF invoices in French or English. Triggers when the user asks to parse, extract, or process an invoice PDF.
  ---

  # PDF invoice extraction

  ## When to use this skill
  ...

  ## Files in this skill
  - `scripts/extract.py` — main extraction logic
  - `examples/invoice_fr.pdf` — French invoice sample
  - `examples/invoice_en.pdf` — English invoice sample

  ## Example invocation
  > Extract the line items from this invoice.pdf

  ## Expected output
  JSON with fields: vendor, total, tax, currency, line_items[]
  ```

Files listed in `files` are **copied** from the source repo, never invented.
A missing reference is a compilation error, not a warning.

### 4.3 RAG → `rag_corpus` mapping

`ctx compile project.ctx --target rag_corpus --output ./rag-output/` produces:

- `rag-output/manifest.yaml` — pipeline config (chunking, embedding, reranker), consumable by LangChain / LlamaIndex / Haystack
- `rag-output/docs/` — restructured and cleaned copy of source documents
- `rag-output/chunks.jsonl` — chunking preview (not executed)
- `rag-output/audit.md` — report of applied R*** rules

ContextOS **does not execute** embedding or indexing. It prepares and validates.

## 5. Parsing existing artifacts

### 5.1 Skills

```bash
ctx parse skills/pdf-extract/SKILL.md           # → AST JSON
ctx parse skills/pdf-extract/ --to-ctx          # → .ctx file
ctx parse skills/ --recursive --to-ctx > skills.ctx
```

### 5.2 RAG corpora

```bash
ctx parse-rag docs/knowledge-base/              # → audit + statistics
ctx parse-rag docs/knowledge-base/ --to-ctx     # → .ctx skeleton with inferred [[document]] entries
```

## 6. Semantic diff

`ctx diff` detects, for skills:

- Description changes (length, keywords)
- Added / removed examples
- Modifications to the `files` list

For RAG:

- Documents added / removed (by hash)
- Pipeline config changes
- Taxonomy moves

## 7. Audit

`ctx audit <repo>` detects:

- Inconsistency between `CLAUDE.md` and a skill in the repo (XA001)
- RAG document contradicting a `CLAUDE.md` rule (XA002)
- Skill pointing to a non-existent RAG document (XA003)
- RAG config in `CLAUDE.md` but absent from `.ctx` (XA004)

## 8. Versioning

`ctx_version` is required in the source file. The parser refuses an unknown
version.

Forward compatibility: a `.ctx` v0.1 must remain readable by ContextOS v0.3.

## 9. Out of MVP

- Live evaluation of skills (real prompt activation tests)
- Live evaluation of RAG (recall measurement on an eval set)
- `.ctx` Skills generation from an existing folder (description induction)
- Automatic RAG chunking suggestion based on content
- "Challenger" mode: A/B variants of skill descriptions
