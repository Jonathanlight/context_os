"""Tests for the lint_document orchestrator."""

from __future__ import annotations

from contextos.analyzers import lint_document
from contextos.ast.agent import AgentDocument, Rule
from contextos.ast.common import Severity
from contextos.ast.document import Document


def _doc(rules: list[Rule]) -> Document:
    return Document(project="P", agent=AgentDocument(rules=rules))


class TestLintDocument:
    def test_empty_doc_yields_empty_bag(self) -> None:
        bag = lint_document(_doc([]))
        assert len(bag) == 0
        assert not bag.has_errors()

    def test_doc_without_agent_yields_empty_bag(self) -> None:
        # Bypass the model validator that requires agent=non-None for type=agent.
        doc = Document.model_construct(project="P", type="agent", agent=None)
        bag = lint_document(doc)
        assert len(bag) == 0

    def test_a001_fires_through_orchestrator(self) -> None:
        rule = Rule(id="X-001", title="Be concise", severity=Severity.MUST)
        bag = lint_document(_doc([rule]))
        assert len(bag) == 1
        assert next(iter(bag)).code == "A001"

    def test_clean_doc_passes(self) -> None:
        rule = Rule(
            id="X-001",
            title="Use type hints on public APIs",
            severity=Severity.MUST,
        )
        bag = lint_document(_doc([rule]))
        assert len(bag) == 0

    def test_source_is_forwarded_to_analyzers(self) -> None:
        # A001 doesn't use source today, but the kwarg must not raise.
        rule = Rule(id="X-001", title="Be concise", severity=Severity.MUST)
        bag = lint_document(_doc([rule]), source="my.ctx")
        assert len(bag) == 1
