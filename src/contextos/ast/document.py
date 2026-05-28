"""Root Document model — entry point of the AST.

A Document is one of four ``type`` flavors per ARCHITECTURE.md:
``agent`` | ``rag`` | ``skill`` | ``multi``. Phase 1 shipped the
``agent`` flavor; Phase 5.1 added ``skill``; Phase 6.1 adds ``rag``.
The ``multi`` flavor is reserved for a later phase that aggregates
several artifacts in one ``.ctx`` source.

This narrow-then-widen approach keeps ``mypy --strict`` honest: the
literal documents exactly what's representable today, and adding a new
family is a single Literal expansion that ripples through every
match-statement.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from contextos.ast.agent import AgentDocument
from contextos.ast.rag import RagDocument
from contextos.ast.skill import SkillDocument

CTX_VERSION = "0.3"
"""Current ``.ctx`` format version. Bump in lockstep with SPEC.md changelog."""

DocumentType = Literal["agent", "skill", "rag"]
"""Artifact families currently parseable.

Will widen to ``"multi"`` later — each addition is a single literal
change plus a new clause in the family-slot model validator below.
"""


class Document(BaseModel):
    """Root of the ContextOS AST.

    The active flavor is selected by :attr:`type`. Exactly one of the
    family slots (:attr:`agent` / :attr:`skill` / :attr:`rag`) must be
    populated and must match :attr:`type`; the model validator below
    enforces both halves of that invariant.
    """

    model_config = ConfigDict(extra="forbid")

    project: str = Field(min_length=1)
    ctx_version: str = CTX_VERSION
    type: DocumentType = "agent"
    languages: list[str] = Field(default_factory=list)
    authors: list[str] = Field(default_factory=list)
    version: str = "0.1.0"
    agent: AgentDocument | None = None
    skill: SkillDocument | None = None
    rag: RagDocument | None = None

    @model_validator(mode="after")
    def _check_family_slot_populated(self) -> Document:
        """Ensure exactly the slot matching :attr:`type` is populated.

        We reject both directions: a missing required slot **and** any
        stray populated slot from a different family. Otherwise a
        ``rag`` Document could smuggle a ``skill`` payload through and
        silently corrupt downstream emitters.
        """
        match self.type:
            case "agent":
                if self.agent is None:
                    msg = "Document.type='agent' requires Document.agent to be set"
                    raise ValueError(msg)
                _reject_foreign(self, family="agent", forbidden=("skill", "rag"))
            case "skill":
                if self.skill is None:
                    msg = "Document.type='skill' requires Document.skill to be set"
                    raise ValueError(msg)
                _reject_foreign(self, family="skill", forbidden=("agent", "rag"))
            case "rag":
                if self.rag is None:
                    msg = "Document.type='rag' requires Document.rag to be set"
                    raise ValueError(msg)
                _reject_foreign(self, family="rag", forbidden=("agent", "skill"))
        return self


_ARTICLES: dict[str, str] = {"agent": "an", "skill": "a", "rag": "a"}


def _reject_foreign(doc: Document, *, family: str, forbidden: tuple[str, ...]) -> None:
    """Raise if any slot in ``forbidden`` is populated on ``doc``.

    Extracted to keep the validator readable as the family count grows.
    The per-family article ("an agent" vs "a skill" vs "a rag") is
    looked up in :data:`_ARTICLES` so error messages stay grammatical.
    """
    for name in forbidden:
        if getattr(doc, name) is not None:
            article = _ARTICLES.get(name, "a")
            msg = (
                f"Document.type='{family}' must not carry {article} {name} payload; "
                f"set type='{name}' or clear Document.{name}"
            )
            raise ValueError(msg)
