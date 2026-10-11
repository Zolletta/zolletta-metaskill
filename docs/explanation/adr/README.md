---
audience: ai, human
status: stable
skills: [review]
description: "Routing guide: which records belong in architecture/ versus activity/."
---

# ADR directory guide

Two folders, two kinds of record.

## `architecture/` — the corpus

Standing architectural decisions in Nygard format (`# ADR-NNNN:` + `## Status` + `## Decision`). This is the **only** directory the ADR distiller reads (`documentation.adrs` in `.zolletta-metaskill/settings.json` points here), and every `Accepted` record becomes an enforced directive in `adr-distilled.md`. Lifecycle — Proposed, Accepted, Superseded — is defined by [ADR-0000](architecture/0000-adrs-record-architecture-not-activity.md). Numbering is append-only; Accepted records are immutable and change only through supersession.

## `activity/` — the log

Records of work done that are **not** standing architecture: tool evaluations, migrations, feature-adds, rejected alternatives. Put a record here when it documents something the codebase cannot — above all, why something was *not* adopted, so it is not re-proposed and re-argued from scratch.

Rules for activity records:

- Use an `# ACT-NNN:` heading, never `# ADR-NNNN:` — the heading is what keeps discovery and distillation out of this folder.
- No `## Status` section — these records are not decisions in force and carry no lifecycle.
- Delete a record once its durable content is absorbed into the corpus or is self-evident from the code; the original remains in git history.
- Nothing here is distilled, enforced, or published to the documentation site.

When in doubt: if the record states a rule future work must obey, it is an ADR — write it in `architecture/`. If it explains something that happened, it is activity — it goes here.
