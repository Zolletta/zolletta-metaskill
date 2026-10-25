---
audience: human, ai
status: stable
skills: [grice]
---

# Quantity Metrics

Grice's Quantity maxim asks a speaker to say enough and not more. Read as a documentation rule it names two failure modes: a section so thin it says nothing, and a document that keeps saying the same thing in new words. Both are measured here, and both are measured relative to the corpus — a two-hundred-word section is generous in a changelog and stingy in a tutorial, and only the corpus knows which one it is looking at.

All five metrics are on a 0-100 scale, oriented so that higher is better. None of them produces a finding: quantity is a continuous judgement with no defect to point at.

## Metrics

| Metric                | Measures                                                               |
| --------------------- | ---------------------------------------------------------------------- |
| `section_balance`     | Words per section against the corpus median                            |
| `section_redundancy`  | How much the document's sections repeat each other                     |
| `sentence_redundancy` | How much its sentences repeat each other                               |
| `corpus_duplication`  | How much of the document is already said by its nearest peer           |
| `content_ratio`       | Share of the document's words that carry prose rather than boilerplate |

## `section_balance`

A section far from the corpus median is either starved or sprawling, and neither can be judged on its own. The raw value is `100 / (1 + |length − median| / median)`, where `length` is the document's words per section and `median` is the median words per section across every document in the corpus with at least one word in a section. A document exactly at the median scores 100; a document four times the median scores 25.

This is the one double-relative metric in the set: its raw value already depends on the corpus, and the normaliser then ranks that raw value against the other documents' raw values. That is intentional — "close to typical" is itself a property worth ranking — but it means `section_balance` should be read as a rank of closeness, not as a length.

A document with no sections, or a corpus where no document has a measurable section, scores 0 for this metric.

## `section_redundancy` and `sentence_redundancy`

Both answer the same question at different granularity: does this document say the same thing twice? Each takes the pairwise TF-IDF cosine similarity of every section (or sentence) against every other, keeps the strongest pair, and inverts it — `100 × (1 − max similarity)`. A document whose two sections are identical scores 0; one whose sections share no vocabulary scores 100.

Sentences are sampled at the first 200. The check is quadratic, and the longest documents in a real corpus carry hundreds of sentences; the first 200 are a deterministic sample of the same shape, and a document does not become less repetitive further down.

The strongest-pair choice is deliberate. Taking a mean would let one duplicated pair hide behind twenty unrelated ones, and a duplicated section is exactly what the reader notices.

## `corpus_duplication`

Quantity is also violated by a document that duplicates a neighbour: the corpus then says the same thing twice, which is more than anyone needed. This metric is `100 × (1 − similarity to the nearest other document)`, where similarity is the TF-IDF cosine between this document's prose and each peer's, keeping the maximum.

A document with no peers — a corpus of one — scores 100, because nothing else says what it says.

Quantity deliberately measures distance to the **nearest peer** while Relation's `corpus_pertinence` measures distance to the **corpus mean**. The two are opposites: a document can be far from every peer (high duplication score) and still sit close to the corpus centroid if the corpus is broad. Measuring both against the mean would have made the two maxims restate each other, so the split is what keeps them independent.

## `content_ratio`

Not every word in a markdown file is prose. Badge lines, horizontal rules and HTML comments are counted as boilerplate by the parser and subtracted here: `content_ratio = 100 × (words − boilerplate) / words`. A README that is mostly badges scores low; a plain reference page scores 100.

A document with no words at all scores 100, not 0 — nothing decorative is being measured there, and a zero would read as "a full document of boilerplate", which is the opposite of the truth.

## Reading the aggregate

The Quantity index is the mean of the normalised values of the metrics the document carried. Every document carries `section_redundancy`, `sentence_redundancy`, `corpus_duplication` and `content_ratio`, so a low Quantity index is usually a length or duplication story. Check `section_balance` first when a document has unusually long or unusually short sections, and `corpus_duplication` first when a document reads like a copy of its neighbour.

## Related pages

- [Grice overview](index.md) — the normalisation and what a percentile means.
- [Relation metrics](relation.md) — the corpus-mean counterpart of `corpus_duplication`.
- [Quality metrics](quality.md) — whether what the document says can be checked.
