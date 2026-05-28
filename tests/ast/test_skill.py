"""Tests for the SkillDocument AST node — Phase 5.1.

The Pydantic model is the only public surface this PR exposes; the
parser and emitter land in 5.2 / 5.3. So the tests here focus on the
**invariants** the model is supposed to enforce on its own: slug shape,
description length cap, the closed set of output formats, and
extra-field rejection.
"""

from __future__ import annotations

import pytest
from hypothesis import given
from hypothesis import strategies as st
from pydantic import ValidationError

from contextos.ast.agent import AgentDocument
from contextos.ast.document import Document
from contextos.ast.skill import (
    DESCRIPTION_MAX_CHARS,
    NAME_PATTERN,
    SkillDocument,
)


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


class TestRequiredFields:
    def test_minimal_skill_validates(self) -> None:
        skill = _minimal_skill()
        assert skill.name == "pdf-extract"
        assert skill.title.startswith("PDF")
        assert skill.description.startswith("Extract")

    def test_recommended_fields_default_to_empty(self) -> None:
        skill = _minimal_skill()
        assert skill.trigger_keywords == []
        assert skill.applies_to == []
        assert skill.languages_supported == []
        assert skill.files == []
        assert skill.tags == []
        assert skill.required_runtime is None
        assert skill.example_invocation is None
        assert skill.expected_output_format is None
        assert skill.body == ""

    def test_missing_name_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SkillDocument(title="t", description="d")  # type: ignore[call-arg]

    def test_missing_title_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SkillDocument(name="pdf", description="d")  # type: ignore[call-arg]

    def test_missing_description_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SkillDocument(name="pdf", title="t")  # type: ignore[call-arg]


class TestNameSlugConstraints:
    """``name`` must match :data:`NAME_PATTERN` (lowercase kebab-case, ≤64)."""

    @pytest.mark.parametrize(
        "name",
        [
            "a",
            "abc",
            "pdf-extract",
            "a1",
            "data-pipeline-v2",
            "a" * 64,
        ],
    )
    def test_valid_slugs_accepted(self, name: str) -> None:
        skill = _minimal_skill(name=name)
        assert skill.name == name
        assert skill.is_valid_name()

    @pytest.mark.parametrize(
        "name",
        [
            "",
            "PDF-Extract",  # uppercase
            "1pdf",  # starts with digit
            "-pdf",  # starts with hyphen
            "pdf_extract",  # underscore
            "pdf extract",  # space
            "a" * 65,  # too long
            "pdf--extract!",  # special char
        ],
    )
    def test_invalid_slugs_rejected(self, name: str) -> None:
        with pytest.raises(ValidationError):
            _minimal_skill(name=name)

    def test_pattern_constant_is_anchored(self) -> None:
        # Guard against a future edit dropping the ^/$ — a non-anchored
        # regex would accept "Invalid Name pdf-extract" via partial match
        # when used by downstream code via re.search.
        assert NAME_PATTERN.startswith("^")
        assert NAME_PATTERN.endswith("$")


class TestDescriptionLengthCap:
    def test_at_limit_is_accepted(self) -> None:
        skill = _minimal_skill(description="a" * DESCRIPTION_MAX_CHARS)
        assert len(skill.description) == DESCRIPTION_MAX_CHARS

    def test_one_over_limit_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _minimal_skill(description="a" * (DESCRIPTION_MAX_CHARS + 1))

    def test_empty_description_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _minimal_skill(description="")


class TestExpectedOutputFormat:
    @pytest.mark.parametrize(
        "fmt",
        ["json", "markdown", "text", "yaml", "toml"],
    )
    def test_allowed_format(self, fmt: str) -> None:
        skill = _minimal_skill(expected_output_format=fmt)
        assert skill.expected_output_format == fmt

    @pytest.mark.parametrize("fmt", ["JSON", "xml", "csv", "binary", ""])
    def test_rejected_format(self, fmt: str) -> None:
        with pytest.raises(ValidationError):
            _minimal_skill(expected_output_format=fmt)

    def test_none_is_allowed(self) -> None:
        skill = _minimal_skill(expected_output_format=None)
        assert skill.expected_output_format is None


class TestExtraFieldsForbidden:
    def test_unknown_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _minimal_skill(unknown_field="oops")


class TestRoundTrip:
    def test_round_trip_via_dict(self) -> None:
        original = _minimal_skill(
            trigger_keywords=["pdf", "invoice"],
            files=["scripts/extract.py", "examples/invoice.pdf"],
            required_runtime="python>=3.10",
            example_invocation="Extract the line items.",
            expected_output_format="json",
            tags=["data", "pdf"],
            body="# Overview\n\nThis skill extracts PDF invoices.\n",
        )
        restored = SkillDocument.model_validate(original.model_dump())
        assert restored == original

    def test_round_trip_via_json(self) -> None:
        original = _minimal_skill(tags=["data"])
        restored = SkillDocument.model_validate_json(original.model_dump_json())
        assert restored == original


class TestDocumentSkillFlavor:
    """Document.type='skill' integration — symmetric to the agent flavor."""

    def test_minimal_skill_document(self) -> None:
        doc = Document(project="MyApp", type="skill", skill=_minimal_skill())
        assert doc.type == "skill"
        assert doc.skill is not None
        assert doc.skill.name == "pdf-extract"
        assert doc.agent is None

    def test_skill_type_requires_skill_slot(self) -> None:
        with pytest.raises(ValidationError, match=r"requires Document\.skill"):
            Document(project="X", type="skill", skill=None)

    def test_skill_type_rejects_stray_agent_payload(self) -> None:
        with pytest.raises(ValidationError, match=r"must not carry an agent payload"):
            Document(
                project="X",
                type="skill",
                skill=_minimal_skill(),
                agent=AgentDocument(),
            )

    def test_skill_document_round_trips_via_json(self) -> None:
        original = Document(project="MyApp", type="skill", skill=_minimal_skill())
        restored = Document.model_validate_json(original.model_dump_json())
        assert restored == original


class TestHypothesisInvariants:
    """Property-based: build a slug from the pattern, model accepts it."""

    @given(
        first=st.text(alphabet="abcdefghijklmnopqrstuvwxyz", min_size=1, max_size=1),
        rest=st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789-", max_size=60),
    )
    def test_generated_slugs_always_accepted(self, first: str, rest: str) -> None:
        slug = first + rest
        skill = _minimal_skill(name=slug)
        assert skill.name == slug
        assert skill.is_valid_name()
