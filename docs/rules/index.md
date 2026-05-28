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
| **X** | [Anti-pattern](#anti-pattern-x) | warning | 3 |
| **XA** | Cross-artifact | warning | 1 (in the audit) |

**Phase 2 deliverable** — 15 rules. Phase 5 adds Skills rules (S***);
Phase 6 adds RAG rules (R***).

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
