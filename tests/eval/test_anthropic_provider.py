"""Tests for the Anthropic provider — Phase 7.8.

The unit test relies on a stubbed ``client`` injected via the
constructor so we never hit the real API. The integration smoke test
is skipped unless ``ANTHROPIC_API_KEY`` is set.
"""

from __future__ import annotations

import os
from typing import Any

import pytest

from contextos.ast.skill import SkillDocument
from contextos.eval.anthropic_provider import (
    AnthropicSkillProvider,
    _parse_response,
    _skill_to_tool,
)


def _skill(name: str = "pdf-extract") -> SkillDocument:
    return SkillDocument(
        name=name,
        title="PDF extract",
        description="Triggers when the user uploads a PDF and asks for line items.",
    )


# ---------------------------------------------------------------------------
# _skill_to_tool — pure helper, no network.
# ---------------------------------------------------------------------------


class TestSkillToTool:
    def test_name_and_description_passed_through(self) -> None:
        tool = _skill_to_tool(_skill("pdf-extract"))
        assert tool["name"] == "pdf-extract"
        assert "Triggers when" in tool["description"]

    def test_input_schema_present(self) -> None:
        tool = _skill_to_tool(_skill())
        schema = tool["input_schema"]
        assert schema["type"] == "object"
        assert "trigger" in schema["properties"]


# ---------------------------------------------------------------------------
# _parse_response — uses synthetic message objects to avoid the SDK.
# ---------------------------------------------------------------------------


class _StubToolUseBlock:
    def __init__(self, name: str) -> None:
        self.type = "tool_use"
        self.name = name


class _StubTextBlock:
    def __init__(self, text: str) -> None:
        self.type = "text"
        self.text = text


class _StubUsage:
    def __init__(self, input_tokens: int, output_tokens: int) -> None:
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _StubMessage:
    def __init__(self, content: list[Any], usage: _StubUsage) -> None:
        self.content = content
        self.usage = usage


class TestParseResponse:
    def test_tool_use_block_extracts_skill_name(self) -> None:
        message = _StubMessage(
            content=[_StubToolUseBlock("pdf-extract")],
            usage=_StubUsage(input_tokens=42, output_tokens=8),
        )
        response = _parse_response(message)  # type: ignore[arg-type]
        assert response.picked_skill == "pdf-extract"
        assert response.token_usage is not None
        assert response.token_usage.input_tokens == 42
        assert response.token_usage.output_tokens == 8

    def test_no_tool_use_returns_none(self) -> None:
        message = _StubMessage(
            content=[_StubTextBlock("I cannot help with that.")],
            usage=_StubUsage(input_tokens=10, output_tokens=5),
        )
        response = _parse_response(message)  # type: ignore[arg-type]
        assert response.picked_skill is None

    def test_first_tool_use_wins(self) -> None:
        # When the model emits multiple tool_use blocks (rare in
        # routing scenarios) we take the first.
        message = _StubMessage(
            content=[
                _StubToolUseBlock("first"),
                _StubToolUseBlock("second"),
            ],
            usage=_StubUsage(input_tokens=20, output_tokens=10),
        )
        response = _parse_response(message)  # type: ignore[arg-type]
        assert response.picked_skill == "first"


# ---------------------------------------------------------------------------
# AnthropicSkillProvider with a stubbed client — no network.
# ---------------------------------------------------------------------------


class _StubClient:
    def __init__(self, response: _StubMessage) -> None:
        self.messages = _StubMessagesClient(response)


class _StubMessagesClient:
    def __init__(self, response: _StubMessage) -> None:
        self._response = response
        self.last_call: dict[str, Any] | None = None

    def create(self, **kwargs: Any) -> _StubMessage:
        self.last_call = kwargs
        return self._response


class TestAnthropicProviderWithStubClient:
    def test_route_returns_picked_skill(self) -> None:
        message = _StubMessage(
            content=[_StubToolUseBlock("pdf-extract")],
            usage=_StubUsage(input_tokens=100, output_tokens=5),
        )
        provider = AnthropicSkillProvider(client=_StubClient(message))  # type: ignore[arg-type]
        response = provider.route("Extract this PDF", [_skill("pdf-extract")])
        assert response.picked_skill == "pdf-extract"
        assert response.token_usage is not None
        assert response.token_usage.total == 105

    def test_route_forwards_tools_and_prompt(self) -> None:
        message = _StubMessage(
            content=[_StubToolUseBlock("pdf-extract")],
            usage=_StubUsage(input_tokens=10, output_tokens=2),
        )
        stub = _StubClient(message)
        provider = AnthropicSkillProvider(client=stub)  # type: ignore[arg-type]
        provider.route("Extract this PDF", [_skill("pdf-extract")])
        call = stub.messages.last_call
        assert call is not None
        assert call["messages"][0]["content"] == "Extract this PDF"
        assert len(call["tools"]) == 1
        assert call["tools"][0]["name"] == "pdf-extract"


# ---------------------------------------------------------------------------
# Smoke test — skipped unless ANTHROPIC_API_KEY is present.
# ---------------------------------------------------------------------------


@pytest.mark.skipif(
    not os.environ.get("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set; skip real-API integration test",
)
def test_anthropic_smoke() -> None:
    """One real-API call to ensure the path works end-to-end.

    Intentionally tiny: one prompt, one skill, one model call. Costs
    ~one Haiku-4.5 invocation (~$0.0001). Skipped by default in CI.
    """
    provider = AnthropicSkillProvider()
    response = provider.route(
        "Extract the line items from this invoice.pdf",
        [_skill("pdf-extract")],
    )
    # We don't assert which skill the model picked — model behavior
    # is non-deterministic. We assert the path didn't raise and that
    # we got a response with token usage attached.
    assert response.token_usage is not None
    assert response.token_usage.total > 0
