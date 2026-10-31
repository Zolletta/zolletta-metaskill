---
audience: human, ai
status: stable
skills: [grice]
---

# Manner Metrics

Grice's Manner maxim asks for clarity: be brief, be orderly, avoid obscurity. In documentation that covers how hard the prose is to read, how much it hedges, and whether the structure descends in an order a reader can follow.

Manner carries more metrics than the other maxims because clarity is the maxim with the most observable failure modes. Five of the eight are English-only and disappear together; the three structural ones are language-neutral and always run.

## Metrics

| Metric              | Measures                                                    | Language |
|---------------------|-------------------------------------------------------------|----------|
| `readability`       | Flesch Reading Ease                                         | English  |
| `grade_level`       | Gunning Fog, inverted so that simpler is higher             | English  |
| `smog`              | SMOG index, inverted the same way                           | English  |
| `hedging`           | Share of sentences that do not hedge                        | English  |
| `passive_voice`     | Share of sentences that do not read as passive              | English  |
| `heading_hierarchy` | Share of heading transitions that descend exactly one level | Any      |
| `sentence_length`   | Share of sentences within 25 words                          | Any      |
| `section_structure` | Share of sections between 20 and 400 words                  | Any      |

## Readability, grade level and SMOG

The three formulas come from `textstat`. Flesch Reading Ease is used as-is and clamped to 0-100. Gunning Fog and SMOG measure grade level, where lower is better, so both are inverted — `100 − clamp(score × 5)` — which makes every metric in the set point the same direction and lets the normaliser treat them identically.

`textstat` formulas are unbounded: Flesch exceeds 100 on very simple prose and goes negative on very dense prose. Clamping keeps a negative index from inverting the ranking the normaliser builds.

Two guards stop the formulas from fitting noise:

- All English metrics are skipped when the document carries fewer than 20 words, because a formula over two sentences measures the sample, not the document.
- SMOG is skipped unless there are at least three sentences, which is the formula's own minimum — below it `textstat` returns a number that means nothing.

These formulas were calibrated on English prose. Nothing in the scanner attempts to translate the word lists or the syllable heuristics, which is why the whole English group is dropped for any `documentation.language` other than `"en"` and named in `disabled_metrics`.

## Hedging and passive voice

Both are counted from fixed word lists and regular expressions, which makes them heuristics rather than grammar. They are still deterministic, and determinism is the property that matters here: the same text yields the same count on every run, and the corpus percentile says whether this document hedges more than its neighbours, not whether hedging is wrong.

`hedging` scans the hedge list — `may`, `might`, `perhaps`, `generally`, `roughly` and their neighbours — and counts **sentences** that contain at least one of them, not occurrences. Counting sentences keeps one evasive paragraph from dominating the metric.

`passive_voice` counts sentences containing an auxiliary followed within a couple of words by a participle, and the metric is the share that do not. The pattern over-matches genuine passives and under-matches unusual ones; read it as a proxy, not a grammar verdict.

Both metrics are computed only when the English group runs, so a non-English corpus carries neither.

## `heading_hierarchy`

A heading tree that skips a level — `##` straight to `####` — tells the reader that a section belongs somewhere it does not. This metric is the share of heading transitions that descend exactly one level; a jump of two or more loses its transition, and a document with fewer than two headings has no transition to break and scores 100.

This is the second Manner metric that produces findings. Each skip becomes a `low` finding at the offending heading's line, described as `heading '<text>' jumps from level N to M`. Acknowledging a level by skipping it is still a skip: the extractor reads the actual heading levels, not the outline an author intended.

## `sentence_length`

A sentence a reader has to restart is a clarity cost. This metric is the share of sentences of at most 25 words. The threshold is a policy number at the upper end of the plain-language range, not a measurement, and it is deliberately blunt: it says nothing about whether a long sentence is well built, only that it is long.

A document with no sentences is not measured on this metric rather than scoring zero — a title-only page has no sentence to judge.

## `section_structure`

A section under 20 words is a stub; one over 400 is a chapter that has stopped being a section. This metric is the share of sections inside that band. The bounds are policy, and they are wide on purpose: the metric is meant to catch a page split into one-line headings or a page that is one giant blob, not to enforce a house style.

A document with no sections is not measured on this metric.

## Reading the aggregate

The Manner index is the mean of the normalised values of the metrics the document carried. Which metrics those were is visible in the input shape rather than in the report, so compare two documents with care: a short page that lost the English group has a Manner index resting on three metrics, while its neighbour's rests on eight. When a Manner index looks surprising, `heading_hierarchy` and `section_structure` are the cheapest explanations to rule out — they are structural, and a reader can see the same defect in the document without a tool.

## Related pages

- [Grice overview](index.md) — the normalisation and what a percentile means.
- [Relation metrics](relation.md) — heading-to-body relevance, which is the semantic counterpart of heading order.
- [Quality metrics](quality.md) — whether the document's references hold up.
