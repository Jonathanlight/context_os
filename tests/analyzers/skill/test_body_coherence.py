"""Tests for the skill body-coherence analyzers — S004/S005/S006."""

from __future__ import annotations

from contextos.analyzers.skill.body_coherence import (
    S004_CODE,
    S005_CODE,
    S006_CODE,
    check,
)
from contextos.ast.skill import SkillDocument


def _skill(**overrides: object) -> SkillDocument:
    payload: dict[str, object] = {
        "name": "pdf-extract",
        "title": "PDF invoice extraction",
        "description": "Extract PDFs. Triggers when the user uploads an invoice.",
        "body": "# PDF invoice extraction\n\nBody content.\n",
    }
    payload.update(overrides)
    return SkillDocument.model_validate(payload)


def _codes(skill: SkillDocument) -> list[str]:
    return [d.code for d in check(skill)]


class TestS004ExampleInvocation:
    def test_fires_when_missing(self) -> None:
        skill = _skill()
        assert S004_CODE in _codes(skill)

    def test_silent_when_present(self) -> None:
        skill = _skill(example_invocation="Extract the totals from this invoice.pdf")
        assert S004_CODE not in _codes(skill)

    def test_whitespace_only_treated_as_missing(self) -> None:
        skill = _skill(example_invocation="    ")
        assert S004_CODE in _codes(skill)


class TestS005BodyH1:
    def test_silent_when_h1_matches_title(self) -> None:
        skill = _skill(
            title="PDF invoice extraction",
            body="# PDF invoice extraction\n\nDocs.\n",
        )
        assert S005_CODE not in _codes(skill)

    def test_fires_when_body_has_no_h1(self) -> None:
        skill = _skill(body="No heading at all, just a paragraph.\n")
        diags = [d for d in check(skill) if d.code == S005_CODE]
        assert len(diags) == 1
        assert "has no H1" in diags[0].message

    def test_fires_when_h1_mismatch(self) -> None:
        skill = _skill(
            title="Real title",
            body="# Wrong heading\n\nDocs.\n",
        )
        diags = [d for d in check(skill) if d.code == S005_CODE]
        assert len(diags) == 1
        assert "does not match" in diags[0].message

    def test_silent_when_body_is_empty(self) -> None:
        skill = _skill(body="")
        assert S005_CODE not in _codes(skill)

    def test_match_tolerates_inline_formatting(self) -> None:
        skill = _skill(
            title="PDF extraction",
            body="# **PDF** _extraction_\n\nDocs.\n",
        )
        assert S005_CODE not in _codes(skill)

    def test_match_tolerates_case(self) -> None:
        skill = _skill(
            title="PDF Extraction",
            body="# pdf extraction\n\nDocs.\n",
        )
        assert S005_CODE not in _codes(skill)


class TestS006KeywordOverlap:
    def test_silent_with_no_keywords(self) -> None:
        skill = _skill(trigger_keywords=[])
        assert S006_CODE not in _codes(skill)

    def test_fires_when_every_keyword_appears_verbatim(self) -> None:
        skill = _skill(
            description="Extract PDFs. Triggers when the user uploads an invoice PDF.",
            trigger_keywords=["pdf", "invoice"],
        )
        assert S006_CODE in _codes(skill)

    def test_silent_when_one_keyword_is_new(self) -> None:
        skill = _skill(
            description="Extract PDFs. Triggers when the user uploads an invoice PDF.",
            trigger_keywords=["pdf", "invoice", "facture"],  # facture not in desc
        )
        assert S006_CODE not in _codes(skill)

    def test_case_insensitive(self) -> None:
        skill = _skill(
            description="Extract PDFs. Triggers when the user uploads an INVOICE PDF.",
            trigger_keywords=["pdf", "invoice"],
        )
        assert S006_CODE in _codes(skill)
