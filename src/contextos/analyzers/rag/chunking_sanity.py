"""Chunking-sanity RAG analyzers — R001, R002, R006."""

from __future__ import annotations

from collections.abc import Iterable

from contextos.ast.rag import RagDocument
from contextos.diagnostics import Diagnostic, DiagSeverity

# ---------------------------------------------------------------------------
# R001 — excessive chunk overlap
# ---------------------------------------------------------------------------

R001_CODE = "R001"
R001_SEVERITY = DiagSeverity.WARNING
R001_DOC_URL = "https://contextos.dev/rules/R001"

R001_OVERLAP_RATIO_LIMIT = 0.5
"""Overlap above 50% of the target chunk means every retrieval result
duplicates more than half of its neighbour. The reranker then has to
deduplicate effort instead of ranking distinct material — and the
index doubles in size for no recall gain."""

# ---------------------------------------------------------------------------
# R002 — target/max headroom too tight
# ---------------------------------------------------------------------------

R002_CODE = "R002"
R002_SEVERITY = DiagSeverity.INFO
R002_DOC_URL = "https://contextos.dev/rules/R002"

R002_MIN_HEADROOM_RATIO = 0.2
"""``chunk_max_tokens`` should sit at least 20% above ``chunk_target_tokens``.

Without headroom, header-aware or semantic chunkers regularly trip
against the ceiling and either truncate context or fall back to fixed
chunking, both of which hurt retrieval quality on the long tail.
"""

# ---------------------------------------------------------------------------
# R006 — large file without chunking_override
# ---------------------------------------------------------------------------

R006_CODE = "R006"
R006_SEVERITY = DiagSeverity.INFO
R006_DOC_URL = "https://contextos.dev/rules/R006"

R006_LARGE_FILE_KB = 500
"""Files declared larger than 500 KB benefit from header_aware chunking
to keep the indexer from producing fragmented chunks; INFO surfaces
that suggestion."""


def check(rag: RagDocument) -> Iterable[Diagnostic]:
    """Run every chunking-sanity check against ``rag``."""
    yield from _check_overlap_ratio(rag)
    yield from _check_target_max_headroom(rag)
    yield from _check_large_file_chunking(rag)


def _check_overlap_ratio(rag: RagDocument) -> Iterable[Diagnostic]:
    """R001 — overlap is more than 50% of the target chunk size."""
    cfg = rag.config
    if cfg.chunk_target_tokens == 0:
        return
    ratio = cfg.chunk_overlap_tokens / cfg.chunk_target_tokens
    if ratio <= R001_OVERLAP_RATIO_LIMIT:
        return
    yield Diagnostic(
        code=R001_CODE,
        severity=R001_SEVERITY,
        message=(
            f"chunk_overlap_tokens ({cfg.chunk_overlap_tokens}) is "
            f"{ratio * 100:.0f}% of chunk_target_tokens "
            f"({cfg.chunk_target_tokens}) — limit is "
            f"{int(R001_OVERLAP_RATIO_LIMIT * 100)}%"
        ),
        suggestion=(
            "reduce chunk_overlap_tokens to 15-30% of chunk_target_tokens "
            "(typical: 50 overlap on 500 target)"
        ),
        doc_url=R001_DOC_URL,
    )


def _check_target_max_headroom(rag: RagDocument) -> Iterable[Diagnostic]:
    """R002 — chunk_max should sit at least 20% above chunk_target."""
    cfg = rag.config
    if cfg.chunk_target_tokens == 0:
        return
    headroom = (cfg.chunk_max_tokens - cfg.chunk_target_tokens) / cfg.chunk_target_tokens
    if headroom >= R002_MIN_HEADROOM_RATIO:
        return
    yield Diagnostic(
        code=R002_CODE,
        severity=R002_SEVERITY,
        message=(
            f"chunk_max_tokens ({cfg.chunk_max_tokens}) gives only "
            f"{headroom * 100:.0f}% headroom over chunk_target_tokens "
            f"({cfg.chunk_target_tokens}) — recommend "
            f">={int(R002_MIN_HEADROOM_RATIO * 100)}%"
        ),
        suggestion=(
            "raise chunk_max_tokens so header-aware or semantic chunkers "
            "have room to bend before falling back to fixed chunking"
        ),
        doc_url=R002_DOC_URL,
    )


def _check_large_file_chunking(rag: RagDocument) -> Iterable[Diagnostic]:
    """R006 — large declared sources benefit from header_aware chunking."""
    for entry in rag.documents:
        if entry.max_size_kb is None or entry.max_size_kb < R006_LARGE_FILE_KB:
            continue
        if entry.chunking_override == "header_aware":
            continue
        yield Diagnostic(
            code=R006_CODE,
            severity=R006_SEVERITY,
            message=(
                f"document '{entry.source}' is up to {entry.max_size_kb} KB "
                "but has no header_aware chunking_override — long documents "
                "fragment poorly under fixed/semantic chunkers"
            ),
            suggestion=(
                'set `chunking_override = "header_aware"` on this entry, or '
                "split the source into smaller files"
            ),
            doc_url=R006_DOC_URL,
        )
