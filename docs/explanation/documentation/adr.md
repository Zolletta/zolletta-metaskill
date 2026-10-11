---
audience: human, ai
status: stable
skills: [documentor]
---

# Architecture Decision Records (ADRs)

> ADRs capture important architectural decisions along with their context and consequences. For a thorough introduction, see [Documenting Architecture Decisions](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions) by Michael Nygard, the essay that popularized the format.

## Architecture, not activity

The A in ADR stands for **Architecture**, not activity. An ADR states a standing constraint on the system's structure, boundaries, or behavior that future work must obey or supersede. Records of work done — tool evaluations, feature-adds, migrations — are activities and belong in a log, not in the corpus. This distinction is operational: every `Accepted` ADR is distilled into a directive that review subagents enforce, so activity records must never reach `Accepted` status in the corpus.

This project's corpus follows [ADR-0000](../adr/architecture/0000-adrs-record-architecture-not-activity.md):

- Architecture ADRs live in `docs/explanation/adr/architecture/` — the only directory the distiller reads.
- Optional activity records (evaluations, feature-adds, rejected alternatives) live in `docs/explanation/adr/activity/` — never distilled, excluded from the published site. The routing rules are in the [ADR directory guide](../adr/README.md).
- The pre-reform corpus (ADR-0001–0017) was consolidated into the current ADRs or removed — decode old numbering references through git history.

## ADR Format

```markdown
# ADR-NNNN: Title

## Status

Proposed | Accepted | Superseded by ADR-NNNN

## Context

What is the issue that we are seeing that is motivating this decision?

## Decision

What is the change that we are proposing and/or doing?

## Consequences

What becomes easier or harder to do because of this change?
```

## ADR Status Lifecycle

- **Proposed** — under discussion, not in force. Never distilled; may be edited freely or withdrawn.
- **Accepted** — in force and distilled. Once Accepted, the record's content and status are immutable: corrections and evolutions happen by supersession, never by editing or demoting the record.
- **Superseded by ADR-NNNN** — terminal, and the only permitted transition out of Accepted. The superseding ADR links back to the record it replaces; the superseded file stays in the corpus as history.

`Deprecated` is not a valid status in this project — retirement is supersession.

## ADR Best Practices

- Number sequentially, never reuse numbers
- Keep each ADR focused on a single standing decision
- Record the date of the decision
- Link to related ADRs, and always link back from a superseding ADR
- Never edit an Accepted ADR — supersede it
- Write the first line of the Decision section as a complete single-line sentence: the distiller uses exactly that line as the enforced directive
- Include an ADR index in project documentation

## ADR Distillation

The ADR distiller finds ADRs under the directory configured as `documentation.adrs` in `settings.json` (this project: `docs/explanation/adr/architecture/`) and distills each **Accepted** ADR into a one-line directive in `adr-distilled.md`. The generated file lives inside the ADR corpus directory and serves as an executable architectural manifest — a quick-reference index of the rules in force.

### How it works

1. **Setup** detects the architecture ADR folder (`adr/architecture/` when present) and stores its path as `documentation.adrs` in `settings.json` (or `null` if no ADRs found).
2. **Review** runs the distiller, which extracts the first line of the Decision section of each Accepted ADR and produces a directive with a markdown link to the source ADR.
3. An **mtime cache** tracks changes — only new, stale (modified), and removed ADRs are re-distilled on each review run.
4. The orchestrator **refines** stale/new directives into concise one-liners (agent LLM).
5. **Review subagents** read `adr-distilled.md` as architectural context and use judgment to check whether code aligns with each directive.

### What gets distilled

Only ADRs with Status `Accepted` are included. Proposed and Superseded ADRs are excluded — the distilled file represents the rules in force, not proposals or retired decisions. Activity records are excluded by construction: discovery reads only the configured `architecture/` directory.

### Directive format

Each directive is a single line with a link to the source ADR:

```markdown
- [ADR-0001](0001-use-postgres.md) Use PostgreSQL for the primary database instead of MySQL.
- [ADR-0003](0003-adopt-microservices.md) Adopt microservices architecture for the platform.
```

### Binary vs nuanced directives

Review subagents read the directives and use judgment to determine whether each is binary or nuanced:

- **Binary directives** (e.g., "use PostgreSQL", "use async events for inter-service communication") — clear violations are flagged as findings.
- **Nuanced directives** (e.g., "adopt microservices", "prefer composition over inheritance") — deviations are noted as observations with context, not findings.

The directive's content tells the reviewer whether it's binary or nuanced. No severity tag system is used — the ADR Status field is used only as a filter (Accepted = in, everything else = out).

### Examples

The [euforicio/adr-demo](https://github.com/euforicio/adr-demo) repository (a fictional e-commerce "ShopFlow" platform with 10 ADRs covering all statuses) provides realistic examples:

- **Accepted ADR** → distills to a directive with a link (e.g., "Adopt microservices architecture" → a line like `` `- [ADR-0003](0003-adopt-microservices.md) Adopt microservices architecture for the platform.` ``)
- **Proposed ADR** → excluded from the distilled file (not yet a decision in force)
- **Superseded ADR** → excluded (no longer active)

### Attribution

This approach is inspired by the concept of declarative architectural governance described in [Architectural Governance at AI Speed](https://www.infoq.com/articles/architectural-governance-ai-speed/) (InfoQ, 2026), which proposes distilling ADRs into machine-enforceable `architecture.md` directives.
