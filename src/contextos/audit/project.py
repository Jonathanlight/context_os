"""Project-level data model for the repo audit.

A :class:`ProjectInferred` aggregates every recognized context artifact a
:func:`scan_repo` call finds. Phase 3.5 shipped ``agent_files``; Phase
5.5 adds ``skill_files`` for the Anthropic-skills family. ``rag_files``
will land in Phase 6.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict

from contextos.ast.document import Document


class AgentFile(BaseModel):
    """One agent-context file the scanner parsed successfully."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    path: Path
    target: str
    document: Document


class SkillFile(BaseModel):
    """One ``SKILL.md`` the scanner parsed successfully.

    Carries the same shape as :class:`AgentFile` so dispatch code in the
    auditor / stats aggregator can iterate uniformly; the parsed
    Document's ``.type`` field signals which family the file belongs to.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    path: Path
    target: str
    document: Document


class SkippedFile(BaseModel):
    """A recognized artifact the scanner cannot yet parse.

    Holds the path and the target name so the audit report can list it
    explicitly — silent skips would hide coverage gaps from the author.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    path: Path
    target: str
    reason: str


class ProjectInferred(BaseModel):
    """Repo-level virtual document aggregating every artifact found.

    The name mirrors SPEC.md §3 / ARCHITECTURE.md — the audit treats the
    repo as one logical project, even though the files live in different
    places and target different agents.
    """

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    repo_path: Path
    agent_files: list[AgentFile] = []
    skill_files: list[SkillFile] = []
    skipped_files: list[SkippedFile] = []
