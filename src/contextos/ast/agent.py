"""AST submodels for the **context** family (agent context files).

These mirror SPEC.md §1.2 and the Document type=agent contract from
ARCHITECTURE.md. Each model is strict (``extra="forbid"``) so an unknown
field raises during parsing rather than silently dropping.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from contextos.ast.common import Position, ProseBlock, Severity

RULE_ID_PATTERN = r"^[A-Z]+-\d{3,}$"
"""Regex that every ``Rule.id`` must match. See SPEC.md §1.2.

Examples that match: ``TDD-001``, ``SEC-042``, ``LINT-12345``.
Examples that do not match: ``tdd-001`` (lowercase), ``T-01`` (< 3 digits),
``001-TDD`` (digits-first), ``TDD_001`` (underscore not hyphen).
"""


class Identity(BaseModel):
    """The ``[identity]`` section of a context document."""

    model_config = ConfigDict(extra="forbid")

    role: str = Field(min_length=1)
    context: str | None = None
    author: str | None = None


class Stack(BaseModel):
    """The ``[stack]`` section: required / forbidden / preferred tech."""

    model_config = ConfigDict(extra="forbid")

    required: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    preferred: list[str] = Field(default_factory=list)


class Style(BaseModel):
    """The ``[style]`` section: code style conventions."""

    model_config = ConfigDict(extra="forbid")

    conventions: list[str] = Field(default_factory=list)


class Tools(BaseModel):
    """The ``[tools]`` section: required / forbidden tooling."""

    model_config = ConfigDict(extra="forbid")

    required: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)


class Rule(BaseModel):
    """A single ``[[rules]]`` entry.

    All optional fields default to ``None`` or empty list so the model
    round-trips cleanly through TOML where missing keys disappear.
    """

    model_config = ConfigDict(extra="forbid")

    id: str = Field(pattern=RULE_ID_PATTERN)
    title: str = Field(min_length=1)
    severity: Severity
    applies_to: list[str] = Field(default_factory=list)
    rationale: str | None = None
    detail: str | None = None
    example_good: str | None = None
    example_bad: str | None = None
    tags: list[str] = Field(default_factory=list)
    links: list[str] = Field(default_factory=list)
    position: Position | None = None


class AgentDocument(BaseModel):
    """The context-family submodel of a Document.

    Every section is optional individually — a minimal CLAUDE.md may only
    have rules, while a richer one populates all six. The Document-level
    invariant that at least *something* is present is enforced at the
    ``Document`` root, not here.
    """

    model_config = ConfigDict(extra="forbid")

    identity: Identity | None = None
    stack: Stack | None = None
    style: Style | None = None
    tools: Tools | None = None
    rules: list[Rule] = Field(default_factory=list)
    forbidden_patterns: list[str] = Field(default_factory=list)
    prose: list[ProseBlock] = Field(default_factory=list)
