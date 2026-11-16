---
audience: ai, human
status: stable
skills: [grice, review, setup]
description: "The grice report is a deterministic triage — per-group summary, structural defects, outliers with rule-based diagnosis, benchmarks — computed by the scanner over a corpus without ADRs; it carries no grade and its SUMMARY row shows the corpus median plus the defect count."
---

# ADR-0014: The Grice report is a deterministic triage, not a grade

> **Superseded.** This record is kept as history per [ADR-0000](0000-adrs-record-architecture-not-activity.md). [ADR-0015](0015-grice-triage-is-per-group.md) carries its rules forward and splits the triage per group: one outlier table and up to five benchmarks (balanced plus the top on each maxim) per group, no `benchmark_count` setting, and no abbreviated metric names.

## Status

Superseded by [ADR-0015](0015-grice-triage-is-per-group.md)

## Context

The grice report opened with a 0-100 grade next to 0-100 corpus-relative indices, which invited reading 50 as a pass mark. Real runs on large corpora (300+ documents) produced a single flat table that a reader could not triage: the documents worth opening first were not selected, the structural defects were repeated once per linking page, and ADRs — whose hypothetical wording is what the genre demands — surfaced as expected false positives while shifting every other percentile. Corpora are also laid out differently: some split `current/` and `old/`, most do not, so any rule keyed on directory meaning would fit one project and misfire on the next.

## Decision

The grice report is a deterministic triage computed by the scanner over a corpus without ADRs, carries no grade, and is written in the invocation language.

- **No grade.** The report opens with an Executive Summary: one row per group with document count, median `grice_index`, outlier count and defect count. The review SUMMARY row shows the corpus median `grice_index` and the number of defects, still advisory and never weighted.
- **The scanner computes everything; the LLM only lays it out.** Groups, outliers, positive benchmarks, the rule-based diagnosis and the numbered defects are emitted in `cache/grice.json` together with the full per-document export, so the same tree produces the same report content under any reviewer.
- **ADRs are excluded before normalisation**: the configured `documentation.adrs` directory and every directory named `adr` or `adrs` at any depth. The report header states how many were excluded.
- **Groups are layout, not meaning.** A document belongs to the first-level child of `documentation.dir` that holds it; root documents and files directly in `documentation.dir` form `(root)`. No directory name is special-cased and the whole corpus is analysed; normalisation stays corpus-wide, so groups only affect presentation.
- **The diagnosis reads only the four maxim sub-scores**, through a fixed first-match rule table.
- **Every structural defect is listed**, broken links and anchors deduplicated per resolved target with every occurrence kept, numbered `G1`, `G2`… progressively.
- **Thresholds live in settings**: `subcommands.grice.outlier_threshold` (default 40) and `subcommands.grice.benchmark_count` (default 5), read through `ProjectConfig` — no CLI flag, per `cli.1`.
- **The report is written in the invocation language**, like review: the template stays in English and the headings, prose and diagnosis wording are translated; paths, metric names, codes and ids are not.

## Consequences

- A reader triages from three short tables instead of a corpus-sized one; the full table stays available in the payload.
- Diagnoses and selections are reproducible and testable, at the cost of English rule wording that the report writer must translate.
- Excluding ADRs changes every remaining percentile compared with earlier runs, so trends across this change are not comparable.
- A project whose ADRs live in a directory not named `adr`/`adrs` must set `documentation.adrs` to keep them out.
