"""Tests for the rustc-style CLI renderer."""

from __future__ import annotations

import re
import textwrap

import pytest

from contextos.ast.common import Position
from contextos.diagnostics import (
    Diagnostic,
    DiagnosticBag,
    DiagSeverity,
    render_cli,
    render_cli_many,
)

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")


class TestRenderCliPlain:
    """Plain (color=False) output is the golden contract."""

    def test_minimal_diagnostic_renders_header_only(self) -> None:
        d = Diagnostic(code="A001", severity=DiagSeverity.WARNING, message="vague")
        assert render_cli(d) == "warning[A001]: vague"

    def test_with_position(self) -> None:
        d = Diagnostic(
            code="S001",
            severity=DiagSeverity.ERROR,
            message="description too vague",
            position=Position(file="x.md", line=3, column=14),
        )
        expected = textwrap.dedent(
            """\
            error[S001]: description too vague
              --> x.md:3:14"""
        )
        assert render_cli(d) == expected

    def test_with_position_no_file(self) -> None:
        d = Diagnostic(
            code="A001",
            severity=DiagSeverity.INFO,
            message="m",
            position=Position(line=5, column=2),
        )
        assert "<unknown>:5:2" in render_cli(d)

    def test_with_suggestion_and_doc(self) -> None:
        d = Diagnostic(
            code="S001",
            severity=DiagSeverity.ERROR,
            message="vague",
            position=Position(file="x.md", line=1, column=1),
            suggestion="be specific",
            doc_url="https://contextos.dev/rules/S001",
        )
        rendered = render_cli(d)
        assert "   = help: be specific" in rendered
        assert "   = doc: https://contextos.dev/rules/S001" in rendered

    def test_with_source_text_shows_underline(self) -> None:
        source = "line one\nthe offending line here\nline three"
        d = Diagnostic(
            code="A001",
            severity=DiagSeverity.ERROR,
            message="bad",
            position=Position(file="x.md", line=2, column=5),
        )
        rendered = render_cli(d, source_text=source)
        # The line itself appears.
        assert "the offending line here" in rendered
        # The line number gutter.
        assert " 2 |" in rendered
        # The underline caret at column 5 (1-indexed → 4 spaces then ^).
        assert "    ^" in rendered

    def test_source_text_out_of_range_skips_preview(self) -> None:
        source = "single line"
        d = Diagnostic(
            code="A001",
            severity=DiagSeverity.ERROR,
            message="bad",
            position=Position(file="x.md", line=99, column=1),
        )
        rendered = render_cli(d, source_text=source)
        assert "single line" not in rendered
        # Still has header + location.
        assert rendered.startswith("error[A001]: bad")

    @pytest.mark.parametrize(
        ("severity", "label"),
        [
            (DiagSeverity.ERROR, "error"),
            (DiagSeverity.WARNING, "warning"),
            (DiagSeverity.INFO, "info"),
        ],
    )
    def test_severity_label_in_header(self, severity: DiagSeverity, label: str) -> None:
        d = Diagnostic(code="X001", severity=severity, message="m")
        assert render_cli(d).startswith(f"{label}[X001]: m")


class TestRenderCliColored:
    """Color=True wraps the same content in ANSI escapes; semantics unchanged."""

    def test_includes_ansi_reset(self) -> None:
        d = Diagnostic(code="A001", severity=DiagSeverity.ERROR, message="m")
        rendered = render_cli(d, color=True)
        assert "\033[" in rendered  # has an ANSI escape
        assert "\033[0m" in rendered  # has a reset

    def test_color_does_not_change_visible_text(self) -> None:
        d = Diagnostic(
            code="A001",
            severity=DiagSeverity.ERROR,
            message="vague",
            position=Position(file="x.md", line=1, column=1),
            suggestion="be specific",
        )
        plain = render_cli(d, color=False)
        colored = render_cli(d, color=True)
        stripped = _ANSI_RE.sub("", colored)
        assert stripped == plain


class TestRenderCliMany:
    def test_empty_bag_renders_empty_string(self) -> None:
        assert render_cli_many(DiagnosticBag()) == ""

    def test_multiple_diagnostics_separated_by_blank_line(self) -> None:
        bag = DiagnosticBag(
            [
                Diagnostic(
                    code="A001",
                    severity=DiagSeverity.WARNING,
                    message="vague",
                ),
                Diagnostic(
                    code="C001",
                    severity=DiagSeverity.ERROR,
                    message="contradicts",
                ),
            ]
        )
        rendered = render_cli_many(bag)
        assert "warning[A001]" in rendered
        assert "error[C001]" in rendered
        assert "\n\n" in rendered  # blank line separator

    def test_renders_in_sorted_order(self) -> None:
        bag = DiagnosticBag(
            [
                Diagnostic(
                    code="Z999",
                    severity=DiagSeverity.INFO,
                    message="z",
                    position=Position(line=10),
                ),
                Diagnostic(
                    code="A001",
                    severity=DiagSeverity.ERROR,
                    message="a",
                    position=Position(line=2),
                ),
            ]
        )
        rendered = render_cli_many(bag)
        assert rendered.index("a") < rendered.index("z")
