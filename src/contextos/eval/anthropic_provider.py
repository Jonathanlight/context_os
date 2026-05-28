"""Anthropic-backed Skills routing provider — Phase 7.8.

Lives in its own module so the rest of :mod:`contextos.eval` stays
importable without the ``anthropic`` SDK. Users who want to run
``ctx eval`` against a real API install the ``[eval]`` extras:

    pipx install context-os[eval]

The routing strategy emulates Anthropic Skills via the Messages API's
tool-use feature: each :class:`SkillDocument` becomes a tool definition
whose ``description`` is the skill's trigger signal. We send the user
prompt; the model decides whether to call a tool. The tool call's name
maps back to the skill slug.

This is **emulation, not the actual Skills product** — that lives at
the Claude app / Claude Code layer, not the public API. The routing
heuristics the model uses for tool selection in the Messages API are
close enough to the Skills router for evaluation purposes, but we
document the gap so authors know what the metric measures.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from contextos.ast.skill import SkillDocument
from contextos.eval.providers import RoutingResponse, TokenUsage

if TYPE_CHECKING:
    from anthropic import Anthropic
    from anthropic.types import Message

_DEFAULT_MODEL = "claude-haiku-4-5-20251001"
"""Cheapest fast model for evaluation. Override via the constructor
when you want sonnet/opus quality at higher cost-per-case.
"""

_DEFAULT_MAX_TOKENS = 1024


class AnthropicSkillProvider:
    """Provider that asks Claude to route the prompt to the right skill.

    The class is intentionally small — most of the work is in
    constructing the tools list from the SkillDocument set and
    parsing the ``tool_use`` block back out of the response.

    Cost note: each ``route()`` call is one Messages API request.
    Token usage is small (the skill descriptions plus the prompt;
    typically a few hundred input tokens, a few output tokens), but
    cost scales linearly with the number of cases. The runner
    surfaces the total via :attr:`EvalRunResult.total_tokens`.
    """

    def __init__(
        self,
        *,
        client: Anthropic | None = None,
        model: str = _DEFAULT_MODEL,
        max_tokens: int = _DEFAULT_MAX_TOKENS,
    ) -> None:
        """Create the provider.

        :param client: pre-built ``anthropic.Anthropic`` instance. If
            ``None``, we construct one with default settings (reads
            ``ANTHROPIC_API_KEY`` from the environment).
        :param model: model ID. Defaults to Haiku 4.5 for low-cost
            evaluation; bump to Sonnet / Opus for higher fidelity.
        :param max_tokens: per-call cap. 1024 is plenty for tool
            selection; raise only if you also configure the model to
            generate prose.
        """
        from anthropic import Anthropic  # noqa: PLC0415 — lazy by design

        self._client = client if client is not None else Anthropic()
        self._model = model
        self._max_tokens = max_tokens

    def route(
        self,
        prompt: str,
        skills: list[SkillDocument],
    ) -> RoutingResponse:
        """Route ``prompt`` against the ``skills`` registry."""
        tools = [_skill_to_tool(s) for s in skills]
        response = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            tools=tools,  # type: ignore[arg-type]
            messages=[{"role": "user", "content": prompt}],
        )
        return _parse_response(response)


def _skill_to_tool(skill: SkillDocument) -> dict[str, Any]:
    """Render a SkillDocument as the Anthropic tool definition shape.

    The ``input_schema`` is a single optional ``trigger`` string — the
    minimum that satisfies the API's schema requirement. We do not
    use the input value; only the **fact** that the model chose this
    tool matters for evaluation.
    """
    return {
        "name": skill.name,
        "description": skill.description,
        "input_schema": {
            "type": "object",
            "properties": {
                "trigger": {
                    "type": "string",
                    "description": "The matching trigger phrase from the user prompt.",
                },
            },
        },
    }


def _parse_response(response: Message) -> RoutingResponse:
    """Extract the picked skill from a Messages API response.

    Walks the content blocks looking for the first ``tool_use``; the
    tool's name is the skill slug. If no tool_use is present, the
    model declined to route — we return ``picked_skill=None`` so the
    runner can score the case correctly.
    """
    picked: str | None = None
    for block in response.content:
        if getattr(block, "type", None) == "tool_use":
            picked = getattr(block, "name", None)
            break

    usage = response.usage
    token_usage = TokenUsage(
        input_tokens=int(getattr(usage, "input_tokens", 0)),
        output_tokens=int(getattr(usage, "output_tokens", 0)),
    )

    return RoutingResponse(
        picked_skill=picked,
        raw_response=str(response.content),
        token_usage=token_usage,
    )


__all__ = ["AnthropicSkillProvider"]
