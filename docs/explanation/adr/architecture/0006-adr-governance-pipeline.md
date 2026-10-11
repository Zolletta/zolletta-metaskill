---
audience: ai, human
status: stable
skills: [review]
description: "ADR governance pipeline: Accepted ADRs distilled into adr-distilled.md directives enforced by review."
---

# ADR-0006: ADR governance pipeline — Accepted-only distillation into enforced directives

## Status

Accepted

## Context

Review subagents had no awareness of the project's architectural decisions — code violating an accepted decision passed review silently. The InfoQ article *Architectural Governance at AI Speed* (2026) proposes distilling ADRs into machine-enforceable directives so the conformant path becomes the path of least resistance. This ADR defines the pipeline's architecture; it works in tandem with ADR-0000, which defines what may enter the corpus the pipeline reads.

## Decision

`Accepted` ADRs are distilled into `adr-distilled.md` directives, synced by an mtime cache, enforced by review subagents.

The mechanics:

- **Source of truth.** `documentation.adrs` in `settings.json` points at the corpus directory (`adr/architecture/` — see ADR-0000); the distiller reads only that directory.
- **Directive format.** `- [ADR-NNNN](file.md) <decision>` — the ADR reference as a link plus the decision, mechanically extracted from the first non-empty line of `## Decision`, then optionally refined by the orchestrator into a concise one-liner. Distillable ADRs state the complete rule on that line.
- **Status as filter, not severity.** Only `Accepted` enters the file. `Proposed`, `Superseded`, and everything else is excluded — the distilled file is the rules in force. Binary vs nuanced judgment is left to the reviewing LLM; no `[Block]`/`[Warn]` mapping is applied.
- **Incremental sync.** An mtime cache (`.zolletta-metaskill/adr-cache.json`, machine-local, gitignored) classifies ADRs as new/stale/removed/dropped; unchanged directives — including agent-refined text — are preserved.
- **Consumption.** The review orchestrator inlines the distilled file into `cache/_context.md`; subagents apply judgment per directive.

## Consequences

**Positive:**

- Subagents gain architectural awareness from the project's own decisions — the configuration-free way to make reviewers architecture-aware.
- The distilled file doubles as a quick-reference index for humans (onboarding, auditing).
- mtime caching makes refreshes incremental; deterministic regeneration means no noisy diffs.

**Negative:**

- Binary-vs-nuanced judgment is non-deterministic across reviews — the deliberate tradeoff for not conflating acceptance with criticality.
- Only the Nygard heading format (`# ADR-NNNN:` + `## Status` + `## Decision`) is detected; other formats are a known limitation.
- Directives depend on first-line discipline — a decision split across lines distills poorly until hand-refined.

**Neutral:**

- `adr-distilled.md` is committed (auto-generated but deterministic); the cache is not.
- Demoted ADRs (Accepted → anything else) drop their directive via `report.dropped`; removed ADRs via `report.removed`.
