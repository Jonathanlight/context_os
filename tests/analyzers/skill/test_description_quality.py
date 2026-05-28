"""Tests for the skill description-quality analyzers — S001/S002/S003."""

from __future__ import annotations

from contextos.analyzers.skill.description_quality import (
    S001_CODE,
    S002_CODE,
    S002_MIN_CHARS,
    S003_CODE,
    S003_SOFT_CAP_CHARS,
    check,
)
from contextos.ast.skill import DESCRIPTION_MAX_CHARS, SkillDocument


def _skill(**overrides: object) -> SkillDocument:
    payload: dict[str, object] = {
        "name": "pdf-extract",
        "title": "PDF extract",
        "description": (
            "Extract structured data from PDF invoices. Triggers when the "
            "user asks to parse or process an invoice PDF."
        ),
    }
    payload.update(overrides)
    return SkillDocument.model_validate(payload)


def _codes(skill: SkillDocument) -> list[str]:
    return [d.code for d in check(skill)]


class TestS001MissingTrigger:
    def test_fires_when_no_trigger_phrasing(self) -> None:
        skill = _skill(
            description=(
                "Extracts structured data from PDF documents and returns "
                "JSON output for downstream pipelines and aggregation jobs."
            ),
        )
        assert S001_CODE in _codes(skill)

    def test_silent_with_triggers_when(self) -> None:
        skill = _skill(
            description="A description that fires when the user mentions PDFs in their prompt.",
        )
        assert S001_CODE not in _codes(skill)

    def test_silent_with_asks_to(self) -> None:
        skill = _skill(
            description="Activates when the user asks to extract PDF tables from a document.",
        )
        assert S001_CODE not in _codes(skill)

    def test_silent_with_use_when(self) -> None:
        skill = _skill(
            description="Extracts PDF tables. Use when the user uploads a PDF with tabular data.",
        )
        assert S001_CODE not in _codes(skill)

    def test_case_insensitive(self) -> None:
        skill = _skill(
            description="Extracts tables. TRIGGERS WHEN the user uploads a PDF.",
        )
        assert S001_CODE not in _codes(skill)


class TestS002TooShort:
    def test_fires_below_floor(self) -> None:
        skill = _skill(description="Use when extracting PDFs.")
        assert S002_CODE in _codes(skill)

    def test_silent_at_or_above_floor(self) -> None:
        text = "Use when " + "x" * (S002_MIN_CHARS - len("Use when "))
        skill = _skill(description=text)
        assert len(text) >= S002_MIN_CHARS
        assert S002_CODE not in _codes(skill)

    def test_whitespace_does_not_pad(self) -> None:
        # Spaces collapse before length is measured.
        skill = _skill(description="Use when    short.   ")
        assert S002_CODE in _codes(skill)


class TestS003TooLong:
    def test_fires_above_soft_cap(self) -> None:
        prefix = "Use when the user uploads a PDF. "
        padding = "x" * (S003_SOFT_CAP_CHARS + 50 - len(prefix))
        text = prefix + padding
        assert len(text) > S003_SOFT_CAP_CHARS
        assert len(text) <= DESCRIPTION_MAX_CHARS
        skill = _skill(description=text)
        assert S003_CODE in _codes(skill)

    def test_silent_at_soft_cap(self) -> None:
        prefix = "Use when X. "
        text = prefix + "x" * (S003_SOFT_CAP_CHARS - len(prefix))
        assert len(text) == S003_SOFT_CAP_CHARS
        skill = _skill(description=text)
        assert S003_CODE not in _codes(skill)


class TestDiagnosticShape:
    def test_s001_diagnostic_contains_skill_name(self) -> None:
        skill = _skill(
            description=(
                "Extracts structured data from PDF documents and returns "
                "JSON output for downstream pipelines and aggregation jobs."
            ),
        )
        diags = list(check(skill))
        s001 = next(d for d in diags if d.code == S001_CODE)
        assert "pdf-extract" in s001.message
        assert s001.doc_url is not None
        assert s001.doc_url.endswith("/S001")
        assert s001.suggestion is not None

    def test_s002_reports_actual_length(self) -> None:
        skill = _skill(description="Use when X.")
        diags = list(check(skill))
        s002 = next(d for d in diags if d.code == S002_CODE)
        assert "11 chars" in s002.message
