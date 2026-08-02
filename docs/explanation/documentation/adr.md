---
audience: human, ai
status: stable
skills: [documentor]
---

# Architecture Decision Records (ADRs)

> ADRs capture important architectural decisions along with their context and consequences. For a thorough introduction, see [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) by Michael Nygard, the essay that popularized the format.

## ADR Format

```markdown
# ADR-NNN: Title

## Status

Proposed | Accepted | Deprecated | Superseded by ADR-NNN

## Context

What is the issue that we are seeing that is motivating this decision?

## Decision

What is the change that we are proposing and/or doing?

## Consequences

What becomes easier or harder to do because of this change?
```

## ADR Best Practices

- Number sequentially, never reuse numbers
- Keep each ADR focused on a single decision
- Record the date of the decision
- Link to related ADRs
- Update status when superseded (do not delete old ADRs)
- Store in `docs/adr/` or `docs/decisions/`
- Include ADR index in project documentation

## ADR Distillation

The ADR distiller automatically finds ADRs in the project's documentation folder and distills each **Accepted** ADR into a one-line directive in `adr-distilled.md`. This file lives in the ADR directory (e.g. `docs/adr/adr-distilled.md`) and serves as an executable architectural manifest — a quick-reference index of the rules in force.

### How it works

1. **Setup** detects the ADR folder and stores its path as `documentation.adrs` in `settings.json` (or `null` if no ADRs found).
2. **Review** runs the distiller, which extracts the Decision section from each Accepted ADR and produces a directive with a markdown link to the source ADR.
3. An **mtime cache** tracks changes — only new, stale (modified), and removed ADRs are re-distilled on each review run.
4. The orchestrator **refines** stale/new directives into concise one-liners (agent LLM).
5. **Review subagents** read `adr-distilled.md` as architectural context and use judgment to check whether code aligns with each directive.

### What gets distilled

Only ADRs with Status `Accepted` are included. Proposed, Deprecated, and Superseded ADRs are excluded — the distilled file represents the rules in force, not proposals or retired decisions.

### Directive format

Each directive is a single line with a link to the source ADR:

```markdown
- [ADR-001](adr/0001-use-postgres.md) Use PostgreSQL for the primary database instead of MySQL.
- [ADR-003](adr/0003-adopt-microservices.md) Adopt microservices architecture for the platform.
```

### Binary vs nuanced directives

Review subagents read the directives and use judgment to determine whether each is binary or nuanced:

- **Binary directives** (e.g., "use PostgreSQL", "use async events for inter-service communication") — clear violations are flagged as findings.
- **Nuanced directives** (e.g., "adopt microservices", "prefer composition over inheritance") — deviations are noted as observations with context, not findings.

The directive's content tells the reviewer whether it's binary or nuanced. No severity tag system is used — the ADR Status field is used only as a filter (Accepted = in, everything else = out).

### Examples

The [euforicio/adr-demo](https://github.com/euforicio/adr-demo) repository (a fictional e-commerce "ShopFlow" platform with 10 ADRs covering all statuses) provides realistic examples:

- **Accepted ADR** → distills to a directive with a link (e.g., "Adopt microservices architecture" → `- [ADR-0003](adr/0003-adopt-microservices.md) Adopt microservices architecture for the platform.`)
- **Proposed ADR** → excluded from the distilled file (not yet a decision in force)
- **Deprecated/Superseded ADR** → excluded (no longer active)

### Attribution

This approach is inspired by the concept of declarative architectural governance described in [Architectural Governance at AI Speed](https://www.infoq.com/articles/architectural-governance-ai-speed/) (InfoQ, 2026), which proposes distilling ADRs into machine-enforceable `architecture.md` directives.
