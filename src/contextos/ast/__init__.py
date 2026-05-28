"""Common AST for ContextOS — shared types and family-specific submodels.

Phase 1 shipped the ``agent`` family (Identity, Stack, Style, Tools, Rule,
AgentDocument). Phase 5.1 adds the ``skill`` family (SkillDocument).
The ``Document.type`` literal widens family-by-family — ``"rag"`` and
``"multi"`` land in Phase 6.
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
from contextos.ast.skill import (
    DESCRIPTION_MAX_CHARS,
    NAME_PATTERN,
    ExpectedOutputFormat,
    SkillDocument,
)

__all__ = [
    "DESCRIPTION_MAX_CHARS",
    "NAME_PATTERN",
    "AgentDocument",
    "Document",
    "DocumentType",
    "ExpectedOutputFormat",
    "Identity",
    "Position",
    "ProseBlock",
    "Rule",
    "Severity",
    "SkillDocument",
    "Stack",
    "Style",
    "Tools",
]
