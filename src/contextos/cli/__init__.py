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

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any

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
from contextos.audit.renderer_html import render_audit_html
from contextos.diagnostics import render_cli_many, render_json_many
from contextos.diff import diff_documents, render_diff_cli, render_diff_json
from contextos.emitters import (
    emit_claude_markdown,
    emit_clinerules,
    emit_codex_markdown,
    emit_copilot_instructions,
    emit_cursor_mdc,
    emit_rag_manifest,
    emit_skill_markdown,
    emit_windsurfrules,
)
from contextos.parsers import (
    SUPPORTED_TARGETS,
    ContextOSParseError,
    dump_ctx_string,
    parse_ctx_file,
    parse_markdown_file,
    parse_skill_file,
)
from contextos.stats import compute_stats, render_stats_cli, render_stats_json

app = typer.Typer(
    name="ctx",
    help="ContextOS — the operating system for LLM context.",
    no_args_is_help=True,
    add_completion=False,
)

# Compilation targets supported by `ctx compile`. Phase 3 wired the agent
# fleet (claude_code / codex / cursor / copilot / cline / windsurf);
# Phase 5.5 added the anthropic_skill target for SKILL.md;
# Phase 6.5 adds the rag_manifest target for rag.manifest.json.
_COMPILE_TARGETS = (
    "claude_code",
    "codex",
    "cursor",
    "copilot",
    "cline",
    "windsurf",
    "anthropic_skill",
    "rag_manifest",
)
_TARGET_FILENAMES: dict[str, str] = {
    "claude_code": "CLAUDE.md",
    "codex": "AGENTS.md",
    "cursor": ".cursor/rules/agent.mdc",
    "copilot": ".github/copilot-instructions.md",
    "cline": ".clinerules",
    "windsurf": ".windsurfrules",
    "anthropic_skill": "SKILL.md",
    "rag_manifest": "rag.manifest.json",
}

_SKILL_TARGET = "anthropic_skill"
"""Target name used by parse/lint/compile when the source is a SKILL.md.

Kept as a constant so the CLI surface, the audit scanner, and the
stats aggregator all agree on the wire-name and the user-facing
``--target`` value match. The string mirrors SPEC.md §1.3's
``anthropic_skills`` target id (singular here because each invocation
operates on a single SKILL.md, not a directory of skills).
"""


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
AuditHtml = Annotated[
    bool,
    typer.Option(
        "--html",
        help=(
            "Render a self-contained HTML report with severity filters. "
            "Pair with --output to write to a file."
        ),
    ),
]
AuditNoColor = Annotated[
    bool, typer.Option("--no-color", help="Disable ANSI colors in CLI output.")
]
AuditOutput = Annotated[
    Path | None,
    typer.Option(
        "--output",
        "-o",
        help="Write the rendered report to this path instead of stdout.",
    ),
]


@app.command()
def audit(
    root: AuditRoot,
    json_output: AuditJson = False,
    html_output: AuditHtml = False,
    output: AuditOutput = None,
    no_color: AuditNoColor = False,
) -> None:
    """Walk a repo, parse every recognized agent file, run all analyzers.

    Reports per-file diagnostics and cross-artifact rules (XA*** today).
    Files matching a recognized agent target but without a parser yet
    (cursor / cline / windsurf / copilot) are listed under "Skipped".
    Exit code 1 if any error-severity diagnostic fires.

    Output modes:

    - default: rustc-style text on stdout.
    - ``--json``: structured payload for CI pipelines.
    - ``--html``: self-contained HTML page with severity filters,
      well-suited for archiving as a PR artifact or pasting into a
      ``<details>`` block in a sticky comment.
    """
    if json_output and html_output:
        typer.echo("--json and --html are mutually exclusive", err=True)
        raise typer.Exit(code=1)

    project = scan_repo(root)
    report = audit_project(project)

    rendered: str
    if json_output:
        rendered = render_audit_json(report, indent=2)
    elif html_output:
        rendered = render_audit_html(report)
    else:
        rendered = render_audit_cli(report, color=not no_color)

    _emit_payload(rendered, output=output)

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
StatsTopN = Annotated[int, typer.Option("--top", help="Number of top diagnostic codes to surface.")]


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


@app.command(name="lsp")
def lsp_cmd() -> None:
    """Run the ContextOS language server over stdio.

    Requires the ``lsp`` extras (``pipx install context-os[lsp]``).
    Phase 7.1 ships stdio transport only — TCP / WebSocket lands later
    if downstream editors need it. The server is consumed by the
    ``contextos-vscode`` extension shipped in Phase 7.4, or by any
    LSP-aware editor (Neovim ``lspconfig``, Helix, Sublime LSP, …).
    """
    try:
        from contextos.lsp import run_stdio  # noqa: PLC0415 — lazy by design
    except ImportError as exc:  # pragma: no cover — guarded import
        typer.echo(
            "ctx lsp requires the 'lsp' extras: `pip install context-os[lsp]`",
            err=True,
        )
        raise typer.Exit(code=1) from exc
    run_stdio()


def _dispatch_parse(file: Path, *, target: str | None) -> Document:
    """Pick the right parser based on file extension and explicit target.

    Dispatch order:

    1. ``.ctx`` → :func:`parse_ctx_file` regardless of ``--target``.
    2. ``--target anthropic_skill`` OR basename ``SKILL.md`` →
       :func:`parse_skill_file`.
    3. Otherwise an explicit ``--target`` is required for the agent
       Markdown parser; missing ``--target`` raises a parse error with
       the supported-target list.
    """
    if file.suffix.lower() == ".ctx":
        return parse_ctx_file(file)
    if target == _SKILL_TARGET or (target is None and file.name == "SKILL.md"):
        return parse_skill_file(file)
    if target is None:
        raise ContextOSParseError(
            f"--target is required for non-.ctx sources (got {file.name})",
            source=str(file),
            suggestion=(
                f"add --target one of: {', '.join((*SUPPORTED_TARGETS, _SKILL_TARGET))}"
            ),
        )
    return parse_markdown_file(file, target=target)


_EMITTERS: dict[str, Callable[[Document], str]] = {
    "claude_code": emit_claude_markdown,
    "codex": emit_codex_markdown,
    "cursor": emit_cursor_mdc,
    "copilot": emit_copilot_instructions,
    "cline": emit_clinerules,
    "windsurf": emit_windsurfrules,
    "anthropic_skill": emit_skill_markdown,
    "rag_manifest": emit_rag_manifest,
}


def _render_for_target(doc: Document, *, target: str) -> str:
    """Dispatch to the emitter for the requested target."""
    emitter = _EMITTERS.get(target)
    if emitter is None:
        # Guarded upstream by _COMPILE_TARGETS; safety net for the future.
        msg = f"no emitter wired for target '{target}'"
        raise RuntimeError(msg)
    return emitter(doc)


def _emit_payload(payload: str, *, output: Path | None) -> None:
    """Write ``payload`` to ``output`` if set, otherwise stdout."""
    if output is None:
        typer.echo(payload)
        return
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(payload, encoding="utf-8")
    typer.echo(f"wrote {output}")


# --- ctx eval ---------------------------------------------------------------

_EVAL_SUITE_HELP = "Eval suite to run (``.eval.toml``)."
_EVAL_DRY_RUN_HELP = (
    "Use a mock provider that returns the expected answer for every case. "
    "Validates suite parsing + wiring without spending tokens or hitting "
    "an API. Every case passes by construction."
)
_EVAL_SKILLS_DIR_HELP = (
    "Directory containing SKILL.md files (recursive walk). Required for "
    "skill suites; ignored for rag suites."
)
_EVAL_RAG_CHUNKS_HELP = (
    "JSON file with pre-indexed chunks (list of {source, vector, content?}). "
    "Required for rag suites running against a real embedding provider; "
    "ignored in --dry-run."
)
_EVAL_RAG_EMBED_MODEL_HELP = (
    "OpenAI embedding model for the query side. Default: "
    "text-embedding-3-large. Must match the model that produced the "
    "chunks' vectors."
)

EvalSuiteFile = Annotated[
    Path,
    typer.Argument(exists=True, dir_okay=False, readable=True, help=_EVAL_SUITE_HELP),
]
EvalDryRun = Annotated[bool, typer.Option("--dry-run", help=_EVAL_DRY_RUN_HELP)]
EvalJson = Annotated[
    bool,
    typer.Option("--json", help="Emit JSON instead of human-readable text."),
]
EvalHtml = Annotated[
    bool,
    typer.Option(
        "--html",
        help=(
            "Render a self-contained HTML report. Pair with --output to "
            "write to a file."
        ),
    ),
]
EvalOutput = Annotated[
    Path | None,
    typer.Option("--output", "-o", help="Write the rendered output to this path."),
]
EvalSkillsDir = Annotated[
    Path | None,
    typer.Option("--skills-dir", help=_EVAL_SKILLS_DIR_HELP),
]
EvalRagChunks = Annotated[
    Path | None,
    typer.Option("--rag-chunks", help=_EVAL_RAG_CHUNKS_HELP),
]
EvalRagEmbedModel = Annotated[
    str,
    typer.Option("--rag-embed-model", help=_EVAL_RAG_EMBED_MODEL_HELP),
]


@app.command(name="eval")
def eval_cmd(
    suite_file: EvalSuiteFile,
    dry_run: EvalDryRun = False,
    json_output: EvalJson = False,
    html_output: EvalHtml = False,
    output: EvalOutput = None,
    skills_dir: EvalSkillsDir = None,
    rag_chunks: EvalRagChunks = None,
    rag_embed_model: EvalRagEmbedModel = "text-embedding-3-large",
) -> None:
    """Run a ``.eval.toml`` suite against a real (or mock) provider.

    Behavior is dispatched by ``suite.target``:

    - ``anthropic_skill`` — invokes the model via the Anthropic SDK
      with the loaded skills attached as tools. Requires the ``[eval]``
      extras and ``ANTHROPIC_API_KEY``. ``--skills-dir`` points at a
      directory of ``SKILL.md`` files (walked recursively).
    - ``rag`` — embeds the query via OpenAI, ranks the pre-indexed
      chunks by cosine similarity, checks if any expected source is
      in the top_k. Requires ``OPENAI_API_KEY`` and a chunks file
      passed via ``--rag-chunks``.

    ``--dry-run`` bypasses both real providers and uses an internal
    Mock that returns the expected answer for every case — useful to
    smoke-test the suite shape and the runner wiring without
    spending API budget.

    Exit code:

    - 0 — every case passed.
    - 1 — at least one case failed or the run errored before
      starting (missing skills dir, malformed chunks, etc).
    """
    from contextos.eval import (  # noqa: PLC0415 — lazy by design
        EvalRunResult,
        RagEvalRunner,
        SkillEvalRunner,
    )
    from contextos.eval.cli_helpers import (  # noqa: PLC0415 — lazy by design
        build_dry_run_rag_provider,
        build_dry_run_skill_provider,
        build_openai_embed_query,
        load_chunks,
        load_skills_from_dir,
    )
    from contextos.eval.renderer import (  # noqa: PLC0415 — lazy by design
        render_eval_cli,
        render_eval_json,
    )
    from contextos.eval.renderer_html import (  # noqa: PLC0415 — lazy by design
        render_eval_html,
    )
    from contextos.parsers import parse_eval_file  # noqa: PLC0415 — heavy imports near use

    if json_output and html_output:
        typer.echo("--json and --html are mutually exclusive", err=True)
        raise typer.Exit(code=1)

    try:
        suite = parse_eval_file(suite_file)
    except ContextOSParseError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    result: EvalRunResult
    if suite.target == "anthropic_skill":
        result = _run_skill_eval(
            suite=suite,
            dry_run=dry_run,
            skills_dir=skills_dir,
            build_dry_run=build_dry_run_skill_provider,
            load_skills=load_skills_from_dir,
            runner_cls=SkillEvalRunner,
        )
    elif suite.target == "rag":
        result = _run_rag_eval(
            suite=suite,
            dry_run=dry_run,
            rag_chunks=rag_chunks,
            rag_embed_model=rag_embed_model,
            build_dry_run=build_dry_run_rag_provider,
            load_chunks_fn=load_chunks,
            build_embed=build_openai_embed_query,
            runner_cls=RagEvalRunner,
        )
    else:  # pragma: no cover — Pydantic literal rejects others upstream
        typer.echo(f"unsupported suite target: {suite.target}", err=True)
        raise typer.Exit(code=1)

    if json_output:
        rendered = render_eval_json(result)
    elif html_output:
        rendered = render_eval_html(result)
    else:
        rendered = render_eval_cli(result)
    _emit_payload(rendered, output=output)

    if result.fail_count > 0:
        raise typer.Exit(code=1)


def _run_skill_eval(
    *,
    suite: Any,
    dry_run: bool,
    skills_dir: Path | None,
    build_dry_run: Any,
    load_skills: Any,
    runner_cls: Any,
) -> Any:
    """Dispatch a skill eval to the right provider + runner.

    Kept out of ``eval_cmd`` so the command body stays under the
    Typer / ruff complexity ceiling. ``Any`` typing is the price of
    the lazy imports — the call sites validate shapes.
    """
    if dry_run:
        provider = build_dry_run(suite)
        skills: list[Any] = []
    else:
        if skills_dir is None:
            typer.echo(
                "skill eval needs --skills-dir <path>; pass --dry-run to skip "
                "the live provider.",
                err=True,
            )
            raise typer.Exit(code=1)
        try:
            from contextos.eval.anthropic_provider import (  # noqa: PLC0415 — lazy
                AnthropicSkillProvider,
            )
        except ImportError as exc:  # pragma: no cover
            typer.echo(
                "ctx eval (live) requires the 'eval' extras: `pip install context-os[eval]`",
                err=True,
            )
            raise typer.Exit(code=1) from exc
        provider = AnthropicSkillProvider()
        skills = load_skills(skills_dir)
    return runner_cls(provider).run(suite, skills)


def _run_rag_eval(
    *,
    suite: Any,
    dry_run: bool,
    rag_chunks: Path | None,
    rag_embed_model: str,
    build_dry_run: Any,
    load_chunks_fn: Any,
    build_embed: Any,
    runner_cls: Any,
) -> Any:
    """Dispatch a rag eval to the right provider + runner."""
    if dry_run:
        provider = build_dry_run(suite)
    else:
        if rag_chunks is None:
            typer.echo(
                "rag eval needs --rag-chunks <path>; pass --dry-run to skip "
                "the live provider.",
                err=True,
            )
            raise typer.Exit(code=1)
        try:
            from contextos.eval.embedding_provider import (  # noqa: PLC0415 — lazy
                EmbeddingRagProvider,
            )
        except ImportError as exc:  # pragma: no cover
            typer.echo(
                "ctx eval (live rag) requires the 'eval' extras: "
                "`pip install context-os[eval]`",
                err=True,
            )
            raise typer.Exit(code=1) from exc
        chunks = load_chunks_fn(rag_chunks)
        embed = build_embed(rag_embed_model)
        provider = EmbeddingRagProvider(chunks=chunks, embed_query=embed)
    return runner_cls(provider).run(suite)


# --- ctx eval-diff ---------------------------------------------------------

_DIFF_BASELINE_HELP = "Baseline eval result JSON (typically committed alongside the suite)."
_DIFF_CURRENT_HELP = "Current eval result JSON (from a fresh ctx eval --json --output run)."
_DIFF_FAIL_ON_NEW_HELP = (
    "Exit non-zero when the current run added cases that fail. Default is "
    "'false' so newly-introduced failing cases do not block a PR until a "
    "second run validates the regression — but real regressions "
    "(case passed in baseline, fails now) always block regardless."
)

EdiffBaseline = Annotated[
    Path,
    typer.Argument(exists=True, dir_okay=False, readable=True, help=_DIFF_BASELINE_HELP),
]
EdiffCurrent = Annotated[
    Path,
    typer.Argument(exists=True, dir_okay=False, readable=True, help=_DIFF_CURRENT_HELP),
]
EdiffJson = Annotated[
    bool,
    typer.Option("--json", help="Emit JSON instead of human-readable text."),
]
EdiffOutput = Annotated[
    Path | None,
    typer.Option("--output", "-o", help="Write the rendered output to this path."),
]
EdiffFailOnNew = Annotated[
    bool,
    typer.Option("--fail-on-new-failure", help=_DIFF_FAIL_ON_NEW_HELP),
]


@app.command(name="eval-diff")
def eval_diff_cmd(
    baseline: EdiffBaseline,
    current: EdiffCurrent,
    json_output: EdiffJson = False,
    output: EdiffOutput = None,
    fail_on_new_failure: EdiffFailOnNew = False,
) -> None:
    """Compare two ``ctx eval --json`` outputs to detect regressions.

    Cases are matched by ``case_name`` between baseline and current.
    Each transition is classified into one of five buckets:

    - **regression** — was passing in baseline, fails now.
    - **improvement** — was failing in baseline, passes now.
    - **new_failure** — case is new in the current run + failing.
    - **new_pass** — case is new in the current run + passing.
    - **removed** — case was in baseline, gone from current.

    Exit code semantics:

    - 0 — no regressions (and no new failures if --fail-on-new-failure).
    - 1 — at least one regression, or a new failure when the flag is set.

    Typical CI flow:

    .. code-block:: yaml

       - run: ctx eval suite.eval.toml --json --output current.json
       - run: ctx eval-diff baseline.json current.json
    """
    from contextos.eval.diff import (  # noqa: PLC0415 — keep heavy imports near use
        compute_eval_diff,
        render_diff_cli,
        render_diff_json,
    )
    from contextos.eval.results import EvalRunResult  # noqa: PLC0415

    try:
        baseline_run = EvalRunResult.model_validate_json(
            baseline.read_text(encoding="utf-8")
        )
        current_run = EvalRunResult.model_validate_json(
            current.read_text(encoding="utf-8")
        )
    except Exception as exc:
        typer.echo(f"failed to parse eval result JSON: {exc}", err=True)
        raise typer.Exit(code=1) from exc

    diff = compute_eval_diff(baseline_run, current_run)
    rendered = render_diff_json(diff) if json_output else render_diff_cli(diff)
    _emit_payload(rendered, output=output)

    if diff.has_regressions():
        raise typer.Exit(code=1)
    if fail_on_new_failure and diff.has_new_failures():
        raise typer.Exit(code=1)


# --- ctx fix ---------------------------------------------------------------

_FIX_TARGET_HELP = (
    "File or directory to fix. Directories are walked the same way "
    "``ctx audit`` walks them (CLAUDE.md / AGENTS.md / SKILL.md / *.ctx)."
)
_FIX_APPLY_HELP = (
    "Write the fixed content back to disk. Without this flag, ``ctx fix`` "
    "prints a diff and leaves files untouched."
)

FixTarget = Annotated[
    Path,
    typer.Argument(exists=True, readable=True, help=_FIX_TARGET_HELP),
]
FixApply = Annotated[bool, typer.Option("--apply", help=_FIX_APPLY_HELP)]


@app.command(name="fix")
def fix_cmd(
    target: FixTarget,
    apply: FixApply = False,
) -> None:
    """Apply structured fixes for the four supported diagnostic codes.

    Supported fixes today: ``X003`` (drop trailing ``?`` from a rule
    title), ``F001`` (sentence-case an ALL CAPS title), ``X001``
    (strip ``TODO`` / ``FIXME`` / ``XXX`` / ``HACK`` markers at the
    start of a title), ``S005`` (prepend ``# <title>`` to a SKILL.md
    body that lacks an H1).

    Default behavior is ``--dry-run``: the command prints a unified
    diff of what would change and exits 0. Pass ``--apply`` to write
    the fixes back to disk.
    """
    import difflib  # noqa: PLC0415

    from contextos.fix import fix_path  # noqa: PLC0415

    try:
        results = fix_path(target)
    except ValueError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc

    changed = [r for r in results if r.changed()]
    if not changed:
        typer.echo("no fixable diagnostics found")
        raise typer.Exit(code=0)

    for result in changed:
        codes = ", ".join(sorted(set(result.applied_codes)))
        typer.echo(f"--- {result.path} ({codes})")
        if apply:
            result.path.write_text(result.new_text, encoding="utf-8")
            typer.echo(f"wrote {result.path}")
        else:
            diff = difflib.unified_diff(
                result.original_text.splitlines(keepends=True),
                result.new_text.splitlines(keepends=True),
                fromfile=str(result.path),
                tofile=f"{result.path} (fixed)",
            )
            typer.echo("".join(diff))

    if apply:
        typer.echo(f"applied fixes to {len(changed)} file(s)")
    else:
        typer.echo(
            f"dry-run: {len(changed)} file(s) would change. Re-run with --apply."
        )
