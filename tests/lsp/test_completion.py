"""Unit tests for LSP completion logic — Phase 7.2."""

from __future__ import annotations

import pytest
from lsprotocol import types as lsp

from contextos.lsp.completion import compute_completions


def _at(line: int, character: int) -> lsp.Position:
    return lsp.Position(line=line, character=character)


def _labels(items: list[lsp.CompletionItem]) -> list[str]:
    return [item.label for item in items]


class TestCtxTopLevelKeys:
    def test_empty_line_suggests_all_known_keys(self) -> None:
        items = compute_completions("", _at(0, 0), "file:///tmp/x.ctx")
        # All KNOWN_ROOT_FIELDS should appear.
        labels = _labels(items)
        assert "project" in labels
        assert "artifacts" in labels
        assert "skill" in labels
        assert "rag" in labels

    def test_prefix_pro_suggests_project(self) -> None:
        items = compute_completions("pro", _at(0, 3), "file:///tmp/x.ctx")
        labels = _labels(items)
        assert "project" in labels
        assert "artifacts" not in labels

    def test_indented_prefix_still_works(self) -> None:
        items = compute_completions("  pro", _at(0, 5), "file:///tmp/x.ctx")
        assert "project" in _labels(items)


class TestCtxSectionNames:
    def test_single_bracket_offers_table_sections(self) -> None:
        items = compute_completions("[", _at(0, 1), "file:///tmp/x.ctx")
        labels = _labels(items)
        assert "identity" in labels
        assert "stack" in labels
        assert "rag" in labels
        # AoT-only sections should NOT appear under single bracket.
        assert "rules" not in labels
        assert "document" not in labels

    def test_double_bracket_offers_aot_sections(self) -> None:
        items = compute_completions("[[", _at(0, 2), "file:///tmp/x.ctx")
        labels = _labels(items)
        assert "rules" in labels
        assert "skill" in labels
        assert "document" in labels
        assert "identity" not in labels

    def test_section_insert_text_carries_closing_bracket(self) -> None:
        items = compute_completions("[rag", _at(0, 4), "file:///tmp/x.ctx")
        rag = next(i for i in items if i.label == "rag")
        assert rag.insert_text == "rag]"

    def test_aot_insert_text_carries_double_closing_bracket(self) -> None:
        items = compute_completions("[[doc", _at(0, 5), "file:///tmp/x.ctx")
        doc = next(i for i in items if i.label == "document")
        assert doc.insert_text == "document]]"


class TestCtxValueEnums:
    def test_severity_value_completion(self) -> None:
        line = 'severity = "'
        items = compute_completions(line, _at(0, len(line)), "file:///tmp/x.ctx")
        labels = _labels(items)
        assert {"must", "should", "may"} == set(labels)

    def test_chunking_strategy_value_completion(self) -> None:
        line = 'chunking_strategy = "sem'
        items = compute_completions(line, _at(0, len(line)), "file:///tmp/x.ctx")
        labels = _labels(items)
        assert "semantic" in labels
        assert "fixed" not in labels  # filtered by 'sem' prefix
        assert "header_aware" not in labels

    def test_chunking_override_completes_too(self) -> None:
        line = 'chunking_override = "'
        items = compute_completions(line, _at(0, len(line)), "file:///tmp/x.ctx")
        labels = _labels(items)
        assert set(labels) == {"fixed", "semantic", "header_aware"}

    def test_unknown_field_yields_no_value_suggestions(self) -> None:
        line = 'mystery_field = "'
        items = compute_completions(line, _at(0, len(line)), "file:///tmp/x.ctx")
        # Falls through to top-level keys; since the line is non-empty and not
        # matching any other pattern, returns empty.
        assert items == []


class TestSkillFrontmatterCompletion:
    def test_inside_frontmatter_offers_skill_keys(self) -> None:
        text = "---\n\n---\n# Body\n"
        # Cursor on the empty line between fences.
        items = compute_completions(text, _at(1, 0), "file:///tmp/SKILL.md")
        labels = _labels(items)
        assert "name" in labels
        assert "title" in labels
        assert "description" in labels
        assert "trigger_keywords" in labels

    def test_outside_frontmatter_stays_silent(self) -> None:
        text = "---\nname: x\n---\n\n# Body\n"
        # Cursor in the body section, well past the closing fence.
        items = compute_completions(text, _at(4, 0), "file:///tmp/SKILL.md")
        assert items == []

    def test_expected_output_format_value_completes(self) -> None:
        text = "---\nexpected_output_format: "
        items = compute_completions(
            text, _at(1, len("expected_output_format: ")), "file:///tmp/SKILL.md"
        )
        labels = _labels(items)
        assert set(labels) == {"json", "markdown", "text", "yaml", "toml"}


class TestUnsupportedFiles:
    def test_unknown_extension_returns_empty(self) -> None:
        items = compute_completions("pro", _at(0, 3), "file:///tmp/random.py")
        assert items == []


class TestPositionOutOfRange:
    def test_position_past_last_line_returns_empty(self) -> None:
        items = compute_completions("a\nb\n", _at(99, 0), "file:///tmp/x.ctx")
        # Empty prefix → top-level keys per the BARE_PREFIX pattern.
        # No exception, no crash — that's the contract this test pins.
        labels = _labels(items)
        assert "project" in labels


@pytest.mark.parametrize(
    ("line", "expected_in"),
    [
        ('severity = "m', "must"),
        ('severity = "may', "may"),
        ('expected_output_format = "ya', "yaml"),
    ],
)
def test_prefix_filters_value_enum(line: str, expected_in: str) -> None:
    items = compute_completions(line, _at(0, len(line)), "file:///tmp/x.ctx")
    assert expected_in in _labels(items)
