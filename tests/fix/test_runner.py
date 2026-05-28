"""Tests for the fix runner — Phase 8.5."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from contextos.fix.runner import FixResult, fix_path

_CTX_WITH_X003 = textwrap.dedent(
    """\
    project = "Test"
    artifacts = ["context"]

    [[rules]]
    id = "DOC-001"
    title = "Why do we document everything?"
    severity = "should"
    rationale = "Document for clarity."
    """
)


class TestFixPathSingleFile:
    def test_x003_fix_applied_in_memory(self, tmp_path: Path) -> None:
        ctx_file = tmp_path / "p.ctx"
        ctx_file.write_text(_CTX_WITH_X003, encoding="utf-8")
        results = fix_path(ctx_file)
        assert len(results) == 1
        assert results[0].changed()
        assert "X003" in results[0].applied_codes
        assert "?" not in results[0].new_text.split("title = ")[1].split("\n")[0]
        # File is NOT touched — the runner returns proposed text.
        assert ctx_file.read_text(encoding="utf-8") == _CTX_WITH_X003

    def test_no_diagnostics_returns_empty(self, tmp_path: Path) -> None:
        clean = textwrap.dedent(
            """\
            project = "Test"
            artifacts = ["context"]

            [[rules]]
            id = "DOC-001"
            title = "Document every public function"
            severity = "should"
            rationale = "..."
            example_good = "def foo(): ..."
            """
        )
        ctx_file = tmp_path / "p.ctx"
        ctx_file.write_text(clean, encoding="utf-8")
        results = fix_path(ctx_file)
        # No structured-fix-bearing diagnostics → empty results.
        assert results == []


class TestFixPathDirectory:
    def test_walks_recursively_via_scanner(self, tmp_path: Path) -> None:
        # Two ctx files; only one has an X003 violation.
        (tmp_path / "a.ctx").write_text(_CTX_WITH_X003, encoding="utf-8")
        (tmp_path / "b.ctx").write_text(
            textwrap.dedent(
                """\
                project = "B"
                artifacts = ["context"]

                [[rules]]
                id = "OK-001"
                title = "Stay calm"
                severity = "should"
                rationale = "Why not."
                example_good = "x"
                """
            ),
            encoding="utf-8",
        )
        results = fix_path(tmp_path)
        paths = {r.path.name for r in results}
        assert "a.ctx" in paths
        assert "b.ctx" not in paths

    def test_invalid_target_raises(self, tmp_path: Path) -> None:
        bogus = tmp_path / "missing"
        with pytest.raises(ValueError, match=r"neither a file nor a directory"):
            fix_path(bogus)


class TestFixResultProperties:
    def test_changed_true_when_text_differs(self) -> None:
        result = FixResult(
            path=Path("/tmp/x"),
            original_text="a",
            new_text="b",
            applied_codes=["X003"],
        )
        assert result.changed() is True

    def test_changed_false_when_text_identical(self) -> None:
        result = FixResult(
            path=Path("/tmp/x"),
            original_text="a",
            new_text="a",
            applied_codes=[],
        )
        assert result.changed() is False
