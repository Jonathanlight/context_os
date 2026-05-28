"""Build a starter :class:`Document` from a project name + language list.

Used by both ``ctx create`` (manual scaffold) and ``ctx init``
(detected scaffold). The builder is pure -- no I/O, no Typer
references -- so the CLI layer can call it with either user-supplied
or detected values and serialize the result via :func:`dump_ctx_string`.
"""

from __future__ import annotations

from contextos.ast.agent import AgentDocument, Identity, Rule, Stack
from contextos.ast.common import Severity
from contextos.ast.document import Document
from contextos.scaffold.templates import (
    BASELINE_RULES,
    LANGUAGE_TEMPLATES,
    display_name,
)


def build_starter_document(
    *,
    project: str,
    languages: list[str],
    title: str | None = None,
    domain: str | None = None,
    role: str | None = None,
    extra_stack: list[str] | None = None,
) -> Document:
    """Assemble a :class:`Document` from inputs.

    :param project: project slug used for ``Document.project``.
    :param languages: list of language slugs known to :data:`LANGUAGE_TEMPLATES`
        (unknown slugs are silently ignored -- the validator further
        below catches the empty-rule-set case anyway).
    :param title: optional human-readable title. When provided, becomes
        the H1 of the compiled Markdown. When None, the project slug
        is used.
    :param domain: optional activity domain (e.g. "fintech", "health").
        When provided, populates ``identity.context`` with a short
        sentence; when None, the identity section is omitted.
    :param role: optional role label for the LLM agent (e.g. "Senior
        backend engineer"). Defaults to a generic ``"Senior software
        engineer"`` so the produced Document always has a valid
        ``[identity]`` section.
    :param extra_stack: optional ``stack.required`` items to append
        beyond what the language templates contribute.
    """
    stack_required = _merge_stack(languages, extra=extra_stack)
    rules = _merge_rules(languages)

    identity = _build_identity(
        project=project,
        languages=languages,
        domain=domain,
        role=role,
    )
    stack = Stack(required=stack_required) if stack_required else None

    agent = AgentDocument(
        identity=identity,
        stack=stack,
        rules=rules,
    )

    return Document(
        project=title or project,
        type="agent",
        languages=list(languages),
        agent=agent,
    )


def _merge_stack(
    languages: list[str],
    *,
    extra: list[str] | None,
) -> list[str]:
    """Concatenate ``stack.required`` entries from every selected language.

    Deduplicates while preserving the order of first appearance so the
    emitted ``CLAUDE.md`` reads predictably.
    """
    seen: dict[str, None] = {}
    for slug in languages:
        entry = LANGUAGE_TEMPLATES.get(slug)
        if entry is None:
            continue
        for item in entry["stack_required"]:
            seen.setdefault(item, None)
    if extra is not None:
        for item in extra:
            seen.setdefault(item, None)
    return list(seen)


def _merge_rules(languages: list[str]) -> list[Rule]:
    """Concatenate baseline + language-template rules; dedup by id.

    Baseline rules come first so reviewers see the universal rules
    at the top. Then per-language rules in the order the user listed
    the languages (which usually puts the dominant stack first).
    """
    raw_rules: list[dict[str, object]] = list(BASELINE_RULES)
    for slug in languages:
        entry = LANGUAGE_TEMPLATES.get(slug)
        if entry is None:
            continue
        raw_rules.extend(entry["rules"])

    seen_ids: set[str] = set()
    rules: list[Rule] = []
    for raw in raw_rules:
        rule_id = str(raw["id"])
        if rule_id in seen_ids:
            continue
        seen_ids.add(rule_id)
        rules.append(_rule_from_dict(raw))
    return rules


def _rule_from_dict(raw: dict[str, object]) -> Rule:
    """Convert a template dict into a :class:`Rule`.

    Severity strings come straight from the template; we map to the
    :class:`Severity` enum so invalid values surface as a Pydantic
    validation error rather than producing a silently-wrong AST.
    """
    severity = Severity(str(raw["severity"]))
    return Rule(
        id=str(raw["id"]),
        title=str(raw["title"]),
        severity=severity,
        rationale=_opt_str(raw.get("rationale")),
        example_good=_opt_str(raw.get("example_good")),
        example_bad=_opt_str(raw.get("example_bad")),
    )


def _opt_str(value: object) -> str | None:
    """Coerce a possibly-missing template field to ``str | None``.

    The template dicts are typed as ``dict[str, Any]`` so reviewers can
    read them at a glance; this guard keeps the AST type-safe without
    sprinkling ``cast(str, …)`` calls through the builder.
    """
    if value is None:
        return None
    return str(value)


_DEFAULT_ROLE = "Senior software engineer"


def _build_identity(
    *,
    project: str,
    languages: list[str],
    domain: str | None,
    role: str | None,
) -> Identity:
    """Compose the agent's ``[identity]`` section.

    Always returns an Identity: the AST requires a ``role`` and an
    empty identity section in CLAUDE.md is the single biggest "useless
    scaffold" complaint reviewers raise. We default ``role`` to a
    generic senior-engineer label that's easy to refine, and skip the
    ``context`` sentence when there's nothing concrete to say
    (no domain, no languages).
    """
    chosen_role = role or _DEFAULT_ROLE

    names = [display_name(slug) for slug in languages]
    stack_phrase = " / ".join(names) if names else None

    if domain and stack_phrase:
        context: str | None = f"{project} is a {domain} project written in {stack_phrase}."
    elif domain:
        context = f"{project} is a {domain} project."
    elif stack_phrase:
        context = f"{project} is written in {stack_phrase}."
    else:
        context = None

    return Identity(role=chosen_role, context=context)


__all__ = ["build_starter_document"]
