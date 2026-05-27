"""Agent-family analyzers — one module per lint category.

Categories per SPEC.md §2:

- :mod:`ambiguity` — A***: vague directives, subjective adjectives
- :mod:`contradiction` — C***: rules that disagree (Milestone 2.5)
- :mod:`completeness` — K***: missing sections, undocumented behaviour
- :mod:`antipattern` — X***: known bad patterns
- :mod:`llm_friendly` — F***: formatting that hurts the model
- :mod:`platform` — P***: target-specific gotchas
"""

from __future__ import annotations
