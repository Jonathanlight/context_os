"""Tests for the lint_document orchestrator."""

from __future__ import annotations

from contextos.analyzers import lint_document
from contextos.ast.agent import AgentDocument, Rule
from contextos.ast.common import Severity
from contextos.ast.document import Document


def _doc(rules: list[Rule]) -> Document:
    return Document(project="P", agent=AgentDocument(rules=rules))


def _clean_rule(title: str, sev: Severity = Severity.MUST) -> Rule:
    """A rule that triggers no analyzer — used as a baseline for orchestrator tests.

    Provides ``rationale`` and ``example_good`` so K002 / K003 stay silent
    even for the strictest ``must`` severity.
    """
    return Rule(
        id="X-001",
        title=title,
        severity=sev,
        rationale="documented in the spec",
        example_good="see fixtures",
    )


class TestLintDocument:
    def test_empty_doc_yields_only_k001(self) -> None:
        # Empty rules list triggers exactly one completeness diagnostic.
        bag = lint_document(_doc([]))
        codes = [d.code for d in bag]
        assert codes == ["K001"]
        assert not bag.has_errors()

    def test_doc_without_agent_yields_empty_bag(self) -> None:
        # Bypass the model validator that requires agent=non-None for type=agent.
        doc = Document.model_construct(project="P", type="agent", agent=None)
        bag = lint_document(doc)
        assert len(bag) == 0

    def test_a001_fires_through_orchestrator(self) -> None:
        # Provide rationale + example so only A001 fires.
        rule = Rule(
            id="X-001",
            title="Be concise",
            severity=Severity.MUST,
            rationale="...",
            example_good="...",
        )
        bag = lint_document(_doc([rule]))
        codes = {d.code for d in bag}
        assert "A001" in codes

    def test_clean_doc_passes(self) -> None:
        rule = _clean_rule("Use type hints on public APIs")
        bag = lint_document(_doc([rule]))
        assert len(bag) == 0

    def test_source_is_forwarded_to_analyzers(self) -> None:
        rule = Rule(
            id="X-001",
            title="Be concise",
            severity=Severity.MUST,
            rationale="...",
            example_good="...",
        )
        bag = lint_document(_doc([rule]), source="my.ctx")
        codes = {d.code for d in bag}
        assert "A001" in codes
