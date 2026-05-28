"""Pipeline-completeness RAG analyzers — R003, R004, R005."""

from __future__ import annotations

from collections.abc import Iterable

from contextos.ast.rag import RagDocument
from contextos.diagnostics import Diagnostic, DiagSeverity

# ---------------------------------------------------------------------------
# R003 — freshness_policy missing
# ---------------------------------------------------------------------------

R003_CODE = "R003"
R003_SEVERITY = DiagSeverity.INFO
R003_DOC_URL = "https://contextos.dev/rules/R003"

# ---------------------------------------------------------------------------
# R004 — embedding_model unspecified
# ---------------------------------------------------------------------------

R004_CODE = "R004"
R004_SEVERITY = DiagSeverity.WARNING
R004_DOC_URL = "https://contextos.dev/rules/R004"

# ---------------------------------------------------------------------------
# R005 — header_aware override without required_anchors
# ---------------------------------------------------------------------------

R005_CODE = "R005"
R005_SEVERITY = DiagSeverity.INFO
R005_DOC_URL = "https://contextos.dev/rules/R005"


def check(rag: RagDocument) -> Iterable[Diagnostic]:
    """Run every pipeline-completeness check against ``rag``."""
    yield from _check_freshness_policy(rag)
    yield from _check_embedding_model(rag)
    yield from _check_anchor_chunking_match(rag)


def _check_freshness_policy(rag: RagDocument) -> Iterable[Diagnostic]:
    """R003 — corpus has no freshness_policy.

    Without a freshness policy, the indexer has nothing to compare
    document age against, so stale content keeps surfacing forever.
    INFO because a few corpora are genuinely permanent (legal,
    historical) — the rule is a nudge, not a defect.
    """
    if rag.config.freshness_policy is not None:
        return
    yield Diagnostic(
        code=R003_CODE,
        severity=R003_SEVERITY,
        message="RAG corpus has no `freshness_policy` — stale documents will never be marked",
        suggestion=(
            'set `freshness_policy = "30d"` (or another compact d/w/m/y '
            "value) under [rag] so the indexer can flag stale content"
        ),
        doc_url=R003_DOC_URL,
    )


def _check_embedding_model(rag: RagDocument) -> Iterable[Diagnostic]:
    """R004 — no `embedding_model` declared.

    The indexer needs an embedding model name to know how to vectorize.
    Leaving it unspecified pushes the decision to operations time and
    breaks reproducibility — two indexers reading the same manifest
    may pick different defaults. WARNING.
    """
    if rag.config.embedding_model and rag.config.embedding_model.strip():
        return
    yield Diagnostic(
        code=R004_CODE,
        severity=R004_SEVERITY,
        message=(
            "RAG corpus has no `embedding_model` — downstream indexers "
            "cannot pick one deterministically"
        ),
        suggestion=('declare `embedding_model = "voyage-3"` (or your chosen vendor) under [rag]'),
        doc_url=R004_DOC_URL,
    )


def _check_anchor_chunking_match(rag: RagDocument) -> Iterable[Diagnostic]:
    """R005 — entries with header_aware override should declare required_anchors.

    Header-aware chunking only works when the source actually has
    headers to anchor on. Declaring the override without the anchors
    means the chunker either falls back silently or produces nonsense.
    """
    for entry in rag.documents:
        if entry.chunking_override != "header_aware":
            continue
        if entry.required_anchors:
            continue
        yield Diagnostic(
            code=R005_CODE,
            severity=R005_SEVERITY,
            message=(
                f"document '{entry.source}' overrides chunking to "
                "header_aware but declares no `required_anchors`"
            ),
            suggestion=(
                'add `required_anchors = ["##"]` (or the heading level your '
                "source actually uses) so the chunker has something to "
                "anchor on"
            ),
            doc_url=R005_DOC_URL,
        )
