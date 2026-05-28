"""Unit tests for LSP code actions — Phase 7.3."""

from __future__ import annotations

import textwrap

import pytest
from lsprotocol import types as lsp

from contextos.lsp.code_actions import compute_code_actions


def _diag(
    *,
    code: str,
    message: str,
    line: int = 0,
    character: int = 0,
) -> lsp.Diagnostic:
    anchor = lsp.Position(line=line, character=character)
    return lsp.Diagnostic(
        range=lsp.Range(start=anchor, end=anchor),
        message=message,
        severity=lsp.DiagnosticSeverity.Warning,
        code=code,
        source="contextos",
    )


def _titles(actions: list[lsp.CodeAction]) -> list[str]:
    return [a.title for a in actions]


class TestInfoOnly:
    def test_diagnostic_with_suggestion_yields_quickfix(self) -> None:
        diag = _diag(
            code="A001",
            message="vague directive\n\nhelp: rephrase with a measurable criterion",
        )
        actions = compute_code_actions("", [diag], "file:///tmp/x.ctx")
        assert len(actions) == 1
        assert actions[0].kind == lsp.CodeActionKind.QuickFix
        assert "A001" in actions[0].title
        assert "rephrase with a measurable criterion" in actions[0].title

    def test_diagnostic_without_suggestion_yields_nothing(self) -> None:
        diag = _diag(code="A001", message="vague directive")
        actions = compute_code_actions("", [diag], "file:///tmp/x.ctx")
        assert actions == []

    def test_multiline_suggestion_uses_first_line(self) -> None:
        diag = _diag(
            code="K002",
            message=(
                "must-severity rule 'TDD-001' has no rationale\n\n"
                'help: add `rationale = "..."` explaining why\n'
                "(what breaks if it is violated)"
            ),
        )
        actions = compute_code_actions("", [diag], "file:///tmp/x.ctx")
        assert len(actions) == 1
        assert "explaining why" in actions[0].title
        assert "(what breaks" not in actions[0].title

    def test_diagnostic_attached_to_action(self) -> None:
        diag = _diag(code="A001", message="vague\n\nhelp: rephrase")
        actions = compute_code_actions("", [diag], "file:///tmp/x.ctx")
        assert actions[0].diagnostics == [diag]


class TestX003StructuredFix:
    """Strip the trailing ``?`` from a rule title."""

    _SRC = textwrap.dedent(
        """\
        project = "X"
        artifacts = ["context"]

        [[rules]]
        id = "DOC-001"
        title = "Why should we document everything?"
        severity = "should"
        """
    )

    def _x003_diag(self, line: int) -> lsp.Diagnostic:
        return _diag(
            code="X003",
            message=(
                "rule 'DOC-001' title ends with '?'\n\n"
                "help: rephrase as a directive (drop the trailing '?')"
            ),
            line=line,
        )

    def test_emits_structured_action_with_workspace_edit(self) -> None:
        diag = self._x003_diag(line=3)  # [[rules]] header line
        actions = compute_code_actions(self._SRC, [diag], "file:///tmp/x.ctx")
        # Two actions: structured + info-only fallback.
        assert len(actions) == 2
        structured = actions[0]
        assert structured.edit is not None
        assert structured.is_preferred is True
        assert "drop the trailing" in structured.title.lower()

    def test_workspace_edit_targets_question_mark(self) -> None:
        diag = self._x003_diag(line=3)
        actions = compute_code_actions(self._SRC, [diag], "file:///tmp/x.ctx")
        structured = actions[0]
        assert structured.edit is not None
        changes = structured.edit.changes
        assert changes is not None
        edits = changes["file:///tmp/x.ctx"]
        assert len(edits) == 1
        text_edit = edits[0]
        # The edit should delete exactly one character (the '?').
        assert text_edit.new_text == ""
        title_line = self._SRC.splitlines()[5]  # the title line
        question_pos = title_line.index("?")
        assert text_edit.range.start.line == 5
        assert text_edit.range.start.character == question_pos
        assert text_edit.range.end.character == question_pos + 1

    def test_no_action_when_title_has_no_question_mark(self) -> None:
        src = textwrap.dedent(
            """\
            [[rules]]
            id = "DOC-001"
            title = "Document everything."
            severity = "should"
            """
        )
        diag = _diag(code="X003", message="x\n\nhelp: y", line=0)
        actions = compute_code_actions(src, [diag], "file:///tmp/x.ctx")
        # Only the info-only fallback should fire — no structured edit.
        assert len(actions) == 1
        assert actions[0].edit is None

    def test_bails_when_title_not_found_within_window(self) -> None:
        src = "\n" * 20 + 'title = "Something?"'
        diag = _diag(code="X003", message="x\n\nhelp: y", line=0)
        actions = compute_code_actions(src, [diag], "file:///tmp/x.ctx")
        # Only info-only fallback (no structured edit since title is
        # beyond the 8-line scan window).
        assert len(actions) == 1
        assert actions[0].edit is None

    def test_bails_when_blank_line_separates_diagnostic_from_title(self) -> None:
        src = textwrap.dedent(
            """\
            [[rules]]

            title = "Unsafe?"
            """
        )
        diag = _diag(code="X003", message="x\n\nhelp: y", line=0)
        actions = compute_code_actions(src, [diag], "file:///tmp/x.ctx")
        # The blank line on the 2nd line of the source stops the
        # forward scan — we don't want to fix a different rule's title.
        # However, because the scan also stops on next-section markers
        # (lines starting with `[`), this test pins the no-cross-section
        # contract.
        assert len(actions) == 1
        assert actions[0].edit is None


class TestActionOrdering:
    def test_structured_fix_emitted_before_info_only(self) -> None:
        src = textwrap.dedent(
            """\
            [[rules]]
            id = "X-001"
            title = "Safe?"
            severity = "must"
            """
        )
        diag = _diag(code="X003", message="x\n\nhelp: drop the ?", line=0)
        actions = compute_code_actions(src, [diag], "file:///tmp/x.ctx")
        assert len(actions) == 2
        assert actions[0].edit is not None
        assert actions[1].edit is None


@pytest.mark.parametrize(
    "code",
    ["A001", "S001", "R001", "K002", "F001", "X001", "P001"],
)
def test_other_codes_emit_info_only(code: str) -> None:
    diag = _diag(code=code, message=f"{code} fired\n\nhelp: do better")
    actions = compute_code_actions("", [diag], "file:///tmp/x.ctx")
    assert len(actions) == 1
    assert actions[0].edit is None
