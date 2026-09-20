---
audience: human, ai
status: stable
skills: [documentor]
---

# Drift Detection Tools Reference

The `documentor` skill includes four drift detection tools. All are Python 3.8+ stdlib only — no external dependencies required.

## Tools

| Tool                      | Purpose                                       | Command                                                                     |
| ------------------------- | --------------------------------------------- | --------------------------------------------------------------------------- |
| `drift_analyzer.py`       | Full drift analysis between code and docs     | `python src/zolletta_metaskill/documentor/drift_analyzer.py [--json]`        |
| `doc_staleness_scorer.py` | Score documentation freshness 0-100           | `python src/zolletta_metaskill/documentor/doc_staleness_scorer.py [--json]`  |
| `api_doc_validator.py`    | Validate API docs against Python source (AST) | `python src/zolletta_metaskill/documentor/api_doc_validator.py [--json]`     |
| `link_checker.py`         | Audit all markdown links and anchors          | `python src/zolletta_metaskill/documentor/link_checker.py [--broken-only]`   |

All tools: Python 3.8+ stdlib only, `[--json]`, run from the repository root, any OS. All configuration — docs directory, source roots, thresholds — comes from `.zolletta-metaskill/settings.json` under `documentation.*`.

## drift_analyzer.py

Full drift analysis between code and documentation. Maps docs to code, compares git histories, detects renamed files, version drift, and structural gaps. Classifies each issue by category, severity, and fix type. Analyzes the repository at the current working directory.

```bash
python src/zolletta_metaskill/documentor/drift_analyzer.py [--json]
```

| Setting                            | Default            | Description                                       |
| ---------------------------------- | ------------------ | ------------------------------------------------- |
| `documentation.dir`                | `docs`             | Documentation directory                           |
| `documentation.doc_patterns`       | `*.md,*.rst,*.txt` | Comma-separated doc file patterns                 |
| `<lang>.paths.source`              | `src`/`src/`       | Code analysis scope = union of source roots       |
| `documentation.min_severity`       | `low`              | Minimum severity to report (high, medium, low)    |
| `documentation.include_referential` | false             | Include referential drift (suppressed by default) |

**Per-file factual drift**: only flags when specific referenced source files changed. Referential drift suppressed by default (`include_referential`); `link_checker.py` covers broken links more reliably.

## doc_staleness_scorer.py

Scores documentation freshness on a 0-100 scale across five dimensions. Respects `.gitignore`.

```bash
python src/zolletta_metaskill/documentor/doc_staleness_scorer.py [--json] [--quiet]
```

| Option / Setting                    | Default    | Description                            |
| ----------------------------------- | ---------- | -------------------------------------- |
| `--quiet`                           | off        | Output only the score number           |
| `documentation.staleness_threshold` | (none)     | Fail if score drops below this value   |
| `documentation.readme_focus`        | false      | Focus on README-style docs             |
| `documentation.readme_sections`     | (auto)     | Comma-separated required section names |
| `documentation.staleness_weights`   | (defaults) | Scoring weights for the five dimensions |
| `documentation.diataxis_translations` | (none)   | Translated README section names        |

`staleness_weights` is a mapping over `updated`, `alignment`, `links`, `completeness`, `accuracy`.

## api_doc_validator.py

AST-based extraction of Python signatures/classes compared against markdown API docs. Reports real drift (phantom docs, parameter mismatches, deprecations) as issues. Undocumented items are separated as prioritized suggestions.

```bash
python src/zolletta_metaskill/documentor/api_doc_validator.py [--json]
```

| Setting                            | Default | Description                                        |
| ---------------------------------- | ------- | -------------------------------------------------- |
| `python.paths.source`              | `[src]` | Source roots to extract signatures from            |
| `documentation.dir`                | `docs`  | Docs file or directory                             |
| `documentation.api_docs_recursive` | false   | Scan docs directory recursively                    |
| `documentation.include_private`    | false   | Include private methods in validation              |
| `documentation.suggest_coverage`   | false   | Show undocumented items as prioritized suggestions |

Undocumented items do not affect the exit code or issue count.

## link_checker.py

Validates all markdown links: local files, anchors, cross-document anchors, images, case-sensitivity, and duplicate anchors. Optional external URL checks. Audits the repository at the current working directory.

```bash
python src/zolletta_metaskill/documentor/link_checker.py [--broken-only] [--json]
```

| Option / Setting                | Default | Description                               |
| ------------------------------- | ------- | ----------------------------------------- |
| `--broken-only`                 | off     | Only show broken links                    |
| `documentation.check_external`  | false   | Check external URLs (makes HTTP requests) |

## Exit codes

All tools are report-only and exit 0 on findings; exit 1 is reserved for usage errors (e.g. no configured docs/source directories on disk). The one exception is `doc_staleness_scorer.py`: when `documentation.staleness_threshold` is set it exits 1 if the score drops below the threshold, preserving the CI gate.
