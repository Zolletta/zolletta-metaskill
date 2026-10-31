---
audience: human, ai
status: stable
skills: [grice]
---

# Relation Metrics

Grice's Relation maxim asks a speaker to be relevant. A document can fail it in three places: a heading that promises something its section does not deliver, a frontmatter block that describes a different document than the one beneath it, and a page that sits in a corpus it has nothing to do with. Each is a cosine between two texts that are supposed to be about the same thing.

All three metrics are on a 0-100 scale and produce no findings. Relevance is a continuous judgement; the one discrete defect in it — a broken anchor — already belongs to Quality.

## Metrics

| Metric                | Compares                                    | Measured when                |
|-----------------------|---------------------------------------------|------------------------------|
| `heading_body`        | Each heading against its own section        | The document has headings    |
| `frontmatter_content` | The frontmatter block against the body      | The frontmatter is non-blank |
| `corpus_pertinence`   | The document against the rest of the corpus | Always                       |

## `heading_body`

A heading is a promise about the text below it. This metric takes the cosine of every heading against its own section, and averages the pairs — `100 × mean(cosines)`. A heading whose words reappear in its section scores high; a heading that names a different subject scores near zero.

The parser guarantees the two sides line up: a document's sections correspond one for one with its headings, and prose written before the first heading joins that heading's body rather than forming a heading-less pseudo-section nobody wrote a title for. Pairs where both halves are blank are skipped, so an empty heading does not silently pull the mean down to zero — but a document whose headings and sections share no vocabulary at all scores 0.

A document with no headings is not measured on this metric at all, and contributes nothing to the aggregate for it.

## `frontmatter_content`

Frontmatter carries claims about the page — its audience, its status, what it covers. This metric is the cosine between the frontmatter text and the body prose, scaled to 0-100. A page titled as a tutorial whose body is a reference table scores low; a page whose frontmatter names the same subject as its body scores high.

Measurements are skipped when the frontmatter is blank or absent. That is a deliberate "not measured" rather than a zero: a document with no frontmatter has made no claim to check, and penalising it would reward the ritual of adding a block over the discipline of making it true.

## `corpus_pertinence`

A page that has drifted out of its corpus — an old guide for a removed feature, a note pasted in from another project — shares little vocabulary with its neighbours. This metric is the cosine between the document's prose and the concatenation of every other document's prose, scaled to 0-100.

A sole document in a corpus scores 0, because there is nothing to be pertinent to. That is the price of the relativity rule: with no peers, "does this belong here?" has no answer, and inventing one would be worse than reporting the gap.

`corpus_pertinence` measures distance to the **corpus mean**, while Quantity's `corpus_duplication` measures distance to the **nearest peer**. They are not redundant: a document can resemble one neighbour closely and still sit far from the centroid of a broad corpus, which is exactly the case a reviewer wants to see. If both were measured against the same reference, the two maxims would restate each other.

## Reading the aggregate

The Relation index is the mean of the normalised values of the metrics the document carried. Because `heading_body` and `frontmatter_content` are skipped rather than zeroed, a Relation index can rest on `corpus_pertinence` alone — the lexically most typical document in a corpus will look "most relevant" no matter how well its headings match its sections. Read the three metrics together: a low index driven by `heading_body` is an editorial problem, one driven by `corpus_pertinence` is a placement problem.

## Related pages

- [Grice overview](index.md) — the normalisation and what a percentile means.
- [Quantity metrics](quantity.md) — the nearest-peer counterpart of `corpus_pertinence`.
- [Manner metrics](manner.md) — whether the document is ordered and clear.
