"""Tests for the structured-fix dispatcher — Phase 8.5."""

from __future__ import annotations

import textwrap

from contextos.ast.common import Position
from contextos.diagnostics import Diagnostic, DiagSeverity
from contextos.fix.edit import apply_text_edit
from contextos.fix.structured import compute_fix


def _diag(code: str, *, line: int = 1, column: int = 1) -> Diagnostic:
    return Diagnostic(
        code=code,
        severity=DiagSeverity.WARNING,
        message="...",
        position=Position(file="x", line=line, column=column),
    )


# ---------------------------------------------------------------------------
# X003 — strip trailing ?
# ---------------------------------------------------------------------------


class TestX003:
    _SRC = textwrap.dedent(
        """\
        project = "X"

        [[rules]]
        id = "X-001"
        title = "Why log everything?"
        severity = "should"
        """
    )

    def test_strips_question_mark(self) -> None:
        edit = compute_fix(self._SRC, _diag("X003", line=3))
        assert edit is not None
        out = apply_text_edit(self._SRC, edit)
        assert 'title = "Why log everything"' in out
        assert "?" not in out.split("title = ")[1].split("\n")[0]

    def test_no_op_when_no_question_mark(self) -> None:
        src = self._SRC.replace("?", "")
        edit = compute_fix(src, _diag("X003", line=3))
        assert edit is None


# ---------------------------------------------------------------------------
# F001 — sentence case ALL CAPS title
# ---------------------------------------------------------------------------


class TestF001:
    def test_sentence_cases_all_caps_title(self) -> None:
        src = textwrap.dedent(
            """\
            [[rules]]
            id = "X-001"
            title = "NEVER COMMIT SECRETS"
            severity = "must"
            """
        )
        edit = compute_fix(src, _diag("F001", line=1))
        assert edit is not None
        out = apply_text_edit(src, edit)
        assert 'title = "Never commit secrets"' in out

    def test_no_op_when_already_sentence_case(self) -> None:
        src = textwrap.dedent(
            """\
            [[rules]]
            id = "X-001"
            title = "Already nice"
            severity = "must"
            """
        )
        edit = compute_fix(src, _diag("F001", line=1))
        assert edit is None

    def test_no_op_on_empty_title(self) -> None:
        # An empty title is rejected by parsing earlier, but defensive.
        src = textwrap.dedent(
            """\
            [[rules]]
            title = ""
            """
        )
        edit = compute_fix(src, _diag("F001", line=1))
        assert edit is None


# ---------------------------------------------------------------------------
# X001 — strip TODO / FIXME / XXX / HACK at start of title
# ---------------------------------------------------------------------------


class TestX001:
    def test_strips_todo(self) -> None:
        src = textwrap.dedent(
            """\
            [[rules]]
            title = "TODO: review this rule"
            """
        )
        edit = compute_fix(src, _diag("X001", line=1))
        assert edit is not None
        out = apply_text_edit(src, edit)
        assert 'title = "Review this rule"' in out

    def test_strips_fixme(self) -> None:
        src = textwrap.dedent(
            """\
            [[rules]]
            title = "FIXME: deprecated"
            """
        )
        edit = compute_fix(src, _diag("X001", line=1))
        assert edit is not None
        out = apply_text_edit(src, edit)
        assert 'title = "Deprecated"' in out

    def test_no_op_when_marker_mid_title(self) -> None:
        src = textwrap.dedent(
            """\
            [[rules]]
            title = "Review TODO list"
            """
        )
        edit = compute_fix(src, _diag("X001", line=1))
        assert edit is None

    def test_strips_case_insensitive(self) -> None:
        src = textwrap.dedent(
            """\
            [[rules]]
            title = "todo: do something"
            """
        )
        edit = compute_fix(src, _diag("X001", line=1))
        assert edit is not None
        out = apply_text_edit(src, edit)
        assert 'title = "Do something"' in out


# ---------------------------------------------------------------------------
# S005 — prepend # <title> to SKILL.md body
# ---------------------------------------------------------------------------


class TestS005:
    def test_inserts_h1_when_missing(self) -> None:
        src = textwrap.dedent(
            """\
            ---
            name: demo
            title: Demo skill
            description: Triggers when the user invokes demo via the harness.
            ---

            Plain body without a heading.
            """
        )
        edit = compute_fix(src, _diag("S005"))
        assert edit is not None
        out = apply_text_edit(src, edit)
        assert "# Demo skill" in out
        # H1 must come BEFORE the plain body.
        h1_idx = out.index("# Demo skill")
        body_idx = out.index("Plain body")
        assert h1_idx < body_idx

    def test_no_op_when_body_already_has_h1(self) -> None:
        src = textwrap.dedent(
            """\
            ---
            name: demo
            title: Demo skill
            description: Triggers when the user invokes demo via the harness.
            ---

            # Demo skill

            Body.
            """
        )
        edit = compute_fix(src, _diag("S005"))
        assert edit is None

    def test_no_op_when_no_frontmatter(self) -> None:
        src = "no frontmatter here\n"
        edit = compute_fix(src, _diag("S005"))
        assert edit is None


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


class TestDispatch:
    def test_unknown_code_returns_none(self) -> None:
        src = '[[rules]]\ntitle = "x"\n'
        edit = compute_fix(src, _diag("A001", line=1))
        assert edit is None

    def test_diag_without_position_returns_none(self) -> None:
        diag = Diagnostic(
            code="X003",
            severity=DiagSeverity.WARNING,
            message="...",
            position=None,
        )
        edit = compute_fix("...", diag)
        assert edit is None
