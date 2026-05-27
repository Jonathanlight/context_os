"""Root Document model — entry point of the AST.

A Document is one of four ``type`` flavors per ARCHITECTURE.md:
``agent`` | ``rag`` | ``skill`` | ``multi``. Phase 1 (Milestone 1.1) ships
only the ``agent`` flavor; the literal will widen in Phase 5 (skills) and
Phase 6 (RAG). Until then, ``Document.type`` accepts only ``"agent"``.

This narrow-then-widen approach keeps ``mypy --strict`` honest: the literal
documents exactly what's parseable today, and adding a new family is a
single Literal expansion that ripples through every match-statement.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from contextos.ast.agent import AgentDocument

CTX_VERSION = "0.3"
"""Current ``.ctx`` format version. Bump in lockstep with SPEC.md changelog."""


class Document(BaseModel):
    """Root of the ContextOS AST.

    ``type=agent`` requires ``agent`` to be populated. Future types
    (``skill``, ``rag``, ``multi``) will require their respective slots when
    they land in Phase 5/6.
    """

    model_config = ConfigDict(extra="forbid")

    project: str = Field(min_length=1)
    ctx_version: str = CTX_VERSION
    type: Literal["agent"] = "agent"
    languages: list[str] = Field(default_factory=list)
    authors: list[str] = Field(default_factory=list)
    version: str = "0.1.0"
    agent: AgentDocument | None = None

    @model_validator(mode="after")
    def _check_family_slot_populated(self) -> Document:
        """Ensure the slot matching ``type`` is populated."""
        if self.type == "agent" and self.agent is None:
            msg = "Document.type='agent' requires Document.agent to be set"
            raise ValueError(msg)
        return self
