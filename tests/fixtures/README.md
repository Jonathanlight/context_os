# Test fixtures

This directory holds representative artifacts across the three families
ContextOS targets. Each fixture is a **synthetic paraphrase** authored for
this repo — none is a verbatim copy of a third-party source, even when
inspired by one. This avoids any licensing question and lets us pin
deliberate defects for the analyzers to flag.

## Layout

```
tests/fixtures/
├── agent/                       # Family 1 — agent context files
│   ├── claude_monorepo_style.md       # CLAUDE.md, monorepo flavor
│   ├── agents_codex_style.md          # AGENTS.md, single-maintainer flavor
│   └── cursorrules_nextjs_style.mdc   # .cursorrules with YAML frontmatter, ALL-CAPS sections
├── skill/                       # Family 2 — Anthropic Skills
│   └── pdf_extract_example/
│       └── SKILL.md                   # SKILL.md with frontmatter (name, description, compatibility)
└── rag/                         # Family 3 — RAG corpus configurations
    └── llamaindex_style_manifest.yaml # ContextOS manifest output for the rag_corpus target
```

## Inspiration sources

Structural inspiration only — no content reuse. URLs captured for the
Phase 0 audit grid in `docs/specs/RESEARCH.md`.

| Fixture | Inspired by | Real-world reference |
|---|---|---|
| `claude_monorepo_style.md` | The structural pattern observed in `langchain-ai/langchain/CLAUDE.md` and similar mid-sized OSS monorepos | https://github.com/langchain-ai/langchain (MIT) |
| `agents_codex_style.md` | The shorter, single-maintainer `AGENTS.md` flavor used by Codex / OpenAI-aligned projects | OpenAI Codex documentation, public Codex examples |
| `cursorrules_nextjs_style.mdc` | The `.mdc` frontmatter format observed in `PatrickJS/awesome-cursorrules` and Cursor's own docs | https://github.com/PatrickJS/awesome-cursorrules (license per-rule, varied) |
| `pdf_extract_example/SKILL.md` | The canonical `anthropics/skills` `SKILL.md` format (frontmatter + Overview / When-to-use / Workflow / Files / Example invocation / Expected output) | https://github.com/anthropics/skills (Apache 2.0) |
| `llamaindex_style_manifest.yaml` | The YAML form ContextOS will emit for its `rag_corpus` target — LlamaIndex itself is Python-code-configured, so this is an idealized portable manifest | https://github.com/run-llama/llama_index (MIT) |

## Intentional lint-able defects

Each fixture contains at least one defect that a future analyzer should
catch. These are deliberate — they give Phase 2 / 5 / 6 something to
exercise from day one. The defects:

| Fixture | Defect | Rule code (planned) |
|---|---|---|
| `claude_monorepo_style.md` | "Be concise" under "Code quality standards" — vague directive | A001 |
| `claude_monorepo_style.md` | "Always backtest a new strategy on at least 6 months of data" appears nowhere in the trader fixture, but a future XA001 cross-artifact rule should detect a CLAUDE rule with no matching code | (XA exploration) |
| `agents_codex_style.md` | "Prefer pure functions for indicator logic" — soft "prefer" without a `should`/`must` severity tag, ambiguous parsing | A004 (severity inference) |
| `cursorrules_nextjs_style.mdc` | "Always wrap code in fenced blocks tagged with the language" contradicts the absence of code blocks elsewhere in the file — possible C001 across families | C001 |
| `pdf_extract_example/SKILL.md` | References `references/anchors_fr.yaml` and `examples/invoice_fr.pdf` which do **not** exist on disk | S004 |
| `pdf_extract_example/SKILL.md` | Frontmatter `compatibility:` field is non-standard (Anthropic's official field is implicit in the body) | (S exploration) |
| `llamaindex_style_manifest.yaml` | `chunk_size: 500` with `overlap: 50` — 10% overlap, healthy. But `mmr_lambda: 0.6` may flag with the future MMR linter when chunk_size > 400 | (R exploration) |
| `llamaindex_style_manifest.yaml` | `score_threshold: 0.55` is below the conventional 0.7 floor for cosine similarity | (R exploration) |

These defects are documented so Phase 2/5/6 reviewers know what to look
for. Tests will assert specific diagnostics on each fixture.

## License

All fixtures in this directory are released under the same MIT license as
the rest of this repository. They were authored from scratch for ContextOS.
