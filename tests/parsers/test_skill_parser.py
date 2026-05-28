"""Tests for the SKILL.md parser — Phase 5.2."""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

from contextos.parsers import (
    ContextOSParseError,
    parse_skill_file,
    parse_skill_string,
)

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "skill"


class TestMinimal:
    def test_round_required_fields(self) -> None:
        doc = parse_skill_file(FIXTURES / "minimal.md")
        assert doc.type == "skill"
        assert doc.skill is not None
        assert doc.skill.name == "minimal-skill"
        assert doc.skill.title == "Minimal skill"
        assert doc.skill.description.startswith("A bare-bones skill")
        assert doc.project == "minimal-skill"

    def test_body_preserved_verbatim(self) -> None:
        doc = parse_skill_file(FIXTURES / "minimal.md")
        assert doc.skill is not None
        assert doc.skill.body.startswith("\n# Minimal skill")
        assert "Body content goes here." in doc.skill.body

    def test_unset_optional_fields_default_to_empty(self) -> None:
        doc = parse_skill_file(FIXTURES / "minimal.md")
        assert doc.skill is not None
        assert doc.skill.trigger_keywords == []
        assert doc.skill.files == []
        assert doc.skill.tags == []
        assert doc.skill.required_runtime is None
        assert doc.skill.expected_output_format is None


class TestFullFixture:
    def test_every_field_populated(self) -> None:
        doc = parse_skill_file(FIXTURES / "full.md")
        assert doc.skill is not None
        skill = doc.skill
        assert skill.name == "pdf-extract"
        assert skill.title == "PDF invoice extraction"
        assert "Extract structured data" in skill.description
        assert skill.trigger_keywords == ["pdf", "invoice", "extract", "facture"]
        assert skill.applies_to == ["data-extraction"]
        assert skill.languages_supported == ["fr", "en"]
        assert skill.files == [
            "scripts/extract.py",
            "examples/invoice_fr.pdf",
            "examples/invoice_en.pdf",
        ]
        assert skill.required_runtime == "python>=3.10"
        assert skill.example_invocation == "Extract the line items from this invoice.pdf"
        assert skill.expected_output_format == "json"
        assert skill.tags == ["data", "pdf", "extraction"]

    def test_body_preserves_h2_sections_and_fenced_code(self) -> None:
        doc = parse_skill_file(FIXTURES / "full.md")
        assert doc.skill is not None
        body = doc.skill.body
        assert "## When to use" in body
        assert "## Files" in body
        assert "## Example invocation" in body
        assert "```\nExtract the line items from this invoice.pdf\n```" in body


class TestTitleFallbackFromH1:
    def test_derives_title_when_yaml_omits_it(self) -> None:
        doc = parse_skill_file(FIXTURES / "h1_derived_title.md")
        assert doc.skill is not None
        assert doc.skill.title == "Title derived from H1"

    def test_yaml_title_wins_when_both_present(self) -> None:
        text = textwrap.dedent(
            """\
            ---
            name: both
            title: YAML wins
            description: A skill whose YAML title takes precedence over the body H1.
            ---

            # Body H1 should lose
            """
        )
        doc = parse_skill_string(text)
        assert doc.skill is not None
        assert doc.skill.title == "YAML wins"

    def test_missing_title_and_no_h1_fails(self) -> None:
        text = textwrap.dedent(
            """\
            ---
            name: untitled
            description: A skill with no title field and no H1 in body should be rejected.
            ---

            Just a paragraph, no heading.
            """
        )
        with pytest.raises(ContextOSParseError, match=r"validation"):
            parse_skill_string(text)

    def test_h1_with_inline_formatting(self) -> None:
        text = textwrap.dedent(
            """\
            ---
            name: formatted
            description: >
              A skill whose H1 carries bold and emphasis markers; only the
              visible text becomes title.
            ---

            # **Strong** and _emphasized_ heading
            """
        )
        doc = parse_skill_string(text)
        assert doc.skill is not None
        assert doc.skill.title == "Strong and emphasized heading"


class TestErrorSurfacing:
    def test_missing_frontmatter_delimiter(self) -> None:
        with pytest.raises(ContextOSParseError, match=r"missing the YAML frontmatter"):
            parse_skill_string("# Just a Markdown file\n\nno frontmatter here.\n")

    def test_unterminated_frontmatter(self) -> None:
        with pytest.raises(ContextOSParseError, match=r"missing the YAML frontmatter"):
            parse_skill_string("---\nname: x\ndescription: d\n# never closed\n")

    def test_empty_frontmatter(self) -> None:
        with pytest.raises(ContextOSParseError, match=r"frontmatter is empty"):
            parse_skill_string("---\n---\n")

    def test_frontmatter_must_be_mapping(self) -> None:
        with pytest.raises(ContextOSParseError, match=r"YAML mapping"):
            parse_skill_string("---\n- name: list-not-a-mapping\n---\n")

    def test_malformed_yaml_surfaces_position(self) -> None:
        # Tab indent inside a mapping value is a hard YAML error.
        text = "---\nname: x\ndescription: |\n\t\ttab indent\n---\n"
        with pytest.raises(ContextOSParseError, match=r"invalid YAML"):
            parse_skill_string(text)

    def test_missing_required_name(self) -> None:
        text = textwrap.dedent(
            """\
            ---
            title: Missing name field
            description: A skill missing the required slug.
            ---

            # Missing name field
            """
        )
        with pytest.raises(ContextOSParseError, match=r"name"):
            parse_skill_string(text)

    def test_missing_required_description(self) -> None:
        text = textwrap.dedent(
            """\
            ---
            name: nodesc
            title: Missing description
            ---

            # Missing description
            """
        )
        with pytest.raises(ContextOSParseError, match=r"description"):
            parse_skill_string(text)

    def test_unknown_key_rejected(self) -> None:
        text = textwrap.dedent(
            """\
            ---
            name: extras
            title: Extras
            description: A skill that smuggles in an unknown key the parser should reject.
            allowed-tools:
              - bash
            ---

            # Extras
            """
        )
        with pytest.raises(ContextOSParseError, match=r"validation"):
            parse_skill_string(text)

    def test_invalid_slug_surfaces_validation_error(self) -> None:
        text = textwrap.dedent(
            """\
            ---
            name: NotAValidSlug
            title: Bad slug
            description: A skill whose slug breaks the kebab-case constraint.
            ---

            # Bad slug
            """
        )
        with pytest.raises(ContextOSParseError, match=r"name"):
            parse_skill_string(text)


class TestFileReadingErrors:
    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(ContextOSParseError, match=r"cannot read file"):
            parse_skill_file(tmp_path / "does-not-exist.md")


class TestBodyEdgeCases:
    def test_no_body(self) -> None:
        text = textwrap.dedent(
            """\
            ---
            name: nobody
            title: No body
            description: A skill with frontmatter and nothing after the closing delimiter.
            ---
            """
        )
        doc = parse_skill_string(text)
        assert doc.skill is not None
        assert doc.skill.body == ""

    def test_body_with_leading_blank_line(self) -> None:
        # Verbatim preservation: the blank line between `---` and body
        # must survive so an emitter can re-emit the same bytes.
        text = textwrap.dedent(
            """\
            ---
            name: blanks
            title: Blanks
            description: >
              Verify leading blank lines after the closing delimiter
              survive a round trip.
            ---


            Body starts after two blank lines.
            """
        )
        doc = parse_skill_string(text)
        assert doc.skill is not None
        assert doc.skill.body.startswith("\n\nBody starts")
