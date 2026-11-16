---
name: zolletta-metaskill-grice
description: >
  Scores project documentation against Grice's four maxims — Quantity, Quality, Relation and Manner — as indices relative to the documentation corpus itself, and writes a dated report. Use when auditing how well docs say what they need to say. Do not use for Diátaxis compliance or drift detection — that is documentor.
license: MIT + Commons Clause
---

# Zolletta-metaskill Grice

Grice's cooperative principle describes what a reader expects from an utterance: as much information as needed and no more (**Quantity**), only what is true and supported (**Quality**), only what is relevant (**Relation**), and presented clearly and in order (**Manner**). The same four expectations apply to documentation, and this skill measures them.

The scan is deterministic: the same tree produces the same numbers on every run, under any reviewer. Judgement is left to the reader of the report.

## When to use

- Auditing an existing documentation tree for how well it communicates, not only whether it is structurally correct.
- Comparing documents inside one corpus, to find the outliers worth reading first.
- Tracking whether a documentation rewrite moved the middle of the corpus from one run to the next.

Do **not** use this skill for:

- Diátaxis quadrant compliance, drift, staleness or broken API docs — that is `documentor`.
- Authoring or rewriting documentation — this skill measures and reports.

## The one rule that governs every number

**The indices are relative to the corpus, always.** A `grice_index` of 50 means "the middle of this corpus", never "mediocre". Two consequences are load-bearing:

- A corpus of uniformly excellent documents still produces a spread of indices — someone is always at the median.
- A single document cannot be scored at all, because there is nothing to be relative to. The scanner reports `SKIPPED` for an empty corpus and adds a noise note below five documents.

So the report is a ranking of documents against each other, and the only defect-like output is the structural defects — a broken internal link, a heading that skips a level — because those are wrong in the document, not merely below its peers. That is also why the report carries no headline grade: a 0-100 grade next to a 0-100 relative index invites reading 50 as a pass mark.

## Corpus

The corpus is the documentor's, by construction: `DocumentationFilesFinder.find()` names it, so it is the markdown under `documentation.dir` plus `README.md`, `CONTRIBUTING.md` and `AGENTS.md`. `skills/`, `SKILL.md` and `CHANGELOG.md` are never scored — they are contracts and generated release output, so a percentile over them would measure something the author cannot change.

**ADRs are excluded before normalisation**: every file under the configured `documentation.adrs` directory and under any directory named `adr` or `adrs` at any depth (e.g. `current/security/adr/`, `maintainers/adr/`, `old/v3.x/security/adr/`). A decision record's hypothetical wording and private vocabulary are what the genre demands, so ranking it against guides only produces expected false positives and shifts every other document's percentile. The payload lists the excluded paths in `excluded_adrs` and the report header states their count.

The whole remaining corpus is analysed — there is no "active" versus "archive" split. **Groups** are presentation only: each document belongs to the first-level child of `documentation.dir` that holds it (`docs/current/php/x.md` → `current`), and the root documents plus the files directly in `documentation.dir` form `(root)`. Normalisation stays corpus-wide, so a group median says where that group sits in the corpus, never a ranking inside the group.

## Procedure

1. Read `AGENTS.md` and any documentation rules in your agent configuration.
2. Run the scanner and persist its JSON, from the project root:

   ```bash
   uv run python ../../src/zolletta_metaskill/grice/grice_scanner.py --json > <runs_dir>/<YYYY-MM-DD-HH-MM>/cache/grice.json
   ```

   The scanner also writes the same payload to `cache/grice.json` under the run directory resolved by `DocumentorSettings.resolve_cache_dir`, so the cache is present even when the redirect is forgotten. It prints `Result: SKIPPED (no documentation files found)` and exits 0 when the corpus is empty — that is a "nothing to review" result, not an error.

3. Assemble the report from the JSON. Do **not** re-read the documents and do not recompute anything: the groups, the outliers, the benchmarks, the diagnoses and the defect ids are all in the cached payload, already sorted.

## What each maxim measures

Each maxim is an aggregate of several raw metrics, normalised per metric across the corpus and averaged. A metric that was not measured for a document (no headings, no frontmatter, too few words) is left out of that document's average rather than scored as zero.

| Maxim        | Metrics                                                                                                                                                                                                                      |
|--------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Quantity** | `section_balance` (words per section against the corpus median), `section_redundancy`, `sentence_redundancy`, `corpus_duplication` (1 − similarity to the nearest peer), `content_ratio` (prose share, boilerplate excluded) |
| **Quality**  | `link_resolution` (internal links and anchors that resolve), `reference_resolution` (file references that exist), `lexical_alignment` (vocabulary shared with `src/`)                                                        |
| **Relation** | `heading_body` (heading against its own section), `frontmatter_content` (frontmatter against the body), `corpus_pertinence` (document against the corpus mean)                                                               |
| **Manner**   | `readability`, `grade_level`, `smog` (textstat), `hedging`, `passive_voice`, `sentence_length`, `heading_hierarchy`, `section_structure`                                                                                     |

The manner metrics in the first group are English-only and are dropped — and named in `disabled_metrics` — whenever `documentation.language` is not `"en"`. The structural manner metrics are language-neutral and always run.

## Structural defects

Only defects carry a file and a line: an internal link or anchor that does not resolve, and a heading that skips a level. The payload's `defects` lists **all** of them, numbered `G1`, `G2`, … in one progressive sequence (severity first, then first occurrence). Broken links are deduplicated per resolved target — the same missing anchor reached from twenty pages is one defect with a `count` of 20 and every location kept — because one fix resolves all of them. Every heading skip is its own defect. Missing file references lower the `reference_resolution` metric but produce no defect, because the extractor cannot attribute them to a line. `findings` keeps the raw, undeduplicated list.

Everything else the report says is a measurement. A low `grice_index` is a prompt to read the document, not a defect to file.

## Triage

Two tables per group pick the documents worth opening first, both computed by the scanner. The payload's `triage` holds one entry per group, in the Executive Summary order, each with its `outliers` and its `benchmarks`:

- **Outliers** — every document of the group whose `grice_index`, rounded to one decimal, is below `subcommands.grice.outlier_threshold` (default `40`), worst first.
- **Positive benchmarks** — at most five non-outliers per group, in slot order: the best-ranked `balanced` document, then the document with the highest Quantity, Quality, Relation and Manner score. A document that wins several slots is listed once, with every slot it won in `strengths`; a group with no `balanced` document has no balanced slot. Ties break on the higher `grice_index`, then on the path. These are style models for refactoring the outliers of the same group.

Each entry carries a `diagnosis` from a fixed rule table over the four maxim sub-scores and nothing else, first match wins:

| Code                   | Rule                                         | Reading                                   |
|------------------------|----------------------------------------------|-------------------------------------------|
| `uniform_deficit`      | ≥ 2 maxims measured, all below 40            | Uniformly weak — rework the page          |
| `dense_isolated`       | Relation < 20 and Quantity > 60              | Dense text with low cohesion — cross-link |
| `isolated`             | Relation < 20                                | Isolated page — link it from its flow     |
| `verbose_unreferenced` | Quantity > 60 and Quality < 35               | Verbose and poorly referenced — condense  |
| `weak_<maxim>`         | otherwise, the lowest maxim                  | Problem on that maxim                     |
| `balanced`             | benchmark: ≥ 2 maxims measured, all above 60 | Above the corpus on every maxim           |
| `strong_<maxim>`       | benchmark: the highest score on that maxim   | Strength on that maxim                    |

`summary` and `action` hold the English wording of the rule; translate it with the rest of the report. An outlier entry carries one `diagnosis`; a benchmark entry carries one `strengths` item per slot it won.

## Report format

**Language.** Write the report in the same language the user used to invoke you. The template below is in English: translate its headings and prose — including the diagnosis wording — into the invocation language. Do not translate paths, group names, metric names (`grice_index`, `Quantity`…), diagnosis codes or ids (`G1`…). Never abbreviate a metric name in a table header or cell: write `Quantity`, `Quality`, `Relation`, `Manner` in full, never `Qty`/`Qual`/`Rel`/`Man`.

Write `<runs_dir>/<YYYY-MM-DD-HH-MM>/reports/grice.md` with the sections below, in order, every value taken from `cache/grice.json`. An empty section reads `*None.*`.

```markdown
# Grice Documentation Analysis — `<project>`

> **Purpose:** assess the clarity, semantic cohesion and structural integrity of the documentation, for human readers and AI agents.
> **Method:** Grice indices are **relative to the corpus** (50 = the middle of this repository, not a school grade). They point at stylistic or structural anomalies against the project's own standard, not at blocking errors.

- **Repository / Branch:** `<repo>` (`<branch>`)
- **Scope:** `<corpus_size>` documents in `<len(groups)>` groups — `<excluded_adrs.count>` ADR files excluded
- **Scan date:** <YYYY-MM-DD>
- **Generator:** `zolletta-metaskill grice` (`grice_scanner.py`)

## Executive Summary

| Group      | Docs            | Median `grice_index` | Outliers (`< <outlier_threshold>`) | Defects          |
|------------|-----------------|----------------------|------------------------------------|------------------|
| `<name>`   | …               | …                    | …                                  | …                |
| **Corpus** | `<corpus_size>` | `<corpus_median>`    | `<outlier_count>`                  | `<len(defects)>` |

One row per entry of `groups`, `(root)` last; one sentence of interpretation below the table (which groups to look at first).

## 1. Structural Defects

### Heading level skips

| ID | File | Line | Group | Problem | Recommended action |
(every `heading_skip` defect)

### Broken internal links and anchors

| ID | Target | Occurrences | Locations |
(every `broken_link` defect, one row per target, all `file:line` locations)

## 2. Pragmatic Analysis — Outliers (`grice_index < <outlier_threshold>`)

### Metric legend
- **Quantity:** information density and length against the corpus (too short = stub; too long = wall of text).
- **Quality:** reliability and verifiability (lowered by broken links, unresolved references, hedging, no anchors to the code).
- **Relation:** semantic cohesion with the rest of the corpus (lowered by orphan pages and isolated vocabulary).
- **Manner:** syntactic readability, paragraph balance and a clean heading hierarchy.

### Triage table

One table per entry of `triage` whose `outliers` is not empty, in payload order; groups without outliers are left out.

#### `<group>`

| Document | Quantity | Quality | Relation | Manner | **Index** | Diagnosis & recommended action |
(every entry of that group's `outliers`; bold the sub-score named by `diagnosis.maxim`; last column = `**<summary>** (<Maxim> <value>): <action>`)

## 3. Positive Benchmarks

One table per entry of `triage` whose `benchmarks` is not empty, in payload order — at most five rows each.

### `<group>`

| Document | Quantity | Quality | Relation | Manner | **Index** | Strength |
(every entry of that group's `benchmarks`, in payload order; bold the sub-score of every maxim slot the entry won; Strength = one item per `strengths` entry, joined with `; ` — `**Balanced:** <summary>` for `balanced`, `**Top <Maxim> (<value>):** <summary>` for `strong_<maxim>`)

## Notes

(the payload `notes` verbatim, translated; plus `disabled_metrics` when not empty)
```

The Grice result is **advisory and unweighted**: it never enters the overall review score, and there is no headline grade. The full per-document export stays in `cache/grice.json` (`documents`) for programmatic analysis; do not paste it into the report.

## Output

- **Path**: `<runs_dir>/<YYYY-MM-DD-HH-MM>/reports/grice.md` (timestamp = run start time, via `date +%Y-%m-%d-%H-%M`; `runs_dir` from `settings.json`, default `.zolletta-metaskill`)
- **Compound skills** (e.g. `zolletta-metaskill-review`) may override the directory and filename — follow their instructions instead
- **Cache**: `<runs_dir>/<YYYY-MM-DD-HH-MM>/cache/grice.json`
- **Directory setup**: the `.zolletta-metaskill/` directory and `.git/info/exclude` entry are created by the setup guard (`../../SKILL.md#setup-guard`) — no manual setup needed

## Scope & Limitations

**Covers:**

- Corpus-relative indices for Grice's four maxims over the same documentation set `documentor` reviews
- Deterministic structural defects for broken internal links, broken anchors (deduplicated per target) and skipped heading levels
- Deterministic triage: per-group summary, and per group the outliers with a rule-based diagnosis and up to five positive benchmarks (balanced plus the top document on each maxim)
- Automatic, declared degradation to language-neutral metrics for non-English documentation

**Does NOT cover:**

- Absolute quality judgements — no index means "good" or "bad" on its own, only "above or below this corpus"
- ADRs — excluded before normalisation, wherever they live
- Semantic correctness of claims against source code — that is the documentor's accuracy and API-doc pass
- Corpora below five documents, where a percentile describes individual quirks rather than a distribution
- Non-English readability, hedging and passive-voice metrics — `textstat` and the word lists are English
