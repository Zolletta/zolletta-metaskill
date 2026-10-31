---
audience: ai, human
status: stable
skills: [review]
description: "ADR governance: architecture not activity; status lifecycle, corpus layout, supersession rules."
---

# ADR-0000: ADRs record architecture, not activity

## Status

Accepted

## Context

The ADR corpus drifted toward activity logging: alongside structural decisions it accumulated evaluation write-ups ("we surveyed tool X and rejected it") and feature-add records ("we built Y"). Because every `Accepted` ADR is distilled into a directive that review subagents enforce (ADR-0006), the distinction is operational, not cosmetic — activity records should not produce enforced directives.

The A in ADR stands for **Architecture**, not *activity*. An ADR states a standing constraint on the system's structure, boundaries, or behavior that future work must obey or supersede. Records of work done — evaluations, feature-adds, migrations — are activities and belong in a log, not in the corpus.

## Decision

ADRs in this corpus record standing architectural decisions, never activities.

The corpus lives in `docs/explanation/adr/architecture/` and is the **only** directory the distiller reads (`documentation.adrs` must point at it). Activity records are not part of the corpus at all — evaluations and feature-adds may be kept in `adr/activity/` as ordinary documentation (`ACT-` headings, no status, never distilled), or simply left to git history.

### Statuses

An ADR carries exactly one of these statuses:

- **Proposed** — under discussion, not in force. Never distilled, may be edited freely, may be withdrawn (removed from the corpus).
- **Accepted** — in force. Distilled into `adr-distilled.md`. Once Accepted, the ADR's content **and** status are immutable — wording fixes are made by supersession, not edits.
- **Superseded by ADR-NNNN** — terminal. The only permitted transition out of Accepted. The superseding ADR must link back to the record it replaces. The superseded file remains in the corpus as history.

`Deprecated` is not a valid status: retirement is supersession — a newer ADR takes over and the superseded file stays in the corpus as history.

### Numbering

Numbers are append-only and never reused. The pre-reform namespace ADR-0001–ADR-0017 is closed; those records were consolidated into this corpus or removed, and the originals remain decodable through git history.

## Consequences

**Positive:**

- `adr-distilled.md` reflects only standing architecture — the file review subagents enforce cannot be polluted by evaluation logs or change records.
- Immutability makes `Accepted` a trustworthy signal: what you read is what was decided, and any evolution is explicit via supersession links.
- No parallel namespace to maintain — pre-reform records stay decodable through git history rather than a shadow archive.

**Negative:**

- Corrections cost a new ADR rather than an edit — deliberate friction, so changes to in-force decisions are always traceable.
- Superseded files accumulate in the corpus; that is the price of an honest decision history.

**Neutral:**

- This ADR is self-referential: it defines the convention it follows.
- The one-time corpus rewrite that created this directory is the founding act and exempt from the immutability rule.
