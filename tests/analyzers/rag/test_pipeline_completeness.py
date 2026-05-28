"""Tests for the RAG pipeline-completeness analyzers — R003/R004/R005."""

from __future__ import annotations

from contextos.analyzers.rag.pipeline_completeness import (
    R003_CODE,
    R004_CODE,
    R005_CODE,
    check,
)
from contextos.ast.rag import DocumentEntry, RagConfig, RagDocument


def _rag(
    *,
    config_overrides: dict[str, object] | None = None,
    documents: list[DocumentEntry] | None = None,
) -> RagDocument:
    cfg = RagConfig.model_validate(config_overrides or {})
    docs = documents if documents is not None else [DocumentEntry(source="docs/*.md")]
    return RagDocument(config=cfg, documents=docs)


def _codes(rag: RagDocument) -> list[str]:
    return [d.code for d in check(rag)]


class TestR003Freshness:
    def test_fires_when_missing(self) -> None:
        rag = _rag()
        assert R003_CODE in _codes(rag)

    def test_silent_when_set(self) -> None:
        rag = _rag(config_overrides={"freshness_policy": "30d"})
        assert R003_CODE not in _codes(rag)


class TestR004EmbeddingModel:
    def test_fires_when_missing(self) -> None:
        rag = _rag()
        assert R004_CODE in _codes(rag)

    def test_silent_when_set(self) -> None:
        rag = _rag(config_overrides={"embedding_model": "voyage-3"})
        assert R004_CODE not in _codes(rag)

    def test_whitespace_only_treated_as_missing(self) -> None:
        rag = _rag(config_overrides={"embedding_model": "   "})
        assert R004_CODE in _codes(rag)


class TestR005HeaderAnchorMatch:
    def test_silent_when_no_header_aware_override(self) -> None:
        rag = _rag(documents=[DocumentEntry(source="x.md")])
        assert R005_CODE not in _codes(rag)

    def test_silent_when_override_has_anchors(self) -> None:
        rag = _rag(
            documents=[
                DocumentEntry(
                    source="x.md",
                    chunking_override="header_aware",
                    required_anchors=["##"],
                )
            ]
        )
        assert R005_CODE not in _codes(rag)

    def test_fires_when_override_lacks_anchors(self) -> None:
        rag = _rag(
            documents=[
                DocumentEntry(source="x.md", chunking_override="header_aware"),
            ]
        )
        diags = [d for d in check(rag) if d.code == R005_CODE]
        assert len(diags) == 1
        assert "x.md" in diags[0].message

    def test_fires_once_per_offending_document(self) -> None:
        rag = _rag(
            documents=[
                DocumentEntry(source="a.md", chunking_override="header_aware"),
                DocumentEntry(source="b.md"),
                DocumentEntry(source="c.md", chunking_override="header_aware"),
            ]
        )
        diags = [d for d in check(rag) if d.code == R005_CODE]
        assert len(diags) == 2
        sources = sorted(d.message for d in diags)
        assert "a.md" in sources[0]
        assert "c.md" in sources[1]
