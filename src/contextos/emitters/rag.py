"""``rag.manifest.json`` emitter — :class:`Document` → indexer manifest.

Phase 6.3 ships the RAG counterpart of the agent/skill emitters: a
function that takes a :class:`Document` whose ``type='rag'`` and
produces a deterministic JSON manifest. The manifest is the contract
ContextOS exposes to external indexers (Qdrant, Pinecone, custom
implementations): they read the JSON and run the pipeline; ContextOS
doesn't execute anything on its own.

Byte-stability contract: the same :class:`RagDocument` always emits
the same bytes. Lists preserve their `.ctx` order; dict keys are
written in a fixed canonical order (not alphabetic — the order
matches SPEC §1.4 so a hand-read manifest matches what an author
would expect).

Manifest shape:

.. code-block:: json

   {
     "version": "1.0",
     "project": "MyCorpus",
     "rag": {
       "chunking_strategy": "...",
       ...
     },
     "documents": [
       {"source": "...", ...},
       ...
     ]
   }
"""

from __future__ import annotations

import json
from typing import Any

from contextos.ast.document import Document
from contextos.ast.rag import DocumentEntry, RagConfig

MANIFEST_VERSION = "1.0"
"""Manifest schema version.

Bumped when the JSON shape changes incompatibly — e.g. a top-level
key rename, a field-type change, or a contract break with downstream
indexers. Adding optional fields does NOT bump this; consumers that
ignore unknown keys keep working.
"""

_CONFIG_FIELD_ORDER: tuple[str, ...] = (
    "chunking_strategy",
    "chunk_target_tokens",
    "chunk_overlap_tokens",
    "chunk_min_tokens",
    "chunk_max_tokens",
    "embedding_model",
    "embedding_dimensions",
    "vector_store",
    "reranker",
    "retrieval_top_k",
    "reranking_top_k",
    "freshness_policy",
    "language_default",
)

_DOCUMENT_FIELD_ORDER: tuple[str, ...] = (
    "source",
    "tags",
    "freshness_required",
    "chunking_override",
    "required_anchors",
    "max_size_kb",
    "language",
)


def emit_rag_manifest(doc: Document, *, indent: int | None = 2) -> str:
    """Emit a Document(type='rag') as a JSON manifest string.

    ``indent`` defaults to 2 (human-readable). Pass ``indent=None``
    for the compact form indexers consume programmatically.
    ``ValueError`` is raised when the Document is not of the rag
    flavor — callers route by ``doc.type`` so this is a programming
    error, not a runtime parse error.
    """
    if doc.type != "rag" or doc.rag is None:
        msg = "emit_rag_manifest requires Document.type='rag'"
        raise ValueError(msg)

    payload = {
        "version": MANIFEST_VERSION,
        "project": doc.project,
        "rag": _config_dict(doc.rag.config),
        "documents": [_document_dict(entry) for entry in doc.rag.documents],
    }
    return json.dumps(payload, indent=indent, ensure_ascii=False) + "\n"


def _config_dict(cfg: RagConfig) -> dict[str, Any]:
    """Render a RagConfig as an insertion-ordered dict.

    Defaults are always emitted for the always-present numeric fields
    (chunk sizes, top-k) so the manifest is self-describing. Optional
    scalar fields (``embedding_model``, ``vector_store``, etc.) are
    omitted when ``None`` to keep the JSON tight.
    """
    out: dict[str, Any] = {}
    for field in _CONFIG_FIELD_ORDER:
        value = getattr(cfg, field)
        if value is None:
            continue
        out[field] = value
    return out


def _document_dict(entry: DocumentEntry) -> dict[str, Any]:
    """Render a DocumentEntry as an insertion-ordered dict."""
    out: dict[str, Any] = {}
    for field in _DOCUMENT_FIELD_ORDER:
        value = getattr(entry, field)
        if _is_empty(value):
            continue
        out[field] = value
    return out


def _is_empty(value: object) -> bool:
    """Treat ``None`` and empty lists as omittable defaults.

    Empty strings are NOT empty here — ``source`` is required by the
    AST validator, so the only way to land here with an empty string
    is a programming error worth surfacing.
    """
    if value is None:
        return True
    return isinstance(value, list) and len(value) == 0


__all__ = ["MANIFEST_VERSION", "emit_rag_manifest"]
