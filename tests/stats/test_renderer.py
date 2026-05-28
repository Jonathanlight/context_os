"""Tests for the stats renderers."""

from __future__ import annotations

import json
from pathlib import Path

from contextos.ast.common import Position
from contextos.audit.cross import AuditReport
from contextos.diagnostics import Diagnostic, DiagSeverity
from contextos.stats import compute_stats, render_stats_cli, render_stats_json


def _diag(code: str) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=DiagSeverity.WARNING,
        message="m",
        position=Position(line=1),
    )


def _report(per_file: dict[str, list[Diagnostic]]) -> AuditReport:
    return AuditReport(repo_path=Path("/repo"), per_file=per_file)


class TestCliRendering:
    def test_empty_corpus(self) -> None:
        stats = compute_stats(AuditReport(repo_path=Path("/repo")))
        assert "no files audited" in render_stats_cli(stats)

    def test_files_audited_count(self) -> None:
        stats = compute_stats(_report({"f1": [_diag("A001")], "f2": [_diag("A001")]}))
        out = render_stats_cli(stats)
        assert "files audited:  2" in out

    def test_top_codes_section(self) -> None:
        stats = compute_stats(
            _report(
                {
                    "f1": [_diag("A001"), _diag("A001"), _diag("K002")],
                    "f2": [_diag("A001")],
                }
            )
        )
        out = render_stats_cli(stats)
        assert "top codes:" in out
        assert "A001" in out

    def test_target_coverage_section(self) -> None:
        stats = compute_stats(_report({"/repo/CLAUDE.md": [_diag("A001")]}))
        out = render_stats_cli(stats)
        assert "target coverage:" in out
        assert "claude_code" in out

    def test_trailing_newline(self) -> None:
        stats = compute_stats(_report({"f": [_diag("A001")]}))
        out = render_stats_cli(stats)
        assert out.endswith("\n")
        assert not out.endswith("\n\n")


class TestJsonRendering:
    def test_empty_payload(self) -> None:
        stats = compute_stats(AuditReport(repo_path=Path("/repo")))
        payload = json.loads(render_stats_json(stats))
        assert payload["files_audited"] == 0
        assert payload["total_diagnostics"] == 0
        assert payload["top_codes"] == []

    def test_full_payload_shape(self) -> None:
        stats = compute_stats(_report({"/repo/CLAUDE.md": [_diag("A001"), _diag("K002")]}))
        payload = json.loads(render_stats_json(stats))
        assert payload["files_audited"] == 1
        assert payload["total_diagnostics"] == 2
        # top_codes is a list of [code, count] arrays in JSON.
        codes_in_top = {entry[0] for entry in payload["top_codes"]}
        assert codes_in_top == {"A001", "K002"}

    def test_indent(self) -> None:
        stats = compute_stats(_report({"f": [_diag("A001")]}))
        out = render_stats_json(stats, indent=2)
        assert "\n" in out
        assert "  " in out
