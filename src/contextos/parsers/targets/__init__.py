"""Per-target parsing configuration.

Each target (claude_code, codex, cursor, copilot, cline, windsurf in
Phase 3; anthropic_skills in Phase 5; rag_corpus in Phase 6) declares
its section aliases and severity keywords in
``targets/mappings/<target>.toml``. The shared Markdown parser reads
the mapping to decide where text belongs.
"""

from __future__ import annotations

__all__: list[str] = []
