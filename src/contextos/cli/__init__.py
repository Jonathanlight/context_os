"""``ctx`` CLI — Typer entry point for ContextOS.

Subcommands shipped in Milestone 1.7:

- ``ctx parse <file>`` reads a ``.ctx`` or ``.md`` source and prints the
  AST as JSON. ``--to-ctx`` re-emits the AST as a ``.ctx`` TOML file
  (lossy round-trip for ``.md`` inputs is the price of going through the
  AST). ``--output`` redirects to a file.
- ``ctx compile <file.ctx> --target claude_code`` parses a ``.ctx`` and
  emits a ``CLAUDE.md`` via :func:`emit_claude_markdown`. ``--output-dir``
  writes the file; without it the Markdown goes to stdout. ``--dry-run``
  shows what would be written without touching the filesystem.
- ``ctx --version`` / ``ctx -V``.

Phase 1.7 keeps the CLI surface small but production-shaped: every
subcommand reports parse errors on stderr and returns exit code 1, so
shell scripts can chain ``ctx parse foo.ctx && …`` reliably.
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from contextos import __version__
from contextos.ast.document import Document
from contextos.emitters import emit_claude_markdown
from contextos.parsers import (
    SUPPORTED_TARGETS,
    ContextOSParseError,
    dump_ctx_string,
    parse_ctx_file,
    parse_markdown_file,
)

app = typer.Typer(
    name="ctx",
    help="ContextOS — the operating system for LLM context.",
    no_args_is_help=True,
    add_completion=False,
)

# Compilation targets supported by `ctx compile`. Phase 3 will widen this.
_COMPILE_TARGETS = ("claude_code",)
_TARGET_FILENAMES: dict[str, str] = {"claude_code": "CLAUDE.md"}


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"contextos {__version__}")
        raise typer.Exit


VersionFlag = Annotated[
    bool,
    typer.Option(
        "--version",
        "-V",
        callback=_version_callback,
        is_eager=True,
        help="Show ContextOS version and exit.",
    ),
]


@app.callback()
def main(version: VersionFlag = False) -> None:
    """Root callback. The ``version`` parameter is consumed by the callback."""
    _ = version


_PARSE_FILE_HELP = "Source file. ``.ctx`` is parsed directly; other suffixes need --target."
_PARSE_TARGET_HELP = (
    "Mandatory for non-``.ctx`` inputs (e.g. CLAUDE.md). "
    f"Supported: {', '.join(SUPPORTED_TARGETS)}."
)

ParseFile = Annotated[
    Path,
    typer.Argument(exists=True, dir_okay=False, readable=True, help=_PARSE_FILE_HELP),
]
ParseTarget = Annotated[str | None, typer.Option("--target", "-t", help=_PARSE_TARGET_HELP)]
ParseToCtx = Annotated[
    bool, typer.Option("--to-ctx", help="Re-emit as ``.ctx`` TOML instead of JSON.")
]
ParseOutput = Annotated[
    Path | None,
    typer.Option("--output", "-o", help="Write to this path instead of stdout."),
]


@app.command()
def parse(
    file: ParseFile,
    target: ParseTarget = None,
    to_ctx: ParseToCtx = False,
    output: ParseOutput = None,
) -> None:
    """Parse a ``.ctx`` or Markdown file and print the AST."""
    try:
        doc = _dispatch_parse(file, target=target)
    except ContextOSParseError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    rendered = dump_ctx_string(doc) if to_ctx else doc.model_dump_json(indent=2)
    _emit_payload(rendered, output=output)


_COMPILE_TARGET_HELP = f"Output target. Supported: {', '.join(_COMPILE_TARGETS)}."

CompileFile = Annotated[
    Path,
    typer.Argument(exists=True, dir_okay=False, readable=True, help="``.ctx`` source file."),
]
CompileTarget = Annotated[str, typer.Option("--target", "-t", help=_COMPILE_TARGET_HELP)]
CompileOutputDir = Annotated[
    Path | None,
    typer.Option(
        "--output-dir",
        "-o",
        help="Directory to write the target file to. Without it, stdout.",
    ),
]
CompileDryRun = Annotated[
    bool,
    typer.Option(
        "--dry-run",
        help="Show what would be written without touching the filesystem.",
    ),
]


@app.command(name="compile")
def compile_cmd(
    file: CompileFile,
    target: CompileTarget,
    output_dir: CompileOutputDir = None,
    dry_run: CompileDryRun = False,
) -> None:
    """Compile a ``.ctx`` source to a target format."""
    if target not in _COMPILE_TARGETS:
        typer.echo(
            f"unknown --target '{target}'; supported: {', '.join(_COMPILE_TARGETS)}",
            err=True,
        )
        raise typer.Exit(code=1)

    try:
        doc = parse_ctx_file(file)
    except ContextOSParseError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    rendered = _render_for_target(doc, target=target)
    target_filename = _TARGET_FILENAMES[target]

    if dry_run:
        typer.echo(f"# dry-run: would write {target_filename}")
        typer.echo("---")
        typer.echo(rendered)
        return

    if output_dir is None:
        typer.echo(rendered)
        return

    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / target_filename
    out_path.write_text(rendered, encoding="utf-8")
    typer.echo(f"wrote {out_path}")


def _dispatch_parse(file: Path, *, target: str | None) -> Document:
    """Pick the right parser based on file extension."""
    if file.suffix.lower() == ".ctx":
        return parse_ctx_file(file)
    if target is None:
        raise ContextOSParseError(
            f"--target is required for non-.ctx sources (got {file.name})",
            source=str(file),
            suggestion=f"add --target one of: {', '.join(SUPPORTED_TARGETS)}",
        )
    return parse_markdown_file(file, target=target)


def _render_for_target(doc: Document, *, target: str) -> str:
    """Dispatch to the emitter for the requested target."""
    if target == "claude_code":
        return emit_claude_markdown(doc)
    # Guarded upstream by the _COMPILE_TARGETS check; safety net for the future.
    msg = f"no emitter wired for target '{target}'"
    raise RuntimeError(msg)


def _emit_payload(payload: str, *, output: Path | None) -> None:
    """Write ``payload`` to ``output`` if set, otherwise stdout."""
    if output is None:
        typer.echo(payload)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    typer.echo(f"wrote {output}")
