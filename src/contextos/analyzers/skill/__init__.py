"""Skill-family analyzers (category S) — Phase 5.4.

Six rules across two themes:

- **Trigger signal quality** (S001, S002, S003) — the description is
  the only string the model sees when deciding whether to invoke the
  skill, so quality of phrasing and length directly affect routing.
- **Body / metadata coherence** (S004, S005, S006) — surfaces gaps
  between what the YAML declares and what the body actually delivers.

S-rules are intentionally quieter than K-rules: most are INFO since
they're stylistic. S001 is the only WARNING — a description with no
trigger phrasing is the single failure mode that produces silent
"skill never fires" bugs in production.
"""

from __future__ import annotations

from contextos.analyzers.skill import (
    body_coherence,
    description_quality,
)

__all__ = ["body_coherence", "description_quality"]
