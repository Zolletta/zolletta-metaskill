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

So the report is a ranking of documents against each other, and the only defect-like output is the findings — a broken internal link, a heading that skips a level — because those are wrong in the document, not merely below its peers.

## Corpus

The corpus is the documentor's, by construction: `DocumentationFilesFinder.find()` names it, so it is the markdown under `documentation.dir` plus `README.md`, `CONTRIBUTING.md` and `AGENTS.md`. `skills/`, `SKILL.md` and `CHANGELOG.md` are never scored — they are contracts and generated release output, so a percentile over them would measure something the author cannot change.

## Procedure

1. Read `AGENTS.md` and any documentation rules in your agent configuration.
2. Confirm the toggle. Read `documentation.check_grice` from `.zolletta-metaskill/settings.json`; when it is absent or `false`, write the report as `SKIPPED (check_grice disabled in settings.json)` and stop. The scanner does the same and exits 0 — it is opt-in because a relative index is a judgement about prose, and an unasked-for judgement is noise.
3. Run the scanner and persist its JSON, from the project root:

   ```bash
   uv run python ../../src/zolletta_metaskill/grice/grice_scanner.py --json > <runs_dir>/<YYYY-MM-DD-HH-MM>/cache/grice.json
   ```

   The scanner also writes the same payload to `cache/grice.json` under the run directory resolved by `DocumentorSettings.resolve_cache_dir`, so the cache is present even when the redirect is forgotten. It prints `Result: SKIPPED (no documentation files found)` and exits 0 when the corpus is empty — that is a "nothing to review" result, not an error.

4. Assemble the report from the JSON. Do **not** re-read the documents: every number in the report comes from the cached payload, and the findings are already sorted by file and line.

## What each maxim measures

Each maxim is an aggregate of several raw metrics, normalised per metric across the corpus and averaged. A metric that was not measured for a document (no headings, no frontmatter, too few words) is left out of that document's average rather than scored as zero.

| Maxim        | Metrics                                                                                                                                                                                                                      |
|--------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| **Quantity** | `section_balance` (words per section against the corpus median), `section_redundancy`, `sentence_redundancy`, `corpus_duplication` (1 − similarity to the nearest peer), `content_ratio` (prose share, boilerplate excluded) |
| **Quality**  | `link_resolution` (internal links and anchors that resolve), `reference_resolution` (file references that exist), `lexical_alignment` (vocabulary shared with `src/`)                                                        |
| **Relation** | `heading_body` (heading against its own section), `frontmatter_content` (frontmatter against the body), `corpus_pertinence` (document against the corpus mean)                                                               |
| **Manner**   | `readability`, `grade_level`, `smog` (textstat), `hedging`, `passive_voice`, `sentence_length`, `heading_hierarchy`, `section_structure`                                                                                     |

The manner metrics in the first group are English-only and are dropped — and named in `disabled_metrics` — whenever `documentation.language` is not `"en"`. The structural manner metrics are language-neutral and always run.

## Findings

Only defects become findings, each carrying a file and a line: an internal link or anchor that does not resolve, and a heading that skips a level. Missing file references lower the `reference_resolution` metric but produce no finding, because the extractor cannot attribute them to a line.

Everything else the report says is a measurement. A low `grice_index` is a prompt to read the document, not a defect to file.

## Report format

Write `<runs_dir>/<YYYY-MM-DD-HH-MM>/reports/grice.md` with:

1. **Grade** — the corpus index as a 0-100 score, following the shared grading rule: zero findings means 100, otherwise `100 − Σ weight(finding)` (`critical −40 · high −15 · medium −5 · low −2`), adjustable by at most ±5 with a named justification. A corpus index is **advisory and unweighted** — it never enters the overall review score, so do not present it as a quality verdict.
2. **Corpus table** — one row per document: path, the four maxim indices, the aggregate, with `—` for a maxim that could not be measured. Add the grade band only when it helps a reader act.
3. **Findings** — grouped by severity, `G1`, `G2`, … in one progressive sequence across severities, or `*None.*` when the scan was clean.
4. **Notes** — the caveats from the payload verbatim: relativity, small corpus, disabled metrics. They are what keeps a reader from treating 50 as a pass mark.

## Output

- **Path**: `<runs_dir>/<YYYY-MM-DD-HH-MM>/reports/grice.md` (timestamp = run start time, via `date +%Y-%m-%d-%H-%M`; `runs_dir` from `settings.json`, default `.zolletta-metaskill`)
- **Compound skills** (e.g. `zolletta-metaskill-review`) may override the directory and filename — follow their instructions instead
- **Cache**: `<runs_dir>/<YYYY-MM-DD-HH-MM>/cache/grice.json`
- **Directory setup**: the `.zolletta-metaskill/` directory and `.gitignore` entry are created by the setup guard (`../../SKILL.md#setup-guard`) — no manual setup needed

## Scope & Limitations

**Covers:**

- Corpus-relative indices for Grice's four maxims over the same documentation set `documentor` reviews
- Deterministic findings for broken internal links, broken anchors and skipped heading levels
- Automatic, declared degradation to language-neutral metrics for non-English documentation

**Does NOT cover:**

- Absolute quality judgements — no index means "good" or "bad" on its own, only "above or below this corpus"
- Semantic correctness of claims against source code — that is the documentor's accuracy and API-doc pass
- Corpora below five documents, where a percentile describes individual quirks rather than a distribution
- Non-English readability, hedging and passive-voice metrics — `textstat` and the word lists are English
