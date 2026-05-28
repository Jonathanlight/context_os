"""Tests for the RAG chunking-sanity analyzers — R001/R002/R006."""

from __future__ import annotations

from contextos.analyzers.rag.chunking_sanity import (
    R001_CODE,
    R002_CODE,
    R006_CODE,
    R006_LARGE_FILE_KB,
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


class TestR001OverlapRatio:
    def test_silent_at_default_ratio(self) -> None:
        rag = _rag()  # overlap 50 / target 500 = 10%
        assert R001_CODE not in _codes(rag)

    def test_silent_at_50_percent(self) -> None:
        rag = _rag(
            config_overrides={
                "chunk_target_tokens": 500,
                "chunk_overlap_tokens": 250,
                "chunk_min_tokens": 100,
                "chunk_max_tokens": 1500,
            }
        )
        assert R001_CODE not in _codes(rag)

    def test_fires_above_50_percent(self) -> None:
        rag = _rag(
            config_overrides={
                "chunk_target_tokens": 500,
                "chunk_overlap_tokens": 300,
                "chunk_min_tokens": 100,
                "chunk_max_tokens": 1500,
            }
        )
        codes = _codes(rag)
        assert R001_CODE in codes


class TestR002Headroom:
    def test_silent_with_default_headroom(self) -> None:
        # target 500, max 1500 → headroom 200% → way above 20% threshold
        rag = _rag()
        assert R002_CODE not in _codes(rag)

    def test_fires_when_max_close_to_target(self) -> None:
        rag = _rag(
            config_overrides={
                "chunk_target_tokens": 500,
                "chunk_max_tokens": 550,
                "chunk_min_tokens": 100,
                "chunk_overlap_tokens": 50,
            }
        )
        assert R002_CODE in _codes(rag)

    def test_silent_at_exactly_20_percent_headroom(self) -> None:
        rag = _rag(
            config_overrides={
                "chunk_target_tokens": 500,
                "chunk_max_tokens": 600,
                "chunk_min_tokens": 100,
                "chunk_overlap_tokens": 50,
            }
        )
        assert R002_CODE not in _codes(rag)


class TestR006LargeFiles:
    def test_silent_when_no_max_size_kb(self) -> None:
        rag = _rag(documents=[DocumentEntry(source="x.md")])
        assert R006_CODE not in _codes(rag)

    def test_silent_when_small_file(self) -> None:
        rag = _rag(documents=[DocumentEntry(source="x.md", max_size_kb=100)])
        assert R006_CODE not in _codes(rag)

    def test_fires_when_large_file_no_override(self) -> None:
        rag = _rag(
            documents=[
                DocumentEntry(source="big.md", max_size_kb=R006_LARGE_FILE_KB + 100),
            ]
        )
        codes = _codes(rag)
        assert R006_CODE in codes

    def test_silent_when_large_file_has_header_aware_override(self) -> None:
        rag = _rag(
            documents=[
                DocumentEntry(
                    source="big.md",
                    max_size_kb=R006_LARGE_FILE_KB + 100,
                    chunking_override="header_aware",
                    required_anchors=["##"],
                ),
            ]
        )
        assert R006_CODE not in _codes(rag)
