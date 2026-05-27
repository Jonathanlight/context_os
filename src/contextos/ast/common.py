"""Shared AST types used by every family (context, skill, RAG)."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Severity(StrEnum):
    """Severity level of a rule, as defined in SPEC.md §1.2."""

    MUST = "must"
    SHOULD = "should"
    MAY = "may"


class Position(BaseModel):
    """Source-file position of an element, preserved by parsers.

    ``file`` is None for in-memory parses (``parse_*_string``).
    ``line`` is 1-indexed. ``column`` is 1-indexed and defaults to 1 because
    most container elements are reported at column 1 (e.g. a ``[[rules]]``
    header).
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    file: str | None = None
    line: int = Field(ge=1)
    column: int = Field(default=1, ge=1)


class ProseBlock(BaseModel):
    """A free-form Markdown paragraph attached to a Document.

    Used to preserve the prose interleaved between structured sections in
    a ``.ctx`` source, so that ``compile → parse → compile`` is byte-stable.
    """

    model_config = ConfigDict(extra="forbid")

    content: str = Field(min_length=1)
    position: Position | None = None
