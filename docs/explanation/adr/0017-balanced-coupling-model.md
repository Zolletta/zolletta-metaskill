# ADR-0017: Balanced Coupling model for the patterns review

## Status

Accepted

## Context

Issue #46 asks the `patterns` skill to evaluate not just intra-class
structure (God class detection, SOLID) but the coupling *between* parts
of the codebase: whether knowledge leaks across boundaries and whether
that coupling is balanced given distance and volatility.

Martin Fowler's [Maintainability sensors for coding
agents](https://martinfowler.com/articles/sensors-for-coding-agents.html)
identifies modularity/coupling as a dimension where agents consistently
produce failures. Vlad Khononov's Balanced Coupling model (published
openly at [coupling.dev](https://coupling.dev) and in *Balancing
Coupling in Software Design*) gives an actionable verdict rule:
`BALANCE = (STRENGTH xor DISTANCE) or (not VOLATILITY)` — only an
integration that is simultaneously strong, distant, and volatile is a
complexity finding.

ADR-0011 rejected external dependency-inspector tools as non-zero-config
and explicitly carved out *inferential* modularity review as unaffected.
The reference implementation (`vladikk/modularity`, a Claude Code
plugin) is interactive and licensed CC BY-NC-SA 4.0 — its skill files
cannot be copied.

## Decision

Adopt the Balanced Coupling model in the `patterns` review, split the
repo's standard way — deterministic triage via script, verdict via
judgment:

- **New scanner** `integration_graph_scanner.py` (patterns/general) —
  language-agnostic via `LanguageEngine`/`ModuleInfo.imports`, following
  the standard script CLI (ADR-0015): `[--json]` only, roots and
  languages from `settings.json`, git-ignore aware, report-only. It
  emits *internal* edges only — imports resolving to files inside the
  scanned tree — each with a per-name `usage` hint (`call`/`new`,
  `extends`, `type`, `attribute`, `import-only`) as the deterministic
  signal for strength classification, plus per-module fan-in/fan-out.
  External/stdlib imports are counted, never turned into edges.
- **New mandatory reference** `docs/explanation/code/balanced-coupling.md`
  restating the model in original wording — dimensions, strength levels
  mapped to the usage hints, distance, DDD-subdomain volatility (never
  commit history), the balance rule, verdict table, and the
  assumption-noting convention for inferred classifications.
- **New Phase C judgment item** in the patterns protocol: classify each
  cross-module edge's strength/distance/volatility, apply the balance
  rule, flag **unbalanced-and-volatile only** — the same severity
  discipline as `false-positive-prevention.md` applies to God classes.
- **Zero-config**: no `settings.json` keys — the scanner reads only the
  existing language fields.
- **Review-only scope**: no `design`-mode equivalent.
- The reference plugin's skill files were not copied; the model is
  restated from the openly published source.

## Consequences

**Positive:**

- The patterns review gains a principled answer to "is this coupling a
  problem" — the balance rule converts a fuzzy judgment into a
  repeatable verdict with explicit assumptions.
- Usage hints give the judgment pass deterministic triage signal
  without a dependency-inspector dependency (ADR-0011 unchanged).
- Everything inferred is marked as an assumption, so humans can override
  with domain knowledge the code doesn't carry.

**Negative:**

- Edge resolution is approximate (PSR-4 mapping, package/`__init__`
  resolution, lost relative-import depth) — unresolved imports degrade
  to external counts, never false edges.
- Usage hints are shallower for PHP (tree-sitter node kinds) than for
  Python (full `ast` walk) — documented as a known limitation; the
  judgment pass reads flagged files anyway.
- A new mandatory doc grows the review's required reading.

**Neutral:**

- The integration graph may also serve future structural analyses, but
  none are committed to here.
