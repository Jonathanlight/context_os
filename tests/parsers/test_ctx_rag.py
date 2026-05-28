"""Tests for the [rag] / [[document]] support in the .ctx parser — Phase 6.2."""

from __future__ import annotations

import textwrap

import pytest

from contextos.parsers import (
    ContextOSParseError,
    dump_ctx_string,
    parse_ctx_string,
)

_MINIMAL_RAG_CTX = textwrap.dedent(
    """\
    project = "PolicyCorpus"
    artifacts = ["rag"]

    [rag]
    chunking_strategy = "semantic"
    chunk_target_tokens = 500
    chunk_overlap_tokens = 50
    chunk_min_tokens = 100
    chunk_max_tokens = 1500
    retrieval_top_k = 10
    reranking_top_k = 3

    [[document]]
    source = "docs/policies/**/*.md"
    """
)

_FULL_RAG_CTX = textwrap.dedent(
    """\
    project = "FullCorpus"
    artifacts = ["rag"]

    [rag]
    chunking_strategy = "header_aware"
    chunk_target_tokens = 800
    chunk_overlap_tokens = 100
    chunk_min_tokens = 200
    chunk_max_tokens = 2000
    embedding_model = "voyage-3"
    embedding_dimensions = 1024
    vector_store = "qdrant"
    reranker = "cohere-rerank-3"
    retrieval_top_k = 20
    reranking_top_k = 5
    freshness_policy = "30d"
    language_default = "fr"

    [[document]]
    source = "docs/policies/**/*.md"
    tags = ["policy", "internal"]
    freshness_required = "30d"
    chunking_override = "header_aware"
    required_anchors = ["##"]
    max_size_kb = 200
    language = "fr"

    [[document]]
    source = "docs/api/*.md"
    tags = ["api", "public"]
    required_anchors = ["#", "##", "###"]
    """
)


class TestMinimalRagParse:
    def test_returns_skill_doc(self) -> None:
        doc = parse_ctx_string(_MINIMAL_RAG_CTX)
        assert doc.type == "rag"
        assert doc.rag is not None
        assert doc.rag.config.chunking_strategy == "semantic"
        assert doc.rag.config.chunk_target_tokens == 500
        assert len(doc.rag.documents) == 1
        assert doc.rag.documents[0].source == "docs/policies/**/*.md"

    def test_project_is_preserved(self) -> None:
        doc = parse_ctx_string(_MINIMAL_RAG_CTX)
        assert doc.project == "PolicyCorpus"


class TestFullRagParse:
    def test_every_config_field_populated(self) -> None:
        doc = parse_ctx_string(_FULL_RAG_CTX)
        assert doc.rag is not None
        cfg = doc.rag.config
        assert cfg.chunking_strategy == "header_aware"
        assert cfg.embedding_model == "voyage-3"
        assert cfg.embedding_dimensions == 1024
        assert cfg.vector_store == "qdrant"
        assert cfg.reranker == "cohere-rerank-3"
        assert cfg.retrieval_top_k == 20
        assert cfg.reranking_top_k == 5
        assert cfg.freshness_policy == "30d"
        assert cfg.language_default == "fr"

    def test_documents_populated(self) -> None:
        doc = parse_ctx_string(_FULL_RAG_CTX)
        assert doc.rag is not None
        assert len(doc.rag.documents) == 2
        first, second = doc.rag.documents
        assert first.source == "docs/policies/**/*.md"
        assert first.tags == ["policy", "internal"]
        assert first.required_anchors == ["##"]
        assert first.chunking_override == "header_aware"
        assert first.max_size_kb == 200
        assert first.language == "fr"
        assert second.source == "docs/api/*.md"
        assert second.required_anchors == ["#", "##", "###"]


class TestErrors:
    def test_missing_rag_table(self) -> None:
        ctx = textwrap.dedent(
            """\
            project = "X"
            artifacts = ["rag"]
            """
        )
        with pytest.raises(ContextOSParseError, match=r"requires a \[rag\] table"):
            parse_ctx_string(ctx)

    def test_no_document_blocks(self) -> None:
        ctx = textwrap.dedent(
            """\
            project = "X"
            artifacts = ["rag"]

            [rag]
            chunking_strategy = "semantic"
            chunk_target_tokens = 500
            chunk_overlap_tokens = 50
            chunk_min_tokens = 100
            chunk_max_tokens = 1500
            """
        )
        with pytest.raises(ContextOSParseError, match=r"no \[\[document\]\] entries"):
            parse_ctx_string(ctx)

    def test_chunk_ordering_violation(self) -> None:
        # chunk_min > chunk_target → AST validator rejects
        ctx = textwrap.dedent(
            """\
            project = "X"
            artifacts = ["rag"]

            [rag]
            chunking_strategy = "semantic"
            chunk_target_tokens = 200
            chunk_overlap_tokens = 50
            chunk_min_tokens = 500
            chunk_max_tokens = 1000

            [[document]]
            source = "x.md"
            """
        )
        with pytest.raises(ContextOSParseError, match=r"failed validation"):
            parse_ctx_string(ctx)

    def test_unknown_chunking_strategy(self) -> None:
        ctx = textwrap.dedent(
            """\
            project = "X"
            artifacts = ["rag"]

            [rag]
            chunking_strategy = "recursive"
            chunk_target_tokens = 500
            chunk_min_tokens = 100
            chunk_max_tokens = 1500
            chunk_overlap_tokens = 50

            [[document]]
            source = "x.md"
            """
        )
        with pytest.raises(ContextOSParseError, match=r"failed validation"):
            parse_ctx_string(ctx)

    def test_unknown_document_field_rejected(self) -> None:
        ctx = textwrap.dedent(
            """\
            project = "X"
            artifacts = ["rag"]

            [rag]
            chunking_strategy = "semantic"
            chunk_target_tokens = 500
            chunk_min_tokens = 100
            chunk_max_tokens = 1500
            chunk_overlap_tokens = 50

            [[document]]
            source = "x.md"
            mystery_field = "nope"
            """
        )
        with pytest.raises(ContextOSParseError, match=r"failed validation"):
            parse_ctx_string(ctx)


class TestRoundTrip:
    def test_minimal_round_trip(self) -> None:
        doc_first = parse_ctx_string(_MINIMAL_RAG_CTX)
        dumped = dump_ctx_string(doc_first)
        doc_second = parse_ctx_string(dumped)
        assert doc_first == doc_second

    def test_full_round_trip(self) -> None:
        doc_first = parse_ctx_string(_FULL_RAG_CTX)
        dumped = dump_ctx_string(doc_first)
        doc_second = parse_ctx_string(dumped)
        assert doc_first == doc_second

    def test_dump_starts_with_artifacts_rag(self) -> None:
        doc = parse_ctx_string(_MINIMAL_RAG_CTX)
        dumped = dump_ctx_string(doc)
        assert 'artifacts = ["rag"]' in dumped
        assert "[rag]" in dumped
        assert "[[document]]" in dumped
