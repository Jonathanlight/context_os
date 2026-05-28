"""Unit tests for the eval providers — Phase 7.8."""

from __future__ import annotations

import pytest

from contextos.ast.skill import SkillDocument
from contextos.eval.providers import (
    MockSkillProvider,
    RoutingResponse,
    TokenUsage,
)


def _skill(name: str = "demo") -> SkillDocument:
    return SkillDocument(
        name=name,
        title=f"Skill {name}",
        description=(f"A demo skill named {name}. Triggers when the user asks to run the demo."),
    )


class TestTokenUsage:
    def test_total_sums_input_and_output(self) -> None:
        usage = TokenUsage(input_tokens=10, output_tokens=20)
        assert usage.total == 30

    def test_zero_is_legal(self) -> None:
        usage = TokenUsage(input_tokens=0, output_tokens=0)
        assert usage.total == 0


class TestMockSkillProvider:
    def test_routes_known_prompt(self) -> None:
        provider = MockSkillProvider({"do X": "skill-x"})
        response = provider.route("do X", [_skill("skill-x")])
        assert response.picked_skill == "skill-x"

    def test_unknown_prompt_uses_default(self) -> None:
        provider = MockSkillProvider({"do X": "skill-x"}, default="skill-y")
        response = provider.route("do Z", [_skill("skill-y")])
        assert response.picked_skill == "skill-y"

    def test_default_none_means_model_declined(self) -> None:
        provider = MockSkillProvider({}, default=None)
        response = provider.route("anything", [_skill()])
        assert response.picked_skill is None

    def test_explicit_none_in_table_means_declined(self) -> None:
        provider = MockSkillProvider({"hard prompt": None})
        response = provider.route("hard prompt", [_skill()])
        assert response.picked_skill is None

    def test_raises_when_prompt_in_error_set(self) -> None:
        provider = MockSkillProvider({}, error_for=frozenset({"crash me"}))
        with pytest.raises(RuntimeError, match=r"configured to error"):
            provider.route("crash me", [_skill()])

    def test_response_token_usage_is_zero(self) -> None:
        provider = MockSkillProvider({"x": "y"})
        response = provider.route("x", [_skill("y")])
        assert response.token_usage is not None
        assert response.token_usage.total == 0


class TestRoutingResponse:
    def test_defaults(self) -> None:
        resp = RoutingResponse()
        assert resp.picked_skill is None
        assert resp.raw_response == ""
        assert resp.token_usage is None

    def test_with_picked_skill(self) -> None:
        resp = RoutingResponse(picked_skill="demo", raw_response="...")
        assert resp.picked_skill == "demo"
