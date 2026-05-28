"""Tests for the SKILL.md emitter — Phase 5.3.

The emitter has two contracts to verify:

1. **Byte stability** — the same input always emits the same bytes.
2. **Idempotence** — parse → emit → parse equals the original parse.

The first is checked with snapshot tests on hand-written fixtures.
The second is checked with hypothesis on randomly-generated skills.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from contextos.ast.agent import AgentDocument
from contextos.ast.document import Document
from contextos.ast.skill import (
    DESCRIPTION_MAX_CHARS,
    SkillDocument,
)
from contextos.emitters import emit_skill_markdown
from contextos.parsers import parse_skill_string

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures" / "skill"


def _wrap(skill: SkillDocument) -> Document:
    return Document(project=skill.name, type="skill", skill=skill)


def _minimal_skill(**overrides: object) -> SkillDocument:
    payload: dict[str, object] = {
        "name": "pdf-extract",
        "title": "PDF invoice extraction",
        "description": (
            "Extract structured data from PDF invoices. Triggers when the "
            "user asks to parse or process an invoice PDF."
        ),
    }
    payload.update(overrides)
    return SkillDocument.model_validate(payload)


class TestRequiresSkillFlavor:
    def test_rejects_agent_document(self) -> None:
        with pytest.raises(ValueError, match=r"Document\.type='skill'"):
            emit_skill_markdown(Document(project="X", agent=AgentDocument()))

    def test_rejects_skill_with_none_payload_via_construct(self) -> None:
        # The Document validator forbids type='skill' with skill=None at
        # construction time, so we use model_construct to bypass it and
        # confirm the emitter still defends itself.
        doc = Document.model_construct(project="X", type="skill", skill=None)
        with pytest.raises(ValueError, match=r"Document\.type='skill'"):
            emit_skill_markdown(doc)


class TestStructure:
    def test_starts_with_frontmatter_open(self) -> None:
        out = emit_skill_markdown(_wrap(_minimal_skill()))
        assert out.startswith("---\n")

    def test_contains_frontmatter_close(self) -> None:
        out = emit_skill_markdown(_wrap(_minimal_skill()))
        assert "\n---\n" in out

    def test_ends_with_single_trailing_newline_when_body_present(self) -> None:
        out = emit_skill_markdown(_wrap(_minimal_skill(body="# Hello\n\nBody\n")))
        assert out.endswith("\n")
        assert not out.endswith("\n\n\n")

    def test_no_body_yields_clean_ending(self) -> None:
        out = emit_skill_markdown(_wrap(_minimal_skill()))
        # No body: the file ends right after the closing frontmatter delim.
        assert out.endswith("---\n")

    def test_no_trailing_whitespace_per_line(self) -> None:
        out = emit_skill_markdown(_wrap(_minimal_skill()))
        for line in out.splitlines():
            assert not line.endswith(" "), f"trailing space on line: {line!r}"


class TestFrontmatterFieldOrder:
    def test_canonical_field_order(self) -> None:
        skill = _minimal_skill(
            trigger_keywords=["pdf"],
            applies_to=["data"],
            languages_supported=["en"],
            files=["x.py"],
            required_runtime="python>=3.10",
            example_invocation="Use it.",
            expected_output_format="json",
            tags=["t"],
        )
        out = emit_skill_markdown(_wrap(skill))
        indices = [
            out.index("name:"),
            out.index("title:"),
            out.index("description:"),
            out.index("trigger_keywords:"),
            out.index("applies_to:"),
            out.index("languages_supported:"),
            out.index("files:"),
            out.index("required_runtime:"),
            out.index("example_invocation:"),
            out.index("expected_output_format:"),
            out.index("tags:"),
        ]
        assert indices == sorted(indices)


class TestDefaultOmission:
    def test_unset_optional_fields_not_emitted(self) -> None:
        out = emit_skill_markdown(_wrap(_minimal_skill()))
        for absent_key in (
            "trigger_keywords",
            "applies_to",
            "languages_supported",
            "files",
            "required_runtime",
            "example_invocation",
            "expected_output_format",
            "tags",
        ):
            assert absent_key not in out, f"{absent_key!r} should be omitted"

    def test_empty_lists_treated_as_default(self) -> None:
        skill = _minimal_skill(trigger_keywords=[], tags=[])
        out = emit_skill_markdown(_wrap(skill))
        assert "trigger_keywords" not in out
        assert "tags" not in out


class TestByteStability:
    def test_same_doc_emits_same_bytes(self) -> None:
        doc = _wrap(_minimal_skill(trigger_keywords=["pdf", "invoice"]))
        assert emit_skill_markdown(doc) == emit_skill_markdown(doc)


class TestRoundTrip:
    """parse → emit → parse → equal."""

    @pytest.mark.parametrize("fixture_name", ["minimal", "full", "h1_derived_title"])
    def test_fixture_round_trip(self, fixture_name: str) -> None:
        source = (FIXTURES / f"{fixture_name}.md").read_text(encoding="utf-8")
        doc_first = parse_skill_string(source)
        emitted = emit_skill_markdown(doc_first)
        doc_second = parse_skill_string(emitted)
        assert doc_first == doc_second

    def test_idempotent_emit(self) -> None:
        # emit(parse(emit(parse(text)))) == emit(parse(text))
        source = (FIXTURES / "full.md").read_text(encoding="utf-8")
        first = emit_skill_markdown(parse_skill_string(source))
        second = emit_skill_markdown(parse_skill_string(first))
        assert first == second


class TestSnapshotMinimal:
    def test_minimal_snapshot(self) -> None:
        skill = SkillDocument(
            name="hello",
            title="Hello",
            description="A minimal trigger description with enough text to satisfy the model.",
        )
        out = emit_skill_markdown(_wrap(skill))
        expected = textwrap.dedent(
            """\
            ---
            name: hello
            title: Hello
            description: A minimal trigger description with enough text to satisfy the model.
            ---
            """
        )
        assert out == expected


class TestHypothesisRoundTrip:
    """Generate random valid SkillDocuments and assert idempotence."""

    @staticmethod
    def _slug_strategy() -> st.SearchStrategy[str]:
        first = st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=1)
        rest = st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", max_size=30)
        return st.builds(lambda f, r: f + r, first, rest)

    @staticmethod
    def _safe_text_strategy(min_size: int = 1, max_size: int = 80) -> st.SearchStrategy[str]:
        # ASCII letters, digits, spaces, and basic punctuation only. ruamel
        # emits special characters fine but the body H1 fallback can re-
        # interpret e.g. '#' as a heading; staying ASCII keeps the
        # round-trip deterministic across the full input space.
        alphabet = st.characters(
            min_codepoint=32,
            max_codepoint=126,
            blacklist_characters="\n\r\t:#-",
        )
        return (
            st.text(alphabet=alphabet, min_size=min_size, max_size=max_size)
            .map(str.strip)
            .filter(lambda s: len(s) >= min_size)
        )

    @given(
        name=_slug_strategy(),
        title=_safe_text_strategy(min_size=1, max_size=60),
        description=_safe_text_strategy(min_size=20, max_size=200),
        trigger_keywords=st.lists(
            st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=12),
            max_size=5,
            unique=True,
        ),
        tags=st.lists(
            st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", min_size=1, max_size=12),
            max_size=5,
            unique=True,
        ),
    )
    @settings(
        max_examples=200,
        deadline=None,
        suppress_health_check=[HealthCheck.too_slow, HealthCheck.function_scoped_fixture],
    )
    def test_round_trip_idempotent(
        self,
        name: str,
        title: str,
        description: str,
        trigger_keywords: list[str],
        tags: list[str],
    ) -> None:
        # Description has a hard 1024-char cap; stay well under.
        assert len(description) <= DESCRIPTION_MAX_CHARS
        skill = SkillDocument(
            name=name,
            title=title,
            description=description,
            trigger_keywords=trigger_keywords,
            tags=tags,
        )
        doc = _wrap(skill)
        emitted = emit_skill_markdown(doc)
        reparsed = parse_skill_string(emitted)
        assert reparsed.skill is not None
        assert reparsed.skill.name == skill.name
        assert reparsed.skill.title == skill.title
        assert reparsed.skill.description == skill.description
        assert reparsed.skill.trigger_keywords == skill.trigger_keywords
        assert reparsed.skill.tags == skill.tags
