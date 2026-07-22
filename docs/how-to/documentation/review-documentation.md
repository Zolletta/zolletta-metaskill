---
audience: human, ai
status: stable
skills: [documentor]
---

# Review documentation

> **Paths in this document are relative to the Zolletta-MetaSkill project root.**

Review project documentation for [Diátaxis](https://diataxis.fr/) compliance, drift detection, and quality. The `documentor` skill checks that documentation follows the Diátaxis framework, detects drift between code and docs, and scores documentation freshness.

## Prerequisites

- A project with a documentation directory (default: `docs/`, configurable via `documentation.directory` in `settings.json`)
- The zolletta-metaskill skill installed and available to the agent
- The project set up with `/zolletta-metaskill setup`

## What the review checks

### Diátaxis compliance

The review checks that the documentation directory follows the Diátaxis framework with four quadrants:

- **Tutorials** — learning-oriented, step-by-step lessons
- **How-to guides** — task-oriented, practical steps to achieve a goal
- **Reference** — information-oriented, accurate technical description
- **Explanation** — understanding-oriented, clarification and background

Each file should have frontmatter with `audience`, `status`, and `skills` fields. The review checks that files are placed in the correct quadrant and that frontmatter is consistent.

### Drift detection

The review runs drift detection tools to identify:

- **Stale docs** — documentation that has not been updated when the code it describes changed
- **Missing docs** — code features that have no corresponding documentation
- **Broken links** — internal links that point to non-existent files
- **API drift** — API documentation that does not match the actual code signatures

### Freshness scoring

The review scores documentation freshness on a 0–100 scale using weighted multi-dimensional scoring:

- **Git history** — how recently docs were updated relative to code
- **Code-to-doc mapping** — whether each code feature has corresponding docs
- **Link integrity** — whether internal links resolve
- **Diátaxis structure** — whether the four quadrants are present and populated

## Steps

### Step 1 — Run the staleness scorer

```bash
python3 src/zolletta_metaskill/documentor/doc_staleness_scorer.py . --threshold 50
```

This produces a freshness score and lists stale files below the threshold.

### Step 2 — Run the drift analyzer

```bash
python3 src/zolletta_metaskill/documentor/drift_analyzer.py . --json > drift-report.json
```

This produces a full drift analysis between code and docs.

### Step 3 — Run the link checker

```bash
python3 src/zolletta_metaskill/documentor/link_checker.py .
```

This checks all internal links in the documentation directory.

### Step 4 — Run the API doc validator

```bash
python3 src/zolletta_metaskill/documentor/api_doc_validator.py src/ docs/api.md
```

This validates API documentation against the actual code signatures.

### Step 5 — Review findings

Classify each finding by severity:

- **High** — stale docs for critical features, broken links, missing API docs
- **Medium** — stale docs for non-critical features, Diátaxis misplacement
- **Low** — formatting issues, missing frontmatter fields

## See also

- [Drift detection tools](../../reference/documentation/drift-detection-tools.md) — full reference for drift detection scripts
- [Scoring and categories](../../reference/documentation/scoring-and-categories.md) — freshness scoring methodology
- [Documentation standards](../../explanation/documentation/standards.md) — general documentation rules
- [Settings schema](../../reference/settings-schema.md) — `documentation.directory` configuration
