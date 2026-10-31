---
audience: human, ai
status: stable
skills: [grice]
---

# Quality Metrics

Grice's Quality maxim asks a writer not to say what they cannot support. In documentation the support is usually a reference — a link, a path, a file name. A document dense with references that all resolve is corroborated; one whose references are broken asks the reader to trust it, and has no way to earn that trust back.

All three metrics are on a 0-100 scale, oriented so that higher is better.

## Metrics

| Metric                 | Measures                                                        |
| ---------------------- | --------------------------------------------------------------- |
| `link_resolution`      | Percentage of internal links and anchors that resolve           |
| `reference_resolution` | Percentage of file references that exist on disk                |
| `lexical_alignment`    | How much of the document's vocabulary the source tree also uses |

## `link_resolution`

Every internal link in the document is extracted with the documentor's own `LinkChecker`, so the definition of "a link" and the fence-stripping rules are shared with `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/links/link_checker.py` rather than re-derived. External links are excluded: validating them needs the network, and a network answer is not deterministic — the same repository would score differently on two machines, or on one machine twice.

The metric is the share of internal links that resolve, counting both file targets and cross-document anchors. A document with no internal links scores 100: nothing in it is broken, which is a weak signal but the honest one.

This is the one Quality metric that also produces findings. Each unresolved internal link becomes a `medium` finding carrying the link's own line number, described as `internal link '<target>' does not resolve`, with the validator's error appended when one is available.

## `reference_resolution`

A document also references files without linking them — a bare `pyproject.toml`, a path in a table cell. `DocCodeMapper.extract_references_from_doc` extracts those, and this metric is the share that exist on disk.

Three reference shapes are excluded before resolution, because none can be checked from inside the repository:

- `#anchor` — a same-page anchor, already covered by `link_resolution`.
- `/absolute/path` — an absolute path names the writer's machine, not the project.
- `http://`, `https://`, `ftp://`, `mailto:` — the network again.

A reference is considered resolved when the path exists from any of three plausible roots: the repository root, the directory of the referencing document, or `src/`. The three are checked because a false "unresolved" is a finding against a document that is correct, and authors legitimately write paths from different anchors.

A document that references no files scores 100. A missing reference lowers this metric but produces **no finding**: the extractor returns a set without line numbers, and a finding anchored on line 1 would point nowhere. The score tells you something is missing; the document itself tells you where.

## `lexical_alignment`

A document that documents code it shares no vocabulary with is likely describing something else. This metric is `100 × cosine(prose, source_text)`, where `source_text` is the first 500 source files of the project concatenated — a ceiling rather than a target, since the vectoriser's cost grows with the vocabulary and a thousandth file adds no signal a reviewer would act on.

The comparison is deliberately lexical. A document that explains a concept without ever naming the symbol, the option or the error message it concerns is hard for a reader to connect to the code, and that is exactly what a shared vocabulary measures. The cost is that a paraphrase scores as unrelated: this metric cannot tell "the same idea in other words" from "a different idea".

A project with no source files produces an empty `source_text` and therefore a score of 0 for this metric — there is nothing to align with, and the document is not rewarded for it.

## Reading the aggregate

The Quality index is the mean of the normalised values of the three metrics. Because two of them score 100 when there is nothing to check, a high Quality index can mean "well referenced" or "barely referenced". Read the findings first: a document with no findings and a high index is genuinely corroborated only if it carries references at all.

## Related pages

- [Grice overview](index.md) — the normalisation and what a percentile means.
- [Quantity metrics](quantity.md) — how much the document says.
- [Relation metrics](relation.md) — whether its parts stay on subject.
