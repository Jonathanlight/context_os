"""Pydantic models for the evaluation family — Phase 7.7.

ContextOS's lint pipeline validates *structure*: does this skill have
trigger phrasing, does this RAG config have a freshness policy, etc.
Phase 7B introduces *functional* evaluation: does this skill actually
fire when the model sees the prompts it should, and does this RAG
pipeline actually retrieve the sources the user expects?

An :class:`EvalSuite` is a collection of :class:`SkillCase` and / or
:class:`RagCase` items, loaded from a ``.eval.toml`` file that sits
next to the artifact under test (typically ``project.ctx`` plus
``project.eval.toml``). Phase 7.7 lands the model only; the runners
that actually invoke an LLM and score the result live in
:mod:`contextos.eval` (Phase 7.8 / 7.9).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

EvalTarget = Literal["anthropic_skill", "rag"]
"""Which artifact family an :class:`EvalSuite` evaluates.

The literal mirrors the corresponding ``ctx compile --target`` keys
so the CLI surface stays internally consistent: an eval suite
targeting ``anthropic_skill`` evaluates a ``SKILL.md`` or a `.ctx`
declaring ``artifacts=['skills']``; one targeting ``rag`` evaluates
a `.ctx` declaring ``artifacts=['rag']``.
"""

PromptText = str
"""Free-form prompt string sent to the model under test.

We do not constrain length or content — the prompt is the user's,
not ours, and the model is the thing being measured. The eval
runner reports if the prompt blows the model's context window; we
do not pre-validate.
"""


class SkillCase(BaseModel):
    """One eval case for the Anthropic Skills routing family.

    The runner sends :attr:`prompt` to the model with the skill
    registry attached, observes which skill the model picks (if any),
    and compares the slug to :attr:`expected_skill`. ``None`` for
    "the model is expected to NOT fire any skill on this prompt" is
    a future extension; today every case asserts a positive
    expectation.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, description="Case label shown in the eval report.")
    prompt: PromptText = Field(min_length=1)
    expected_skill: str = Field(
        min_length=1,
        description=(
            "Slug of the skill expected to fire — matches "
            "``SkillDocument.name``. Compared verbatim, no normalization."
        ),
    )
    tags: list[str] = Field(
        default_factory=list,
        description=(
            "Free-form tags for grouping cases (e.g. 'fr' for French "
            "variants). The runner can filter to a tag subset via "
            "``ctx eval --tag <name>``."
        ),
    )


class RagCase(BaseModel):
    """One eval case for the RAG retrieval family.

    The runner embeds :attr:`query`, ranks the indexed chunks by
    cosine similarity, takes the top :attr:`top_k`, and considers
    the case a pass if **any** entry in :attr:`expected_sources`
    appears among the result paths.

    ``top_k`` defaults to 5 — large enough that a marginally-wrong
    chunk-size choice doesn't poison every case, small enough that
    a real retrieval regression still surfaces.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    query: str = Field(min_length=1)
    expected_sources: list[str] = Field(
        min_length=1,
        description=(
            "Source paths (or path globs) expected in the top-k "
            "retrieval results. At least one must match for the case "
            "to pass; this is an OR over the list, not an AND."
        ),
    )
    top_k: int = Field(default=5, ge=1, le=100)
    tags: list[str] = Field(default_factory=list)


class EvalSuite(BaseModel):
    """Collection of eval cases keyed to a single artifact family.

    The :attr:`target` discriminates which list of cases the runner
    iterates. A mismatched ``target`` and case list (e.g. a
    ``target='rag'`` suite carrying ``skill_cases``) is rejected at
    construction time so the runner can't accidentally evaluate the
    wrong family.
    """

    model_config = ConfigDict(extra="forbid")

    project: str = Field(min_length=1)
    target: EvalTarget
    suite_version: str = Field(
        default="1.0",
        description=(
            "Eval suite schema version. Bump only when the result "
            "shape changes incompatibly; adding fields stays at 1.0."
        ),
    )
    skill_cases: list[SkillCase] = Field(default_factory=list)
    rag_cases: list[RagCase] = Field(default_factory=list)

    @model_validator(mode="after")
    def _check_target_matches_cases(self) -> EvalSuite:
        """Enforce that the populated case list matches :attr:`target`.

        Three failure modes caught here:

        - ``target='anthropic_skill'`` with no ``skill_cases`` and at
          least one ``rag_case`` — the runner would silently find
          nothing to evaluate.
        - ``target='rag'`` with no ``rag_cases`` and at least one
          ``skill_case`` — same.
        - ``target='anthropic_skill'`` AND ``rag_cases`` populated —
          the rag list is dead code; almost always a copy-paste
          error worth surfacing.

        A suite with **no** cases at all is allowed (a placeholder
        eval file the author is filling in) and surfaces as an empty
        evaluation report — not an error.
        """
        if self.target == "anthropic_skill" and self.rag_cases:
            msg = (
                "EvalSuite(target='anthropic_skill') must not carry "
                "rag_cases; move them into a separate target='rag' suite"
            )
            raise ValueError(msg)
        if self.target == "rag" and self.skill_cases:
            msg = (
                "EvalSuite(target='rag') must not carry skill_cases; "
                "move them into a separate target='anthropic_skill' suite"
            )
            raise ValueError(msg)
        return self

    def total_cases(self) -> int:
        """Count cases across both families (only one is non-empty)."""
        return len(self.skill_cases) + len(self.rag_cases)


__all__ = [
    "EvalSuite",
    "EvalTarget",
    "PromptText",
    "RagCase",
    "SkillCase",
]
