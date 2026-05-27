"""Core diagnostic types: severity, the Diagnostic model, and a bag collector."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from contextos.ast.common import Position

DIAG_CODE_PATTERN = r"^[A-Z]+\d{3,}$"
"""Regex every :attr:`Diagnostic.code` must match.

Matches the categories declared in SPEC.md §2: ``A``mbiguity, ``C``ontradiction,
``K``-completeness, ``P``latform, ``X``-anti-pattern, ``F``riendliness for the
context family; ``S`` for skills; ``R`` for RAG; ``XA`` for cross-artifact.
"""


class DiagSeverity(StrEnum):
    """Severity of a single diagnostic.

    Distinct from :class:`contextos.ast.common.Severity` (which classifies a
    rule's policy weight: must/should/may). When a rule violation is reported,
    callers typically map ``rule.severity → DiagSeverity``:

    - must → error
    - should → warning
    - may → info
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Diagnostic(BaseModel):
    """One diagnostic emitted by a parser or analyzer.

    Frozen so a diagnostic can be hashed, cached, and stored in sets — useful
    when an analyzer is asked to repeat a check and we want de-duplication.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(pattern=DIAG_CODE_PATTERN)
    severity: DiagSeverity
    message: str = Field(min_length=1)
    position: Position | None = None
    suggestion: str | None = None
    doc_url: str | None = None


class DiagnosticBag:
    """Mutable accumulator. Not a Pydantic model — needs in-place mutation.

    Provides a small API that the orchestrator and CLI rely on:

    - :meth:`add`, :meth:`extend` to feed diagnostics in
    - :meth:`count` (optionally filtered by severity)
    - :meth:`has_errors` for fast exit-code decisions
    - :meth:`sorted` deterministic order for renderers
    - iteration in insertion order
    """

    def __init__(self, diagnostics: Iterable[Diagnostic] | None = None) -> None:
        self._items: list[Diagnostic] = list(diagnostics) if diagnostics else []

    def add(self, diagnostic: Diagnostic) -> None:
        self._items.append(diagnostic)

    def extend(self, diagnostics: Iterable[Diagnostic]) -> None:
        self._items.extend(diagnostics)

    def count(self, severity: DiagSeverity | None = None) -> int:
        if severity is None:
            return len(self._items)
        return sum(1 for d in self._items if d.severity == severity)

    def has_errors(self) -> bool:
        return self.count(DiagSeverity.ERROR) > 0

    def sorted(self) -> list[Diagnostic]:
        """Deterministic order: by file, line, column, then code.

        Diagnostics without a position sort first (no file), then sort
        purely by code so the order is reproducible.
        """
        return sorted(
            self._items,
            key=lambda d: (
                d.position.file or "" if d.position else "",
                d.position.line if d.position else 0,
                d.position.column if d.position else 0,
                d.code,
            ),
        )

    def __iter__(self) -> Iterator[Diagnostic]:
        return iter(self._items)

    def __len__(self) -> int:
        return len(self._items)

    def __bool__(self) -> bool:
        return bool(self._items)

    def __contains__(self, diagnostic: object) -> bool:
        return diagnostic in self._items
