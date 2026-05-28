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
from contextos.analyzers import lint_document
from contextos.ast.document import Document
from contextos.audit import (
    audit_project,
    render_audit_cli,
    render_audit_json,
    scan_repo,
)
from contextos.diagnostics import render_cli_many, render_json_many
from contextos.diff import diff_documents, render_diff_cli, render_diff_json
from contextos.stats import compute_stats, render_stats_cli, render_stats_json
from contextos.emitters import (
    emit_claude_markdown,
    emit_clinerules,
    emit_codex_markdown,
    emit_copilot_instructions,
    emit_cursor_mdc,
    emit_windsurfrules,
)
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

# Compilation targets supported by `ctx compile`. Phase 3 wires the full
# agent fleet: codex (AGENTS.md), cursor (.cursor/rules/*.mdc), and the
# three flat-Markdown targets copilot / cline / windsurf.
_COMPILE_TARGETS = (
    "claude_code",
    "codex",
    "cursor",
    "copilot",
    "cline",
    "windsurf",
)
_TARGET_FILENAMES: dict[str, str] = {
    "claude_code": "CLAUDE.md",
    "codex": "AGENTS.md",
    "cursor": ".cursor/rules/agent.mdc",
    "copilot": ".github/copilot-instructions.md",
    "cline": ".clinerules",
    "windsurf": ".windsurfrules",
}


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


_LINT_FILE_HELP = "Source file. ``.ctx`` is parsed directly; other suffixes need --target."
_LINT_TARGET_HELP = (
    f"Required for non-``.ctx`` inputs (e.g. CLAUDE.md). Supported: {', '.join(SUPPORTED_TARGETS)}."
)

LintFile = Annotated[
    Path,
    typer.Argument(exists=True, dir_okay=False, readable=True, help=_LINT_FILE_HELP),
]
LintTarget = Annotated[str | None, typer.Option("--target", "-t", help=_LINT_TARGET_HELP)]
LintJson = Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON.")]
LintNoColor = Annotated[bool, typer.Option("--no-color", help="Disable ANSI colors in CLI output.")]


@app.command()
def lint(
    file: LintFile,
    target: LintTarget = None,
    json_output: LintJson = False,
    no_color: LintNoColor = False,
) -> None:
    """Lint a ``.ctx`` or Markdown context file and report diagnostics."""
    try:
        doc = _dispatch_parse(file, target=target)
    except ContextOSParseError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    bag = lint_document(doc, source=str(file))

    if json_output:
        typer.echo(render_json_many(bag, indent=2))
    elif not bag:
        typer.echo("no diagnostics")
    else:
        typer.echo(render_cli_many(bag, color=not no_color))

    raise typer.Exit(code=1 if bag.has_errors() else 0)


_DIFF_FILE_HELP = "Source file (``.ctx`` or Markdown with --target)."
_DIFF_TARGET_HELP = (
    "Markdown source target — both files must use the same target. "
    f"Supported: {', '.join(SUPPORTED_TARGETS)}."
)

DiffFileA = Annotated[
    Path,
    typer.Argument(exists=True, dir_okay=False, readable=True, help=_DIFF_FILE_HELP),
]
DiffFileB = Annotated[
    Path,
    typer.Argument(exists=True, dir_okay=False, readable=True, help=_DIFF_FILE_HELP),
]
DiffTarget = Annotated[str | None, typer.Option("--target", "-t", help=_DIFF_TARGET_HELP)]
DiffJson = Annotated[bool, typer.Option("--json", help="Emit JSON instead of text.")]


@app.command()
def diff(
    file_a: DiffFileA,
    file_b: DiffFileB,
    target: DiffTarget = None,
    json_output: DiffJson = False,
) -> None:
    """Diff two context Documents at the AST level."""
    try:
        doc_a = _dispatch_parse(file_a, target=target)
        doc_b = _dispatch_parse(file_b, target=target)
    except ContextOSParseError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    structured = diff_documents(doc_a, doc_b)
    if json_output:
        typer.echo(render_diff_json(structured, indent=2))
    else:
        typer.echo(render_diff_cli(structured))


AuditRoot = Annotated[
    Path,
    typer.Argument(
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Repository root to scan recursively for agent context files.",
    ),
]
AuditJson = Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON.")]
AuditNoColor = Annotated[
    bool, typer.Option("--no-color", help="Disable ANSI colors in CLI output.")
]


@app.command()
def audit(
    root: AuditRoot,
    json_output: AuditJson = False,
    no_color: AuditNoColor = False,
) -> None:
    """Walk a repo, parse every recognized agent file, run all analyzers.

    Reports per-file diagnostics and cross-artifact rules (XA*** today).
    Files matching a recognized agent target but without a parser yet
    (cursor / cline / windsurf / copilot) are listed under "Skipped".
    Exit code 1 if any error-severity diagnostic fires.
    """
    project = scan_repo(root)
    report = audit_project(project)

    if json_output:
        typer.echo(render_audit_json(report, indent=2))
    else:
        typer.echo(render_audit_cli(report, color=not no_color))

    raise typer.Exit(code=1 if report.has_errors() else 0)


StatsRoot = Annotated[
    Path,
    typer.Argument(
        exists=True,
        file_okay=False,
        dir_okay=True,
        readable=True,
        help="Repository root to scan + aggregate stats from.",
    ),
]
StatsJson = Annotated[bool, typer.Option("--json", help="Emit machine-readable JSON.")]
StatsTopN = Annotated[
    int, typer.Option("--top", help="Number of top diagnostic codes to surface.")
]


@app.command()
def stats(
    root: StatsRoot,
    json_output: StatsJson = False,
    top: StatsTopN = 10,
) -> None:
    """Aggregate corpus-wide statistics from an audit run.

    Walks the repo (same scanner as ``ctx audit``), runs analyzers, then
    rolls the result into a :class:`CorpusStats` — per-severity counts,
    top diagnostic codes, rule counts per file, target coverage. Useful
    for surveying a fleet of context files at a glance.
    """
    project = scan_repo(root)
    report = audit_project(project)
    summary = compute_stats(report, top_n=top)

    if json_output:
        typer.echo(render_stats_json(summary, indent=2))
    else:
        typer.echo(render_stats_cli(summary))


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

    out_path = output_dir / target_filename
    # Some targets ship nested filenames (`.cursor/rules/agent.mdc`,
    # `.github/copilot-instructions.md`); create the full parent chain
    # rather than just the bare output_dir.
    out_path.parent.mkdir(parents=True, exist_ok=True)
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
    if target == "codex":
        return emit_codex_markdown(doc)
    if target == "cursor":
        return emit_cursor_mdc(doc)
    if target == "copilot":
        return emit_copilot_instructions(doc)
    if target == "cline":
        return emit_clinerules(doc)
    if target == "windsurf":
        return emit_windsurfrules(doc)
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
