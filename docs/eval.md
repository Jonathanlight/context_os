# Live evaluation

ContextOS's lint pipeline (Phases 2 / 5.4 / 6.4) validates
**structure**: does this skill have trigger phrasing, does this RAG
config have a freshness policy. Phase 7B adds **functional**
evaluation: actually invoke an LLM with the skill registry attached,
or actually embed a query against indexed chunks, and score the
result against an expected answer.

## Architecture

```
┌──────────────────┐
│ project.eval.toml│  ──┐
└──────────────────┘    │
                        ▼
┌──────────────────┐  ┌─────────────┐    ┌────────────────────┐
│ ctx eval         │ ─►│ EvalSuite   │ ─► │ SkillEvalRunner    │ ─┐
│ (entry point)    │  │ (AST)       │    │ RagEvalRunner      │  │
└──────────────────┘  └─────────────┘    └────────────────────┘  │
                                              │                  │
                                              ▼                  │
                                       ┌────────────────────┐    │
                                       │ Provider           │    │
                                       │ • Anthropic        │    │
                                       │ • OpenAI (embed)   │    │
                                       │ • Mock (dry-run)   │    │
                                       └────────────────────┘    │
                                                                 ▼
                                                       ┌──────────────────┐
                                                       │ EvalRunResult    │
                                                       │ (text or JSON)   │
                                                       └──────────────────┘
                                                                 │
                                                                 ▼
                                                       ┌──────────────────┐
                                                       │ ctx eval-diff    │
                                                       │ baseline.json    │
                                                       │ vs current.json  │
                                                       └──────────────────┘
```

Each shape (CLI, library, runner) shares the same Python core; the
provider abstraction is the only thing that varies between dry-run
tests and real evaluation runs.

## Install

The eval runners ship under an optional dependency group:

```bash
# From git source (today, PyPI publication pending)
pipx install 'git+https://github.com/Jonathanlight/context_os.git#egg=context-os-ctx[eval]'

# Once published on PyPI
pipx install 'context-os-ctx[eval]'
```

This pulls `anthropic` (Skills routing), `numpy` (RAG cosine), and
`openai` (RAG embedding). The CLI command stays available without
the extras for `--dry-run` mode; live runs surface a clear "install
context-os-ctx[eval]" error when the SDK isn't on the path.

Environment variables the live providers read:

| Variable | Used by | Provider |
| --- | --- | --- |
| `ANTHROPIC_API_KEY` | Skills routing | `AnthropicSkillProvider` |
| `OPENAI_API_KEY` | RAG embedding | `EmbeddingRagProvider` |

## `.eval.toml` format

An eval suite is a TOML file declaring the project, the target
family, and one or more cases. The full grammar lives in
`src/contextos/ast/eval.py`; the examples below cover the common
shapes.

### Skill suite

```toml
project = "PdfExtract"
target = "anthropic_skill"

[[skill_case]]
name = "happy-path-en"
prompt = "Extract the line items from this invoice.pdf"
expected_skill = "pdf-extract"
tags = ["en"]

[[skill_case]]
name = "happy-path-fr"
prompt = "Extraire les lignes de cette facture.pdf"
expected_skill = "pdf-extract"
tags = ["fr"]

[[skill_case]]
name = "weather-route"
prompt = "What's the weather in Paris today?"
expected_skill = "weather-lookup"
```

`expected_skill` is the slug matching `SkillDocument.name`. Compared
verbatim — no normalization.

### RAG suite

```toml
project = "PolicyCorpus"
target = "rag"

[[rag_case]]
name = "vacation-policy"
query = "What is the maximum vacation balance?"
expected_sources = ["docs/policies/vacation.md"]
top_k = 5

[[rag_case]]
name = "compensation"
query = "How are bonuses calculated?"
expected_sources = ["docs/policies/comp.md", "docs/handbook/bonus.md"]
top_k = 10
```

Pass criterion: **any** entry in `expected_sources` appears in the
provider's top-k retrieval. OR semantics over the expected list.

Validation rules (enforced by the AST at parse time):

- A `target='anthropic_skill'` suite must not carry `rag_cases`,
  and vice versa.
- `expected_sources` must be non-empty.
- `top_k` is bounded 1–100.

## Quick start — dry-run

`--dry-run` uses a Mock provider that returns each case's expected
answer. Every case passes by construction. Useful to verify the
suite parses and the wiring works without spending tokens or hitting
an API.

```bash
ctx eval skills.eval.toml --dry-run
```

Sample output:

```
eval suite: PdfExtract
target:     anthropic_skill
pass:       3/3 (100%)
tokens:     0

  [PASS] happy-path-en
  [PASS] happy-path-fr
  [PASS] weather-route
```

## Live mode — Skills

Anthropic API + the skill registry attached as tools. The model
picks a tool; we read the slug from the tool_use block.

```bash
export ANTHROPIC_API_KEY=sk-ant-...
ctx eval skills.eval.toml \
  --skills-dir agents/skills/ \
  --json --output result.json
```

`--skills-dir` is walked recursively for `SKILL.md` files. The
registry is sorted by path for determinism — the model sees tools
in the same order on every run.

### Cost note

Each case is one Messages API call against Haiku 4.5 by default
(cheapest fast model). Typical case spends a few hundred input
tokens (skill descriptions + prompt) and a handful of output
tokens (tool selection). The aggregate `total_tokens` lands in the
result so a CI dashboard can track cost over time.

## Live mode — RAG

OpenAI embedding for the query + in-process numpy cosine against
pre-indexed chunks. ContextOS does **not** index the corpus itself
(that's downstream pipeline work); you supply the chunks file
produced by your indexer.

```bash
export OPENAI_API_KEY=sk-...
ctx eval rag.eval.toml \
  --rag-chunks chunks.json \
  --rag-embed-model text-embedding-3-large
```

### `chunks.json` format

A JSON array of pre-indexed chunks:

```json
[
  {
    "source": "docs/policies/vacation.md",
    "vector": [0.012, -0.034, 0.181, ...],
    "content": "Optional debug text"
  },
  {
    "source": "docs/policies/comp.md",
    "vector": [...]
  }
]
```

All vectors must share the same dimension. The embedding model
passed via `--rag-embed-model` must produce vectors of the same
dimension — `text-embedding-3-large` (3072) is the default; pin
to whatever produced your chunks.

### Bring your own embedding service

The CLI ships OpenAI as the default. If you use Voyage, a local
model, or a different vendor, drop down to the Python API:

```python
from contextos.ast.eval import EvalSuite
from contextos.eval import EmbeddingRagProvider, RagEvalRunner
from contextos.eval.cli_helpers import load_chunks
from contextos.parsers import parse_eval_file

import voyageai

client = voyageai.Client()

def embed_voyage(text: str) -> list[float]:
    response = client.embed([text], model="voyage-3")
    return response.embeddings[0]

suite = parse_eval_file("rag.eval.toml")
chunks = load_chunks("chunks.json")
provider = EmbeddingRagProvider(chunks=chunks, embed_query=embed_voyage)
result = RagEvalRunner(provider).run(suite)
print(result.pass_rate)
```

The provider abstraction is one class implementing
`RagRetrievalProvider`; the runner consumes the protocol, not any
particular vendor.

## CI flow with regression detection

Commit a `baseline.json` produced by an authoritative run. Every PR
runs the suite fresh and diffs against the baseline:

```yaml
name: ContextOS eval
on:
  pull_request:
    branches: [main]

jobs:
  evaluate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pipx install 'git+https://github.com/Jonathanlight/context_os.git#egg=context-os-ctx[eval]'
      - run: ctx eval skills.eval.toml
              --skills-dir agents/skills/
              --json --output current.json
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      - run: ctx eval-diff baseline.json current.json
```

`ctx eval-diff` classifies every case transition:

| Bucket | Definition |
| --- | --- |
| **regression** | Was passing in baseline, fails now. **Always breaks CI.** |
| **improvement** | Was failing in baseline, passes now. |
| **new_failure** | Case is new in current + failing. Breaks CI only with `--fail-on-new-failure`. |
| **new_pass** | Case is new in current + passing. |
| **removed** | Case was in baseline, gone from current. |

Default behavior: exit 1 only on regressions. New failing cases stay
non-blocking so a PR that adds cases-not-yet-green doesn't break the
gate.

### Updating the baseline

When you intentionally accept a current run as the new baseline:

```bash
ctx eval skills.eval.toml --skills-dir agents/skills/ \
  --json --output baseline.json
git add baseline.json
git commit -m "eval: bump baseline after skill refactor"
```

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ctx eval requires the 'eval' extras` | `[eval]` not installed | `pipx install --force context-os-ctx[eval]` |
| `skill eval needs --skills-dir <path>` | live mode without flag | Pass `--skills-dir` or `--dry-run` |
| `Query embedding dim X does not match chunk dim Y` | model mismatch | Re-embed chunks with the model passed via `--rag-embed-model` |
| `chunks file must be a JSON array` | top-level shape wrong | Make sure your indexer produces a JSON list, not an object |
| Every case `actual: (none)` | provider returned no result | Check API key / network; the `error` field on each case names the exception |
