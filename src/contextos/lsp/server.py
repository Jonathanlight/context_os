"""ContextOS language server — pygls 2.x implementation.

The server reacts to three LSP notifications:

- ``textDocument/didOpen`` — first time the editor exposes the file.
- ``textDocument/didChange`` — every keystroke (pygls accumulates the
  text via ``Incremental`` sync).
- ``textDocument/didSave`` — on disk write; same handling as didChange.

For every notification we route the document to the right ContextOS
parser based on the file shape:

- ``*.ctx`` → :func:`parse_ctx_string` (agent / skill / rag flavors
  dispatch downstream by ``Document.type``).
- ``SKILL.md`` (or path containing ``/SKILL.md``) →
  :func:`parse_skill_string`.

Anything else is ignored — the editor opens many files we don't
analyze; staying silent on those keeps the diagnostics view clean.

A parse error is published as a single diagnostic at the reported
position so the user sees the same ``file:line:column`` shape they'd
get from the CLI.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from lsprotocol import types as lsp
from pygls.lsp.server import LanguageServer

from contextos import __version__
from contextos.analyzers import lint_document
from contextos.ast.common import Position
from contextos.diagnostics import Diagnostic, DiagSeverity
from contextos.lsp.diagnostics_adapter import to_lsp_diagnostic
from contextos.parsers import (
    ContextOSParseError,
    parse_ctx_string,
    parse_skill_string,
)

if TYPE_CHECKING:
    from contextos.ast.document import Document


_SERVER_NAME = "contextos-lsp"


def build_server() -> LanguageServer:
    """Build the configured :class:`LanguageServer` instance.

    Factored out so tests can instantiate the server, feed it synthetic
    LSP notifications, and inspect the diagnostics it would publish
    without ever touching stdio or another subprocess.
    """
    server = LanguageServer(
        name=_SERVER_NAME,
        version=__version__,
        text_document_sync_kind=lsp.TextDocumentSyncKind.Incremental,
    )

    @server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
    def _did_open(params: lsp.DidOpenTextDocumentParams) -> None:
        _publish(server, params.text_document.uri, params.text_document.text)

    @server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
    def _did_change(params: lsp.DidChangeTextDocumentParams) -> None:
        text = server.workspace.get_text_document(params.text_document.uri).source
        _publish(server, params.text_document.uri, text)

    @server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
    def _did_save(params: lsp.DidSaveTextDocumentParams) -> None:
        text = server.workspace.get_text_document(params.text_document.uri).source
        _publish(server, params.text_document.uri, text)

    return server


def run_stdio() -> None:
    """Run the server over stdio. Called by ``ctx lsp``."""
    server = build_server()
    server.start_io()


def _publish(server: LanguageServer, uri: str, text: str) -> None:
    """Parse + lint the document and publish the resulting diagnostics.

    A parse error short-circuits the lint step: we publish only the
    parse diagnostic so the user fixes the structural problem first
    before semantic rules are evaluated against half-broken AST.
    """
    diagnostics = list(_compute(uri, text))
    server.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(uri=uri, diagnostics=diagnostics)
    )


def _compute(uri: str, text: str) -> list[lsp.Diagnostic]:
    """Run the parsers/analyzers for ``uri`` and return LSP diagnostics."""
    parser = _select_parser(uri)
    if parser is None:
        return []
    try:
        doc = parser(text, uri)
    except ContextOSParseError as exc:
        return [to_lsp_diagnostic(_parse_error_as_diagnostic(exc))]
    return [to_lsp_diagnostic(d) for d in lint_document(doc, source=uri)]


_Parser = Callable[[str, str], "Document"]


def _select_parser(uri: str) -> _Parser | None:
    """Pick the parser based on the URI shape.

    Returns a callable ``(text, source_label) -> Document`` or ``None``
    if the file isn't a ContextOS surface. The two surfaces today are
    ``*.ctx`` (routes through the unified ``.ctx`` parser, which itself
    dispatches by ``artifacts`` family) and ``SKILL.md`` (YAML frontmatter
    + body).
    """
    lowered = uri.lower()
    if lowered.endswith(".ctx"):
        return _parse_ctx
    if lowered.endswith("/skill.md") or lowered.endswith("skill.md"):
        return _parse_skill
    return None


def _parse_ctx(text: str, source: str) -> Document:
    return parse_ctx_string(text, source=source)


def _parse_skill(text: str, source: str) -> Document:
    return parse_skill_string(text, source=source)


def _parse_error_as_diagnostic(exc: ContextOSParseError) -> Diagnostic:
    """Wrap a parse error in a Diagnostic so the LSP adapter handles it.

    Parse errors don't carry an analyzer code — we synthesize ``E0001``
    so editors can filter on it the same way they filter A001 / R001 /
    etc. The message includes the original suggestion when present.
    """
    position = exc.position or Position(file=exc.source, line=1, column=1)
    message = exc.message
    if exc.suggestion:
        message = f"{message}\n\nhelp: {exc.suggestion}"
    return Diagnostic(
        code="E0001",
        severity=DiagSeverity.ERROR,
        message=message,
        position=position,
        suggestion=exc.suggestion,
    )


__all__ = ["build_server", "run_stdio"]
