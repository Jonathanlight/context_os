"""Tests for the JSON diagnostic renderer."""

from __future__ import annotations

import json

from contextos.ast.common import Position
from contextos.diagnostics import (
    Diagnostic,
    DiagnosticBag,
    DiagSeverity,
    render_json,
    render_json_many,
)


class TestRenderJson:
    def test_minimal_shape(self) -> None:
        d = Diagnostic(code="A001", severity=DiagSeverity.WARNING, message="vague")
        payload = json.loads(render_json(d))
        assert payload == {"code": "A001", "severity": "warning", "message": "vague"}

    def test_full_shape_matches_spec(self) -> None:
        d = Diagnostic(
            code="S001",
            severity=DiagSeverity.ERROR,
            message="description too vague",
            position=Position(file="skills/pdf-extract/SKILL.md", line=3, column=14),
            suggestion="describe input and output",
            doc_url="https://contextos.dev/rules/S001",
        )
        payload = json.loads(render_json(d))
        # Match SPEC.md §3 exactly (modulo severity which is the DiagSeverity).
        assert payload == {
            "code": "S001",
            "severity": "error",
            "file": "skills/pdf-extract/SKILL.md",
            "line": 3,
            "column": 14,
            "message": "description too vague",
            "suggestion": "describe input and output",
            "doc_url": "https://contextos.dev/rules/S001",
        }

    def test_none_fields_are_omitted(self) -> None:
        d = Diagnostic(code="A001", severity=DiagSeverity.INFO, message="m")
        payload = json.loads(render_json(d))
        assert "suggestion" not in payload
        assert "doc_url" not in payload
        assert "file" not in payload
        assert "line" not in payload

    def test_position_without_file_lifts_line_and_column(self) -> None:
        d = Diagnostic(
            code="A001",
            severity=DiagSeverity.INFO,
            message="m",
            position=Position(line=5, column=3),
        )
        payload = json.loads(render_json(d))
        assert payload["line"] == 5
        assert payload["column"] == 3
        assert "file" not in payload

    def test_keys_sorted_for_diff_stability(self) -> None:
        d = Diagnostic(code="A001", severity=DiagSeverity.INFO, message="m")
        rendered = render_json(d)
        # When sort_keys=True, "code" precedes "message" precedes "severity".
        assert rendered.index("code") < rendered.index("message")
        assert rendered.index("message") < rendered.index("severity")

    def test_indent_pretty_prints(self) -> None:
        d = Diagnostic(code="A001", severity=DiagSeverity.INFO, message="m")
        rendered = render_json(d, indent=2)
        assert "\n" in rendered
        assert "  " in rendered


class TestRenderJsonMany:
    def test_empty_bag(self) -> None:
        assert render_json_many(DiagnosticBag()) == "[]"

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
        payload = json.loads(render_json_many(bag))
        assert [item["code"] for item in payload] == ["A001", "Z999"]

    def test_indent_for_human_consumption(self) -> None:
        bag = DiagnosticBag([Diagnostic(code="A001", severity=DiagSeverity.INFO, message="m")])
        rendered = render_json_many(bag, indent=2)
        assert rendered.startswith("[\n  {")
