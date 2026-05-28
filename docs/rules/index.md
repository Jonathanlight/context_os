# Rules catalog

The lint rules ContextOS ships today, grouped by category. Each rule has
a stable code (`A001`, `C001`, …), a severity, a doc page, and a concrete
suggestion the analyzer prints alongside the diagnostic.

## Categories

| Prefix | Category | Severity range | Count |
|---|---|---|---|
| **A** | [Ambiguity](#ambiguity-a) | warning | 4 |
| **C** | [Contradiction](#contradiction-c) | warning | 1 |
| **F** | [LLM-friendliness](#llm-friendliness-f) | warning | 3 |
| **K** | [Completeness](#completeness-k) | warning / info | 3 |
| **P** | [Platform](#platform-p) | warning | 3 |
| **R** | [RAG](#rag-r) | warning / info | 6 |
| **S** | [Skill](#skill-s) | warning / info | 6 |
| **X** | [Anti-pattern](#anti-pattern-x) | warning | 3 |
| **XA** | Cross-artifact | warning | 1 (in the audit) |

**27 rules shipped** — Phase 2 (15 agent rules) + Phase 5.4 (6 skill
rules) + Phase 6.4 (6 RAG rules). ContextOS now covers all three
artifact families end-to-end.

## Ambiguity (A)

Rules that fire when the directive isn't measurable. The LLM can't enforce
"be concise" without a number to compare against.

- [**A001** vague directive](A001.md) — `Be concise`, `Use good naming`, …
- [**A002** subjective adjective](A002.md) — `clean`, `proper`,
  `reasonable` in titles.
- [**A003** vague quantifier](A003.md) — `usually`, `most`, `rarely`.
- [**A004** hedging cadence](A004.md) — `regularly`, `as needed`,
  `when appropriate`.

## Contradiction (C)

Rules that fire when two rules disagree.

- [**C001** antonym overlap](C001.md) — `Always X` + `Never X` with a
  shared subject. Heuristic, ~80% precision; NLI-based detection lands
  post-MVP.

## LLM-friendliness (F)

Formatting issues that hurt the model even when the underlying directive
is fine.

- [**F001** excessive ALL CAPS](F001.md) — uppercase ratio ≥ 70% in a
  long-enough title.
- [**F002** rule title too long](F002.md) — > 120 characters.
- [**F003** duplicate rule](F003.md) — same normalized title in two rules.

## Completeness (K)

Gaps that hurt the LLM's ability to operationalize the rules.

- [**K001** no rules declared](K001.md) — the `[[rules]]` section is
  empty or missing.
- [**K002** must-rule without rationale](K002.md) — strongest severity,
  no justification.
- [**K003** must-rule without examples](K003.md) — no `example_good` or
  `example_bad` (INFO, not WARNING).

## Platform (P)

Author-specific or machine-specific state leaking into a shared artifact.

- [**P001** personal absolute path](P001.md) — `/Users/alice/...`.
- [**P002** email address in title](P002.md) — belongs in `author` or
  `links`.
- [**P003** bare URL in title](P003.md) — belongs in `links`.

## RAG (R)

Phase 6 lint rules for `.ctx` files declaring `artifacts=['rag']`. Two
themes: chunking-sanity (chunk-size choices that produce pathological
retrieval) and pipeline-completeness (gaps the downstream indexer
can't fill in).

- [**R001** excessive chunk overlap](R001.md) — overlap > 50% of
  target.
- [**R002** tight target/max headroom](R002.md) — max < 120% of target
  (info).
- [**R003** missing freshness_policy](R003.md) — stale docs never
  marked (info).
- [**R004** missing embedding_model](R004.md) — indexers cannot pick
  deterministically.
- [**R005** header_aware override without anchors](R005.md) — chunker
  has nothing to anchor on (info).
- [**R006** large source without chunking override](R006.md) — long
  docs fragment poorly (info).

## Skill (S)

Phase 5 lint rules for `SKILL.md` files. Two themes: description
quality (the routing signal) and body / metadata coherence.

- [**S001** description has no trigger phrasing](S001.md) — silent
  "skill never fires" bug class.
- [**S002** description is too short](S002.md) — under 50 visible chars.
- [**S003** description is approaching the hard cap](S003.md) — soft
  cap 800 / hard cap 1024 (info).
- [**S004** missing `example_invocation`](S004.md) — concrete trigger
  sample (info).
- [**S005** body H1 missing or mismatched](S005.md) — metadata / prose
  drift (info).
- [**S006** `trigger_keywords` already in description](S006.md) —
  redundant keyword list (info).

## Anti-pattern (X)

Titles that look like authoring mistakes — placeholders, template
artifacts, directives phrased as questions.

- [**X001** placeholder marker](X001.md) — `TODO`, `FIXME`, `XXX`, `HACK`
  whole-token in a title.
- [**X002** unfilled template placeholder](X002.md) — `<DB_DRIVER>`,
  `{your_project_name}`, `[INSERT FOO]`.
- [**X003** question instead of directive](X003.md) — title ending in `?`.

## Cross-artifact (XA)

Run only by `ctx audit`. These rules need to see multiple files.

- **XA001** rule id collision — same `Rule.id` across multiple files
  with different content (title/severity). See the audit output rather
  than a single-file lint.

## Severity model

| Severity | Effect on `ctx lint` exit code | Use case |
|---|---|---|
| `error` | exits 1 | Hard failure — file cannot be used as-is |
| `warning` | exits 0 | Diagnostic worth noting; CI doesn't break |
| `info` | exits 0 | Hint, not a defect |

Today every rule ships at `warning` (Phase 2) or `info` (K003). The
`error` tier will land with the NLI-based contradiction detector and
stricter platform rules.
