"""Unit tests for the ContextOS Diagnostic -> LSP Diagnostic adapter."""

from __future__ import annotations

from lsprotocol import types as lsp

from contextos.ast.common import Position
from contextos.diagnostics import Diagnostic, DiagSeverity
from contextos.lsp.diagnostics_adapter import to_lsp_diagnostic


def _diag(**overrides: object) -> Diagnostic:
    payload: dict[str, object] = {
        "code": "A001",
        "severity": DiagSeverity.WARNING,
        "message": "vague directive",
    }
    payload.update(overrides)
    return Diagnostic.model_validate(payload)


class TestSeverityMapping:
    def test_error_maps_to_lsp_error(self) -> None:
        out = to_lsp_diagnostic(_diag(severity=DiagSeverity.ERROR))
        assert out.severity == lsp.DiagnosticSeverity.Error

    def test_warning_maps_to_lsp_warning(self) -> None:
        out = to_lsp_diagnostic(_diag(severity=DiagSeverity.WARNING))
        assert out.severity == lsp.DiagnosticSeverity.Warning

    def test_info_maps_to_lsp_information(self) -> None:
        out = to_lsp_diagnostic(_diag(severity=DiagSeverity.INFO))
        assert out.severity == lsp.DiagnosticSeverity.Information


class TestRangeFromPosition:
    def test_one_indexed_position_converts_to_zero_indexed_lsp(self) -> None:
        diag = _diag(position=Position(line=42, column=7))
        out = to_lsp_diagnostic(diag)
        assert out.range.start.line == 41
        assert out.range.start.character == 6

    def test_zero_length_range_at_anchor(self) -> None:
        diag = _diag(position=Position(line=3, column=5))
        out = to_lsp_diagnostic(diag)
        assert out.range.start == out.range.end

    def test_missing_position_collapses_to_file_origin(self) -> None:
        out = to_lsp_diagnostic(_diag(position=None))
        assert out.range.start.line == 0
        assert out.range.start.character == 0
        assert out.range.end.line == 0
        assert out.range.end.character == 0

    def test_position_line_one_becomes_zero(self) -> None:
        # Pydantic guards against line=0, so the smallest legitimate
        # position is line=1 which must collapse to LSP line 0.
        out = to_lsp_diagnostic(_diag(position=Position(line=1, column=1)))
        assert out.range.start.line == 0
        assert out.range.start.character == 0


class TestMessageComposition:
    def test_message_without_suggestion_is_passed_through(self) -> None:
        out = to_lsp_diagnostic(_diag(message="plain message"))
        assert out.message == "plain message"

    def test_message_with_suggestion_appends_help(self) -> None:
        out = to_lsp_diagnostic(
            _diag(message="vague directive", suggestion="rephrase with a measurable criterion"),
        )
        assert "vague directive" in out.message
        assert "help: rephrase with a measurable criterion" in out.message


class TestSourceAndCode:
    def test_source_is_contextos(self) -> None:
        out = to_lsp_diagnostic(_diag())
        assert out.source == "contextos"

    def test_code_carries_diagnostic_code(self) -> None:
        out = to_lsp_diagnostic(_diag(code="R001"))
        assert out.code == "R001"

    def test_doc_url_attached_as_code_description(self) -> None:
        out = to_lsp_diagnostic(_diag(doc_url="https://contextos.dev/rules/A001"))
        assert out.code_description is not None
        assert out.code_description.href == "https://contextos.dev/rules/A001"

    def test_missing_doc_url_yields_no_code_description(self) -> None:
        out = to_lsp_diagnostic(_diag(doc_url=None))
        assert out.code_description is None
