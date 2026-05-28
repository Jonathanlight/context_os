"""End-to-end tests for lint_document on rag flavors."""

from __future__ import annotations

from contextos.analyzers import lint_document
from contextos.ast.agent import AgentDocument
from contextos.ast.document import Document
from contextos.ast.rag import DocumentEntry, RagConfig, RagDocument


def _clean_rag_doc() -> Document:
    cfg = RagConfig(
        chunking_strategy="semantic",
        chunk_target_tokens=500,
        chunk_overlap_tokens=50,
        chunk_min_tokens=100,
        chunk_max_tokens=1500,
        embedding_model="voyage-3",
        freshness_policy="30d",
    )
    rag = RagDocument(config=cfg, documents=[DocumentEntry(source="docs/**/*.md")])
    return Document(project="MyCorpus", type="rag", rag=rag)


class TestRagDispatch:
    def test_clean_rag_produces_no_diagnostics(self) -> None:
        bag = lint_document(_clean_rag_doc())
        assert list(bag) == []

    def test_problematic_rag_fires_multiple_rules(self) -> None:
        cfg = RagConfig(
            chunking_strategy="semantic",
            chunk_target_tokens=500,
            chunk_overlap_tokens=400,  # 80% → R001
            chunk_min_tokens=100,
            chunk_max_tokens=550,  # 10% headroom → R002
        )
        rag = RagDocument(
            config=cfg,
            documents=[
                DocumentEntry(
                    source="big.md",
                    max_size_kb=1000,
                    chunking_override="header_aware",
                ),
            ],
        )
        doc = Document(project="X", type="rag", rag=rag)
        codes = sorted({d.code for d in lint_document(doc)})
        assert "R001" in codes
        assert "R002" in codes
        assert "R003" in codes  # missing freshness
        assert "R004" in codes  # missing embedding
        assert "R005" in codes  # header_aware without anchors


class TestDispatchIsolation:
    def test_rag_doc_has_no_agent_diagnostics(self) -> None:
        bag = lint_document(_clean_rag_doc())
        for diag in bag:
            assert not diag.code.startswith(("A", "C", "F", "K", "P", "S", "X"))

    def test_agent_doc_has_no_rag_diagnostics(self) -> None:
        doc = Document(project="X", agent=AgentDocument())
        bag = lint_document(doc)
        for diag in bag:
            assert not diag.code.startswith("R")
