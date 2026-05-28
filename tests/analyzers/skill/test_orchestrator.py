"""End-to-end tests for ``lint_document`` on skill flavors."""

from __future__ import annotations

from contextos.analyzers import lint_document
from contextos.ast.agent import AgentDocument
from contextos.ast.document import Document
from contextos.ast.skill import SkillDocument


def _clean_skill_doc() -> Document:
    skill = SkillDocument(
        name="pdf-extract",
        title="PDF invoice extraction",
        description=(
            "Extracts structured data from PDF invoices. Triggers when the "
            "user asks to parse, extract, or process an invoice PDF file."
        ),
        example_invocation="Extract the totals from this invoice.pdf",
        body="# PDF invoice extraction\n\nDocs.\n",
    )
    return Document(project=skill.name, type="skill", skill=skill)


class TestSkillDispatch:
    def test_clean_skill_produces_no_diagnostics(self) -> None:
        bag = lint_document(_clean_skill_doc())
        assert list(bag) == []

    def test_clean_skill_has_no_errors(self) -> None:
        bag = lint_document(_clean_skill_doc())
        assert not bag.has_errors()

    def test_problematic_skill_fires_multiple_rules(self) -> None:
        skill = SkillDocument(
            name="bad-skill",
            title="Bad skill",
            description="Short blurb.",
            body="No heading at all.\n",
        )
        doc = Document(project="X", type="skill", skill=skill)
        codes = sorted({d.code for d in lint_document(doc)})
        # S001 (no trigger), S002 (too short), S004 (no example), S005 (no h1)
        assert "S001" in codes
        assert "S002" in codes
        assert "S004" in codes
        assert "S005" in codes


class TestDispatchIsolation:
    """Agent analyzers must not fire on skill docs and vice versa."""

    def test_skill_doc_does_not_invoke_agent_analyzers(self) -> None:
        bag = lint_document(_clean_skill_doc())
        for diag in bag:
            assert not diag.code.startswith(("A", "C", "F", "K", "P", "X"))

    def test_agent_doc_does_not_invoke_skill_analyzers(self) -> None:
        doc = Document(project="X", agent=AgentDocument())
        bag = lint_document(doc)
        for diag in bag:
            assert not diag.code.startswith("S")
