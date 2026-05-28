"""Sanity tests on the language / framework registry.

The registry is the single source of truth ``ctx create`` / ``ctx
init`` read from. These tests guarantee the invariants downstream
code relies on (no duplicate rule ids across languages, valid
severities, slug-prefixed rule ids, ...). They run on every PR so
adding a new language entry can't silently break the registry.
"""

from __future__ import annotations

import re

from contextos.ast.agent import RULE_ID_PATTERN
from contextos.ast.common import Severity
from contextos.scaffold.templates import (
    BASELINE_RULES,
    LANGUAGE_ALIASES,
    LANGUAGE_TEMPLATES,
    display_name,
    known_languages,
    known_languages_by_category,
    known_languages_by_wave,
    normalize_slug,
)


def test_baseline_rule_ids_are_well_formed() -> None:
    pattern = re.compile(RULE_ID_PATTERN)
    for rule in BASELINE_RULES:
        assert pattern.match(rule["id"]), rule["id"]
        Severity(rule["severity"])


def test_every_language_template_has_required_fields() -> None:
    for slug, entry in LANGUAGE_TEMPLATES.items():
        assert "display_name" in entry, slug
        assert "category" in entry, slug
        assert "wave" in entry, slug
        assert "stack_required" in entry, slug
        assert "rules" in entry, slug
        assert entry["wave"] in {1, 2, 3, 4}, (slug, entry["wave"])


def test_every_template_rule_id_matches_spec() -> None:
    pattern = re.compile(RULE_ID_PATTERN)
    for slug, entry in LANGUAGE_TEMPLATES.items():
        for rule in entry["rules"]:
            assert pattern.match(rule["id"]), (slug, rule["id"])
            Severity(rule["severity"])  # severity is a valid enum member


def test_rule_ids_are_unique_across_the_registry() -> None:
    seen: dict[str, str] = {r["id"]: "<baseline>" for r in BASELINE_RULES}
    duplicates: list[tuple[str, str, str]] = []
    for slug, entry in LANGUAGE_TEMPLATES.items():
        for rule in entry["rules"]:
            if rule["id"] in seen:
                duplicates.append((rule["id"], seen[rule["id"]], slug))
            else:
                seen[rule["id"]] = slug
    assert not duplicates, duplicates


def test_known_languages_is_sorted_and_contains_all_slugs() -> None:
    listed = known_languages()
    assert listed == sorted(LANGUAGE_TEMPLATES)


def test_display_name_falls_back_to_the_slug() -> None:
    assert display_name("python") == "Python"
    assert display_name("does-not-exist") == "does-not-exist"


def test_normalize_slug_resolves_common_aliases() -> None:
    assert normalize_slug("Next.js") == "nextjs"
    assert normalize_slug("c#") == "dotnet"
    assert normalize_slug("ts") == "typescript"
    assert normalize_slug("javascript") == "node"
    # Unknown slugs are returned unchanged (the builder will ignore them).
    assert normalize_slug("brand-new-thing") == "brand-new-thing"


def test_aliases_target_existing_registry_slugs() -> None:
    for alias, target in LANGUAGE_ALIASES.items():
        assert target in LANGUAGE_TEMPLATES, (alias, target)


def test_known_languages_by_wave_returns_each_wave() -> None:
    for wave in (1, 2, 3, 4):
        slugs = known_languages_by_wave(wave)
        for slug in slugs:
            assert LANGUAGE_TEMPLATES[slug]["wave"] == wave


def test_known_languages_by_category_returns_homogeneous_buckets() -> None:
    categories = {entry["category"] for entry in LANGUAGE_TEMPLATES.values()}
    for category in categories:
        for slug in known_languages_by_category(category):
            assert LANGUAGE_TEMPLATES[slug]["category"] == category
