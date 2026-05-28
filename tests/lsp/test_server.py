"""Integration tests for the LSP server — synthetic notifications.

These tests exercise the server in-process. We instantiate the
:class:`LanguageServer` returned by :func:`build_server`, then call
the registered handlers directly with synthetic LSP params, and
intercept the diagnostics it would publish via a stub on
``text_document_publish_diagnostics``.

This pattern keeps the test cost low (no subprocess, no JSON-RPC
framing) while still validating the parser/lint dispatch the real
server uses.
"""

from __future__ import annotations

import textwrap
from collections.abc import Callable
from typing import Any

import pytest
from lsprotocol import types as lsp

from contextos.lsp.server import build_server

_GOOD_CTX = textwrap.dedent(
    """\
    project = "Demo"
    artifacts = ["context"]

    [[rules]]
    id = "TDD-001"
    title = "Write a failing test before any production code change"
    severity = "must"
    rationale = "Catches regressions before they hit review."
    example_good = "pytest tests/test_new_feature.py::test_happy"
    """
)

_BAD_CTX = textwrap.dedent(
    """\
    project = ""
    artifacts = ["context"]
    """
)

_GOOD_SKILL = textwrap.dedent(
    """\
    ---
    name: demo
    title: Demo skill
    description: Triggers when the user uploads a demo file and asks to parse it.
    example_invocation: Parse this demo.csv for me.
    ---

    # Demo skill

    Body.
    """
)


@pytest.fixture
def server_with_capture() -> tuple[Any, list[lsp.PublishDiagnosticsParams]]:
    """Return the server plus a list that captures every publish call.

    The completion / hover handlers need a workspace to fetch document
    text via ``server.workspace.get_text_document(...)``. pygls only
    initializes the workspace on the ``initialize`` request, which we
    don't simulate here; instead, we attach a minimal ``Workspace``
    directly to the protocol so the in-process tests can drive the
    handlers without a JSON-RPC roundtrip.
    """
    from pygls.workspace import Workspace  # noqa: PLC0415 — pygls is an optional dep

    server = build_server()
    server.protocol._workspace = Workspace(root_uri=None)
    captured: list[lsp.PublishDiagnosticsParams] = []

    def _publish(params: lsp.PublishDiagnosticsParams) -> None:
        captured.append(params)

    server.text_document_publish_diagnostics = _publish  # type: ignore[method-assign]
    return server, captured


def _handler(server: Any, feature: str) -> Callable[[Any], Any]:
    """Look up the handler registered for an LSP feature.

    pygls 2.x stores them on the protocol's feature manager
    (``server.protocol.fm.features``). Centralizing the path here
    keeps the upgrade surface small if pygls renames it again.
    """
    return server.protocol.fm.features[feature]  # type: ignore[no-any-return]


class TestCtxFileFlow:
    def test_clean_ctx_publishes_empty_diagnostics(
        self,
        server_with_capture: tuple[Any, list[lsp.PublishDiagnosticsParams]],
    ) -> None:
        server, captured = server_with_capture
        handler = _handler(server, lsp.TEXT_DOCUMENT_DID_OPEN)
        handler(
            lsp.DidOpenTextDocumentParams(
                text_document=lsp.TextDocumentItem(
                    uri="file:///tmp/demo.ctx",
                    language_id="toml",
                    version=1,
                    text=_GOOD_CTX,
                )
            )
        )
        assert len(captured) == 1
        assert captured[0].uri == "file:///tmp/demo.ctx"
        assert captured[0].diagnostics == []

    def test_parse_error_publishes_single_diagnostic(
        self,
        server_with_capture: tuple[Any, list[lsp.PublishDiagnosticsParams]],
    ) -> None:
        server, captured = server_with_capture
        handler = _handler(server, lsp.TEXT_DOCUMENT_DID_OPEN)
        handler(
            lsp.DidOpenTextDocumentParams(
                text_document=lsp.TextDocumentItem(
                    uri="file:///tmp/broken.ctx",
                    language_id="toml",
                    version=1,
                    text=_BAD_CTX,
                )
            )
        )
        assert len(captured) == 1
        diags = captured[0].diagnostics
        assert len(diags) == 1
        assert diags[0].code == "E0001"
        assert diags[0].severity == lsp.DiagnosticSeverity.Error


class TestSkillFileFlow:
    def test_clean_skill_publishes_empty_diagnostics(
        self,
        server_with_capture: tuple[Any, list[lsp.PublishDiagnosticsParams]],
    ) -> None:
        server, captured = server_with_capture
        handler = _handler(server, lsp.TEXT_DOCUMENT_DID_OPEN)
        handler(
            lsp.DidOpenTextDocumentParams(
                text_document=lsp.TextDocumentItem(
                    uri="file:///tmp/skills/demo/SKILL.md",
                    language_id="markdown",
                    version=1,
                    text=_GOOD_SKILL,
                )
            )
        )
        assert len(captured) == 1
        assert captured[0].diagnostics == []


class TestUnknownFile:
    def test_unrelated_extension_publishes_empty_diagnostics(
        self,
        server_with_capture: tuple[Any, list[lsp.PublishDiagnosticsParams]],
    ) -> None:
        # The server should ignore files it doesn't understand — no
        # noise in the editor for opened Python sources or other docs.
        server, captured = server_with_capture
        handler = _handler(server, lsp.TEXT_DOCUMENT_DID_OPEN)
        handler(
            lsp.DidOpenTextDocumentParams(
                text_document=lsp.TextDocumentItem(
                    uri="file:///tmp/unrelated.py",
                    language_id="python",
                    version=1,
                    text="print('hi')\n",
                )
            )
        )
        assert len(captured) == 1
        assert captured[0].diagnostics == []


def _seed_document(server: Any, uri: str, text: str) -> None:
    """Put a document directly into the LSP workspace.

    The in-process tests don't go through the JSON-RPC layer that
    triggers pygls's builtin didOpen handler (which would normally
    call ``workspace.put_text_document``). Registering the document
    here so subsequent completion / hover handlers find it via
    ``server.workspace.get_text_document(...)``.
    """
    server.workspace.put_text_document(
        lsp.TextDocumentItem(uri=uri, language_id="toml", version=1, text=text)
    )


class TestCompletionWiring:
    """The completion handler should plumb through to compute_completions."""

    def test_completion_returns_top_level_keys_on_empty_ctx(
        self,
        server_with_capture: tuple[Any, list[lsp.PublishDiagnosticsParams]],
    ) -> None:
        server, _ = server_with_capture
        _seed_document(server, "file:///tmp/x.ctx", "")
        completion_handler = _handler(server, lsp.TEXT_DOCUMENT_COMPLETION)
        result = completion_handler(
            lsp.CompletionParams(
                text_document=lsp.TextDocumentIdentifier(uri="file:///tmp/x.ctx"),
                position=lsp.Position(line=0, character=0),
            )
        )
        labels = [item.label for item in result.items]
        assert "project" in labels
        assert "artifacts" in labels


class TestHoverWiring:
    """The hover handler should return a Hover for rule codes."""

    def test_hover_on_rule_code(
        self,
        server_with_capture: tuple[Any, list[lsp.PublishDiagnosticsParams]],
    ) -> None:
        server, _ = server_with_capture
        text = "# This file references A001 and S005.\n"
        _seed_document(server, "file:///tmp/note.ctx", text)
        hover_handler = _handler(server, lsp.TEXT_DOCUMENT_HOVER)
        result = hover_handler(
            lsp.HoverParams(
                text_document=lsp.TextDocumentIdentifier(uri="file:///tmp/note.ctx"),
                position=lsp.Position(line=0, character=24),
            )
        )
        assert result is not None
        assert isinstance(result.contents, lsp.MarkupContent)
        assert "A001" in result.contents.value

    def test_hover_off_token_returns_none(
        self,
        server_with_capture: tuple[Any, list[lsp.PublishDiagnosticsParams]],
    ) -> None:
        server, _ = server_with_capture
        _seed_document(server, "file:///tmp/plain.ctx", "hello world\n")
        hover_handler = _handler(server, lsp.TEXT_DOCUMENT_HOVER)
        result = hover_handler(
            lsp.HoverParams(
                text_document=lsp.TextDocumentIdentifier(uri="file:///tmp/plain.ctx"),
                position=lsp.Position(line=0, character=2),
            )
        )
        assert result is None
