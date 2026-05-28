"""Root Document model — entry point of the AST.

A Document is one of four ``type`` flavors per ARCHITECTURE.md:
``agent`` | ``rag`` | ``skill`` | ``multi``. Phase 1 shipped the
``agent`` flavor; Phase 5.1 widens the literal to admit ``skill`` and
attaches a dedicated :class:`~contextos.ast.skill.SkillDocument` slot.
Phase 6 will widen it again for ``rag`` and ``multi``.

This narrow-then-widen approach keeps ``mypy --strict`` honest: the
literal documents exactly what's representable today, and adding a new
family is a single Literal expansion that ripples through every
match-statement.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from contextos.ast.agent import AgentDocument
from contextos.ast.skill import SkillDocument

CTX_VERSION = "0.3"
"""Current ``.ctx`` format version. Bump in lockstep with SPEC.md changelog."""

DocumentType = Literal["agent", "skill"]
"""Artifact families currently parseable.

Will widen to ``"rag"`` / ``"multi"`` in Phase 6 — each addition is a
single literal change plus a new validator clause below.
"""


class Document(BaseModel):
    """Root of the ContextOS AST.

    The active flavor is selected by :attr:`type`. Exactly one of
    :attr:`agent` / :attr:`skill` must be populated and must match
    :attr:`type`; the model validator below enforces both halves of
    that invariant.
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

    @model_validator(mode="after")
    def _check_family_slot_populated(self) -> Document:
        """Ensure exactly the slot matching :attr:`type` is populated.

        We reject both directions: a missing required slot **and** a
        stray populated slot from the wrong family. Otherwise an
        ``agent`` Document could smuggle a ``skill`` payload through
        and silently corrupt downstream emitters.
        """
        match self.type:
            case "agent":
                if self.agent is None:
                    msg = "Document.type='agent' requires Document.agent to be set"
                    raise ValueError(msg)
                if self.skill is not None:
                    msg = (
                        "Document.type='agent' must not carry a skill payload; "
                        "set type='skill' or clear Document.skill"
                    )
                    raise ValueError(msg)
            case "skill":
                if self.skill is None:
                    msg = "Document.type='skill' requires Document.skill to be set"
                    raise ValueError(msg)
                if self.agent is not None:
                    msg = (
                        "Document.type='skill' must not carry an agent payload; "
                        "set type='agent' or clear Document.agent"
                    )
                    raise ValueError(msg)
        return self
