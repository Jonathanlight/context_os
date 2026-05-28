"""``SKILL.md`` emitter — :class:`Document` → Markdown for the skill family.

Phase 5.3 ships the inverse of the Phase 5.2 parser: a function that
takes a :class:`Document` whose ``type='skill'`` and produces the
canonical ``SKILL.md`` source — YAML frontmatter delimited by ``---``,
followed by the body preserved verbatim from
:attr:`SkillDocument.body`.

Byte-stability contract: the same :class:`SkillDocument` always emits
the same bytes. Lists with stable iteration order yield identical YAML;
defaults (``None`` scalars, empty lists, empty body) are omitted; the
frontmatter keys appear in the SPEC §1.3 order so a diff against an
existing file reveals semantic changes, not formatting noise.

Idempotence contract: ``parse(emit(parse(text)))`` produces a Document
equal to ``parse(text)``. Property tests assert this on hypothesis-
generated skills.
"""

from __future__ import annotations

import io

from ruamel.yaml import YAML

from contextos.ast.document import Document
from contextos.ast.skill import SkillDocument

_FRONTMATTER_FIELD_ORDER: tuple[str, ...] = (
    "name",
    "title",
    "description",
    "trigger_keywords",
    "applies_to",
    "languages_supported",
    "files",
    "required_runtime",
    "example_invocation",
    "expected_output_format",
    "tags",
)
"""Canonical key order in the emitted YAML frontmatter.

Mirrors SPEC §1.3 so a hand-written ``SKILL.md`` and one freshly
emitted by ContextOS share the same field layout.
"""


def emit_skill_markdown(doc: Document) -> str:
    """Emit a Document(type='skill') as a ``SKILL.md`` source string.

    The output always begins with ``---``, ends with the body content
    plus a single trailing newline, and never carries trailing
    whitespace on any line. ``ValueError`` is raised when the Document
    is not of the skill flavor — emitter callers route by ``doc.type``,
    so this is a programming error rather than a parse error.
    """
    if doc.type != "skill" or doc.skill is None:
        msg = "emit_skill_markdown requires Document.type='skill'"
        raise ValueError(msg)

    skill = doc.skill
    frontmatter = _serialize_frontmatter(skill)
    body = _normalize_body(skill.body)
    return f"---\n{frontmatter}---\n{body}"


def _serialize_frontmatter(skill: SkillDocument) -> str:
    """Render the SkillDocument as canonical-order YAML.

    Omits ``None`` scalars and empty lists so the smallest valid skill
    serializes to a 3-line frontmatter block (name / title /
    description). The order matches :data:`_FRONTMATTER_FIELD_ORDER`.
    """
    data = _collect_frontmatter_fields(skill)
    yaml = _yaml_dumper()
    buffer = io.StringIO()
    yaml.dump(data, buffer)
    return buffer.getvalue()


def _collect_frontmatter_fields(skill: SkillDocument) -> dict[str, object]:
    """Build the ordered dict of frontmatter fields to emit.

    Python ≥ 3.7 dicts preserve insertion order, so iterating the
    canonical field tuple is sufficient — no ``OrderedDict`` needed.
    """
    payload: dict[str, object] = {}
    for field in _FRONTMATTER_FIELD_ORDER:
        value = getattr(skill, field)
        if _is_empty(value):
            continue
        payload[field] = value
    return payload


def _is_empty(value: object) -> bool:
    """Treat ``None`` and empty containers as omittable defaults."""
    if value is None:
        return True
    return isinstance(value, list | tuple | set | frozenset | str) and len(value) == 0


def _yaml_dumper() -> YAML:
    """Construct the canonical YAML dumper.

    Uses ``typ='rt'`` (round-trip mode) so the dict key order we choose
    is preserved on dump. The cheaper ``typ='safe'`` mode silently
    alphabetizes keys, which would scramble the SPEC §1.3 field
    ordering and produce a noisy diff against any hand-written file.

    Block style by default (``default_flow_style=False``) so lists
    render as ``- item`` rather than ``[item, item]``. Unicode is
    allowed verbatim (UTF-8 SKILL.md sources are the norm). Indent
    settings match ruamel's defaults; pinning them explicitly
    documents the choice and protects against future ruamel default
    changes.
    """
    yaml = YAML(typ="rt")
    yaml.default_flow_style = False
    yaml.allow_unicode = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 1024  # avoid auto-folding long descriptions
    return yaml


def _normalize_body(body: str) -> str:
    """Ensure the body ends with exactly one newline.

    The parser preserves the body verbatim including its trailing
    newlines (or lack thereof). The emitter normalizes to a single
    trailing newline so round-tripping a body that ended without one
    still produces a well-formed file. An empty body emits as an
    empty string — no trailing newline, no padding.
    """
    if not body:
        return ""
    return body.rstrip("\n") + "\n"


__all__ = ["emit_skill_markdown"]
