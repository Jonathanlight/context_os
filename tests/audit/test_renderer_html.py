"""Tests for the HTML audit renderer — Phase 8.3."""

from __future__ import annotations

from pathlib import Path

from contextos.ast.common import Position
from contextos.audit.cross import AuditReport
from contextos.audit.renderer_html import render_audit_html
from contextos.diagnostics import Diagnostic, DiagSeverity


def _diag(
    *,
    code: str = "A001",
    severity: DiagSeverity = DiagSeverity.WARNING,
    message: str = "vague directive",
    line: int = 42,
    column: int = 1,
    doc_url: str | None = None,
    suggestion: str | None = None,
) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=severity,
        message=message,
        position=Position(file="file.md", line=line, column=column),
        doc_url=doc_url,
        suggestion=suggestion,
    )


def _report(
    *,
    per_file: dict[str, list[Diagnostic]] | None = None,
    cross_artifact: list[Diagnostic] | None = None,
    skipped: list[dict[str, str]] | None = None,
) -> AuditReport:
    return AuditReport(
        repo_path=Path("/tmp/repo"),
        per_file=per_file or {},
        cross_artifact=cross_artifact or [],
        skipped=skipped or [],
    )


class TestHtmlScaffold:
    def test_returns_valid_html_doctype(self) -> None:
        out = render_audit_html(_report())
        assert out.startswith("<!doctype html>")

    def test_title_in_head(self) -> None:
        out = render_audit_html(_report(), title="My audit")
        assert "<title>My audit</title>" in out

    def test_default_title(self) -> None:
        out = render_audit_html(_report())
        assert "<title>ContextOS audit</title>" in out

    def test_filters_present(self) -> None:
        out = render_audit_html(_report())
        for sev in ["error", "warning", "info"]:
            assert f'data-filter="{sev}"' in out


class TestDiagnosticRendering:
    def test_single_diagnostic_rendered(self) -> None:
        report = _report(per_file={"CLAUDE.md": [_diag()]})
        out = render_audit_html(report)
        assert "CLAUDE.md" in out
        assert "A001" in out
        assert "vague directive" in out
        assert "warning" in out
        assert "42:1" in out

    def test_doc_link_rendered_when_present(self) -> None:
        report = _report(
            per_file={
                "CLAUDE.md": [
                    _diag(doc_url="https://contextos.dev/rules/A001"),
                ]
            }
        )
        out = render_audit_html(report)
        assert 'href="https://contextos.dev/rules/A001"' in out

    def test_no_doc_link_when_absent(self) -> None:
        report = _report(per_file={"x": [_diag(doc_url=None)]})
        out = render_audit_html(report)
        # The .doc-link class is reserved in the inline CSS; what
        # matters is that no actual <a class="doc-link"> tag is
        # produced when doc_url is empty.
        assert '<a class="doc-link"' not in out

    def test_suggestion_rendered(self) -> None:
        report = _report(
            per_file={"x": [_diag(suggestion="rephrase with measurable criterion")]}
        )
        out = render_audit_html(report)
        assert "rephrase with measurable criterion" in out
        assert "suggestion" in out

    def test_severity_class_applied(self) -> None:
        report = _report(
            per_file={
                "x": [
                    _diag(severity=DiagSeverity.ERROR, code="E0001"),
                    _diag(severity=DiagSeverity.WARNING, code="W0001"),
                    _diag(severity=DiagSeverity.INFO, code="I0001"),
                ]
            }
        )
        out = render_audit_html(report)
        assert "severity-error" in out
        assert "severity-warning" in out
        assert "severity-info" in out


class TestHtmlEscape:
    def test_message_with_html_chars_is_escaped(self) -> None:
        report = _report(
            per_file={"x": [_diag(message="<script>alert('xss')</script>")]}
        )
        out = render_audit_html(report)
        # The literal script tag must NOT appear in the output as
        # an open tag — only as escaped text.
        assert "<script>alert" not in out
        assert "&lt;script&gt;" in out

    def test_path_with_html_chars_is_escaped(self) -> None:
        report = _report(per_file={"<b>bold.md": [_diag()]})
        out = render_audit_html(report)
        assert "<b>bold.md" not in out
        assert "&lt;b&gt;bold.md" in out

    def test_doc_url_is_escaped_in_href(self) -> None:
        report = _report(
            per_file={
                "x": [
                    _diag(doc_url='https://example.com/"><script>alert(1)</script>')
                ]
            }
        )
        out = render_audit_html(report)
        assert "<script>alert" not in out
        # Quotes must be entity-encoded inside the href.
        assert "&quot;" in out


class TestSectionsConditional:
    def test_empty_report_renders_no_sections(self) -> None:
        out = render_audit_html(_report())
        assert "Per-file diagnostics" not in out
        assert "Cross-artifact" not in out
        assert "Skipped" not in out

    def test_cross_artifact_section_appears(self) -> None:
        report = _report(cross_artifact=[_diag(code="XA001")])
        out = render_audit_html(report)
        assert "Cross-artifact" in out
        assert "XA001" in out

    def test_skipped_section_appears(self) -> None:
        report = _report(
            skipped=[
                {
                    "path": "/repo/.cursorrules",
                    "target": "cursor",
                    "reason": "no parser",
                }
            ]
        )
        out = render_audit_html(report)
        assert "Skipped" in out
        assert ".cursorrules" in out
        assert "no parser" in out


class TestSummary:
    def test_summary_reports_total_count(self) -> None:
        report = _report(
            per_file={
                "a": [_diag(code="A001"), _diag(code="A002")],
                "b": [_diag(code="B001")],
            },
            cross_artifact=[_diag(code="XA001")],
        )
        out = render_audit_html(report)
        assert "Total: 4 diagnostic(s)" in out


class TestCounts:
    def test_severity_counts_shown_in_filter_buttons(self) -> None:
        report = _report(
            per_file={
                "x": [
                    _diag(severity=DiagSeverity.ERROR),
                    _diag(severity=DiagSeverity.ERROR),
                    _diag(severity=DiagSeverity.WARNING),
                ]
            }
        )
        out = render_audit_html(report)
        assert "Error (2)" in out
        assert "Warning (1)" in out
        assert "Info (0)" in out


class TestSelfContained:
    def test_no_external_assets(self) -> None:
        out = render_audit_html(_report(per_file={"a": [_diag()]}))
        # No external stylesheets, scripts, or images.
        assert "<link " not in out
        assert "src=" not in out
        # Inline style + script blocks are expected.
        assert "<style>" in out
        assert "<script>" in out
