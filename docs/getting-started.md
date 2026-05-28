# Getting started

A five-minute walk-through: install, write a `.ctx`, compile it to
`CLAUDE.md`, lint the result, audit a whole repo.

## Install

ContextOS is a Python 3.12+ package. The CLI ships as the `ctx` console
script. Use `pipx` so the install stays isolated from the rest of your
Python environment:

```bash
pipx install context-os
ctx --version
```

For development (clone + hack on the parser/analyzers), install editable
with the `dev` extras:

```bash
git clone git@github.com:Jonathanlight/context_os.git
cd context_os
pip install -e ".[dev]"
./scripts/check.sh   # ruff + mypy --strict + pytest
```

## Write your first `.ctx`

A `.ctx` is TOML + embedded Markdown. Save this as `project.ctx`:

```toml
project = "MyApp"
artifacts = ["context"]

[identity]
role = "Senior backend engineer working on the API layer."

[stack]
required = ["python>=3.12", "fastapi"]
forbidden = ["django"]

[[rules]]
id = "TDD-001"
title = "Write a failing test before any production code change"
severity = "must"
rationale = "Catches regressions before they reach the PR review."

[[rules]]
id = "SEC-042"
title = "Sanitize every input crossing a trust boundary"
severity = "must"
rationale = "Prevents path-traversal and injection attacks."
example_good = "bleach.clean(user_html)"
example_bad = "f\"<div>{user_html}</div>\""
```

## Compile to a target

```bash
ctx compile project.ctx --target claude_code --output-dir .
# wrote ./CLAUDE.md

cat CLAUDE.md
```

You'll see a clean Markdown file with `# MyApp`, an `## Identity` section,
the `## Stack` sub-sections (`### Required`, `### Forbidden`), and `## Rules`
bullets with `Must`-prefixed wording so the directive's severity survives
any round-trip back through the parser.

Other targets work the same way:

```bash
ctx compile project.ctx --target codex --output-dir .
# wrote ./AGENTS.md

ctx compile project.ctx --target cursor --output-dir .
# wrote ./.cursor/rules/agent.mdc

ctx compile project.ctx --target copilot --output-dir .
# wrote ./.github/copilot-instructions.md
```

The `.ctx` source is canonical; every target rewrites from it.

## Lint a Markdown file

ContextOS reads existing `CLAUDE.md` / `AGENTS.md` files too. Lint catches
the patterns that hurt the LLM:

```bash
ctx lint CLAUDE.md --target claude_code
```

Sample output:

```
warning[A001]: vague directive: 'Be concise'
  --> CLAUDE.md:42:1
   = help: rephrase with a measurable criterion (e.g. 'public functions
     <= 40 lines' instead of 'be concise')
   = doc:  https://contextos.dev/rules/A001
```

See the [rules catalog](rules/index.md) for every check.

## Diff two versions

After editing a `.ctx`, compare what changed:

```bash
ctx diff project.ctx project.ctx.new
```

ContextOS reports per-section changes: project renames, identity
revisions, stack added/removed, rules added/removed/modified with
field-level deltas (severity, rationale, tags). Use `--json` for CI
consumption.

## Audit a whole repo

For a project with several context files (a CLAUDE.md, an AGENTS.md, and
a `.cursorrules` for example), `ctx audit` walks the tree, parses what it
can, runs every analyzer, and lists cross-artifact issues:

```bash
ctx audit .
```

The report:

- One section per parseable file with its per-rule diagnostics.
- A cross-artifact section listing things like XA001 (rule id collision
  across files).
- A skipped section naming files matching a recognized target the parser
  doesn't yet support (`.cursor/rules/*.mdc`, `.clinerules`, …).
- A summary line with the total count.

## Aggregate stats

`ctx stats` reduces an audit run into a corpus-level summary:

```bash
ctx stats path/to/corpus
```

You get:

- File counts (audited vs skipped).
- Per-severity diagnostic counts (error / warning / info).
- Top 10 diagnostic codes by frequency.
- Per-file rule counts.
- Target coverage (how many CLAUDE.md / AGENTS.md / etc. were found).

Useful when you want to survey a fleet of projects at a glance.

## Lint a SKILL.md

ContextOS understands Anthropic-style skills too. A `SKILL.md` lives at
`skills/<name>/SKILL.md` with YAML frontmatter for the trigger
metadata and a Markdown body for documentation:

```markdown
---
name: pdf-extract
title: PDF invoice extraction
description: |
  Extracts structured invoice data from PDF documents. Triggers when
  the user uploads a `.pdf` or asks to parse one.
example_invocation: Extract the line items from this invoice.pdf
trigger_keywords:
  - facture
files:
  - scripts/extract.py
---

# PDF invoice extraction

When invoked, this skill ...
```

Six dedicated lint rules (`S001`–`S006`) cover the failure modes
specific to skills — descriptions without trigger phrasing, missing
`example_invocation`, body H1 drift, redundant `trigger_keywords`:

```bash
ctx lint skills/pdf-extract/SKILL.md
```

`ctx audit .` walks every `SKILL.md` recursively, so the rules fire
at the repo level alongside the agent rules. Skills show up under
`anthropic_skill` in `ctx stats . target_coverage`.

You can also compile a skill from a `.ctx` source:

```toml
# skill.ctx
project = "PdfExtract"
artifacts = ["skills"]

[[skill]]
name = "pdf-extract"
title = "PDF invoice extraction"
description = "Extracts PDFs. Triggers when the user uploads an invoice."
example_invocation = "Extract the line items from this invoice.pdf"
```

```bash
ctx compile skill.ctx --target anthropic_skill --output-dir .
# wrote ./SKILL.md
```

## Lint and compile a RAG corpus

ContextOS also covers the third LLM-context family: **RAG corpora**.
A `.ctx` declaring `artifacts=['rag']` describes the retrieval
pipeline (chunking, embedding, reranking, freshness) plus the source
files to index:

```toml
# rag.ctx
project = "PolicyCorpus"
artifacts = ["rag"]

[rag]
chunking_strategy = "semantic"
chunk_target_tokens = 500
chunk_overlap_tokens = 50
chunk_min_tokens = 100
chunk_max_tokens = 1500
embedding_model = "voyage-3"
embedding_dimensions = 1024
freshness_policy = "30d"
language_default = "fr"

[[document]]
source = "docs/policies/**/*.md"
tags = ["policy", "internal"]
freshness_required = "30d"
chunking_override = "header_aware"
required_anchors = ["##"]
```

Six dedicated lint rules (`R001`–`R006`) cover the failure modes
specific to RAG — excessive chunk overlap, missing embedding model,
header_aware chunking without anchors:

```bash
ctx lint rag.ctx
```

Compile the corpus to a JSON manifest the indexer (Qdrant, Pinecone,
or your own implementation) consumes:

```bash
ctx compile rag.ctx --target rag_manifest --output-dir .
# wrote ./rag.manifest.json
```

The manifest is the **contract** ContextOS exposes — ContextOS doesn't
execute the pipeline; the indexer reads the JSON and runs it.

## What's next?

- Read the [Vision](specs/VISION.md) and [Spec](specs/SPEC.md) docs to
  understand the architecture.
- Browse the [rules catalog](rules/index.md) to see what each diagnostic
  catches.
- Check the [Roadmap](specs/ROADMAP.md) for what's coming after the
  v2.0 trio (agent + skill + RAG).
