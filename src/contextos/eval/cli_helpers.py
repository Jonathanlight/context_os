"""Helpers for the ``ctx eval`` command — Phase 7.10.

Keeping the wiring (suite parsing, provider selection, skills /
chunks loading) out of the Typer command keeps the command body
small and the helpers individually testable.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from contextos.ast.eval import EvalSuite
from contextos.ast.skill import SkillDocument
from contextos.eval.providers import MockSkillProvider, SkillRoutingProvider
from contextos.eval.rag_providers import (
    Chunk,
    MockRagProvider,
    RagRetrievalProvider,
)
from contextos.parsers import parse_skill_file

if TYPE_CHECKING:
    from contextos.eval.embedding_provider import EmbedQueryFn


def load_skills_from_dir(skills_dir: Path) -> list[SkillDocument]:
    """Walk ``skills_dir`` recursively and parse every ``SKILL.md``.

    Returns SkillDocument instances in **sorted-path order** so two
    runs against the same directory pick up the same skill registry,
    in the same order — important for deterministic provider behavior
    (the model sees tools in the same order each run).
    """
    skills: list[SkillDocument] = []
    for path in sorted(skills_dir.rglob("SKILL.md")):
        doc = parse_skill_file(path)
        if doc.skill is not None:
            skills.append(doc.skill)
    return skills


def load_chunks(chunks_path: Path) -> list[Chunk]:
    """Load pre-indexed chunks from a JSON file.

    Expected shape:

    .. code-block:: json

       [
         {"source": "docs/x.md", "vector": [0.1, ...], "content": "..."},
         ...
       ]

    Raises :class:`ValueError` on malformed top-level (not a list) or
    when any entry fails the :class:`Chunk` validation — that surfaces
    as a clear "your indexer's output doesn't match the contract"
    error rather than a generic Pydantic stack trace.
    """
    data = json.loads(chunks_path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        msg = (
            f"chunks file {chunks_path} must be a JSON array; "
            f"got {type(data).__name__}"
        )
        raise ValueError(msg)
    return [Chunk.model_validate(entry) for entry in data]


def build_dry_run_skill_provider(suite: EvalSuite) -> SkillRoutingProvider:
    """Build a Mock that returns the expected answer for every prompt.

    Used by ``ctx eval --dry-run`` to validate the wiring (parser,
    runner, provider plumbing) without spending real tokens. Every
    case passes by construction — the value is purely "did the
    suite parse + can the runner walk every case without crashing."
    """
    routing_table: dict[str, str | None] = {
        case.prompt: case.expected_skill for case in suite.skill_cases
    }
    return MockSkillProvider(routing_table)


def build_dry_run_rag_provider(suite: EvalSuite) -> RagRetrievalProvider:
    """Build a Mock that returns the expected sources for every query.

    Same role as :func:`build_dry_run_skill_provider`, for the RAG flavor.
    """
    retrieval_table = {
        case.query: list(case.expected_sources) for case in suite.rag_cases
    }
    return MockRagProvider(retrieval_table)


def build_openai_embed_query(model: str = "text-embedding-3-large") -> EmbedQueryFn:
    """Construct an OpenAI-backed embedding callable.

    Lazy import — keeps the module loadable when ``[eval]`` extras
    are missing. The caller's responsibility to set
    ``OPENAI_API_KEY``; we don't read it here, the OpenAI SDK does.
    """
    from openai import OpenAI  # noqa: PLC0415 — lazy by design

    client = OpenAI()

    def embed_query(text: str) -> list[float]:
        response = client.embeddings.create(model=model, input=text)
        return list(response.data[0].embedding)

    return embed_query


__all__ = [
    "build_dry_run_rag_provider",
    "build_dry_run_skill_provider",
    "build_openai_embed_query",
    "load_chunks",
    "load_skills_from_dir",
]
