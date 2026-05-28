"""Corpus-wide statistics over an :class:`AuditReport`.

Phase 4.1 ships the aggregation layer on top of the audit:

- :func:`compute_stats` rolls an :class:`AuditReport` into a
  :class:`CorpusStats` with per-severity counts, top diagnostic codes,
  rule counts per file, and target coverage.
- :func:`render_stats_cli` produces a human-readable summary table.
- :func:`render_stats_json` produces a machine-readable payload for
  dashboards / blog posts.

The audit reports per-file findings — stats answers "what does the
corpus *look like* in aggregate?". The two are intentionally separate:
audit can fire on a single file, stats only makes sense across many.
"""

from __future__ import annotations

from contextos.stats.aggregator import CorpusStats, compute_stats
from contextos.stats.renderer import render_stats_cli, render_stats_json

__all__ = [
    "CorpusStats",
    "compute_stats",
    "render_stats_cli",
    "render_stats_json",
]
