"""Common AST for ContextOS — shared types and family-specific submodels.

Phase 1 shipped the ``agent`` family (Identity, Stack, Style, Tools,
Rule, AgentDocument). Phase 5.1 added the ``skill`` family
(SkillDocument). Phase 6.1 adds the ``rag`` family (RagConfig,
DocumentEntry, RagDocument). ``Document.type`` widens family-by-family.
"""

from __future__ import annotations

from contextos.ast.agent import (
    AgentDocument,
    Identity,
    Rule,
    Stack,
    Style,
    Tools,
)
from contextos.ast.common import Position, ProseBlock, Severity
from contextos.ast.document import Document, DocumentType
from contextos.ast.eval import (
    EvalSuite,
    EvalTarget,
    RagCase,
    SkillCase,
)
from contextos.ast.rag import (
    CHUNK_MAX_TOKENS_CEILING,
    CHUNK_MIN_TOKENS_FLOOR,
    FRESHNESS_PATTERN,
    TOP_K_CEILING,
    ChunkingStrategy,
    DocumentEntry,
    FreshnessPolicy,
    LanguageCode,
    RagConfig,
    RagDocument,
)
from contextos.ast.skill import (
    DESCRIPTION_MAX_CHARS,
    NAME_PATTERN,
    ExpectedOutputFormat,
    SkillDocument,
)

__all__ = [
    "CHUNK_MAX_TOKENS_CEILING",
    "CHUNK_MIN_TOKENS_FLOOR",
    "DESCRIPTION_MAX_CHARS",
    "FRESHNESS_PATTERN",
    "NAME_PATTERN",
    "TOP_K_CEILING",
    "AgentDocument",
    "ChunkingStrategy",
    "Document",
    "DocumentEntry",
    "DocumentType",
    "EvalSuite",
    "EvalTarget",
    "ExpectedOutputFormat",
    "FreshnessPolicy",
    "Identity",
    "LanguageCode",
    "Position",
    "ProseBlock",
    "RagCase",
    "RagConfig",
    "RagDocument",
    "Rule",
    "Severity",
    "SkillCase",
    "SkillDocument",
    "Stack",
    "Style",
    "Tools",
]
