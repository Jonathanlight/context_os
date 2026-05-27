"""Allow ``python -m contextos`` to launch the CLI.

The Typer app and its subcommands live in :mod:`contextos.cli`. This
module is the standard Python ``__main__`` shim that delegates to it, so
both ``python -m contextos`` and the installed ``ctx`` console script
share one implementation.
"""

from __future__ import annotations

from contextos.cli import app

if __name__ == "__main__":
    app()
