"""Filesystem walker — finds every recognized context artifact under a root.

Phase 3 covered the agent family (CLAUDE.md / AGENTS.md plus the four
emit-only formats listed under :data:`_SKIPPED_BASENAMES`). Phase 5.5
adds the skill family — any file named ``SKILL.md`` is parsed via the
skill parser and stored as a :class:`SkillFile`.
"""

from __future__ import annotations

from pathlib import Path

from contextos.audit.project import (
    AgentFile,
    ProjectInferred,
    RagFile,
    SkillFile,
    SkippedFile,
)
from contextos.parsers import (
    ContextOSParseError,
    parse_ctx_file,
    parse_markdown_file,
    parse_skill_file,
)

# Map basename (relative to repo root) -> (target name, parser available)
# `.github/copilot-instructions.md` is matched by suffix because the
# `.github/` prefix is a path segment, not a basename.
_PARSEABLE_BASENAMES: dict[str, str] = {
    "CLAUDE.md": "claude_code",
    "AGENTS.md": "codex",
}
_PARSEABLE_SKILL_BASENAMES: dict[str, str] = {
    "SKILL.md": "anthropic_skill",
}
_SKIPPED_BASENAMES: dict[str, str] = {
    ".cursorrules": "cursor",
    ".clinerules": "cline",
    ".windsurfrules": "windsurf",
}
_SKIPPED_RELATIVE_PATHS: dict[str, str] = {
    ".github/copilot-instructions.md": "copilot",
}

# Directories the scanner never descends into. Keeping the list small
# avoids fighting users' build / VCS conventions — the burden is on the
# user to use `--exclude` (future) for project-specific opt-outs.
_SKIP_DIRS = frozenset({".git", ".venv", "venv", "node_modules", "__pycache__", "dist", "build"})


def scan_repo(root: Path) -> ProjectInferred:
    """Walk ``root`` recursively and parse every recognized artifact.

    Returns a :class:`ProjectInferred` carrying four buckets the audit
    cares about: agent files, skill files, rag files, and skipped
    files (recognized but unparseable). ``.ctx`` files are dispatched
    by their declared ``artifacts`` family so a corpus-level audit can
    cover agents, skills, and RAG configs in one pass.
    """
    root = root.resolve()
    agent_files: list[AgentFile] = []
    skill_files: list[SkillFile] = []
    rag_files: list[RagFile] = []
    skipped_files: list[SkippedFile] = []

    for path in _walk(root):
        rel = path.relative_to(root)
        rel_posix = rel.as_posix()

        agent_target = _PARSEABLE_BASENAMES.get(path.name)
        if agent_target is not None:
            agent_entry = _parse_agent(path, target=agent_target)
            if isinstance(agent_entry, AgentFile):
                agent_files.append(agent_entry)
            else:
                skipped_files.append(agent_entry)
            continue

        skill_target = _PARSEABLE_SKILL_BASENAMES.get(path.name)
        if skill_target is not None:
            skill_entry = _parse_skill(path, target=skill_target)
            if isinstance(skill_entry, SkillFile):
                skill_files.append(skill_entry)
            else:
                skipped_files.append(skill_entry)
            continue

        if path.suffix.lower() == ".ctx":
            _route_ctx_file(
                path,
                agent_files=agent_files,
                skill_files=skill_files,
                rag_files=rag_files,
                skipped_files=skipped_files,
            )
            continue

        skip_target = _SKIPPED_BASENAMES.get(path.name) or _SKIPPED_RELATIVE_PATHS.get(rel_posix)
        if skip_target is not None:
            skipped_files.append(
                SkippedFile(
                    path=path,
                    target=skip_target,
                    reason=f"no parser yet for target '{skip_target}'",
                )
            )

    return ProjectInferred(
        repo_path=root,
        agent_files=agent_files,
        skill_files=skill_files,
        rag_files=rag_files,
        skipped_files=skipped_files,
    )


def _route_ctx_file(
    path: Path,
    *,
    agent_files: list[AgentFile],
    skill_files: list[SkillFile],
    rag_files: list[RagFile],
    skipped_files: list[SkippedFile],
) -> None:
    """Parse a ``.ctx`` and route it into the right bucket by family.

    The ``.ctx`` parser already discriminates on ``artifacts``; we
    just dispatch the resulting Document into the right list and rely
    on its ``.type`` to label the target.
    """
    try:
        doc = parse_ctx_file(path)
    except ContextOSParseError as exc:
        skipped_files.append(SkippedFile(path=path, target="ctx", reason=f"parse error: {exc}"))
        return
    match doc.type:
        case "agent":
            agent_files.append(AgentFile(path=path, target="ctx_agent", document=doc))
        case "skill":
            skill_files.append(SkillFile(path=path, target="ctx_skill", document=doc))
        case "rag":
            rag_files.append(RagFile(path=path, target="rag_manifest", document=doc))


def _walk(root: Path) -> list[Path]:
    """Depth-first walk, skipping :data:`_SKIP_DIRS`. Returns a sorted list
    so two scans of the same tree produce the same audit ordering.
    """
    found: list[Path] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if any(part in _SKIP_DIRS for part in path.relative_to(root).parts):
            continue
        found.append(path)
    return found


def _parse_agent(path: Path, *, target: str) -> AgentFile | SkippedFile:
    """Attempt to parse one agent file; degrade gracefully on parse error."""
    try:
        doc = parse_markdown_file(path, target=target)
    except ContextOSParseError as exc:
        return SkippedFile(path=path, target=target, reason=f"parse error: {exc}")
    return AgentFile(path=path, target=target, document=doc)


def _parse_skill(path: Path, *, target: str) -> SkillFile | SkippedFile:
    """Attempt to parse one ``SKILL.md`` file; degrade on parse error."""
    try:
        doc = parse_skill_file(path)
    except ContextOSParseError as exc:
        return SkippedFile(path=path, target=target, reason=f"parse error: {exc}")
    return SkillFile(path=path, target=target, document=doc)
