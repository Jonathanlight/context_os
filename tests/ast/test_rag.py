"""Tests for the RagDocument AST node — Phase 6.1.

The Pydantic model is the only public surface this PR exposes; the
parser, manifest emitter, and analyzers ship in 6.2 / 6.3 / 6.4. So the
tests here focus on the **invariants** the model enforces on its own:
chunk-size ordering, top_k ordering, freshness pattern, closed-set
chunking strategy, and the Document family-slot validator.
"""

from __future__ import annotations

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from contextos.ast.agent import AgentDocument
from contextos.ast.document import Document
from contextos.ast.rag import (
    CHUNK_MAX_TOKENS_CEILING,
    CHUNK_MIN_TOKENS_FLOOR,
    DocumentEntry,
    RagConfig,
    RagDocument,
    is_valid_freshness,
)
from contextos.ast.skill import SkillDocument


def _config(**overrides: object) -> RagConfig:
    return RagConfig.model_validate(overrides)


def _rag(**overrides: object) -> RagDocument:
    payload: dict[str, object] = {"config": _config()}
    payload.update(overrides)
    return RagDocument.model_validate(payload)


def _minimal_skill() -> SkillDocument:
    return SkillDocument(
        name="x",
        title="X",
        description="Triggers when the user mentions x for testing isolation.",
    )


class TestRagConfigDefaults:
    def test_defaults_validate(self) -> None:
        cfg = _config()
        assert cfg.chunking_strategy == "semantic"
        assert cfg.chunk_target_tokens == 500
        assert cfg.chunk_overlap_tokens == 50
        assert cfg.chunk_min_tokens == 100
        assert cfg.chunk_max_tokens == 1500
        assert cfg.retrieval_top_k == 10
        assert cfg.reranking_top_k == 3

    def test_optional_fields_default_to_none(self) -> None:
        cfg = _config()
        assert cfg.embedding_model is None
        assert cfg.embedding_dimensions is None
        assert cfg.vector_store is None
        assert cfg.reranker is None
        assert cfg.freshness_policy is None
        assert cfg.language_default is None


class TestChunkingStrategyClosedSet:
    @pytest.mark.parametrize("strategy", ["fixed", "semantic", "header_aware"])
    def test_allowed_values(self, strategy: str) -> None:
        cfg = _config(chunking_strategy=strategy)
        assert cfg.chunking_strategy == strategy

    @pytest.mark.parametrize("strategy", ["recursive", "SEMANTIC", "", "auto"])
    def test_rejects_unknown(self, strategy: str) -> None:
        with pytest.raises(ValidationError):
            _config(chunking_strategy=strategy)


class TestChunkSizeBounds:
    def test_rejects_below_floor(self) -> None:
        with pytest.raises(ValidationError):
            _config(chunk_target_tokens=CHUNK_MIN_TOKENS_FLOOR - 1)

    def test_rejects_above_ceiling(self) -> None:
        with pytest.raises(ValidationError):
            _config(chunk_target_tokens=CHUNK_MAX_TOKENS_CEILING + 1)

    def test_accepts_at_floor(self) -> None:
        cfg = _config(
            chunk_target_tokens=CHUNK_MIN_TOKENS_FLOOR,
            chunk_min_tokens=CHUNK_MIN_TOKENS_FLOOR,
            chunk_max_tokens=CHUNK_MIN_TOKENS_FLOOR + 100,
        )
        assert cfg.chunk_target_tokens == CHUNK_MIN_TOKENS_FLOOR


class TestChunkSizeOrdering:
    def test_rejects_min_above_target(self) -> None:
        with pytest.raises(ValidationError, match=r"chunk_min_tokens"):
            _config(chunk_min_tokens=600, chunk_target_tokens=500)

    def test_rejects_target_above_max(self) -> None:
        with pytest.raises(ValidationError, match=r"chunk_target_tokens"):
            _config(chunk_target_tokens=2000, chunk_max_tokens=1500)

    def test_accepts_equal_min_target_max(self) -> None:
        cfg = _config(
            chunk_min_tokens=500,
            chunk_target_tokens=500,
            chunk_max_tokens=500,
        )
        assert cfg.chunk_target_tokens == 500


class TestTopKOrdering:
    def test_rejects_rerank_above_retrieval(self) -> None:
        with pytest.raises(ValidationError, match=r"reranking_top_k"):
            _config(retrieval_top_k=5, reranking_top_k=10)

    def test_accepts_rerank_equal_retrieval(self) -> None:
        cfg = _config(retrieval_top_k=10, reranking_top_k=10)
        assert cfg.reranking_top_k == 10

    def test_rejects_top_k_above_ceiling(self) -> None:
        with pytest.raises(ValidationError):
            _config(retrieval_top_k=101)


class TestFreshnessPolicy:
    @pytest.mark.parametrize("value", ["7d", "30d", "12w", "6m", "1y", "365d"])
    def test_valid_formats(self, value: str) -> None:
        cfg = _config(freshness_policy=value)
        assert cfg.freshness_policy == value
        assert is_valid_freshness(value)

    @pytest.mark.parametrize(
        "value",
        ["30days", "P30D", "30", "d30", "30 d", "thirty days", "1.5d"],
    )
    def test_invalid_formats(self, value: str) -> None:
        with pytest.raises(ValidationError):
            _config(freshness_policy=value)
        assert not is_valid_freshness(value)


class TestExtraForbidden:
    def test_unknown_config_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RagConfig.model_validate({"unknown_field": "value"})

    def test_unknown_document_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            DocumentEntry.model_validate({"source": "x.md", "unknown": "v"})

    def test_unknown_rag_field_rejected(self) -> None:
        with pytest.raises(ValidationError):
            RagDocument.model_validate({"config": {}, "extra": []})


class TestDocumentEntry:
    def test_minimal_entry(self) -> None:
        entry = DocumentEntry(source="docs/*.md")
        assert entry.source == "docs/*.md"
        assert entry.tags == []
        assert entry.required_anchors == []
        assert entry.freshness_required is None
        assert entry.chunking_override is None

    def test_source_cannot_be_empty(self) -> None:
        with pytest.raises(ValidationError):
            DocumentEntry(source="")

    def test_chunking_override_inherits_closed_set(self) -> None:
        with pytest.raises(ValidationError):
            DocumentEntry.model_validate({"source": "x.md", "chunking_override": "bogus"})

    def test_max_size_kb_bounds(self) -> None:
        with pytest.raises(ValidationError):
            DocumentEntry.model_validate({"source": "x.md", "max_size_kb": 0})


class TestRagDocumentRoundTrip:
    def test_round_trip_via_dict(self) -> None:
        original = _rag(
            config=_config(chunking_strategy="header_aware", retrieval_top_k=20),
            documents=[
                DocumentEntry(source="docs/**/*.md", tags=["policy"]),
                DocumentEntry(source="api/*.md", required_anchors=["##"]),
            ],
        )
        restored = RagDocument.model_validate(original.model_dump())
        assert restored == original

    def test_round_trip_via_json(self) -> None:
        original = _rag()
        restored = RagDocument.model_validate_json(original.model_dump_json())
        assert restored == original


class TestDocumentRagFlavor:
    def test_minimal_rag_document(self) -> None:
        doc = Document(project="MyCorpus", type="rag", rag=_rag())
        assert doc.type == "rag"
        assert doc.rag is not None
        assert doc.agent is None
        assert doc.skill is None

    def test_rag_type_requires_rag_slot(self) -> None:
        with pytest.raises(ValidationError, match=r"requires Document\.rag"):
            Document(project="X", type="rag", rag=None)

    def test_rag_type_rejects_stray_agent_payload(self) -> None:
        with pytest.raises(ValidationError, match=r"must not carry an agent payload"):
            Document(project="X", type="rag", rag=_rag(), agent=AgentDocument())

    def test_rag_type_rejects_stray_skill_payload(self) -> None:
        with pytest.raises(ValidationError, match=r"must not carry a skill payload"):
            Document(project="X", type="rag", rag=_rag(), skill=_minimal_skill())

    def test_agent_type_rejects_stray_rag_payload(self) -> None:
        with pytest.raises(ValidationError, match=r"must not carry a rag payload"):
            Document(project="X", agent=AgentDocument(), rag=_rag())


class TestHypothesisChunkOrdering:
    @given(
        small=st.integers(min_value=50, max_value=1500),
        delta1=st.integers(min_value=0, max_value=1500),
        delta2=st.integers(min_value=0, max_value=1000),
    )
    @settings(max_examples=200, deadline=None)
    def test_valid_orderings_always_accepted(
        self,
        small: int,
        delta1: int,
        delta2: int,
    ) -> None:
        target = small + delta1
        big = target + delta2
        if big > CHUNK_MAX_TOKENS_CEILING:
            return
        cfg = RagConfig(
            chunk_min_tokens=small,
            chunk_target_tokens=target,
            chunk_max_tokens=big,
        )
        assert cfg.chunk_min_tokens <= cfg.chunk_target_tokens <= cfg.chunk_max_tokens
