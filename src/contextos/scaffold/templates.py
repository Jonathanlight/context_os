"""Per-language / per-framework rule templates for ``ctx create``.

The registry below maps each supported language or framework slug
to a small set of rules and ``stack.required`` entries the
scaffolded ``.ctx`` will carry. Rules are intentionally
**opinionated but obvious** -- the kind of guidance a senior engineer
would add to a fresh project's CLAUDE.md on day one. Users can edit
or delete any of them.

The catalog is organized by adoption *wave* (see
``docs/roadmap/templates.md``):

- **wave 1** -- the five essentials shipped in 4.x: Symfony, FastAPI,
  Flutter, Next.js / React, NestJS.
- **wave 2** -- the natural extensions: Laravel, Django, Nuxt,
  SvelteKit, Spring Boot / Kotlin.
- **wave 3** -- market coverage: Rails, Go (Gin / Echo / Fiber),
  Phoenix, ASP.NET Core, Rust + Axum, and the broader systems and
  data-science families.
- **wave 4** -- verticals (RAG pipelines, Tauri apps, browser
  extensions, etc.) shipped through ``contextos-templates`` once
  the catalog is community-driven.

Adding a new language is one entry in :data:`LANGUAGE_TEMPLATES`.
Rule ids are **prefixed by the slug** so dedup-by-id leaves the
right rules when several stacks are mixed.
"""

from __future__ import annotations

from typing import Any, Final

# ---------------------------------------------------------------------------
# Baseline rules -- always applied regardless of selected languages.
# ---------------------------------------------------------------------------

BASELINE_RULES: Final[list[dict[str, Any]]] = [
    {
        "id": "TDD-001",
        "title": "Write a failing test before any production code change",
        "severity": "must",
        "rationale": "Catches regressions before the PR review hits them.",
    },
    {
        "id": "SEC-001",
        "title": "Sanitize every input crossing a trust boundary",
        "severity": "must",
        "rationale": "Prevents injection, path-traversal, and similar exploits.",
    },
    {
        "id": "DOC-001",
        "title": "Public functions carry a docstring stating intent and contract",
        "severity": "should",
        "rationale": "Future readers and the LLM both rely on it.",
    },
]


# ---------------------------------------------------------------------------
# Language and framework templates.
#
# Each entry must declare:
#   - display_name -- pretty label for ``ctx create --list-languages``.
#   - category     -- catalog bucket (backend, frontend, mobile, ...)
#   - wave         -- adoption wave 1..4.
#   - stack_required -- items appended to ``[stack].required``.
#   - rules        -- 1-3 opinionated rules with slug-prefixed ids.
# ---------------------------------------------------------------------------

LANGUAGE_TEMPLATES: Final[dict[str, dict[str, Any]]] = {
    # ===================== BACKEND -- Python =====================
    "python": {
        "display_name": "Python",
        "category": "backend",
        "wave": 1,
        "stack_required": ["python>=3.12"],
        "rules": [
            {
                "id": "PY-001",
                "title": "Type-hint every public function signature",
                "severity": "must",
                "rationale": "mypy --strict requires it and reviewers expect it.",
                "example_good": "def foo(name: str) -> int: ...",
            },
            {
                "id": "PY-002",
                "title": "Format with ruff format and lint with ruff check",
                "severity": "should",
                "rationale": "One formatter, zero bike-shedding.",
            },
            {
                "id": "PY-003",
                "title": "Prefer Pydantic models over raw dicts at module boundaries",
                "severity": "should",
                "rationale": "Strict validation + serialization round-trips for free.",
            },
        ],
    },
    "fastapi": {
        "display_name": "FastAPI",
        "category": "backend",
        "wave": 1,
        "stack_required": ["fastapi", "pydantic>=2"],
        "rules": [
            {
                "id": "FAS-001",
                "title": "Declare request and response shapes as Pydantic models",
                "severity": "must",
                "rationale": "OpenAPI docs and validation derive from them.",
            },
            {
                "id": "FAS-002",
                "title": "Use async endpoints unless the handler is purely CPU-bound",
                "severity": "should",
                "rationale": "Avoid blocking the event loop on I/O.",
            },
        ],
    },
    "django": {
        "display_name": "Django",
        "category": "backend",
        "wave": 2,
        "stack_required": ["django>=5"],
        "rules": [
            {
                "id": "DJG-001",
                "title": "Migrations are committed alongside the model change",
                "severity": "must",
                "rationale": "Schema drift between environments is the top Django outage class.",
            },
            {
                "id": "DJG-002",
                "title": "Business logic lives in services, not in views or models",
                "severity": "should",
                "rationale": "Keeps views thin and models simple to test.",
            },
        ],
    },
    "flask": {
        "display_name": "Flask",
        "category": "backend",
        "wave": 3,
        "stack_required": ["flask>=3"],
        "rules": [
            {
                "id": "FLK-001",
                "title": "Use blueprints to split routes by domain",
                "severity": "should",
                "rationale": "Keeps app.py from drifting into a god-file.",
            },
        ],
    },
    "litestar": {
        "display_name": "Litestar",
        "category": "backend",
        "wave": 3,
        "stack_required": ["litestar>=2"],
        "rules": [
            {
                "id": "LIT-001",
                "title": "Controllers via class-based handlers; DTOs as msgspec or Pydantic",
                "severity": "should",
                "rationale": "Litestar's strength is typed handlers and DI -- lean on it.",
            },
        ],
    },
    "starlette": {
        "display_name": "Starlette",
        "category": "backend",
        "wave": 3,
        "stack_required": ["starlette>=0.37"],
        "rules": [
            {
                "id": "STAR-001",
                "title": "Routes declared via ``Route`` objects, not decorators",
                "severity": "may",
                "rationale": "Easier to reason about middleware and lifespans.",
            },
        ],
    },
    # ===================== BACKEND -- PHP =====================
    "php": {
        "display_name": "PHP",
        "category": "backend",
        "wave": 1,
        "stack_required": ["php>=8.3"],
        "rules": [
            {
                "id": "PHP-001",
                "title": "Every file declares strict_types=1 at the top",
                "severity": "must",
                "rationale": "Type coercion is the source of most silent PHP bugs.",
                "example_good": "<?php\ndeclare(strict_types=1);",
            },
            {
                "id": "PHP-002",
                "title": "Follow PSR-12 coding style end-to-end",
                "severity": "should",
                "rationale": "Standard formatting keeps diffs tight.",
            },
        ],
    },
    "symfony": {
        "display_name": "Symfony",
        "category": "backend",
        "wave": 1,
        "stack_required": ["symfony>=7"],
        "rules": [
            {
                "id": "SF-001",
                "title": "Inject services via the constructor; no static service locator",
                "severity": "must",
                "rationale": "Constructor injection makes dependencies explicit and testable.",
            },
            {
                "id": "SF-002",
                "title": "Prefer attributes over annotations on entities and controllers",
                "severity": "should",
                "rationale": "Attributes are native PHP, fewer surprises than DocBlock parsing.",
            },
            {
                "id": "SF-003",
                "title": "Domain rules live in services, not in Doctrine entities",
                "severity": "should",
                "rationale": "Keeps entities anaemic and the domain layer testable.",
            },
        ],
    },
    "laravel": {
        "display_name": "Laravel",
        "category": "backend",
        "wave": 2,
        "stack_required": ["laravel>=11"],
        "rules": [
            {
                "id": "LRV-001",
                "title": "Form Requests validate every incoming HTTP shape",
                "severity": "must",
                "rationale": "Centralizes validation and keeps controllers thin.",
            },
            {
                "id": "LRV-002",
                "title": "Business logic lives in Action classes, not in controllers",
                "severity": "should",
                "rationale": "Controllers stay small and Actions are unit-testable.",
            },
        ],
    },
    "slim": {
        "display_name": "Slim Framework",
        "category": "backend",
        "wave": 3,
        "stack_required": ["slim>=4"],
        "rules": [
            {
                "id": "SLM-001",
                "title": "Middleware composition over inheritance for cross-cutting concerns",
                "severity": "should",
                "rationale": "Slim's PSR-15 pipeline is the cleanest place to handle them.",
            },
        ],
    },
    "hyperf": {
        "display_name": "Hyperf",
        "category": "backend",
        "wave": 4,
        "stack_required": ["hyperf>=3"],
        "rules": [
            {
                "id": "HYP-001",
                "title": "Annotate coroutine boundaries; no blocking I/O in handlers",
                "severity": "must",
                "rationale": "Hyperf runs on Swoole/Open Swoole -- blocking syscalls poison the worker.",
            },
        ],
    },
    # ===================== BACKEND -- TypeScript / Node =====================
    "typescript": {
        "display_name": "TypeScript",
        "category": "backend",
        "wave": 1,
        "stack_required": ["typescript>=5"],
        "rules": [
            {
                "id": "TS-001",
                "title": "tsconfig has strict mode on; no implicit any",
                "severity": "must",
                "rationale": "Catches the entire bug class TypeScript was designed for.",
            },
            {
                "id": "TS-002",
                "title": "Prefer types over interfaces for purely structural shapes",
                "severity": "may",
                "rationale": "Both work; pick one and stay consistent.",
            },
        ],
    },
    "node": {
        "display_name": "Node.js",
        "category": "backend",
        "wave": 2,
        "stack_required": ["node>=20"],
        "rules": [
            {
                "id": "ND-001",
                "title": "Pin Node version via .nvmrc or engines in package.json",
                "severity": "should",
                "rationale": "Drift between local and CI Node versions is a recurring outage.",
            },
        ],
    },
    "nestjs": {
        "display_name": "NestJS",
        "category": "backend",
        "wave": 1,
        "stack_required": ["@nestjs/core>=10", "typescript>=5"],
        "rules": [
            {
                "id": "NST-001",
                "title": "DTOs validated with class-validator on every controller boundary",
                "severity": "must",
                "rationale": "ValidationPipe is global -- bypassing it leaks unvalidated payloads.",
            },
            {
                "id": "NST-002",
                "title": "Business logic in providers (services), never in controllers",
                "severity": "should",
                "rationale": "Controllers are just adapters; services are the testable unit.",
            },
        ],
    },
    "express": {
        "display_name": "Express",
        "category": "backend",
        "wave": 2,
        "stack_required": ["express>=5"],
        "rules": [
            {
                "id": "EXP-001",
                "title": "Centralize error handling via a final error middleware",
                "severity": "must",
                "rationale": "Otherwise thrown errors crash the process or leak stack traces.",
            },
        ],
    },
    "fastify": {
        "display_name": "Fastify",
        "category": "backend",
        "wave": 3,
        "stack_required": ["fastify>=4"],
        "rules": [
            {
                "id": "FST-001",
                "title": "Declare schemas for every route; serialize via fast-json-stringify",
                "severity": "should",
                "rationale": "Schema-first is Fastify's perf and correctness story.",
            },
        ],
    },
    "hono": {
        "display_name": "Hono",
        "category": "backend",
        "wave": 3,
        "stack_required": ["hono>=4"],
        "rules": [
            {
                "id": "HNO-001",
                "title": "Validate inputs with zod / valibot via Hono's typed middleware",
                "severity": "should",
                "rationale": "Hono's type-inference falls apart without a validator.",
            },
        ],
    },
    "elysia": {
        "display_name": "Elysia",
        "category": "backend",
        "wave": 3,
        "stack_required": ["elysia>=1"],
        "rules": [
            {
                "id": "ELY-001",
                "title": "Use ``t.Object`` schemas so the eden client stays type-safe",
                "severity": "should",
                "rationale": "Elysia's end-to-end typing depends on declared schemas.",
            },
        ],
    },
    "adonisjs": {
        "display_name": "AdonisJS",
        "category": "backend",
        "wave": 3,
        "stack_required": ["@adonisjs/core>=6"],
        "rules": [
            {
                "id": "ADO-001",
                "title": "Validate every request body via VineJS validators",
                "severity": "must",
                "rationale": "Centralized validation keeps controllers thin.",
            },
        ],
    },
    "bun": {
        "display_name": "Bun",
        "category": "backend",
        "wave": 3,
        "stack_required": ["bun>=1.1"],
        "rules": [
            {
                "id": "BUN-001",
                "title": "Prefer Bun-native APIs (Bun.file, Bun.serve) over Node compat shims",
                "severity": "may",
                "rationale": "The compat layer is a fallback, not the perf path.",
            },
        ],
    },
    # ===================== BACKEND -- JVM =====================
    "java": {
        "display_name": "Java",
        "category": "backend",
        "wave": 2,
        "stack_required": ["java>=21"],
        "rules": [
            {
                "id": "JV-001",
                "title": "Records for value objects; classes only when behavior is needed",
                "severity": "should",
                "rationale": "Records remove getter/equals/hashCode boilerplate.",
            },
        ],
    },
    "kotlin": {
        "display_name": "Kotlin",
        "category": "backend",
        "wave": 2,
        "stack_required": ["kotlin>=2.0"],
        "rules": [
            {
                "id": "KT-001",
                "title": "Data classes for DTOs; sealed classes for state machines",
                "severity": "should",
                "rationale": "Kotlin's type system is at its best when you lean on these.",
            },
        ],
    },
    "spring-boot": {
        "display_name": "Spring Boot",
        "category": "backend",
        "wave": 2,
        "stack_required": ["spring-boot>=3"],
        "rules": [
            {
                "id": "SP-001",
                "title": "Constructor injection only; no field injection",
                "severity": "must",
                "rationale": "Makes dependencies explicit and components immutable.",
            },
        ],
    },
    "ktor": {
        "display_name": "Ktor",
        "category": "backend",
        "wave": 3,
        "stack_required": ["ktor>=2.3"],
        "rules": [
            {
                "id": "KTR-001",
                "title": "Compose features in the Application module; no globals",
                "severity": "should",
                "rationale": "Ktor's DSL stays clean only if features stay scoped to the module.",
            },
        ],
    },
    "quarkus": {
        "display_name": "Quarkus",
        "category": "backend",
        "wave": 4,
        "stack_required": ["quarkus>=3"],
        "rules": [
            {
                "id": "QRK-001",
                "title": "Build-time configuration over runtime reflection",
                "severity": "should",
                "rationale": "Native-image friendliness depends on it.",
            },
        ],
    },
    "micronaut": {
        "display_name": "Micronaut",
        "category": "backend",
        "wave": 4,
        "stack_required": ["micronaut>=4"],
        "rules": [
            {
                "id": "MNT-001",
                "title": "Prefer compile-time annotation processing over runtime proxies",
                "severity": "should",
                "rationale": "That's the whole point of Micronaut vs Spring at runtime.",
            },
        ],
    },
    # ===================== BACKEND -- Go =====================
    "go": {
        "display_name": "Go",
        "category": "backend",
        "wave": 3,
        "stack_required": ["go>=1.22"],
        "rules": [
            {
                "id": "GO-001",
                "title": "Return errors; do not log-and-return-nil",
                "severity": "must",
                "rationale": "Errors must propagate so callers can decide policy.",
            },
            {
                "id": "GO-002",
                "title": "No init() functions in production packages",
                "severity": "should",
                "rationale": "Side effects at import time break test isolation.",
            },
        ],
    },
    "gin": {
        "display_name": "Gin",
        "category": "backend",
        "wave": 3,
        "stack_required": ["gin>=1.10"],
        "rules": [
            {
                "id": "GIN-001",
                "title": "Use Bind+validator on every request; no ad-hoc decoding",
                "severity": "must",
                "rationale": "Skipping the binder is how malformed input lands on the DB.",
            },
        ],
    },
    "echo": {
        "display_name": "Echo",
        "category": "backend",
        "wave": 3,
        "stack_required": ["echo>=4"],
        "rules": [
            {
                "id": "ECO-001",
                "title": "Centralize errors via custom HTTPErrorHandler",
                "severity": "should",
                "rationale": "Otherwise every handler re-implements its own taxonomy.",
            },
        ],
    },
    "fiber": {
        "display_name": "Fiber",
        "category": "backend",
        "wave": 3,
        "stack_required": ["fiber>=2"],
        "rules": [
            {
                "id": "FBR-001",
                "title": "Do not block the request goroutine -- offload heavy work",
                "severity": "should",
                "rationale": "Fasthttp's perf vanishes the moment you block.",
            },
        ],
    },
    "chi": {
        "display_name": "Chi",
        "category": "backend",
        "wave": 3,
        "stack_required": ["chi>=5"],
        "rules": [
            {
                "id": "CHI-001",
                "title": "Group routes under a sub-router per resource",
                "severity": "may",
                "rationale": "Keeps main.go tidy as the API surface grows.",
            },
        ],
    },
    # ===================== BACKEND -- Rust =====================
    "rust": {
        "display_name": "Rust",
        "category": "backend",
        "wave": 3,
        "stack_required": ["rust>=1.80"],
        "rules": [
            {
                "id": "RS-001",
                "title": "No unwrap()/expect() outside tests and main",
                "severity": "must",
                "rationale": "Propagate errors via ?; let main decide the policy.",
            },
        ],
    },
    "axum": {
        "display_name": "Axum",
        "category": "backend",
        "wave": 3,
        "stack_required": ["axum>=0.7"],
        "rules": [
            {
                "id": "AXM-001",
                "title": "Use extractors for inputs; do not parse req body by hand",
                "severity": "should",
                "rationale": "Extractors carry the type-safety story of the framework.",
            },
        ],
    },
    "actix-web": {
        "display_name": "Actix Web",
        "category": "backend",
        "wave": 4,
        "stack_required": ["actix-web>=4"],
        "rules": [
            {
                "id": "ACT-001",
                "title": "Avoid holding non-Send state across await points",
                "severity": "should",
                "rationale": "Common source of cryptic compile errors on Actix's multi-runtime model.",
            },
        ],
    },
    # ===================== BACKEND -- Others =====================
    "ruby": {
        "display_name": "Ruby",
        "category": "backend",
        "wave": 3,
        "stack_required": ["ruby>=3.3"],
        "rules": [
            {
                "id": "RB-001",
                "title": "Use frozen string literals; opt in via magic comment",
                "severity": "may",
                "rationale": "Cheap memory win on hot paths.",
            },
        ],
    },
    "rails": {
        "display_name": "Ruby on Rails",
        "category": "backend",
        "wave": 3,
        "stack_required": ["rails>=7.2"],
        "rules": [
            {
                "id": "RLS-001",
                "title": "Fat models, slim controllers; extract POROs / interactors over time",
                "severity": "should",
                "rationale": "The Rails-way that ages best on real apps.",
            },
        ],
    },
    "sinatra": {
        "display_name": "Sinatra",
        "category": "backend",
        "wave": 4,
        "stack_required": ["sinatra>=4"],
        "rules": [
            {
                "id": "SNT-001",
                "title": "Modular style for anything beyond a one-file demo",
                "severity": "should",
                "rationale": "Classic style is a trap once the app grows.",
            },
        ],
    },
    "elixir": {
        "display_name": "Elixir",
        "category": "backend",
        "wave": 3,
        "stack_required": ["elixir>=1.16"],
        "rules": [
            {
                "id": "ELX-001",
                "title": "Pattern-match function heads instead of nested case",
                "severity": "should",
                "rationale": "Reads like spec; nested cases age into Christmas trees.",
            },
        ],
    },
    "phoenix": {
        "display_name": "Phoenix",
        "category": "backend",
        "wave": 3,
        "stack_required": ["phoenix>=1.7"],
        "rules": [
            {
                "id": "PHX-001",
                "title": "Contexts own business logic; controllers stay HTTP-only",
                "severity": "must",
                "rationale": "The whole point of Phoenix contexts.",
            },
        ],
    },
    "dotnet": {
        "display_name": ".NET",
        "category": "backend",
        "wave": 3,
        "stack_required": ["dotnet>=9"],
        "rules": [
            {
                "id": "NET-001",
                "title": "Nullable reference types enabled project-wide",
                "severity": "must",
                "rationale": "Closes the entire null-ref bug class.",
            },
        ],
    },
    "aspnet-core": {
        "display_name": "ASP.NET Core",
        "category": "backend",
        "wave": 3,
        "stack_required": ["aspnetcore>=9"],
        "rules": [
            {
                "id": "ASP-001",
                "title": "DTOs separated from EF entities; map via Mapperly or hand-rolled records",
                "severity": "should",
                "rationale": "Entities leaking into HTTP responses is the canonical .NET footgun.",
            },
        ],
    },
    "scala": {
        "display_name": "Scala",
        "category": "backend",
        "wave": 4,
        "stack_required": ["scala>=3.4"],
        "rules": [
            {
                "id": "SC-001",
                "title": "Prefer given/using for type-class derivation over implicit chains",
                "severity": "may",
                "rationale": "Scala 3's contextual syntax is the readable path.",
            },
        ],
    },
    "swift": {
        "display_name": "Swift",
        "category": "backend",
        "wave": 4,
        "stack_required": ["swift>=6"],
        "rules": [
            {
                "id": "SW-001",
                "title": "Adopt Swift 6 strict concurrency; eliminate data-race warnings",
                "severity": "should",
                "rationale": "Backporting later is significantly more painful.",
            },
        ],
    },
    "vapor": {
        "display_name": "Vapor",
        "category": "backend",
        "wave": 4,
        "stack_required": ["vapor>=4"],
        "rules": [
            {
                "id": "VPR-001",
                "title": "Content/Codable for every request and response shape",
                "severity": "must",
                "rationale": "Keeps the HTTP layer aligned with Swift's type system.",
            },
        ],
    },
    "dart": {
        "display_name": "Dart",
        "category": "backend",
        "wave": 2,
        "stack_required": ["dart>=3.4"],
        "rules": [
            {
                "id": "DRT-001",
                "title": "Sound null-safety on; no late variables outside frameworks that demand it",
                "severity": "must",
                "rationale": "Late escapes are the recurring runtime crash in Dart apps.",
            },
        ],
    },
    "clojure": {
        "display_name": "Clojure",
        "category": "backend",
        "wave": 4,
        "stack_required": ["clojure>=1.12"],
        "rules": [
            {
                "id": "CLJ-001",
                "title": "Spec/Malli schemas at every external boundary",
                "severity": "should",
                "rationale": "Dynamic typing without schemas ages into a mystery.",
            },
        ],
    },
    "haskell": {
        "display_name": "Haskell",
        "category": "backend",
        "wave": 4,
        "stack_required": ["ghc>=9.8"],
        "rules": [
            {
                "id": "HSK-001",
                "title": "Use ``newtype`` aggressively for domain primitives",
                "severity": "should",
                "rationale": "Stops Int and Int from being confused at compile time.",
            },
        ],
    },
    # ===================== FRONTEND =====================
    "react": {
        "display_name": "React",
        "category": "frontend",
        "wave": 1,
        "stack_required": ["react>=19"],
        "rules": [
            {
                "id": "RCT-001",
                "title": "Functional components only; no class components",
                "severity": "must",
                "rationale": "Hooks cover every modern use case.",
            },
            {
                "id": "RCT-002",
                "title": "One component per file; co-locate styles and tests",
                "severity": "should",
                "rationale": "Easier to find, easier to delete.",
            },
            {
                "id": "RCT-003",
                "title": "Side effects live in useEffect / hooks, never in render",
                "severity": "must",
                "rationale": "Side effects in render produce inconsistent UI on re-renders.",
            },
        ],
    },
    "nextjs": {
        "display_name": "Next.js",
        "category": "frontend",
        "wave": 1,
        "stack_required": ["next>=15", "react>=19"],
        "rules": [
            {
                "id": "NXT-001",
                "title": "Prefer Server Components by default; mark client islands with 'use client'",
                "severity": "should",
                "rationale": "Inverts the bundle-size cost compared to legacy React apps.",
            },
            {
                "id": "NXT-002",
                "title": "Data fetching via fetch() with revalidate; do not call APIs in client components",
                "severity": "should",
                "rationale": "Keeps the cache and ISR story consistent.",
            },
        ],
    },
    "remix": {
        "display_name": "Remix",
        "category": "frontend",
        "wave": 2,
        "stack_required": ["@remix-run/react>=2"],
        "rules": [
            {
                "id": "RMX-001",
                "title": "Loaders + actions; do not run mutations from client components",
                "severity": "must",
                "rationale": "Aligns with the framework's progressive-enhancement story.",
            },
        ],
    },
    "vue": {
        "display_name": "Vue",
        "category": "frontend",
        "wave": 2,
        "stack_required": ["vue>=3"],
        "rules": [
            {
                "id": "VUE-001",
                "title": "Composition API + <script setup> for new components",
                "severity": "should",
                "rationale": "Better TS inference and smaller bundle.",
            },
        ],
    },
    "nuxt": {
        "display_name": "Nuxt",
        "category": "frontend",
        "wave": 2,
        "stack_required": ["nuxt>=3", "vue>=3"],
        "rules": [
            {
                "id": "NUX-001",
                "title": "Use auto-imports judiciously; never re-export framework globals",
                "severity": "should",
                "rationale": "Auto-imports plus re-exports turn import-resolution into magic.",
            },
        ],
    },
    "svelte": {
        "display_name": "Svelte",
        "category": "frontend",
        "wave": 2,
        "stack_required": ["svelte>=5"],
        "rules": [
            {
                "id": "SVL-001",
                "title": "Use runes ($state, $derived) for new components",
                "severity": "should",
                "rationale": "The Svelte 5 reactivity model -- avoid mixing legacy stores.",
            },
        ],
    },
    "sveltekit": {
        "display_name": "SvelteKit",
        "category": "frontend",
        "wave": 2,
        "stack_required": ["@sveltejs/kit>=2"],
        "rules": [
            {
                "id": "SKT-001",
                "title": "Load functions per route; no top-level await fetches in components",
                "severity": "must",
                "rationale": "Keeps SSR vs CSR identical.",
            },
        ],
    },
    "angular": {
        "display_name": "Angular",
        "category": "frontend",
        "wave": 2,
        "stack_required": ["angular>=18"],
        "rules": [
            {
                "id": "NG-001",
                "title": "Standalone components by default; modules only when sharing across features",
                "severity": "should",
                "rationale": "Standalone removes the NgModule plumbing for ~95% of cases.",
            },
            {
                "id": "NG-002",
                "title": "Use signals for reactive state; RxJS for async streams only",
                "severity": "should",
                "rationale": "Signals are simpler and reviewable; RxJS for what truly needs streams.",
            },
        ],
    },
    "solidjs": {
        "display_name": "SolidJS",
        "category": "frontend",
        "wave": 3,
        "stack_required": ["solid-js>=1.8"],
        "rules": [
            {
                "id": "SOL-001",
                "title": "Read signals via getters; never destructure them",
                "severity": "must",
                "rationale": "Destructuring kills reactivity -- Solid's #1 gotcha.",
            },
        ],
    },
    "qwik": {
        "display_name": "Qwik",
        "category": "frontend",
        "wave": 3,
        "stack_required": ["@builder.io/qwik>=1"],
        "rules": [
            {
                "id": "QWK-001",
                "title": "Use $-suffixed lazy boundaries (component$, useTask$)",
                "severity": "must",
                "rationale": "That is the whole resumability story.",
            },
        ],
    },
    "astro": {
        "display_name": "Astro",
        "category": "frontend",
        "wave": 3,
        "stack_required": ["astro>=4"],
        "rules": [
            {
                "id": "AST-001",
                "title": "Islands only when interactive; ship zero-JS by default",
                "severity": "should",
                "rationale": "Astro's whole pitch -- defaulting to interactivity defeats it.",
            },
        ],
    },
    "preact": {
        "display_name": "Preact",
        "category": "frontend",
        "wave": 4,
        "stack_required": ["preact>=10"],
        "rules": [
            {
                "id": "PRC-001",
                "title": "Use ``preact/compat`` only when porting React libs",
                "severity": "may",
                "rationale": "Otherwise you pay the bundle cost of the compat shim for nothing.",
            },
        ],
    },
    "lit": {
        "display_name": "Lit",
        "category": "frontend",
        "wave": 4,
        "stack_required": ["lit>=3"],
        "rules": [
            {
                "id": "LIT-002",
                "title": "Reactive properties via decorators; no manual ``requestUpdate``",
                "severity": "should",
                "rationale": "Lit's lifecycle handles it correctly when you trust the decorators.",
            },
        ],
    },
    # ===================== HTML-FIRST =====================
    "htmx": {
        "display_name": "HTMX",
        "category": "frontend",
        "wave": 3,
        "stack_required": ["htmx>=2"],
        "rules": [
            {
                "id": "HTX-001",
                "title": "Server returns partials targeted by hx-target; no JSON parsing in browser",
                "severity": "must",
                "rationale": "That's the contract; JSON+HTML mixed defeats the model.",
            },
        ],
    },
    "hotwired": {
        "display_name": "Hotwired (Turbo + Stimulus)",
        "category": "frontend",
        "wave": 3,
        "stack_required": ["@hotwired/turbo>=8", "@hotwired/stimulus>=3"],
        "rules": [
            {
                "id": "HOT-001",
                "title": "Stimulus controllers stay tiny; logic on the server",
                "severity": "should",
                "rationale": "Hotwire shines when client code is glue, not logic.",
            },
        ],
    },
    "livewire": {
        "display_name": "Laravel Livewire",
        "category": "frontend",
        "wave": 4,
        "stack_required": ["livewire>=3"],
        "rules": [
            {
                "id": "LVW-001",
                "title": "Components remain stateless across requests where possible",
                "severity": "should",
                "rationale": "Smaller diffs over the wire = snappier UI.",
            },
        ],
    },
    "alpine": {
        "display_name": "Alpine.js",
        "category": "frontend",
        "wave": 3,
        "stack_required": ["alpinejs>=3"],
        "rules": [
            {
                "id": "ALP-001",
                "title": "Keep x-data shapes flat; avoid deeply nested state in attributes",
                "severity": "may",
                "rationale": "Readable in inspector and templates.",
            },
        ],
    },
    # ===================== CSS / UI =====================
    "tailwind": {
        "display_name": "Tailwind CSS",
        "category": "frontend",
        "wave": 1,
        "stack_required": ["tailwindcss>=4"],
        "rules": [
            {
                "id": "TWL-001",
                "title": "Centralize design tokens in tailwind.config; no magic numbers in classes",
                "severity": "should",
                "rationale": "Design-token drift is the recurring complaint on long-lived Tailwind apps.",
            },
        ],
    },
    "shadcn": {
        "display_name": "shadcn/ui",
        "category": "frontend",
        "wave": 2,
        "stack_required": ["shadcn-ui", "react>=19", "tailwindcss>=4"],
        "rules": [
            {
                "id": "SHD-001",
                "title": "Treat generated components as your code; do not refactor blindly across updates",
                "severity": "should",
                "rationale": "shadcn copies code in; that is the trade-off you opt into.",
            },
        ],
    },
    # ===================== MOBILE =====================
    "flutter": {
        "display_name": "Flutter",
        "category": "mobile",
        "wave": 1,
        "stack_required": ["flutter>=3.24", "dart>=3.4"],
        "rules": [
            {
                "id": "FLT-001",
                "title": "State via Riverpod or BLoC; no setState() beyond local UI bits",
                "severity": "should",
                "rationale": "Scales past the prototype-app phase.",
            },
            {
                "id": "FLT-002",
                "title": "Const constructors wherever possible",
                "severity": "should",
                "rationale": "Free rebuilds win.",
            },
        ],
    },
    "react-native": {
        "display_name": "React Native",
        "category": "mobile",
        "wave": 2,
        "stack_required": ["react-native>=0.76", "react>=19"],
        "rules": [
            {
                "id": "RN-001",
                "title": "Prefer Expo unless a native module forces a bare workflow",
                "severity": "should",
                "rationale": "Expo's tooling covers 90% of needs with a fraction of the upgrade pain.",
            },
        ],
    },
    "kotlin-multiplatform": {
        "display_name": "Kotlin Multiplatform",
        "category": "mobile",
        "wave": 3,
        "stack_required": ["kotlin>=2.0", "compose-multiplatform>=1.6"],
        "rules": [
            {
                "id": "KMP-001",
                "title": "Keep platform-specific code behind expect/actual boundaries",
                "severity": "must",
                "rationale": "Avoids leaking JVM-isms into iOS targets.",
            },
        ],
    },
    "ionic": {
        "display_name": "Ionic",
        "category": "mobile",
        "wave": 3,
        "stack_required": ["@ionic/core>=8"],
        "rules": [
            {
                "id": "ION-001",
                "title": "Use Capacitor plugins via DI; never reach into window.Capacitor directly",
                "severity": "should",
                "rationale": "Keeps tests possible.",
            },
        ],
    },
    "swiftui": {
        "display_name": "SwiftUI",
        "category": "mobile",
        "wave": 3,
        "stack_required": ["swift>=6"],
        "rules": [
            {
                "id": "SUI-001",
                "title": "Adopt Observable macro for view-models on iOS 17+",
                "severity": "should",
                "rationale": "Replaces ObservableObject + @Published boilerplate.",
            },
        ],
    },
    "jetpack-compose": {
        "display_name": "Jetpack Compose",
        "category": "mobile",
        "wave": 3,
        "stack_required": ["compose-bom>=2024.09", "kotlin>=2.0"],
        "rules": [
            {
                "id": "JPC-001",
                "title": "Hoist state; composables stay pure functions of inputs",
                "severity": "must",
                "rationale": "Recomposition correctness depends on it.",
            },
        ],
    },
    # ===================== DESKTOP =====================
    "tauri": {
        "display_name": "Tauri",
        "category": "desktop",
        "wave": 3,
        "stack_required": ["tauri>=2", "rust>=1.80"],
        "rules": [
            {
                "id": "TAU-001",
                "title": "Audit the allowlist on every release; no wildcard scopes",
                "severity": "must",
                "rationale": "Tauri's security model collapses with a broad allowlist.",
            },
        ],
    },
    "electron": {
        "display_name": "Electron",
        "category": "desktop",
        "wave": 4,
        "stack_required": ["electron>=31"],
        "rules": [
            {
                "id": "ELC-001",
                "title": "Context isolation on; sandbox renderer processes",
                "severity": "must",
                "rationale": "Renderer XSS becoming RCE is the canonical Electron failure mode.",
            },
        ],
    },
    "compose-multiplatform-desktop": {
        "display_name": "Compose Multiplatform (Desktop)",
        "category": "desktop",
        "wave": 4,
        "stack_required": ["compose-multiplatform>=1.6", "kotlin>=2.0"],
        "rules": [
            {
                "id": "CMD-001",
                "title": "Share UI; isolate platform integration (menus, dialogs) behind providers",
                "severity": "should",
                "rationale": "Keeps the platform-specific surface small.",
            },
        ],
    },
    # ===================== DATA / ML =====================
    "pytorch": {
        "display_name": "PyTorch",
        "category": "ml",
        "wave": 3,
        "stack_required": ["torch>=2.4"],
        "rules": [
            {
                "id": "PTH-001",
                "title": "Always set the device explicitly; no hidden cuda() calls in production code",
                "severity": "must",
                "rationale": "Silent CPU fallback is the canonical training-slowdown bug.",
            },
        ],
    },
    "tensorflow": {
        "display_name": "TensorFlow",
        "category": "ml",
        "wave": 4,
        "stack_required": ["tensorflow>=2.16"],
        "rules": [
            {
                "id": "TFL-001",
                "title": "Use Keras 3 functional API; avoid bespoke train loops unless required",
                "severity": "should",
                "rationale": "Faster ramp-up and better integration with TF tooling.",
            },
        ],
    },
    "jax": {
        "display_name": "JAX",
        "category": "ml",
        "wave": 4,
        "stack_required": ["jax>=0.4"],
        "rules": [
            {
                "id": "JAX-001",
                "title": "Pure functions only at jit boundaries; no closures over mutable state",
                "severity": "must",
                "rationale": "Jit traces are silent if you leak mutation.",
            },
        ],
    },
    "scikit-learn": {
        "display_name": "scikit-learn",
        "category": "ml",
        "wave": 3,
        "stack_required": ["scikit-learn>=1.5"],
        "rules": [
            {
                "id": "SKL-001",
                "title": "Wrap preprocessing + model in a Pipeline; no manual fit/transform stitching",
                "severity": "should",
                "rationale": "Prevents train/test leakage; mandatory for cross-validation correctness.",
            },
        ],
    },
    "langchain": {
        "display_name": "LangChain",
        "category": "ml",
        "wave": 3,
        "stack_required": ["langchain>=0.3"],
        "rules": [
            {
                "id": "LCH-001",
                "title": "Use LangGraph for any multi-step flow; avoid legacy AgentExecutor",
                "severity": "should",
                "rationale": "Graph control is observable and testable; the legacy executor is not.",
            },
        ],
    },
    "llamaindex": {
        "display_name": "LlamaIndex",
        "category": "ml",
        "wave": 3,
        "stack_required": ["llama-index>=0.11"],
        "rules": [
            {
                "id": "LMX-001",
                "title": "Persist indexes; do not rebuild on every process boot",
                "severity": "should",
                "rationale": "Rebuilds are the recurring cost overrun.",
            },
        ],
    },
    # ===================== DB / ORM =====================
    "postgres": {
        "display_name": "PostgreSQL",
        "category": "database",
        "wave": 2,
        "stack_required": ["postgresql>=16"],
        "rules": [
            {
                "id": "PG-001",
                "title": "Migrations checked into the repo; never alter prod schema by hand",
                "severity": "must",
                "rationale": "Hand edits are how environments drift apart.",
            },
        ],
    },
    "sqlalchemy": {
        "display_name": "SQLAlchemy",
        "category": "database",
        "wave": 2,
        "stack_required": ["sqlalchemy>=2.0"],
        "rules": [
            {
                "id": "SQA-001",
                "title": "Use 2.0-style typed Mapped[] declarations; avoid legacy declarative_base",
                "severity": "should",
                "rationale": "Type safety + IDE completion only work on the new API.",
            },
        ],
    },
    "prisma": {
        "display_name": "Prisma",
        "category": "database",
        "wave": 2,
        "stack_required": ["prisma>=5"],
        "rules": [
            {
                "id": "PRI-001",
                "title": "Run prisma migrate in CI on every PR touching the schema",
                "severity": "must",
                "rationale": "Catches drift before staging deploys do.",
            },
        ],
    },
    "drizzle": {
        "display_name": "Drizzle ORM",
        "category": "database",
        "wave": 3,
        "stack_required": ["drizzle-orm>=0.33"],
        "rules": [
            {
                "id": "DRZ-001",
                "title": "Keep schema and migrations side-by-side; lean on drizzle-kit",
                "severity": "should",
                "rationale": "Drizzle's perf+typing model assumes both stay in sync.",
            },
        ],
    },
    "doctrine": {
        "display_name": "Doctrine ORM",
        "category": "database",
        "wave": 1,
        "stack_required": ["doctrine/orm>=3"],
        "rules": [
            {
                "id": "DOC-002",
                "title": "Migrations via doctrine/migrations; never schema-update in prod",
                "severity": "must",
                "rationale": "schema:update on prod is how databases get silently corrupted.",
            },
        ],
    },
    # ===================== SYSTEMS =====================
    "c": {
        "display_name": "C",
        "category": "systems",
        "wave": 4,
        "stack_required": ["c-std>=c11"],
        "rules": [
            {
                "id": "CSY-001",
                "title": "Compile with -Wall -Wextra -Werror; run sanitizers in CI",
                "severity": "must",
                "rationale": "The bug class C is famous for is preventable with these on.",
            },
        ],
    },
    "cpp": {
        "display_name": "C++",
        "category": "systems",
        "wave": 4,
        "stack_required": ["cpp-std>=cpp20"],
        "rules": [
            {
                "id": "CPP-001",
                "title": "Smart pointers over raw new/delete; RAII for every resource",
                "severity": "must",
                "rationale": "Closes the entire manual-free bug class.",
            },
        ],
    },
    "zig": {
        "display_name": "Zig",
        "category": "systems",
        "wave": 4,
        "stack_required": ["zig>=0.13"],
        "rules": [
            {
                "id": "ZIG-001",
                "title": "Allocators passed explicitly; no global allocator state",
                "severity": "must",
                "rationale": "Zig's explicit-allocator model is the value proposition.",
            },
        ],
    },
    # ===================== INFRA / DEVOPS =====================
    "docker": {
        "display_name": "Docker",
        "category": "infra",
        "wave": 2,
        "stack_required": ["docker"],
        "rules": [
            {
                "id": "DCK-001",
                "title": "Multi-stage builds; do not ship build toolchains in runtime images",
                "severity": "should",
                "rationale": "Smaller images = faster deploys and smaller attack surface.",
            },
        ],
    },
    "kubernetes": {
        "display_name": "Kubernetes",
        "category": "infra",
        "wave": 3,
        "stack_required": ["kubernetes>=1.30"],
        "rules": [
            {
                "id": "KUB-001",
                "title": "Resource requests AND limits on every container",
                "severity": "must",
                "rationale": "Otherwise one workload starves the node.",
            },
        ],
    },
    "terraform": {
        "display_name": "Terraform",
        "category": "infra",
        "wave": 2,
        "stack_required": ["terraform>=1.9"],
        "rules": [
            {
                "id": "TF-001",
                "title": "Remote backend + state locking; never check tfstate into git",
                "severity": "must",
                "rationale": "State theft + state divergence are the canonical Terraform outages.",
            },
        ],
    },
    "github-actions": {
        "display_name": "GitHub Actions",
        "category": "infra",
        "wave": 2,
        "stack_required": ["github-actions"],
        "rules": [
            {
                "id": "GHA-001",
                "title": "Pin third-party actions to a commit SHA, not @main / @v1",
                "severity": "must",
                "rationale": "Supply-chain attacks via mutable tags are real and documented.",
            },
        ],
    },
    # ===================== API =====================
    "graphql": {
        "display_name": "GraphQL",
        "category": "api",
        "wave": 3,
        "stack_required": ["graphql"],
        "rules": [
            {
                "id": "GQL-001",
                "title": "Schema is source of truth; no resolver-level field hiding",
                "severity": "must",
                "rationale": "Hidden fields surface in introspection -- security through obscurity fails.",
            },
        ],
    },
    "grpc": {
        "display_name": "gRPC",
        "category": "api",
        "wave": 4,
        "stack_required": ["grpc", "protobuf"],
        "rules": [
            {
                "id": "GRP-001",
                "title": "buf lint + buf breaking on every PR touching .proto",
                "severity": "must",
                "rationale": "Breaking changes on proto are silent disasters at runtime.",
            },
        ],
    },
    "openapi": {
        "display_name": "OpenAPI",
        "category": "api",
        "wave": 2,
        "stack_required": ["openapi>=3.1"],
        "rules": [
            {
                "id": "OAS-001",
                "title": "Schema-first: write the spec, generate code/client; never the other way",
                "severity": "should",
                "rationale": "Server-driven schemas drift the moment two clients consume them.",
            },
        ],
    },
}


# ---------------------------------------------------------------------------
# Slug aliases -- map user-friendly names to canonical slugs.
# Users type "react-native" or "spring boot"; we normalise.
# ---------------------------------------------------------------------------

LANGUAGE_ALIASES: Final[dict[str, str]] = {
    "py": "python",
    "ts": "typescript",
    "js": "node",
    "javascript": "node",
    "nodejs": "node",
    "next": "nextjs",
    "next.js": "nextjs",
    "nest": "nestjs",
    "nest.js": "nestjs",
    "nuxt.js": "nuxt",
    "vuejs": "vue",
    "vue.js": "vue",
    "solid": "solidjs",
    "solid.js": "solidjs",
    "spring": "spring-boot",
    "springboot": "spring-boot",
    "rails-7": "rails",
    "ror": "rails",
    "rn": "react-native",
    "reactnative": "react-native",
    "kmp": "kotlin-multiplatform",
    "compose-mp": "compose-multiplatform-desktop",
    "tauri-app": "tauri",
    "k8s": "kubernetes",
    "tf": "terraform",
    "actix": "actix-web",
    "asp.net": "aspnet-core",
    "asp": "aspnet-core",
    "dotnetcore": "aspnet-core",
    "net": "dotnet",
    "csharp": "dotnet",
    "c#": "dotnet",
    "tw": "tailwind",
    "tailwindcss": "tailwind",
}


def normalize_slug(raw: str) -> str:
    """Map a free-form user slug to the registry key, or return it as-is."""
    key = raw.strip().lower()
    return LANGUAGE_ALIASES.get(key, key)


def known_languages() -> list[str]:
    """Return the sorted list of language slugs known to the scaffolder."""
    return sorted(LANGUAGE_TEMPLATES)


def known_languages_by_wave(wave: int) -> list[str]:
    """Return languages from the registry tagged with the given adoption wave."""
    return sorted(slug for slug, entry in LANGUAGE_TEMPLATES.items() if entry.get("wave") == wave)


def known_languages_by_category(category: str) -> list[str]:
    """Return languages from the registry grouped under ``category``."""
    return sorted(
        slug for slug, entry in LANGUAGE_TEMPLATES.items() if entry.get("category") == category
    )


def display_name(slug: str) -> str:
    """Return the pretty name for ``slug``; the slug itself if unknown."""
    entry = LANGUAGE_TEMPLATES.get(slug)
    if entry is None:
        return slug
    return str(entry["display_name"])


__all__ = [
    "BASELINE_RULES",
    "LANGUAGE_ALIASES",
    "LANGUAGE_TEMPLATES",
    "display_name",
    "known_languages",
    "known_languages_by_category",
    "known_languages_by_wave",
    "normalize_slug",
]
