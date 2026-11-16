---
audience: ai, human
status: stable
skills: [grice, review, setup]
description: "The grice report is a deterministic, per-group triage — summary, structural defects, one outlier table and one table of at most five benchmarks (balanced plus the top on each maxim) per group — computed by the scanner over a corpus without ADRs; no grade, no abbreviated metric names, and no benchmark_count setting."
---

# ADR-0015: The Grice triage is per group — superseding ADR-0014

## Status

Accepted — supersedes [ADR-0014](0014-grice-report-is-triage-not-grade.md)

## Context

[ADR-0014](0014-grice-report-is-triage-not-grade.md) made the grice report a deterministic triage. On a real corpus of 283 documents in five groups, its two corpus-wide tables still mixed groups: the outlier table interleaved `current`, `old` and `maintainers` rows behind a `Group` column, and the corpus-wide top five benchmarks came from two groups only, so most groups had no style model of their own. The benchmarks also all read "strong on one maxim" without saying which document leads each maxim, and the tables abbreviated the metric names (`Qty`, `Qual`, `Rel`, `Man`), which a reader has to decode. An Accepted record cannot be edited, so the changes are recorded here and every other rule of ADR-0014 is carried forward unchanged.

## Decision

The grice report is a deterministic triage computed by the scanner over a corpus without ADRs, split per group, with no grade, and written in the invocation language.

- **No grade.** The report opens with an Executive Summary: one row per group with document count, median `grice_index`, outlier count and defect count. The review SUMMARY row shows the corpus median `grice_index` and the number of defects, still advisory and never weighted.
- **The scanner computes everything; the LLM only lays it out.** Groups, the per-group outliers and benchmarks, the rule-based diagnosis and the numbered defects are emitted in `cache/grice.json` (`triage`, one entry per group) together with the full per-document export, so the same tree produces the same report content under any reviewer.
- **One outlier table per group**, in the Executive Summary order: the group's documents below `subcommands.grice.outlier_threshold` (default 40), worst first; groups without outliers are left out.
- **One benchmark table per group, at most five rows**: the best-ranked `balanced` document, then the top non-outlier on Quantity, Quality, Relation and Manner. A document that wins several slots is listed once with every slot it won, so a group shows fewer rows rather than a runner-up; a group with no `balanced` document has no balanced slot. Ties break on the higher index, then on the path.
- **No `benchmark_count` setting.** The slots fix the size, so the key is ignored; the schema keeps it as deprecated so existing settings files still validate, and setup no longer writes it. `outlier_threshold` stays the only grice threshold, read through `ProjectConfig` — no CLI flag, per `cli.1`.
- **Metric names are never abbreviated** in report tables: `Quantity`, `Quality`, `Relation`, `Manner`.
- **ADRs are excluded before normalisation**: the configured `documentation.adrs` directory and every directory named `adr` or `adrs` at any depth. The report header states how many were excluded.
- **Groups are layout, not meaning.** A document belongs to the first-level child of `documentation.dir` that holds it; root documents and files directly in `documentation.dir` form `(root)`. No directory name is special-cased and normalisation stays corpus-wide, so a group's benchmarks are the best of that group measured against the whole corpus.
- **The diagnosis reads only the four maxim sub-scores**, through a fixed first-match rule table.
- **Every structural defect is listed**, broken links and anchors deduplicated per resolved target with every occurrence kept, numbered `G1`, `G2`… progressively.
- **The report is written in the invocation language**: the template stays in English and the headings, prose and diagnosis wording are translated; paths, metric names, codes and ids are not.

## Consequences

- Every group gets its own style models next to its own outliers, so a fix can copy a page written in the same context.
- The benchmark table grows with the number of groups — at most five rows each — instead of staying at a fixed corpus-wide count.
- A strong document can fill several slots of its group, which leaves that group with fewer than five benchmarks.
- The JSON payload drops the flat `outliers` and `benchmarks` lists for `triage` and `outlier_count`, so a consumer of the old shape must be updated.
