---
audience: ai
status: generated
description: "Auto-generated architectural directives distilled from Accepted ADRs."
---

# adr-distilled.md — Architectural Directives

> Auto-generated from the project's ADRs by the adr-distiller.
> Do not edit directly — edit the source ADRs and re-run `/zolletta-metaskill adr-distiller` or `/zolletta-metaskill review`.
> Each directive links to its source ADR for full context. Only Accepted decisions are included.

- [ADR-0000](0000-adrs-record-architecture-not-activity.md) ADRs in this corpus record standing architectural decisions, never activities.
- [ADR-0001](0001-meta-skill-architecture.md) A single meta-skill (/zolletta-metaskill with a subcommand) dispatches to sub-skills under skills/, and review runs parallel background subagents.
- [ADR-0002](0002-configuration-architecture.md) .zolletta-metaskill/settings.json is the single configuration source, guarded for freshness, read via [--json]-only CLIs, and resolved once into immutable structs.
- [ADR-0003](0003-diataxis-documentation-structure.md) Project documentation follows the Diátaxis framework with tutorials/, how-to/, reference/, explanation/ quadrants.
- [ADR-0004](0004-scanner-constraints.md) All scanning and detection scripts use the Python standard library only and are unit-testable modules, never inline skill logic.
- [ADR-0005](0005-language-neutral-engine-protocol.md) Scanners consume a language-neutral ModuleInfo model produced by LanguageEngine implementations, never language-specific ASTs.
- [ADR-0006](0006-adr-governance-pipeline.md) Accepted ADRs are distilled into adr-distilled.md directives, synced by an mtime cache, enforced by review subagents.
- [ADR-0007](0007-sensor-adoption-criteria.md) A tool joins the review pipeline only if it is zero-config, bounded in review-time cost, structured-output, maintainability-primary.
- [ADR-0008](0008-balanced-coupling-model.md) The patterns review applies the Balanced Coupling model: graph triage plus a judgment pass flagging only unbalanced-and-volatile edges.
