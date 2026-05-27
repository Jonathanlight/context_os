# Architecture

The technical structure of the ContextOS toolkit. For the format the toolkit
operates on, see [`SPEC.md`](./SPEC.md).

## Overview

```
┌────────────────────────────────────────────────────────────────────┐
│                          ContextOS CLI (Python)                     │
├────────────────────────────────────────────────────────────────────┤
│  Commands                                                            │
│    ctx lint, compile, parse, diff, audit, new                        │
├────────────────────────────────────────────────────────────────────┤
│  Core pipeline                                                       │
│    Input → Parser → AST (Pydantic) → Analyzer → Diagnostics/Emitter  │
├────────────────────────────────────────────────────────────────────┤
│  Parsers                                                             │
│    .ctx parser (tomlkit)                                             │
│    Agent parser (Markdown + per-target heuristics)                   │
│    RAG parser (YAML / JSON / Python AST)                             │
│    Skill parser (Markdown + YAML frontmatter)                        │
├────────────────────────────────────────────────────────────────────┤
│  Common AST                                                          │
│    Document → AgentDoc | RagDoc | SkillDoc | MultiDoc                │
├────────────────────────────────────────────────────────────────────┤
│  Analyzers                                                           │
│    Agent: A C K X F P                                                │
│    RAG:   R                                                          │
│    Skill: S                                                          │
│    Cross-artifacts: XA                                               │
├────────────────────────────────────────────────────────────────────┤
│  Emitters                                                            │
│    Agent: Claude, Codex, Cursor, Copilot, Cline, Windsurf            │
│    RAG:   LlamaIndex, LangChain, Haystack, raw YAML                  │
│    Skill: Anthropic, Cursor MDC                                      │
└────────────────────────────────────────────────────────────────────┘
```

## Technical stack

- **Python 3.12+** strict, `mypy --strict`
- **Pydantic v2** for the AST
- **Typer** for the CLI
- **mistletoe** for Markdown
- **tomlkit** for TOML (preserves order + comments)
- **PyYAML** for YAML (RAG configs)
- **pytest + hypothesis** for tests + property-based
- **ruff** for lint and format
- Distribution: `pipx install context-os`

Additional dependencies for RAG and Skills:

- `python-frontmatter` — parsing YAML frontmatter inside `SKILL.md`
- `jsonref` or a PyYAML extension — resolving `${VAR}` in RAG configs

No heavy ML dependency (no LlamaIndex, no LangChain in core): we read and
write their formats, we do not execute them.

## Repository structure

```
context_os/
├── pyproject.toml
├── src/contextos/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli/
│   │   ├── lint.py
│   │   ├── compile.py
│   │   ├── parse.py
│   │   ├── diff.py
│   │   ├── audit.py
│   │   └── new.py
│   ├── ast/
│   │   ├── common.py         # shared types (Position, Severity, ...)
│   │   ├── agent.py          # AgentDocument and submodels
│   │   ├── rag.py            # RagDocument and submodels
│   │   ├── skill.py          # SkillDocument and submodels
│   │   └── document.py       # root Document (multi)
│   ├── parsers/
│   │   ├── ctx/              # .ctx source
│   │   │   └── parser.py
│   │   ├── agent/            # native .md
│   │   │   ├── markdown.py
│   │   │   └── targets/
│   │   │       ├── claude.py
│   │   │       ├── codex.py
│   │   │       ├── cursor.py
│   │   │       ├── copilot.py
│   │   │       ├── cline.py
│   │   │       └── windsurf.py
│   │   ├── rag/              # native configs
│   │   │   ├── yaml_parser.py
│   │   │   ├── python_parser.py   # Python AST for LlamaIndex / LangChain
│   │   │   └── targets/
│   │   │       ├── llamaindex.py
│   │   │       ├── langchain.py
│   │   │       └── haystack.py
│   │   └── skill/
│   │       ├── folder_parser.py   # reads a <name>/SKILL.md folder + assets
│   │       └── targets/
│   │           ├── anthropic.py
│   │           └── cursor_mdc.py
│   ├── analyzers/
│   │   ├── base.py
│   │   ├── agent/
│   │   │   ├── ambiguity.py
│   │   │   ├── contradiction.py
│   │   │   ├── completeness.py
│   │   │   ├── antipattern.py
│   │   │   ├── llm_friendly.py
│   │   │   └── platform.py
│   │   ├── rag/
│   │   │   └── rules.py         # R001-R017
│   │   ├── skill/
│   │   │   └── rules.py         # S001-S010
│   │   └── cross/
│   │       └── rules.py         # XA001-XA004
│   ├── diagnostics/
│   │   ├── diagnostic.py
│   │   ├── renderer_cli.py
│   │   └── renderer_json.py
│   ├── emitters/
│   │   ├── base.py
│   │   ├── agent/
│   │   │   ├── claude.py
│   │   │   ├── codex.py
│   │   │   ├── cursor.py
│   │   │   ├── copilot.py
│   │   │   ├── cline.py
│   │   │   ├── windsurf.py
│   │   │   └── mappings/        # per-target YAML
│   │   ├── rag/
│   │   │   ├── llamaindex.py
│   │   │   ├── langchain.py
│   │   │   ├── haystack.py
│   │   │   └── raw_yaml.py
│   │   └── skill/
│   │       ├── anthropic.py
│   │       └── cursor_mdc.py
│   ├── diff/
│   │   ├── agent.py
│   │   ├── rag.py
│   │   ├── skill.py
│   │   └── project.py
│   ├── audit/
│   │   ├── repo_scanner.py
│   │   └── report.py
│   ├── templates/                 # scaffolds for `ctx new`
│   │   ├── agent_symfony.ctx
│   │   ├── agent_flutter.ctx
│   │   ├── agent_python_cli.ctx
│   │   ├── rag_docs.ctx
│   │   ├── rag_support.ctx
│   │   ├── skill_blank.ctx
│   │   ├── skill_data_tool.ctx
│   │   └── project_full.ctx
│   └── corpus/                    # Phase 4 public corpus study
│       ├── fetcher.py
│       └── stats.py
└── tests/
    ├── ast/
    ├── parsers/
    ├── analyzers/
    ├── emitters/
    ├── diff/
    ├── audit/
    ├── fixtures/
    │   ├── agent/                 # real native .md
    │   ├── rag/                   # real native configs
    │   ├── skill/                 # real SKILL.md folders
    │   └── projects/               # full anonymized repos
    └── integration/
```

## Common AST model

```python
# src/contextos/ast/document.py
from typing import Literal
from pydantic import BaseModel
from .agent import AgentDocument
from .rag import RagDocument
from .skill import SkillDocument

class Document(BaseModel):
    project: str
    ctx_version: str = "0.3"
    type: Literal["agent", "rag", "skill", "multi"]
    languages: list[str] = []
    authors: list[str] = []
    version: str = "0.1.0"

    # One or more of these populated according to `type`
    agent: AgentDocument | None = None
    rag: RagDocument | None = None
    skill: SkillDocument | None = None        # type=skill: a single one
    skills: list[SkillDocument] = []          # type=multi: many

    model_config = {"extra": "forbid"}
```

### AgentDocument

Holds `Identity`, `Stack`, `Style`, `Tools`, `Rule`, `ProseBlock` submodels.

### RagDocument

```python
# src/contextos/ast/rag.py
class EmbeddingsConfig(BaseModel):
    provider: Literal["openai", "anthropic", "cohere", "voyage", "local"]
    model: str
    dimensions: int
    api_env_var: str | None = None

class VectorStoreConfig(BaseModel):
    type: Literal["qdrant", "pinecone", "weaviate", "chroma", "pgvector", "milvus"]
    endpoint: str | None = None
    collection: str
    namespace: str | None = None
    distance: Literal["cosine", "dot", "euclidean"] = "cosine"

class ChunkingConfig(BaseModel):
    strategy: Literal["fixed", "recursive", "semantic", "sentence"]
    chunk_size: int
    overlap: int = 0
    separators: list[str] = []

class KnowledgeBase(BaseModel):
    name: str
    description: str
    when_to_use: str | None = None
    sources: list[str]
    update_freq: str | None = None
    priority: int = 1

class RetrievalConfig(BaseModel):
    top_k: int = 5
    score_threshold: float | None = None
    hybrid_search: bool = False
    mmr_lambda: float | None = None

class RerankingConfig(BaseModel):
    enabled: bool = False
    provider: str | None = None
    model: str | None = None
    top_n: int = 3

class CitationConfig(BaseModel):
    format: str = "[doc:{id}]"
    require_inline: bool = True
    include_url: bool = True

class RagDocument(BaseModel):
    targets: list[str] = []
    embeddings: EmbeddingsConfig
    vector_store: VectorStoreConfig
    chunking: ChunkingConfig
    knowledge_bases: list[KnowledgeBase]
    retrieval: RetrievalConfig = RetrievalConfig()
    reranking: RerankingConfig = RerankingConfig()
    citation: CitationConfig = CitationConfig()
```

### SkillDocument

```python
# src/contextos/ast/skill.py
class SkillMetadata(BaseModel):
    description: str
    version: str = "0.1.0"
    license: str | None = None
    tags: list[str] = []

class SkillWorkflow(BaseModel):
    title: str
    trigger: str
    steps: list[str]
    example: str | None = None

class SkillFiles(BaseModel):
    reference: str | None = None
    examples: list[str] = []
    scripts: list[str] = []
    templates: list[str] = []

class SkillDocument(BaseModel):
    name: str
    targets: list[str] = ["anthropic"]
    metadata: SkillMetadata
    workflows: list[SkillWorkflow] = []
    files: SkillFiles = SkillFiles()
    prose: list[ProseBlock] = []   # from ast.common
```

## Pipeline orchestration

```python
# src/contextos/lint.py (orchestrator)
def lint_document(doc: Document) -> list[Diagnostic]:
    diagnostics: list[Diagnostic] = []

    if doc.agent is not None:
        for analyzer in AGENT_ANALYZERS:
            diagnostics.extend(analyzer.analyze(doc.agent))

    if doc.rag is not None:
        for analyzer in RAG_ANALYZERS:
            diagnostics.extend(analyzer.analyze(doc.rag))

    if doc.skill is not None:
        for analyzer in SKILL_ANALYZERS:
            diagnostics.extend(analyzer.analyze(doc.skill))

    for s in doc.skills:
        for analyzer in SKILL_ANALYZERS:
            diagnostics.extend(analyzer.analyze(s))

    # Cross-artifact rules only fire when more than one type is present
    if doc.type == "multi":
        for analyzer in CROSS_ANALYZERS:
            diagnostics.extend(analyzer.analyze(doc))

    return sorted(diagnostics, key=lambda d: (d.file or "", d.line, d.column))
```

## Cross-artifact audit

`ctx audit <path>`:

1. Recursive walk of the repo
2. Detection of each artifact (`CLAUDE.md`, `AGENTS.md`, `.cursorrules`, `SKILL.md`, `rag_config.*`)
3. Individual parsing to `Document` objects
4. Aggregation into a **virtual MultiDocument** (the whole repo)
5. Run individual analyzers + cross-artifact rules
6. HTML / Markdown report

A repo may have a `CLAUDE.md` + a `.cursorrules` describing **the same project
from two angles**. ContextOS reconciles them through a project-level view:

```python
class ProjectInferred(BaseModel):
    """Repo-level virtual document aggregating every artifact found."""
    repo_path: Path
    agent_files: list[tuple[Path, AgentDocument]]
    rag_files: list[tuple[Path, RagDocument]]
    skill_folders: list[tuple[Path, SkillDocument]]
```

XA001–XA004 operate on `ProjectInferred`.

## CLI surface

```bash
# v0.1 (Phase 1)
ctx lint <file>
ctx compile <file.ctx>
ctx parse <file>
ctx diff <a> <b>

# v0.2 (Phase 5–6)
ctx lint --type=skill skills/pdf-toolkit/
ctx lint --type=rag rag_config.yaml

ctx compile project.ctx --types=agent,rag,skill
ctx compile project.ctx --skip=rag

ctx audit . --report=html --output=audit.html
ctx audit . --types=agent --strict

ctx parse skills/pdf-toolkit/ --to-ctx
ctx parse rag_config.yaml --to-ctx --type=rag

ctx new --template=project/full myapp
```

## Test layout

Three corpora of fixtures:

- `tests/fixtures/agent/` — 25+ native `.md` files
- `tests/fixtures/rag/` — 15+ LlamaIndex / LangChain / YAML configs
- `tests/fixtures/skill/` — 15+ `SKILL.md` folders
- `tests/fixtures/projects/` — 10+ full anonymized repos

Property tests per type:

- Round-trip agent: `compile → parse` is neutral
- Round-trip rag: `compile → parse` is neutral
- Round-trip skill: `compile → parse` is neutral
- Round-trip multi: composes the three

## CI / CD

GitHub Actions, three workflows: `ci.yml` (lint / typecheck / test on every
PR and push), `release.yml` (PyPI publish on tag), `docs.yml` (docs site
build).

## Success metrics

At the end of Phase 6 (~5 months):

- 60+ lint rules implemented (all categories)
- 6 agent targets, 4 RAG targets, 2 skill targets = 12 emitters
- 65+ real fixtures pass tests
- Round-trip property test on 1000 hypothesis iterations per type
- Coverage ≥ 90 %
- Documentation site with one page per rule
- `ctx audit` on a 100-file context repo < 3 s
