"""Cross-artifact audit — per-file analyzers + XA*** rules.

Phase 3.5 ships XA001 only: rule ids that collide across files. NLI- or
semantic-similarity-based cross-rules land later.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from contextos.analyzers import lint_document
from contextos.audit.project import AgentFile, ProjectInferred
from contextos.diagnostics import Diagnostic, DiagnosticBag, DiagSeverity

# ---------------------------------------------------------------------------
# XA001 — rule id collision across files
# ---------------------------------------------------------------------------

XA001_CODE = "XA001"
XA001_SEVERITY = DiagSeverity.WARNING
XA001_DOC_URL = "https://contextos.dev/rules/XA001"

# A rule id needs at least two occurrences for a collision to make sense.
_MIN_COLLISION = 2


class AuditReport(BaseModel):
    """Output of :func:`audit_project` — per-file + cross-artifact diagnostics."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    repo_path: Path
    per_file: dict[str, list[Diagnostic]] = {}
    cross_artifact: list[Diagnostic] = []
    skipped: list[dict[str, str]] = []

    def total_count(self) -> int:
        return sum(len(diags) for diags in self.per_file.values()) + len(self.cross_artifact)

    def has_errors(self) -> bool:
        for diags in self.per_file.values():
            if any(d.severity == DiagSeverity.ERROR for d in diags):
                return True
        return any(d.severity == DiagSeverity.ERROR for d in self.cross_artifact)


def audit_project(project: ProjectInferred) -> AuditReport:
    """Run every analyzer on every parseable file + cross-artifact rules.

    Iterates both ``agent_files`` and ``skill_files`` so all S-coded
    diagnostics surface alongside the A/C/F/K/P/X ones. Cross-artifact
    rules currently only operate on the agent file set (XA001 detects
    rule-id collisions between agent files); skill cross-rules will
    arrive when more than one skill-side dimension warrants them.
    """
    per_file: dict[str, list[Diagnostic]] = {}
    for entry in project.agent_files:
        bag = lint_document(entry.document, source=str(entry.path))
        per_file[str(entry.path)] = bag.sorted()
    for skill_entry in project.skill_files:
        bag = lint_document(skill_entry.document, source=str(skill_entry.path))
        per_file[str(skill_entry.path)] = bag.sorted()

    cross_artifact = list(_check_xa001(project.agent_files))

    skipped = [
        {
            "path": str(s.path),
            "target": s.target,
            "reason": s.reason,
        }
        for s in project.skipped_files
    ]

    return AuditReport(
        repo_path=project.repo_path,
        per_file=per_file,
        cross_artifact=cross_artifact,
        skipped=skipped,
    )


def _check_xa001(agent_files: list[AgentFile]) -> Iterable[Diagnostic]:
    """XA001 — flag rule ids that appear in multiple files with conflicting content.

    Two rules sharing an id is acceptable when their content is identical
    (same title + severity) — that's the same rule referenced from two
    targets. It is a problem when the content differs, because the LLM
    sees inconsistent directives under the same identifier.
    """
    by_id: dict[str, list[tuple[AgentFile, object]]] = defaultdict(list)
    for entry in agent_files:
        agent = entry.document.agent
        if agent is None:
            continue
        for rule in agent.rules:
            by_id[rule.id].append((entry, rule))

    for rule_id, occurrences in sorted(by_id.items()):
        if len(occurrences) < _MIN_COLLISION:
            continue
        # All occurrences identical (title + severity) → no diagnostic.
        signatures = {(rule.title, rule.severity) for _, rule in occurrences}  # type: ignore[attr-defined]
        if len(signatures) <= 1:
            continue

        files = sorted({str(f.path) for f, _ in occurrences})
        yield Diagnostic(
            code=XA001_CODE,
            severity=XA001_SEVERITY,
            message=(
                f"rule id '{rule_id}' collides across {len(occurrences)} "
                f"files with different content: {files}"
            ),
            suggestion=(
                "give each rule a unique id, or unify the title/severity if "
                "the two files genuinely describe the same directive"
            ),
            doc_url=XA001_DOC_URL,
        )


def _bag_from_diagnostics(diagnostics: list[Diagnostic]) -> DiagnosticBag:
    """Convenience for callers that want the bag API back."""
    bag = DiagnosticBag()
    bag.extend(diagnostics)
    return bag
