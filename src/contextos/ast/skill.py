"""Pydantic models for the **skill** family — Phase 5.

A *skill* in the Anthropic Skills sense is a self-contained packaged
capability the model can invoke on demand. On disk it lives as
``skills/<name>/SKILL.md`` with YAML frontmatter declaring at minimum a
``name`` and a ``description`` (the trigger signal), plus an optional
body describing usage, examples, and references.

ContextOS represents a single skill as :class:`SkillDocument`. The field
shape mirrors the SPEC §1.3 ``[[skill]]`` declaration so a `.ctx` source
and a ``SKILL.md`` file round-trip through the same AST.

Phase 5.1 lands the AST only — the parser, emitter, and analyzers ship
in 5.2 / 5.3 / 5.4.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NAME_PATTERN = r"^[a-z][a-z0-9-]{0,63}$"
"""Skill slug shape — kebab-case, starts with a letter, ≤ 64 chars.

Matches the Anthropic Skills directory-name convention so the slug can
serve as both the AST identifier and the on-disk folder name.
"""

_NAME_REGEX = re.compile(NAME_PATTERN)

DESCRIPTION_MAX_CHARS = 1024
"""Hard ceiling on the description string per SPEC §1.3.

The description is the **trigger signal** loaded into the model's
context every time the skill is registered, so length directly trades
against the rest of the context budget. The 1024-character ceiling
keeps a fully-loaded skill registry from drowning out the user prompt.
"""

ExpectedOutputFormat = Literal["json", "markdown", "text", "yaml", "toml"]
"""Allowed values for :attr:`SkillDocument.expected_output_format`.

The set stays intentionally small — the field is informational rather
than executable, and a free-form string would invite typos that no rule
could surface.
"""

SkillName = Annotated[str, StringConstraints(pattern=NAME_PATTERN)]
SkillTitle = Annotated[str, StringConstraints(min_length=1, strip_whitespace=False)]
SkillDescription = Annotated[
    str,
    StringConstraints(min_length=1, max_length=DESCRIPTION_MAX_CHARS),
]


class SkillDocument(BaseModel):
    """A single Anthropic-style skill.

    Required fields (``name``, ``title``, ``description``) mirror SPEC
    §1.3. All recommended fields default to empty so a minimal skill
    declaring only the required trio still validates.

    The model is configured with ``extra="forbid"`` so an unrecognized
    field surfaces as a parse error rather than silently dropping —
    Phase 5.2's parser relies on that to flag unknown keys.
    """

    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    name: SkillName = Field(
        description="Kebab-case slug; doubles as the SKILL.md folder name.",
    )
    title: SkillTitle = Field(
        description="Human-readable title shown in skill registries.",
    )
    description: SkillDescription = Field(
        description=(
            "Trigger signal loaded into context — should describe **when** "
            "the model should invoke the skill, not just what it does."
        ),
    )
    trigger_keywords: list[str] = Field(
        default_factory=list,
        description="Lexical hints that complement the description.",
    )
    applies_to: list[str] = Field(default_factory=list)
    languages_supported: list[str] = Field(default_factory=list)
    files: list[str] = Field(
        default_factory=list,
        description=(
            "Files packaged alongside SKILL.md, relative to the skill folder. "
            "The Phase 5 emitter verifies existence before copying."
        ),
    )
    required_runtime: str | None = None
    example_invocation: str | None = None
    expected_output_format: ExpectedOutputFormat | None = Field(
        default=None,
        description=(
            "Constrained to the values declared by "
            ":data:`ExpectedOutputFormat`; Pydantic rejects anything else."
        ),
    )
    tags: list[str] = Field(default_factory=list)
    body: str = Field(
        default="",
        description=(
            "Free-form Markdown body of the SKILL.md, between the closing "
            "frontmatter delimiter and EOF. Preserved verbatim for round-trip."
        ),
    )

    def is_valid_name(self) -> bool:
        """Re-check the slug shape (handy after deserialization)."""
        return bool(_NAME_REGEX.fullmatch(self.name))


__all__ = [
    "DESCRIPTION_MAX_CHARS",
    "NAME_PATTERN",
    "ExpectedOutputFormat",
    "SkillDescription",
    "SkillDocument",
    "SkillName",
    "SkillTitle",
]
