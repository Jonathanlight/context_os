"""Tests for compute_stats and CorpusStats."""

from __future__ import annotations

from pathlib import Path

from contextos.ast.common import Position
from contextos.audit.cross import AuditReport
from contextos.diagnostics import Diagnostic, DiagSeverity
from contextos.stats import compute_stats


def _diag(
    code: str,
    severity: DiagSeverity = DiagSeverity.WARNING,
    line: int = 1,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=severity,
        message="m",
        position=Position(line=line),
    )


def _report(
    per_file: dict[str, list[Diagnostic]] | None = None,
    cross: list[Diagnostic] | None = None,
    skipped: list[dict[str, str]] | None = None,
) -> AuditReport:
    return AuditReport(
        repo_path=Path("/repo"),
        per_file=per_file or {},
        cross_artifact=cross or [],
        skipped=skipped or [],
    )


class TestComputeStatsBasics:
    def test_empty_report(self) -> None:
        stats = compute_stats(_report())
        assert stats.is_empty()
        assert stats.files_audited == 0
        assert stats.total_diagnostics == 0

    def test_files_counted(self) -> None:
        report = _report(
            per_file={
                "/repo/a/CLAUDE.md": [_diag("A001")],
                "/repo/b/CLAUDE.md": [],
            }
        )
        stats = compute_stats(report)
        assert stats.files_audited == 2

    def test_skipped_counted(self) -> None:
        report = _report(
            skipped=[
                {"path": "/repo/.cursorrules", "target": "cursor", "reason": "no parser"},
                {"path": "/repo/.clinerules", "target": "cline", "reason": "no parser"},
            ]
        )
        stats = compute_stats(report)
        assert stats.files_skipped == 2


class TestSeverityCounts:
    def test_all_severities_present_even_when_zero(self) -> None:
        stats = compute_stats(_report(per_file={"f": [_diag("A001")]}))
        # All three buckets are keyed; zero counts stay visible.
        assert set(stats.diagnostics_by_severity) == {"error", "warning", "info"}

    def test_counts_aggregate_across_files(self) -> None:
        report = _report(
            per_file={
                "f1": [_diag("A001", DiagSeverity.WARNING), _diag("K003", DiagSeverity.INFO)],
                "f2": [_diag("A001", DiagSeverity.WARNING)],
            }
        )
        stats = compute_stats(report)
        assert stats.diagnostics_by_severity["warning"] == 2
        assert stats.diagnostics_by_severity["info"] == 1

    def test_cross_artifact_diagnostics_counted(self) -> None:
        report = _report(
            per_file={"f": [_diag("A001")]},
            cross=[_diag("XA001")],
        )
        stats = compute_stats(report)
        assert stats.total_diagnostics == 2
        assert any(code == "XA001" for code, _ in stats.top_codes)


class TestTopCodes:
    def test_top_codes_sorted_by_count_desc(self) -> None:
        report = _report(
            per_file={
                "f1": [_diag("A001"), _diag("A001"), _diag("K002")],
                "f2": [_diag("A001"), _diag("F002")],
            }
        )
        stats = compute_stats(report)
        # A001 (3) > K002 (1) and F002 (1).
        codes = [c for c, _ in stats.top_codes]
        assert codes[0] == "A001"
        # Ties broken by code lexicographic order.
        assert codes.index("F002") < codes.index("K002")

    def test_top_n_truncates(self) -> None:
        report = _report(
            per_file={"f": [_diag(c) for c in ["A001", "A002", "A003", "A004", "A005"]]}
        )
        stats = compute_stats(report, top_n=3)
        assert len(stats.top_codes) == 3


class TestRulesPerFile:
    def test_distinct_codes_per_file(self) -> None:
        # Two A001 + one K002 in f1 = 2 distinct codes.
        report = _report(
            per_file={
                "f1": [_diag("A001"), _diag("A001"), _diag("K002")],
                "f2": [_diag("A001")],
            }
        )
        stats = compute_stats(report)
        assert stats.rules_per_file == {"f1": 2, "f2": 1}


class TestTargetCoverage:
    def test_claude_files_counted(self) -> None:
        report = _report(
            per_file={
                "/repo/CLAUDE.md": [],
                "/repo/sub/CLAUDE.md": [],
                "/repo/AGENTS.md": [],
            }
        )
        stats = compute_stats(report)
        assert stats.target_coverage.get("claude_code") == 2
        assert stats.target_coverage.get("codex") == 1

    def test_skipped_targets_counted(self) -> None:
        report = _report(
            skipped=[
                {
                    "path": "/repo/.cursorrules",
                    "target": "cursor",
                    "reason": "no parser",
                }
            ]
        )
        stats = compute_stats(report)
        assert stats.target_coverage.get("cursor") == 1
