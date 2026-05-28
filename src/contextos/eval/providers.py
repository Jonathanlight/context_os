"""Provider abstractions for evaluation — Phase 7.8.

Defines the :class:`SkillRoutingProvider` protocol plus
:class:`MockSkillProvider`, the deterministic test fixture every
unit test in this module relies on. The real Anthropic-backed
provider lives in :mod:`contextos.eval.anthropic_provider` so the
``anthropic`` SDK stays a strictly optional runtime dep.
"""

from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field

from contextos.ast.skill import SkillDocument


class TokenUsage(BaseModel):
    """Token counts reported back by the provider.

    All providers populate this so the runner can sum across cases and
    surface ``total_tokens`` in the aggregate report. The mock provider
    reports zeros — useful for asserting "no real tokens were spent".
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    input_tokens: int = Field(ge=0)
    output_tokens: int = Field(ge=0)

    @property
    def total(self) -> int:
        return self.input_tokens + self.output_tokens


class RoutingResponse(BaseModel):
    """Provider's response for one ``SkillCase``."""

    model_config = ConfigDict(extra="forbid")

    picked_skill: str | None = Field(
        default=None,
        description=(
            "Slug of the skill the model chose, or ``None`` if the "
            "model declined to route (no tool_use block in the "
            "response)."
        ),
    )
    raw_response: str = Field(
        default="",
        description=(
            "Stringified provider response for debugging — never used "
            "by the runner's pass/fail logic."
        ),
    )
    token_usage: TokenUsage | None = None


class SkillRoutingProvider(Protocol):
    """The shape every Skills routing evaluator backend must satisfy.

    Implementations:

    - :class:`MockSkillProvider` for tests (deterministic, zero-cost).
    - :class:`~contextos.eval.anthropic_provider.AnthropicSkillProvider`
      for production runs (real API calls, real billing).

    Adding a new backend (OpenAI, local Llama, …) is one class
    implementing this protocol — no changes to the runner.
    """

    def route(
        self,
        prompt: str,
        skills: list[SkillDocument],
    ) -> RoutingResponse: ...


class MockSkillProvider:
    """Deterministic provider that looks prompts up in a routing table.

    Used exclusively by the test suite — never by ``ctx eval``. A real
    run always uses a paid backend; the mock exists so we can validate
    the runner's accounting (pass/fail logic, token sum, error
    handling) without burning credits or worrying about LLM flakiness.
    """

    def __init__(
        self,
        routing_table: dict[str, str | None],
        *,
        default: str | None = None,
        error_for: frozenset[str] | None = None,
    ) -> None:
        """Build a mock provider.

        :param routing_table: prompt → picked skill slug (or ``None``
            for "model declined").
        :param default: fallback for prompts not in the table.
        :param error_for: prompts that should raise instead of
            returning a response — for testing the runner's error
            handling path.
        """
        self._routing_table = dict(routing_table)
        self._default = default
        self._error_for = error_for or frozenset()

    def route(
        self,
        prompt: str,
        skills: list[SkillDocument],
    ) -> RoutingResponse:
        """Return the configured response for ``prompt``."""
        _ = skills  # mock doesn't consult the registry
        if prompt in self._error_for:
            msg = f"MockSkillProvider configured to error on prompt: {prompt!r}"
            raise RuntimeError(msg)
        picked = self._routing_table.get(prompt, self._default)
        return RoutingResponse(
            picked_skill=picked,
            raw_response=f"mock(picked={picked!r})",
            token_usage=TokenUsage(input_tokens=0, output_tokens=0),
        )


__all__ = [
    "MockSkillProvider",
    "RoutingResponse",
    "SkillRoutingProvider",
    "TokenUsage",
]
