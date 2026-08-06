---
name: zolletta-metaskill-adr-distiller
description: >
  Distill Accepted Architecture Decision Records (ADRs) into a single
  adr-distilled.md directives file. Discovers ADRs, compares mtimes against
  a cache, mechanically extracts one-line directives from the Decision
  section, and writes the distilled file for review subagents to read.
  Use when refreshing architectural directives before a review.
license: MIT + Commons Clause
---

# Zolletta-metaskill ADR Distiller

Distills **Accepted** ADRs into a single `adr-distilled.md` file containing one-line architectural directives, each linking back to its source ADR.

The distiller uses an mtime cache so only **new**, **stale** (modified), and **removed** ADRs are re-processed on subsequent runs. Directives for up-to-date ADRs (including agent-refined text) are preserved.

> ADR distillation inspired by [Architectural Governance at AI Speed](https://www.infoq.com/articles/architectural-governance-ai-speed/) (InfoQ, 2026).

## When to run

- **During review** — the `review` orchestrator calls this subcommand at
  Step 3.5 to refresh `adr-distilled.md` before launching review subagents.
- **Standalone** — run `/zolletta-metaskill adr-distiller` to refresh
  directives without a full review (e.g. after adding a new ADR).

## Prerequisites

1. `.zolletta-metaskill/settings.json` must exist (run `setup` first).
2. Read `documentation.adrs` and `documentation.dir` from `settings.json`.
3. If `documentation.adrs` is `null`, exit immediately — no ADRs configured.

## Procedure

### Step 1 — Run the distiller

```bash
python3 ../../src/zolletta_metaskill/adr/adr_orchestrator.py \
  --docs-dir <docs_dir> \
  --adrs-path <adrs_path> \
  --json
```

The orchestrator:
1. Discovers ADR files in `<docs_dir>/<adrs_path>/`.
2. Compares mtimes against the cache at `.zolletta-metaskill/adr-cache.json`.
3. Re-distills **new** and **stale** ADRs (Accepted status only).
4. Removes directives for **removed** ADRs.
5. Preserves up-to-date directives (including any agent refinements).
6. Writes the updated `adr-distilled.md` and cache.

### Step 2 — Parse the JSON report

The `--json` flag outputs a report like:

```json
{
  "has_adrs": true,
  "new": ["0007-async-event-bus"],
  "stale": ["0003-use-postgresql"],
  "removed": ["0002-old-approach"]
}
```

If `has_adrs` is `false`, no Accepted ADRs were found — print a message and exit.

### Step 3 — Refine new and stale directives

For each ADR in `new` and `stale`:

1. Read the source ADR file.
2. Read the mechanically-extracted directive in `adr-distilled.md`.
3. Refine it into a concise one-liner that captures the architectural
   decision. Preserve category headings if present.
4. Write the refined directive back to `adr-distilled.md`.

The mechanical extraction pulls the first sentence from the Decision section — it is a starting point, not the final form. A human-readable one-liner is more useful for review subagents.

### Step 4 — Report

Print a summary:

```
ADR Directives Refreshed
========================
New:      2  (0007-async-event-bus, 0009-cqrs-read-models)
Stale:    1  (0003-use-postgresql)
Removed:  0
Total:    8 directives in adr-distilled.md
```

## Files

| File         | Location                                         | Purpose                                                         |
|--------------|--------------------------------------------------|-----------------------------------------------------------------|
| Orchestrator | `src/zolletta_metaskill/adr/adr_orchestrator.py` | Coordinates discovery + distillation + cache                    |
| CLI          | `src/zolletta_metaskill/adr/adr_cli.py`          | CLI entry point — argument parsing, report formatting, `main()` |
| Discovery    | `src/zolletta_metaskill/adr/adr_discovery.py`    | Finds ADR files, parses status                                  |
| Distiller    | `src/zolletta_metaskill/adr/adr_distiller.py`    | Extracts directive from a single ADR                            |
| Cache        | `src/zolletta_metaskill/adr/adr_cache.py`        | mtime cache (`.zolletta-metaskill/adr-cache.json`)              |
| Structs      | `src/zolletta_metaskill/adr/structs/`            | `ADRRecord`, `DistillReport` data models                        |
| Output       | `<docs_dir>/<adrs_path>/adr-distilled.md`        | Distilled directives file                                       |
