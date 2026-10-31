---
audience: human, ai
status: stable
skills: [grice]
---

# Grice Maxims — Overview

Grice's cooperative principle describes what a reader expects from an utterance: enough information and no more (**Quantity**), only what is true and supported (**Quality**), only what is relevant (**Relation**), and presented clearly and in order (**Manner**). This reference documents how `skills/zolletta-metaskill/src/zolletta_metaskill/grice/grice_scanner.py` turns those four expectations into numbers, and — more importantly — what those numbers do and do not mean.

Read this page first. The four metric pages describe the individual measurements; this one describes the frame they sit in, and the frame is the part that is easy to misread.

## The scores are relative, always

Every index in a grice report is a percentile inside the documentation corpus that produced it. `50` means "the middle of this corpus", never "mediocre", and no index means "good" or "bad" on its own.

Three consequences follow, and all three are load-bearing:

- A corpus of uniformly excellent documents still produces a spread of indices. Someone is always at the median, however good the median is.
- A single document cannot be scored at all. With nothing to be relative to, there is no percentile; the scanner reports `SKIPPED` for an empty corpus and adds a noise note below five documents.
- Two projects cannot be compared by index. A 62 in one repository and a 62 in another are both "slightly above the middle of their own corpus", and nothing more.

The scanner says this in every report: the first entry of `notes` is always the relativity statement, and it is not decoration.

## Findings are the exception

Relativity governs the indices, not the defects. A broken internal link or a heading that descends two levels is wrong in the document itself, whatever its peers do, so those become ordinary findings with a file and a line. Everything else the scanner produces is a measurement.

Missing file references are the deliberate half-way case: they lower the `reference_resolution` metric but produce no finding, because the reference extractor returns a set without line numbers and a finding anchored on line 1 would point nowhere.

## The corpus

The corpus is the documentor's, by construction. `DocumentationFilesFinder.find()` names it, so the scan covers the markdown under `documentation.dir` plus the root documents `README.md`, `CONTRIBUTING.md` and `AGENTS.md`. `skills/`, `SKILL.md` and `CHANGELOG.md` are never scored — they are hand-maintained contracts and generated release output, so a percentile over them would measure something the author cannot act on.

Two scans of the same tree produce the same numbers. Nothing here reads git history, network state or wall-clock time; the metrics are computed from the document text and the file tree alone.

## The pipeline

Each document is parsed once into a `DocumentFeatures` record: prose, frontmatter, sections, sentences, headings with levels and line numbers, inline code spans, and a count of boilerplate words. Every maxim then reads that single parse, which is what keeps the cross-document metrics (corpus median, peer similarity, pertinence) and the per-document ones consistent with each other.

1. **Parse** — `MarkdownCorpus.parse` splits frontmatter, fenced blocks, headings, sections and sentences. Fenced code is excluded from prose but a heading after a fence is still found.
2. **Measure** — each maxim class returns raw metrics on a 0-100 scale, all oriented so that higher is better. Metrics that a document cannot carry (no headings, no frontmatter, too few words) are left out rather than scored as zero.
3. **Normalise** — `CorpusNormalizer` converts each metric independently across the documents that carry it, so a document that lost one manner metric loses one metric, not the whole maxim.
4. **Aggregate** — a document's maxim index is the mean of its normalised metrics for that maxim; `grice_index` is the mean of the maxim indices that were measured.

## Normalisation: z-score to percentile

A raw metric is turned into a corpus percentile in four steps:

1. Take the values of that metric across the documents that measured it, and compute their population mean and variance.
2. If the sample is flat or has a single value, every document gets `50`: nothing is above or below its peers, and inventing a ranking out of a flat sample would be noise dressed as signal.
3. Otherwise, convert each value to a z-score against the mean, then push it through the normal cumulative distribution function — `100 × 0.5 × (1 + erf(z / √2))`.
4. Round to one decimal place for the report; the aggregate is computed from the unrounded values.

The result is a percentile in 0-100 with 50 at the mean. It is deliberately not a rank: ranks discard distance, and in a small sample two documents a hair apart would land forty points from each other purely because there were only five of them.

## Reading a report

The markdown report is a table with one row per document and five numeric columns: the four maxim indices plus the aggregate. An em dash (`—`) means "not measured", never "zero" — a document with no frontmatter has no frontmatter-content score, and printing `0` would read as "measured and worst".

Below the table come `Corpus index`, `Disabled metrics`, `Findings` and `Notes`. The notes are the part to read before acting on any number: they carry the relativity statement, the small-corpus warning, and the list of metrics that did not run.

## Limits

- **Small corpora.** Below five documents, a percentile describes individual quirks rather than a distribution. The report says so, but the warning does not make the numbers reliable.
- **English-only metrics.** Readability, grade level, SMOG, hedging and passive voice are dropped when `documentation.language` is not `"en"`, and named in `disabled_metrics`. The structural metrics are language-neutral and always run.
- **Lexical, not semantic.** Similarity is TF-IDF cosine over words. Two documents that say the same thing in different vocabulary look unrelated to every metric that uses it, and a paraphrase is invisible.
- **No correctness judgement.** Whether a documented claim matches the code is the documentor's accuracy and API-doc pass, not this one. Grice asks whether a document supports what it says, not whether what it says is true.

## Related pages

- [Quantity metrics](quantity.md) — how much a document says against how much it repeats.
- [Quality metrics](quality.md) — whether its references can be checked.
- [Relation metrics](relation.md) — whether its parts stay on subject.
- [Manner metrics](manner.md) — how clear, ordered and plainly written it is.
