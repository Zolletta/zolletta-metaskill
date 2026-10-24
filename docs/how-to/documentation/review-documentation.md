---
audience: human, ai
status: stable
skills: [documentor]
---

# Review documentation

> **Paths in this document are relative to the Zolletta-MetaSkill project root.**

Review project documentation for [Diátaxis](https://diataxis.fr/) compliance, drift detection, and quality. The `documentor` skill checks that documentation follows the Diátaxis framework, detects drift between code and docs, and scores documentation freshness.

## Prerequisites

- A project with a documentation directory (default: `docs`, configurable via `documentation.dir` in `settings.json`)
- The project set up with `/zolletta-metaskill setup`

## What the review checks

- **Diátaxis compliance** — four quadrants (tutorials, how-to, reference, explanation), correct file placement, consistent frontmatter
- **Drift detection** — stale docs, missing docs, broken links, API drift. See [drift-detection-tools.md](../../reference/documentation/drift-detection-tools.md)
- **Freshness scoring** — 0–100 weighted score across five dimensions. See [scoring-and-categories.md](../../reference/documentation/scoring-and-categories.md)

## Steps

### Step 1 — Run the documentor CLI

```bash
python3 src/zolletta_metaskill/documentor/documentor_client.py
```

This runs all three documentor tools and prints one aggregated report. Each tool also writes its own JSON cache into the current run folder, `<runs_dir>/<YYYY-MM-DD-HH-MM>/cache/` — `.zolletta-metaskill/<timestamp>/cache/` with the default `runs_dir` — so each review keeps its own history instead of overwriting the last; before the first run folder exists, artifacts land in `<runs_dir>/cache/`:

- `quality.json` — unified drift + staleness review (freshness score 0-100 plus drift issues); when `documentation.staleness_threshold` is set the CLI exits non-zero below it
- `api_doc_validator.json` — API documentation validated against actual code signatures
- `link_checker.json` — all internal links in the documentation directory checked

Use `--json` for machine-readable output:

```bash
python3 src/zolletta_metaskill/documentor/documentor_client.py --json > drift-report.json
```

### Step 2 — (Optional) Run individual tools

Run a single tool when you only need one category of findings:

```bash
# Unified drift + staleness quality review (writes cache/quality.json)
python3 src/zolletta_metaskill/documentor/quality/quality_review.py

# API doc validator (writes cache/api_doc_validator.json)
python3 src/zolletta_metaskill/documentor/api_doc/api_doc_validator.py

# Link checker (writes cache/link_checker.json)
python3 src/zolletta_metaskill/documentor/links/link_checker.py
```

### Step 3 — Review findings

Classify each finding by severity:

- **High** — stale docs for critical features, broken links, missing API docs
- **Medium** — stale docs for non-critical features, Diátaxis misplacement
- **Low** — formatting issues, missing frontmatter fields

## See also

- [Drift detection tools](../../reference/documentation/drift-detection-tools.md) — full reference for drift detection scripts
- [Scoring and categories](../../reference/documentation/scoring-and-categories.md) — freshness scoring methodology
- [Documentation standards](../../explanation/documentation/standards.md) — general documentation rules
- [Settings schema](../../reference/settings-schema.md) — `documentation.dir` configuration
