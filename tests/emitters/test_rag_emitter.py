"""Tests for the RAG manifest emitter — Phase 6.3."""

from __future__ import annotations

import json
import textwrap

import pytest

from contextos.ast.agent import AgentDocument
from contextos.ast.document import Document
from contextos.ast.rag import DocumentEntry, RagConfig, RagDocument
from contextos.emitters import emit_rag_manifest
from contextos.emitters.rag import MANIFEST_VERSION
from contextos.parsers import parse_ctx_string


def _wrap(rag: RagDocument, project: str = "MyCorpus") -> Document:
    return Document(project=project, type="rag", rag=rag)


def _config(**overrides: object) -> RagConfig:
    return RagConfig.model_validate(overrides)


def _rag(**overrides: object) -> RagDocument:
    payload: dict[str, object] = {
        "config": _config(),
        "documents": [DocumentEntry(source="docs/*.md")],
    }
    payload.update(overrides)
    return RagDocument.model_validate(payload)


class TestRequiresRagFlavor:
    def test_rejects_agent_document(self) -> None:
        with pytest.raises(ValueError, match=r"Document\.type='rag'"):
            emit_rag_manifest(Document(project="X", agent=AgentDocument()))

    def test_rejects_rag_with_none_payload(self) -> None:
        doc = Document.model_construct(project="X", type="rag", rag=None)
        with pytest.raises(ValueError, match=r"Document\.type='rag'"):
            emit_rag_manifest(doc)


class TestManifestShape:
    def test_top_level_keys_in_canonical_order(self) -> None:
        manifest = json.loads(emit_rag_manifest(_wrap(_rag())))
        assert list(manifest.keys()) == ["version", "project", "rag", "documents"]

    def test_version_pinned(self) -> None:
        manifest = json.loads(emit_rag_manifest(_wrap(_rag())))
        assert manifest["version"] == MANIFEST_VERSION

    def test_project_preserved(self) -> None:
        manifest = json.loads(emit_rag_manifest(_wrap(_rag(), project="MyCorpus")))
        assert manifest["project"] == "MyCorpus"


class TestConfigFieldOrder:
    def test_canonical_order_of_emitted_fields(self) -> None:
        rag = _rag(
            config=_config(
                chunking_strategy="header_aware",
                embedding_model="voyage-3",
                vector_store="qdrant",
                freshness_policy="30d",
                language_default="fr",
            )
        )
        manifest = json.loads(emit_rag_manifest(_wrap(rag)))
        keys = list(manifest["rag"].keys())
        expected_prefix = [
            "chunking_strategy",
            "chunk_target_tokens",
            "chunk_overlap_tokens",
            "chunk_min_tokens",
            "chunk_max_tokens",
            "embedding_model",
            "vector_store",
            "retrieval_top_k",
            "reranking_top_k",
            "freshness_policy",
            "language_default",
        ]
        assert keys == expected_prefix

    def test_optionals_omitted_when_none(self) -> None:
        manifest = json.loads(emit_rag_manifest(_wrap(_rag())))
        for absent_key in (
            "embedding_model",
            "embedding_dimensions",
            "vector_store",
            "reranker",
            "freshness_policy",
            "language_default",
        ):
            assert absent_key not in manifest["rag"]


class TestDocumentsArray:
    def test_documents_preserve_input_order(self) -> None:
        rag = _rag(
            documents=[
                DocumentEntry(source="b.md"),
                DocumentEntry(source="a.md"),
                DocumentEntry(source="c.md"),
            ]
        )
        manifest = json.loads(emit_rag_manifest(_wrap(rag)))
        sources = [d["source"] for d in manifest["documents"]]
        assert sources == ["b.md", "a.md", "c.md"]

    def test_document_field_canonical_order(self) -> None:
        rag = _rag(
            documents=[
                DocumentEntry(
                    source="x.md",
                    tags=["t1"],
                    freshness_required="7d",
                    chunking_override="fixed",
                    required_anchors=["##"],
                    max_size_kb=10,
                    language="en",
                )
            ]
        )
        manifest = json.loads(emit_rag_manifest(_wrap(rag)))
        assert list(manifest["documents"][0].keys()) == [
            "source",
            "tags",
            "freshness_required",
            "chunking_override",
            "required_anchors",
            "max_size_kb",
            "language",
        ]

    def test_document_empty_optionals_omitted(self) -> None:
        rag = _rag(documents=[DocumentEntry(source="x.md")])
        manifest = json.loads(emit_rag_manifest(_wrap(rag)))
        doc_dict = manifest["documents"][0]
        assert set(doc_dict.keys()) == {"source"}


class TestByteStability:
    def test_same_doc_emits_same_bytes(self) -> None:
        doc = _wrap(_rag())
        assert emit_rag_manifest(doc) == emit_rag_manifest(doc)

    def test_indent_none_yields_compact(self) -> None:
        out = emit_rag_manifest(_wrap(_rag()), indent=None)
        assert "\n  " not in out  # no internal indent
        assert out.endswith("\n")


class TestSnapshotMinimal:
    def test_minimal_manifest_snapshot(self) -> None:
        rag = RagDocument(
            config=RagConfig(),
            documents=[DocumentEntry(source="docs/*.md")],
        )
        out = emit_rag_manifest(_wrap(rag, project="Demo"))
        expected = textwrap.dedent(
            """\
            {
              "version": "1.0",
              "project": "Demo",
              "rag": {
                "chunking_strategy": "semantic",
                "chunk_target_tokens": 500,
                "chunk_overlap_tokens": 50,
                "chunk_min_tokens": 100,
                "chunk_max_tokens": 1500,
                "retrieval_top_k": 10,
                "reranking_top_k": 3
              },
              "documents": [
                {
                  "source": "docs/*.md"
                }
              ]
            }
            """
        )
        assert out == expected


class TestEndToEndFromCtx:
    """parse a .ctx → emit manifest. Verifies the full pipeline."""

    def test_minimal_ctx_to_manifest(self) -> None:
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

            [[document]]
            source = "docs/**/*.md"
            tags = ["docs"]
            """
        )
        doc = parse_ctx_string(ctx)
        manifest = json.loads(emit_rag_manifest(doc))
        assert manifest["project"] == "X"
        assert manifest["rag"]["chunking_strategy"] == "semantic"
        assert manifest["documents"][0]["source"] == "docs/**/*.md"
        assert manifest["documents"][0]["tags"] == ["docs"]
