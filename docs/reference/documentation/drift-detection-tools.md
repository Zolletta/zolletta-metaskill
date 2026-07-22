---
audience: human, ai
status: stable
skills: [documentor]
---

# Drift Detection Tools Reference

The `documentor` skill includes four drift detection tools. All are Python 3.8+ stdlib only — no external dependencies required.

## Tools

| Tool | Purpose | Command |
|------|---------|---------|
| `drift_analyzer.py` | Full drift analysis between code and docs | `python scripts/drift_analyzer.py <repo> --min-severity high --json` |
| `doc_staleness_scorer.py` | Score documentation freshness 0-100 | `python scripts/doc_staleness_scorer.py <repo> --threshold 60` |
| `api_doc_validator.py` | Validate API docs against Python source (AST) | `python scripts/api_doc_validator.py <src> <docs> --recursive` |
| `link_checker.py` | Audit all markdown links and anchors | `python scripts/link_checker.py <repo> --broken-only` |

All tools: Python 3.8+ stdlib only, `--json` and `--help`, non-zero exit codes for CI, any OS.

## drift_analyzer.py

Full drift analysis between code and documentation. Maps docs to code, compares git histories, detects renamed files, version drift, and structural gaps. Classifies each issue by category, severity, and fix type.

```bash
python scripts/drift_analyzer.py <repo> [--doc-patterns "*.md,*.rst,*.txt"] [--scope src/] [--min-severity high] [--include-referential] [--json]
```

| Option | Default | Description |
|--------|---------|-------------|
| `<repo>` | (required) | Repository root path |
| `--doc-patterns` | `*.md,*.rst,*.txt` | Comma-separated doc file patterns |
| `--scope` | (all) | Limit analysis to a specific directory |
| `--min-severity` | (all) | Minimum severity to report (high, medium, low) |
| `--include-referential` | off | Include referential drift (suppressed by default) |
| `--json` | off | JSON output for tooling |

**Per-file factual drift**: only flags when specific referenced source files changed. Referential drift suppressed by default (use `--include-referential`); `link_checker.py` covers broken links more reliably.

## doc_staleness_scorer.py

Scores documentation freshness on a 0-100 scale across five dimensions. Respects `.gitignore`.

```bash
python scripts/doc_staleness_scorer.py <repo> [--threshold N] [--readme-focus] [--required-sections "..."] [--json]
```

| Option | Default | Description |
|--------|---------|-------------|
| `<repo>` | (required) | Repository root path |
| `--threshold` | (none) | Fail if score drops below this value |
| `--readme-focus` | off | Focus on README-style docs |
| `--required-sections` | (auto) | Comma-separated required section names |
| `--json` | off | JSON output for tooling |

Weight customization flags: `--weight-updated`, `--weight-alignment`, `--weight-links`, `--weight-completeness`, `--weight-accuracy`.

## api_doc_validator.py

AST-based extraction of Python signatures/classes compared against markdown API docs. Reports real drift (phantom docs, parameter mismatches, deprecations) as issues. Undocumented items are separated as prioritized suggestions.

```bash
python scripts/api_doc_validator.py <src> <docs> [--recursive] [--include-private] [--suggest-coverage] [--json]
```

| Option | Default | Description |
|--------|---------|-------------|
| `<src>` | (required) | Source directory |
| `<docs>` | (required) | Docs file or directory |
| `--recursive` | off | Scan docs directory recursively |
| `--include-private` | off | Include private methods in validation |
| `--suggest-coverage` | off | Show undocumented items as prioritized suggestions |
| `--json` | off | JSON output for tooling |

Undocumented items do not affect the exit code or issue count.

## link_checker.py

Validates all markdown links: local files, anchors, cross-document anchors, images, case-sensitivity, and duplicate anchors. Optional external URL checks.

```bash
python scripts/link_checker.py <repo> [--check-external] [--broken-only] [--json]
```

| Option | Default | Description |
|--------|---------|-------------|
| `<repo>` | (required) | Repository root or specific file |
| `--check-external` | off | Check external URLs (makes HTTP requests) |
| `--broken-only` | off | Only show broken links |
| `--json` | off | JSON output for tooling |

## Exit codes

All tools return non-zero exit codes for CI integration:

- Exit 0: No issues (or all within threshold)
- Exit 1: Issues found exceeding threshold
- Exit 2: Tool error (invalid arguments, missing files)
