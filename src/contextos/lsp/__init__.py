"""LSP server for ContextOS — Phase 7.1.

Exposes :func:`run_stdio` as the CLI entry-point and
:func:`build_server` as the test seam for spinning up the server
in-process. The server itself lives in :mod:`contextos.lsp.server`
and is only imported lazily so the rest of the package stays
runnable when ``pygls`` is not installed.

Install the LSP extras to enable this surface::

    pipx install context-os[lsp]
"""

from __future__ import annotations

__all__ = ["build_server", "run_stdio"]


def build_server() -> object:
    """Construct the language server (lazy pygls import).

    Returns a configured :class:`LanguageServer` instance ready to
    serve. Kept thin so tests can grab the server, send simulated LSP
    notifications, and assert on published diagnostics without going
    through stdio.
    """
    from contextos.lsp.server import build_server as _build  # noqa: PLC0415 — lazy by design

    return _build()


def run_stdio() -> None:
    """Block on the LSP server over stdio. Called by ``ctx lsp``."""
    from contextos.lsp.server import run_stdio as _run  # noqa: PLC0415 — lazy by design

    _run()
