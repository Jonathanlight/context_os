"""Entry point for the `ctx` CLI.

The CLI is a thin Typer wrapper. Subcommands land in Phase 1 (parse, compile,
lint, diff, audit, new). For now only `--version` is exposed so that
`ctx --version` works after installation, and the package can be smoke-tested
through `python -m contextos`.
"""

from __future__ import annotations

import typer

from contextos import __version__

app = typer.Typer(
    name="ctx",
    help="ContextOS — the operating system for LLM context.",
    no_args_is_help=True,
    add_completion=False,
)


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"contextos {__version__}")
        raise typer.Exit


@app.callback()
def main(
    version: bool = typer.Option(  # noqa: ARG001 - bound by callback
        False,
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show ContextOS version and exit.",
    ),
) -> None:
    """Root callback. Subcommands land in Phase 1."""


if __name__ == "__main__":
    app()
