"""Aggregation logic — :class:`AuditReport` → :class:`CorpusStats`."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from contextos.audit import AuditReport
from contextos.diagnostics import DiagSeverity


class CorpusStats(BaseModel):
    """Aggregated statistics over an audited corpus."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    repo_path: Path
    files_audited: int = 0
    files_skipped: int = 0
    total_diagnostics: int = 0
    diagnostics_by_severity: dict[str, int] = {}
    top_codes: list[tuple[str, int]] = []
    rules_per_file: dict[str, int] = {}
    target_coverage: dict[str, int] = {}

    def is_empty(self) -> bool:
        return self.files_audited == 0 and self.files_skipped == 0


def compute_stats(
    report: AuditReport,
    *,
    top_n: int = 10,
) -> CorpusStats:
    """Roll up an :class:`AuditReport` into a :class:`CorpusStats`.

    ``top_n`` controls how many diagnostic codes appear in
    ``top_codes`` (default 10). Codes are sorted by descending count;
    ties break by code lexicographic order so output is reproducible.
    """
    code_counter: Counter[str] = Counter()
    severity_counter: Counter[str] = Counter()

    for diagnostics in report.per_file.values():
        for diag in diagnostics:
            code_counter[diag.code] += 1
            severity_counter[diag.severity.value] += 1

    for diag in report.cross_artifact:
        code_counter[diag.code] += 1
        severity_counter[diag.severity.value] += 1

    total_diagnostics = sum(code_counter.values())

    # Ensure every severity bucket is present, even when 0.
    diagnostics_by_severity: dict[str, int] = {
        DiagSeverity.ERROR.value: severity_counter.get(DiagSeverity.ERROR.value, 0),
        DiagSeverity.WARNING.value: severity_counter.get(DiagSeverity.WARNING.value, 0),
        DiagSeverity.INFO.value: severity_counter.get(DiagSeverity.INFO.value, 0),
    }

    # Stable order: count desc, then code lexicographic asc.
    sorted_codes = sorted(code_counter.items(), key=lambda item: (-item[1], item[0]))
    top_codes = sorted_codes[:top_n]

    return CorpusStats(
        repo_path=report.repo_path,
        files_audited=len(report.per_file),
        files_skipped=len(report.skipped),
        total_diagnostics=total_diagnostics,
        diagnostics_by_severity=diagnostics_by_severity,
        top_codes=top_codes,
        rules_per_file=_rules_per_file(report),
        target_coverage=_target_coverage(report),
    )


def _rules_per_file(report: AuditReport) -> dict[str, int]:
    """Count of distinct rule codes per file (after audit)."""
    counts: dict[str, int] = {}
    for path, diagnostics in report.per_file.items():
        counts[path] = len({d.code for d in diagnostics})
    return counts


def _target_coverage(report: AuditReport) -> dict[str, int]:
    """How many files of each target the audit covered.

    AuditReport doesn't carry per-file targets directly (the per_file
    dict is keyed by path). Coverage is computed from the skipped list —
    files NOT in skipped were audited and therefore have a target the
    scanner recognized; we infer "claude_code" vs "codex" from the file
    basename. Targets without a parser show up under skipped.
    """
    coverage: Counter[str] = Counter()
    for path in report.per_file:
        if path.endswith("CLAUDE.md"):
            coverage["claude_code"] += 1
        elif path.endswith("AGENTS.md"):
            coverage["codex"] += 1
        elif path.endswith("SKILL.md"):
            coverage["anthropic_skill"] += 1
        else:
            coverage["other"] += 1
    for entry in report.skipped:
        target = str(entry.get("target", "unknown"))
        coverage[target] += 0  # ensure key present
        coverage[target] += 1
    return dict(coverage)
