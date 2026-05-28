"""Repo-level audit — walk a repository, parse every recognized context
artifact, and run per-document analyzers plus cross-artifact rules.

Phase 3.5 ships the agent-family audit only:

- ``scan_repo(root)`` walks the filesystem and returns a
  :class:`ProjectInferred` aggregating every parseable agent file. Files
  matching unsupported targets (``.cursorrules``, ``.clinerules``, …)
  are noted but skipped — their parsers land later.
- ``audit_project(project)`` runs per-document analyzers on each
  agent file, plus cross-artifact rules (XA001 today).
- ``render_audit_cli`` and ``render_audit_json`` produce human and
  machine-readable reports.

Phase 5 (skills) and Phase 6 (RAG) extend the scanner and add their own
cross-artifact rules.
"""

from __future__ import annotations

from contextos.audit.cross import AuditReport, audit_project
from contextos.audit.project import AgentFile, ProjectInferred, SkippedFile
from contextos.audit.renderer import render_audit_cli, render_audit_json
from contextos.audit.scanner import scan_repo

__all__ = [
    "AgentFile",
    "AuditReport",
    "ProjectInferred",
    "SkippedFile",
    "audit_project",
    "render_audit_cli",
    "render_audit_json",
    "scan_repo",
]
