---
audience: ai, human
status: stable
skills: [review]
description: "Balanced Coupling model for the patterns review: triage plus judgment pass on volatile integrations."
---

# ADR-0008: Balanced Coupling model for the patterns review

## Status

Accepted

## Context

The patterns review evaluated intra-class structure (God classes, SOLID) but had no principled answer to "is this coupling a problem" — whether knowledge leaks across module boundaries. Vlad Khononov's Balanced Coupling model (coupling.dev, *Balancing Coupling in Software Design*) gives an actionable verdict rule: `BALANCE = (STRENGTH xor DISTANCE) or (not VOLATILITY)` — only an integration that is simultaneously strong, distant, and volatile is a complexity finding. External dependency-inspector tools are excluded by ADR-0007; inferential modularity review is unaffected.

## Decision

The patterns review applies the Balanced Coupling model: graph triage plus a judgment pass flagging only unbalanced-and-volatile edges.

- **Deterministic triage.** `integration_graph_scanner.py` (language-agnostic via `LanguageEngine`/`ModuleInfo.imports`, `[--json]` only, git-ignore aware, report-only) emits *internal* edges with a per-name `usage` hint (`call`/`new`, `extends`, `type`, `attribute`, `import-only`) as the strength signal, plus fan-in/fan-out per module. External/stdlib imports are counted, never turned into edges.
- **Judgment pass.** The patterns protocol classifies each cross-module edge's strength/distance/volatility (DDD-subdomain inference, never commit history), applies the balance rule, and flags only unbalanced-and-volatile integrations — same severity discipline as God class findings. Inferred classifications are marked as assumptions for human override.
- **Required reading.** `docs/explanation/code/balanced-coupling.md` restates the model in original wording (dimensions, verdict table, assumption convention); the reference implementation's skill files were not copied (CC BY-NC-SA).

## Consequences

**Positive:**

- A fuzzy judgment becomes a repeatable verdict with explicit assumptions — the balance rule, not reviewer taste, decides what is flagged.
- Usage hints give deterministic triage without a dependency-inspector dependency.

**Negative:**

- Edge resolution is approximate (PSR-4 mapping, `__init__` resolution, relative-import depth); unresolved imports degrade to external counts, never false edges.
- PHP usage hints are shallower than Python's (tree-sitter node kinds vs full `ast` walk) — documented limitation; the judgment pass reads flagged files anyway.

**Neutral:**

- The integration graph may serve future structural analyses; none are committed here.
