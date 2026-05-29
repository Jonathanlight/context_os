"""Detect a project's languages / frameworks from on-disk manifests.

Used by ``ctx init`` to bootstrap a ``.ctx`` for an existing repo
without forcing the user to enumerate the stack by hand. The
detector reads only the well-known manifest files at the repo root --
no recursive scan, no parsing of source files -- so it stays fast on
large repositories.

Detection precedence runs **most-specific to most-general**: e.g.
``composer.json`` containing ``symfony/framework-bundle`` declares
both ``symfony`` and ``php``, with ``symfony`` ranked first so the
emitted ``stack.required`` reads "symfony, php" (the framework comes
first in author-style). Same idea for Python frameworks atop the
``python`` base, JS frameworks atop ``typescript`` / ``node``, etc.
"""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from pathlib import Path

import tomlkit
from pydantic import BaseModel, ConfigDict, Field

from contextos.scaffold.templates import LANGUAGE_TEMPLATES, display_name

Adder = Callable[[str, str], None]


class DetectedProject(BaseModel):
    """The detector's output: detected slugs and a confidence summary."""

    model_config = ConfigDict(extra="forbid", arbitrary_types_allowed=True)

    root: Path
    languages: list[str] = Field(default_factory=list)
    rationale: list[str] = Field(
        default_factory=list,
        description=(
            "One human-readable line per detected slug naming the manifest "
            "that triggered it. Surfaced by ``ctx init`` so the operator "
            "sees WHY each language landed in the generated ``.ctx``."
        ),
    )


SKIP_DIRECTORIES: frozenset[str] = frozenset(
    {
        ".git",
        ".hg",
        ".svn",
        ".jj",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "vendor",
        "dist",
        "build",
        "target",
        "out",
        ".next",
        ".nuxt",
        ".svelte-kit",
        ".astro",
        ".turbo",
        ".cache",
        ".pytest_cache",
        ".mypy_cache",
        ".ruff_cache",
        ".tox",
        ".coverage",
        "__pycache__",
        ".idea",
        ".vscode",
        ".gradle",
        ".m2",
        "Pods",
        "DerivedData",
    }
)
"""Directory names skipped by :func:`detect_project` when walking recursively.

Conservative list -- it covers VCS metadata, vendored deps, build
caches, and IDE state but never anything that would plausibly host a
user-authored manifest.
"""

_MANIFEST_FILENAMES: frozenset[str] = frozenset(
    {
        "composer.json",
        "pyproject.toml",
        "setup.py",
        "requirements.txt",
        "package.json",
        "go.mod",
        "Cargo.toml",
        "pubspec.yaml",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
        "mix.exs",
        "Gemfile",
        "Dockerfile",
        "compose.yaml",
        "docker-compose.yml",
    }
)
"""Filenames that mark a sub-directory worth re-scanning recursively.

A directory is only re-scanned when it contains at least one of these
files; otherwise we don't recurse, which keeps walks fast on big
monorepos.
"""


def detect_project(root: Path, *, recursive: bool = True, max_depth: int = 4) -> DetectedProject:
    """Inspect ``root`` and return the detected languages + rationale.

    :param recursive: when ``True`` (the default) the detector walks
        sub-directories up to ``max_depth`` looking for nested
        manifests -- catches monorepos with ``frontend/`` + ``api/``
        sub-projects, or Symfony apps with a ``client/`` Angular
        bundle. When ``False`` only the root is inspected (the v4.1
        behaviour, kept for tests and for fast checks).
    :param max_depth: hard cap on recursion depth to keep walks
        bounded on huge trees. ``1`` means "root only" (equivalent to
        ``recursive=False``); ``4`` covers nearly every real layout
        without scanning further than necessary.
    """
    detected: list[str] = []
    rationale: list[str] = []

    def add(slug: str, source: str) -> None:
        if slug in detected:
            return
        if slug not in LANGUAGE_TEMPLATES:
            return
        detected.append(slug)
        rationale.append(f"{display_name(slug)} <- {source}")

    _run_detectors(root, add)
    if recursive:
        for sub_root in _iter_sub_roots(root, max_depth=max_depth):
            _run_detectors(sub_root, add, prefix=sub_root.relative_to(root).as_posix() + "/")

    return DetectedProject(root=root, languages=detected, rationale=rationale)


def _run_detectors(root: Path, add: Adder, *, prefix: str = "") -> None:
    """Apply every per-ecosystem detector to ``root``.

    ``prefix`` is prepended to every rationale source string so the
    operator can tell a nested ``backend/composer.json`` apart from
    the root one in the ``ctx init`` output.
    """
    nested = add if not prefix else _prefixed_adder(add, prefix=prefix)
    _detect_php(root, nested)
    _detect_python(root, nested)
    _detect_js(root, nested)
    _detect_go(root, nested)
    _detect_rust(root, nested)
    _detect_dart_flutter(root, nested)
    _detect_java(root, nested)
    _detect_dotnet(root, nested)
    _detect_elixir(root, nested)
    _detect_ruby(root, nested)
    _detect_infra(root, nested)


def _prefixed_adder(add: Adder, *, prefix: str) -> Adder:
    """Wrap ``add`` so every rationale line carries the relative prefix."""

    def wrapped(slug: str, source: str) -> None:
        add(slug, f"{prefix}{source}")

    return wrapped


def _iter_sub_roots(root: Path, *, max_depth: int) -> list[Path]:
    """Return every sub-directory under ``root`` that hosts a manifest.

    Walks at most ``max_depth`` levels deep, skipping
    :data:`SKIP_DIRECTORIES`. A directory is only yielded when at
    least one entry from :data:`_MANIFEST_FILENAMES` lives directly
    in it -- avoiding pointless re-scans of plain doc / asset
    folders.
    """
    sub_roots: list[Path] = []
    stack: list[tuple[Path, int]] = [(root, 0)]
    while stack:
        current, depth = stack.pop()
        if depth >= max_depth:
            continue
        try:
            entries = list(current.iterdir())
        except (OSError, PermissionError):
            continue
        for entry in entries:
            if not entry.is_dir() or entry.is_symlink():
                continue
            if entry.name in SKIP_DIRECTORIES:
                continue
            if entry == root:
                continue
            stack.append((entry, depth + 1))
            if any((entry / name).is_file() for name in _MANIFEST_FILENAMES):
                sub_roots.append(entry)
    return sub_roots


# ---------------------------------------------------------------------------
# Per-ecosystem detection blocks. Each one is small enough to keep the
# rules a reviewer can read top-to-bottom.
# ---------------------------------------------------------------------------


def _detect_php(root: Path, add: Adder) -> None:
    composer_json = root / "composer.json"
    if not composer_json.is_file():
        return
    deps = _composer_dependencies(composer_json)
    if any(p.startswith("symfony/") for p in deps):
        add("symfony", "composer.json (symfony/* package)")
    if any(p.startswith("laravel/") for p in deps):
        add("laravel", "composer.json (laravel/* package)")
    if "slim/slim" in deps:
        add("slim", "composer.json (slim/slim)")
    if "hyperf/framework" in deps:
        add("hyperf", "composer.json (hyperf/framework)")
    if "doctrine/orm" in deps:
        add("doctrine", "composer.json (doctrine/orm)")
    add("php", "composer.json")


def _detect_python(root: Path, add: Adder) -> None:
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        deps = _pyproject_dependencies(pyproject)
        _maybe_add(add, deps, "fastapi", "fastapi", "pyproject.toml")
        _maybe_add(add, deps, "django", "django", "pyproject.toml")
        _maybe_add(add, deps, "flask", "flask", "pyproject.toml")
        _maybe_add(add, deps, "litestar", "litestar", "pyproject.toml")
        _maybe_add(add, deps, "starlette", "starlette", "pyproject.toml")
        _maybe_add(add, deps, "sqlalchemy", "sqlalchemy", "pyproject.toml")
        _maybe_add(add, deps, "torch", "pytorch", "pyproject.toml")
        _maybe_add(add, deps, "tensorflow", "tensorflow", "pyproject.toml")
        _maybe_add(add, deps, "jax", "jax", "pyproject.toml")
        _maybe_add(add, deps, "scikit-learn", "scikit-learn", "pyproject.toml")
        _maybe_add(add, deps, "langchain", "langchain", "pyproject.toml")
        _maybe_add(add, deps, "llama-index", "llamaindex", "pyproject.toml")
        add("python", "pyproject.toml")
        return
    if (root / "setup.py").is_file() or (root / "requirements.txt").is_file():
        add("python", "setup.py or requirements.txt")


def _detect_js(root: Path, add: Adder) -> None:
    package_json = root / "package.json"
    if not package_json.is_file():
        return
    deps = _package_json_dependencies(package_json)

    # Frameworks first so they rank before the base language.
    _maybe_add(add, deps, "next", "nextjs", "package.json")
    _maybe_add(add, deps, "@remix-run/react", "remix", "package.json")
    _maybe_add(add, deps, "react", "react", "package.json")
    _maybe_add(add, deps, "react-native", "react-native", "package.json")
    _maybe_add(add, deps, "@nestjs/core", "nestjs", "package.json")
    _maybe_add(add, deps, "nuxt", "nuxt", "package.json")
    _maybe_add(add, deps, "vue", "vue", "package.json")
    _maybe_add(add, deps, "@angular/core", "angular", "package.json")
    _maybe_add(add, deps, "@sveltejs/kit", "sveltekit", "package.json")
    _maybe_add(add, deps, "svelte", "svelte", "package.json")
    _maybe_add(add, deps, "solid-js", "solidjs", "package.json")
    _maybe_add(add, deps, "astro", "astro", "package.json")
    _maybe_add(add, deps, "@builder.io/qwik", "qwik", "package.json")
    _maybe_add(add, deps, "preact", "preact", "package.json")
    _maybe_add(add, deps, "lit", "lit", "package.json")
    _maybe_add(add, deps, "express", "express", "package.json")
    _maybe_add(add, deps, "fastify", "fastify", "package.json")
    _maybe_add(add, deps, "hono", "hono", "package.json")
    _maybe_add(add, deps, "elysia", "elysia", "package.json")
    _maybe_add(add, deps, "@adonisjs/core", "adonisjs", "package.json")
    if "prisma" in deps or "@prisma/client" in deps:
        add("prisma", "package.json (prisma dep)")
    _maybe_add(add, deps, "drizzle-orm", "drizzle", "package.json")
    _maybe_add(add, deps, "tailwindcss", "tailwind", "package.json")
    _maybe_add(add, deps, "electron", "electron", "package.json")
    if "@tauri-apps/api" in deps or (root / "src-tauri" / "tauri.conf.json").is_file():
        add("tauri", "src-tauri/ or @tauri-apps/api")

    if "typescript" in deps or (root / "tsconfig.json").is_file():
        add("typescript", "package.json (typescript dep) or tsconfig.json")
    add("node", "package.json")


def _detect_go(root: Path, add: Adder) -> None:
    go_mod = root / "go.mod"
    if not go_mod.is_file():
        return
    content = go_mod.read_text(encoding="utf-8", errors="ignore")
    for module, slug in (
        ("github.com/gin-gonic/gin", "gin"),
        ("github.com/labstack/echo", "echo"),
        ("github.com/gofiber/fiber", "fiber"),
        ("github.com/go-chi/chi", "chi"),
    ):
        if module in content:
            add(slug, f"go.mod ({module})")
    add("go", "go.mod")


def _detect_rust(root: Path, add: Adder) -> None:
    cargo = root / "Cargo.toml"
    if not cargo.is_file():
        return
    content = cargo.read_text(encoding="utf-8", errors="ignore")
    if "axum" in content:
        add("axum", "Cargo.toml (axum)")
    if "actix-web" in content:
        add("actix-web", "Cargo.toml (actix-web)")
    if "tauri" in content:
        add("tauri", "Cargo.toml (tauri)")
    add("rust", "Cargo.toml")


def _detect_dart_flutter(root: Path, add: Adder) -> None:
    pubspec = root / "pubspec.yaml"
    if not pubspec.is_file():
        return
    content = pubspec.read_text(encoding="utf-8", errors="ignore")
    if "flutter:" in content or "sdk: flutter" in content:
        add("flutter", "pubspec.yaml (flutter sdk)")
    add("dart", "pubspec.yaml")


def _detect_java(root: Path, add: Adder) -> None:
    pom = root / "pom.xml"
    gradle = root / "build.gradle"
    gradle_kts = root / "build.gradle.kts"
    if not (pom.is_file() or gradle.is_file() or gradle_kts.is_file()):
        return
    for candidate in (pom, gradle, gradle_kts):
        if candidate.is_file():
            content = candidate.read_text(encoding="utf-8", errors="ignore")
            if "spring-boot" in content:
                add("spring-boot", f"{candidate.name} (spring-boot reference)")
            if "quarkus" in content:
                add("quarkus", f"{candidate.name} (quarkus reference)")
            if "micronaut" in content:
                add("micronaut", f"{candidate.name} (micronaut reference)")
            if "ktor" in content:
                add("ktor", f"{candidate.name} (ktor reference)")
    if gradle_kts.is_file():
        add("kotlin", "build.gradle.kts")
    add("java", "pom.xml / build.gradle")


def _detect_dotnet(root: Path, add: Adder) -> None:
    csproj = list(root.glob("*.csproj"))
    sln = list(root.glob("*.sln"))
    if not (csproj or sln):
        return
    for proj in csproj:
        content = proj.read_text(encoding="utf-8", errors="ignore")
        if "Microsoft.AspNetCore" in content or 'Sdk="Microsoft.NET.Sdk.Web"' in content:
            add("aspnet-core", f"{proj.name} (Microsoft.AspNetCore)")
    add("dotnet", ".csproj / .sln")


def _detect_elixir(root: Path, add: Adder) -> None:
    mix_exs = root / "mix.exs"
    if not mix_exs.is_file():
        return
    content = mix_exs.read_text(encoding="utf-8", errors="ignore")
    if ":phoenix" in content:
        add("phoenix", "mix.exs (:phoenix dep)")
    add("elixir", "mix.exs")


def _detect_ruby(root: Path, add: Adder) -> None:
    gemfile = root / "Gemfile"
    if not gemfile.is_file():
        return
    content = gemfile.read_text(encoding="utf-8", errors="ignore")
    if "'rails'" in content or '"rails"' in content:
        add("rails", "Gemfile (rails)")
    if "'sinatra'" in content or '"sinatra"' in content:
        add("sinatra", "Gemfile (sinatra)")
    add("ruby", "Gemfile")


def _detect_infra(root: Path, add: Adder) -> None:
    if (
        (root / "Dockerfile").is_file()
        or (root / "compose.yaml").is_file()
        or (root / "docker-compose.yml").is_file()
    ):
        add("docker", "Dockerfile / compose file")
    if (root / ".github" / "workflows").is_dir():
        add("github-actions", ".github/workflows/")
    if any(root.glob("*.tf")):
        add("terraform", "*.tf file at repo root")
    if (root / "k8s").is_dir() or (root / "kubernetes").is_dir():
        add("kubernetes", "k8s/ or kubernetes/ directory")


def _maybe_add(add: Adder, deps: set[str], dep: str, slug: str, manifest: str) -> None:
    """Helper that wraps the common ``dep in deps → add(slug)`` pattern.

    Keeps the per-ecosystem detection blocks readable instead of a
    long sequence of inline ``if`` statements.
    """
    if dep in deps:
        add(slug, f"{manifest} ({dep} dep)")


# ---------------------------------------------------------------------------
# Manifest parsing helpers -- each is lenient and never raises.
# ---------------------------------------------------------------------------


def _composer_dependencies(path: Path) -> set[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    out: set[str] = set()
    for key in ("require", "require-dev"):
        section = data.get(key, {})
        if isinstance(section, dict):
            out.update(section)
    return out


def _pyproject_dependencies(path: Path) -> set[str]:
    try:
        data = tomlkit.parse(path.read_text(encoding="utf-8")).unwrap()
    except Exception:
        return set()
    out: set[str] = set()
    project = data.get("project", {})
    if isinstance(project, dict):
        out.update(_pep508_roots(project.get("dependencies", [])))
        extras = project.get("optional-dependencies", {})
        if isinstance(extras, dict):
            for items in extras.values():
                if isinstance(items, list):
                    out.update(_pep508_roots(items))
    tool = data.get("tool", {})
    if isinstance(tool, dict):
        poetry = tool.get("poetry", {})
        if isinstance(poetry, dict):
            deps = poetry.get("dependencies", {})
            if isinstance(deps, dict):
                out.update(name.lower() for name in deps if isinstance(name, str))
    return out


def _pep508_roots(items: Iterable[object]) -> set[str]:
    return {_pep508_root(item) for item in items}


def _pep508_root(spec: object) -> str:
    """Pull the bare package name out of a PEP 508 requirement string."""
    text = str(spec).strip()
    for idx, ch in enumerate(text):
        if not (ch.isalnum() or ch in "-._"):
            return text[:idx].lower()
    return text.lower()


def _package_json_dependencies(path: Path) -> set[str]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return set()
    out: set[str] = set()
    for key in ("dependencies", "devDependencies", "peerDependencies"):
        section = data.get(key, {})
        if isinstance(section, dict):
            out.update(section)
    return out


__all__ = ["DetectedProject", "detect_project"]
