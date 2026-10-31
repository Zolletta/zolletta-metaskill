---
audience: human, ai
status: stable
skills: [documentor]
---

# Drift Detection Tools Reference

The `documentor` skill includes a top-level orchestrator plus four domain tools. All run on the package's Python (>=3.12 per `pyproject.toml`) and import only the standard library plus the shared `zolletta_metaskill.core` helpers.

## Tools

| Tool                                                                                             | Purpose                                                                     | Command                                                                                                          |
|--------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------|
| `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/documentor_client.py`               | Run all tools and aggregate into one report                                 | `python skills/zolletta-metaskill/src/zolletta_metaskill/documentor/documentor_client.py [--json]`               |
| `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/quality_review.py`          | Unified drift + staleness review (writes `quality.json`)                    | `python skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/quality_review.py [--json]`          |
| `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/api_doc/api_doc_validator.py`       | Validate API docs against Python source (AST)                               | `python skills/zolletta-metaskill/src/zolletta_metaskill/documentor/api_doc/api_doc_validator.py [--json]`       |
| `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/links/link_checker.py`              | Audit all markdown links and anchors                                        | `python skills/zolletta-metaskill/src/zolletta_metaskill/documentor/links/link_checker.py [--broken-only]`       |
| `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/unwrapped_prose_scanner.py` | Flag markdown paragraphs hard-wrapped mid-sentence (opt-in, run separately) | `python skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/unwrapped_prose_scanner.py [--json]` |

All tools: Python 3.12+, `[--json]`, run from the repository root, any OS. All configuration — docs directory, source roots, thresholds — comes from `.zolletta-metaskill/settings.json` under `documentation.*`.

Each tool writes its own JSON cache artifact into the current run folder, `<runs_dir>/<YYYY-MM-DD-HH-MM>/cache/` — `.zolletta-metaskill/<timestamp>/cache/` with the default `runs_dir` — so each review keeps its own history instead of overwriting the last. Before the first run folder exists, artifacts land in `<runs_dir>/cache/`:

| Tool cache file          | Produced by                                                                                |
|--------------------------|--------------------------------------------------------------------------------------------|
| `quality.json`           | `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/quality_review.py`    |
| `api_doc_validator.json` | `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/api_doc/api_doc_validator.py` |
| `link_checker.json`      | `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/links/link_checker.py`        |

## skills/zolletta-metaskill/src/zolletta_metaskill/documentor/documentor_client.py

Top-level orchestrator. Runs the quality review, API doc validation, and link checking, then merges their cache files into a single report via `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/report_aggregator.py`. Prints Markdown by default, JSON with `--json`. Respects settings and skips gracefully when a tool has no applicable work (the tool still writes a skip cache record so the aggregate report includes the section).

```bash
python skills/zolletta-metaskill/src/zolletta_metaskill/documentor/documentor_client.py [--json]
```

The aggregated report has named sections — `quality`, `api_doc`, `links` — plus a high-level summary (aggregate quality score/label, totals for documents, drift issues, API-doc issues/suggestions, links checked, broken links, duplicate anchors, and any missing cache sections). Enforces `documentation.staleness_threshold` on the aggregate quality score.

## skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/quality_review.py

Unified documentation quality review: combines drift detection (`skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/drift_detector.py`) and multi-dimensional staleness scoring (`skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/quality_scorer.py`) in a single pass, writes `quality.json`. Maps docs to code, compares git histories, detects renamed files, version drift, and structural gaps; classifies each drift issue by category, severity, and fix type; scores freshness 0-100 across five dimensions. Respects `.gitignore`. Documentation is the markdown under `documentation.dir` plus the root documents `README.md`, `CONTRIBUTING.md` and `AGENTS.md`; `skills/`, `SKILL.md` and `CHANGELOG.md` are out of scope.

```bash
python skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/quality_review.py [--json]
```

| Setting                               | Default      | Description                                       |
|---------------------------------------|--------------|---------------------------------------------------|
| `documentation.dir`                   | `docs`       | Documentation directory                           |
| `<lang>.paths.source`                 | `src`/`src/` | Code analysis scope = union of source roots       |
| `documentation.min_severity`          | `low`        | Minimum severity to report (high, medium, low)    |
| `documentation.include_referential`   | false        | Include referential drift (suppressed by default) |
| `documentation.staleness_threshold`   | (none)       | Fail if score drops below this value              |
| `documentation.readme_focus`          | false        | Focus on README-style docs                        |
| `documentation.readme_sections`       | (auto)       | Comma-separated required section names            |
| `documentation.staleness_weights`     | (defaults)   | Scoring weights for the five dimensions           |
| `documentation.diataxis_translations` | (none)       | Translated README section names                   |

`staleness_weights` is a mapping over `last_updated`, `code_doc_alignment`, `link_health`, `completeness`, `accuracy`.

**Per-file factual drift**: only flags when specific referenced source files changed. Referential drift suppressed by default (`include_referential`); `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/links/link_checker.py` covers broken links more reliably.

## skills/zolletta-metaskill/src/zolletta_metaskill/documentor/api_doc/api_doc_validator.py

AST-based extraction of Python signatures/classes compared against markdown API docs. Reports real drift (phantom docs, parameter mismatches, deprecations) as issues. Undocumented items are separated as prioritized suggestions. Writes `api_doc_validator.json`.

```bash
python skills/zolletta-metaskill/src/zolletta_metaskill/documentor/api_doc/api_doc_validator.py [--json]
```

| Setting                                  | Default | Description                                        |
|------------------------------------------|---------|----------------------------------------------------|
| `python.paths.source`                    | `[src]` | Source roots to extract signatures from            |
| `documentation.dir`                      | `docs`  | Docs file or directory                             |
| `documentation.api_doc_recursive`        | false   | Scan docs directory recursively                    |
| `documentation.api_doc_include_private`  | false   | Include private methods in validation              |
| `documentation.api_doc_suggest_coverage` | false   | Show undocumented items as prioritized suggestions |

Undocumented items do not affect the exit code or issue count.

## skills/zolletta-metaskill/src/zolletta_metaskill/documentor/links/link_checker.py

Validates all markdown links: local files, anchors, cross-document anchors, images, case-sensitivity, and duplicate anchors. Optional external URL checks. Audits the repository at the current working directory. Writes `link_checker.json`.

```bash
python skills/zolletta-metaskill/src/zolletta_metaskill/documentor/links/link_checker.py [--broken-only] [--json]
```

| Option / Setting               | Default | Description                               |
|--------------------------------|---------|-------------------------------------------|
| `--broken-only`                | off     | Only show broken links                    |
| `documentation.check_external` | false   | Check external URLs (makes HTTP requests) |

## skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/unwrapped_prose_scanner.py

Flags markdown paragraphs hard-wrapped across lines — a formatting rule, not a wording one (the text renders identically either way). Deliberately outside `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/documentor_client.py`: the check is opt-in, and its findings are formatting noise until the backlog is cleared. Prints findings to stdout and writes no cache artifact.

```bash
python skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/unwrapped_prose_scanner.py [--json]
```

| Setting                               | Default | Description                     |
|---------------------------------------|---------|---------------------------------|
| `documentation.check_unwrapped_prose` | false   | Enable the unwrapped-prose scan |

## Exit codes

All tools are report-only and exit 0 on findings; exit 1 is reserved for usage errors (e.g. no configured docs/source directories on disk). The one exception is the quality review (`skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/quality_review.py` and `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/documentor_client.py`): when `documentation.staleness_threshold` is set it exits 1 if the aggregate score drops below the threshold, preserving the CI gate.
