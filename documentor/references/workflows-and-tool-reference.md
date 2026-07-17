# Workflows & Tool Reference

Read this when running a drift analysis end-to-end, wiring tools into CI, or looking up the exact flags, parameters, output formats, and exit codes for each CLI tool.

## Quick Start

```bash
# 1. Run full drift analysis on a repository
python scripts/drift_analyzer.py /path/to/repo

# 2. Score documentation freshness
python scripts/doc_staleness_scorer.py /path/to/repo

# 3. Validate API docs against Python source
python scripts/api_doc_validator.py /path/to/repo/src /path/to/repo/docs/api.md

# 4. Check all markdown links
python scripts/link_checker.py /path/to/repo

# JSON output for any tool
python scripts/drift_analyzer.py /path/to/repo --json

# Set failure threshold for CI
python scripts/doc_staleness_scorer.py /path/to/repo --threshold 60
```

All tools support `--help` for full usage details.

## Core Workflows

### Workflow 1: Full Drift Analysis

Scan all documentation against code changes since each doc was last updated. This is the primary entry point for understanding the overall drift state of a repository.

```bash
# Basic analysis
python scripts/drift_analyzer.py /path/to/repo

# Analyze with custom doc patterns
python scripts/drift_analyzer.py /path/to/repo --doc-patterns "*.md,*.rst,*.txt"

# JSON output for tooling
python scripts/drift_analyzer.py /path/to/repo --json

# Only show high-severity drift
python scripts/drift_analyzer.py /path/to/repo --min-severity high

# Analyze specific directory
python scripts/drift_analyzer.py /path/to/repo --scope src/
```

**What it does:**

1. Discovers all documentation files in the repo
2. For each doc, identifies the code directories it describes (via path proximity and content references)
3. Compares the doc's last-modified date against the git history of its associated code
4. Identifies specific changes (renamed files, moved directories, changed function signatures)
5. Classifies each drift instance by category and severity
6. Generates an actionable report with specific file:line references

**Output example:**

```text
Documentation Drift Report
==========================
Repository: /path/to/repo
Scan date:  2026-03-18
Docs found: 12
Drifted:    5

HIGH SEVERITY:
  docs/api.md (last updated: 2026-01-15)
    - 23 code files changed since doc update
    - 4 functions renamed in src/handlers/
    - 2 new modules undocumented
    Category: Factual + Structural
    Recommendation: Manual update required

MEDIUM SEVERITY:
  README.md (last updated: 2026-02-28)
    - Installation section references removed dependency
    - Version string outdated (says 1.8.0, current 2.0.0)
    Category: Factual + Temporal
    Recommendation: Auto-fixable (version), Manual (installation)
```

### Workflow 2: API Documentation Validation

Check that API documentation accurately reflects the actual function signatures, class definitions, and module structure in your Python source code.

```bash
# Validate API docs against source
python scripts/api_doc_validator.py /path/to/src /path/to/docs/api.md

# Scan entire docs directory
python scripts/api_doc_validator.py /path/to/src /path/to/docs/ --recursive

# JSON output
python scripts/api_doc_validator.py /path/to/src /path/to/docs/api.md --json

# Include private methods in validation
python scripts/api_doc_validator.py /path/to/src /path/to/docs/ --include-private
```

**What it detects:**

- Functions/classes present in code but missing from docs
- Functions/classes documented but no longer in code (removed or renamed)
- Parameter mismatches (missing params, wrong types, wrong defaults)
- Deprecated items still documented as current
- Return type mismatches
- Module-level docstring drift

**How it works:**

The tool uses Python's `ast` module to parse source files and extract function signatures, class definitions, decorators, and docstrings. It then parses the markdown documentation looking for function/class references, parameter lists, and code blocks. Mismatches are reported with exact locations in both source and documentation.

### Workflow 3: README Health Check

Validate README sections against the actual project state. This combines drift analysis, link checking, and completeness scoring into a single README-focused report.

```bash
# Check README health
python scripts/doc_staleness_scorer.py /path/to/repo --readme-focus

# Check with custom sections
python scripts/doc_staleness_scorer.py /path/to/repo --required-sections "Installation,Usage,API,Contributing,License"
```

**Validates:**

- Required sections are present (Installation, Usage, API Reference, Contributing, License)
- Version strings match package version (package.json, setup.py, pyproject.toml)
- File references in README actually exist
- Badge URLs are well-formed
- Code examples reference existing files/functions
- Table of contents matches actual headings

### Workflow 4: Link Integrity Audit

Check every link in every markdown file -- local file references, anchors, cross-document links, and optionally external URLs.

```bash
# Check all markdown links
python scripts/link_checker.py /path/to/repo

# Include external URL checks (slower, makes HTTP requests)
python scripts/link_checker.py /path/to/repo --check-external

# Check specific file
python scripts/link_checker.py /path/to/repo/README.md

# JSON output
python scripts/link_checker.py /path/to/repo --json

# Only show broken links
python scripts/link_checker.py /path/to/repo --broken-only
```

**What it checks:**

- Local file references (`[link](path/to/file.md)`) -- does the file exist?
- Anchor references (`[link](#section-name)`) -- does the heading exist?
- Cross-document anchors (`[link](other.md#section)`) -- does the file and heading exist?
- Relative path correctness (catches `../` errors)
- Case sensitivity issues (common on Linux but silent on macOS)
- Image references -- do referenced images exist?
- Duplicate anchors that would cause ambiguous links

### Workflow 5: Continuous Doc Monitoring

Integrate documentation drift detection into your CI/CD pipeline for ongoing monitoring.

**GitHub Actions example:**

```yaml
name: Documentation Drift Check
on:
  pull_request:
    branches: [main, dev]
  push:
    branches: [main]

jobs:
  doc-drift:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0 # Full history for git log analysis

      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Run drift analysis
        run: python engineering/zolletta-documentor/scripts/drift_analyzer.py . --json > drift-report.json

      - name: Check staleness score
        run: python engineering/zolletta-documentor/scripts/doc_staleness_scorer.py . --threshold 50

      - name: Validate API docs
        run: python engineering/zolletta-documentor/scripts/api_doc_validator.py src/ docs/api.md

      - name: Check links
        run: python engineering/zolletta-documentor/scripts/link_checker.py .

      - name: Upload drift report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: drift-report
          path: drift-report.json
```

**Pre-commit hook:**

```bash
#!/bin/bash
# .git/hooks/pre-commit
# Fail commit if docs are severely stale
python engineering/zolletta-documentor/scripts/doc_staleness_scorer.py . --threshold 30 --quiet
if [ $? -ne 0 ]; then
    echo "Documentation is critically stale. Update docs before committing."
    exit 1
fi
```

## Tools Summary

| Tool                      | Purpose                                   | Lines | Key Feature                                       |
| ------------------------- | ----------------------------------------- | ----- | ------------------------------------------------- |
| `drift_analyzer.py`       | Full drift analysis between code and docs | ~550  | Git history comparison with code-to-doc mapping   |
| `doc_staleness_scorer.py` | Score documentation freshness 0-100       | ~450  | Weighted multi-dimensional scoring                |
| `api_doc_validator.py`    | Validate API docs against Python source   | ~400  | AST-based signature extraction and comparison     |
| `link_checker.py`         | Audit all markdown links and anchors      | ~400  | Local file, anchor, and cross-document validation |

All tools:

- Python 3.8+ standard library only
- Support `--json` for machine-readable output
- Support `--help` for usage details
- Use non-zero exit codes on failure (CI/CD compatible)
- Work on any OS (Windows, macOS, Linux)

## Tool Reference

### drift_analyzer.py

**Purpose:** Scan a git repository for documentation that has fallen out of sync with code. Maps documentation files to their associated code directories, compares git modification dates, detects renamed files, version string drift, broken references, and structural gaps. Classifies every issue by category, severity, and fix type.

**Usage:**

```bash
python scripts/drift_analyzer.py <repo_path> [options]
```

**Parameters:**

| Flag             | Type       | Default                   | Description                                                                                 |
| ---------------- | ---------- | ------------------------- | ------------------------------------------------------------------------------------------- |
| `repo_path`      | positional | _(required)_              | Path to the git repository to analyze                                                       |
| `--json`         | flag       | off                       | Output the full drift report as JSON                                                        |
| `--min-severity` | choice     | `low`                     | Minimum severity to include in report. Choices: `critical`, `high`, `medium`, `low`, `info` |
| `--scope`        | string     | `""` (all)                | Limit code analysis to a subdirectory (e.g., `src/`)                                        |
| `--doc-patterns` | string     | `*.md,*.rst,*.txt,*.adoc` | Comma-separated file patterns for documentation discovery                                   |

**Example:**

```bash
python scripts/drift_analyzer.py /path/to/repo --min-severity medium --scope src/ --json
```

**Output Formats:**

- **Human-readable** (default): Grouped by severity with `[AUTO]`/`[SEMI]`/`[MANUAL]` fix-type tags, category labels, and a fix-type summary
- **JSON** (`--json`): Structured object with `repository`, `scan_date`, `summary` (counts by severity, category, fix type), and `issues` array

**Exit Codes:** 0 = no high/critical issues, 1 = high or critical issues found, 2 = tool error (invalid path, not a git repo)

### doc_staleness_scorer.py

**Purpose:** Score documentation freshness on a weighted 0-100 scale across five dimensions: last updated, code-doc alignment, link health, completeness, and accuracy. Supports CI/CD threshold gates and README-focused analysis.

**Usage:**

```bash
python scripts/doc_staleness_scorer.py <repo_path> [options]
```

**Parameters:**

| Flag                      | Type       | Default                                       | Description                                                                                                                               |
| ------------------------- | ---------- | --------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| `repo_path`               | positional | _(required)_                                  | Path to the git repository to score                                                                                                       |
| `--json`                  | flag       | off                                           | Output the full scoring report as JSON                                                                                                    |
| `--threshold`             | float      | _(none)_                                      | Fail with exit code 1 if aggregate score falls below this value                                                                           |
| `--readme-focus`          | flag       | off                                           | Only score README files (filenames starting with `readme`)                                                                                |
| `--required-sections`     | string     | `Installation,Usage,API,Contributing,License` | Comma-separated section names for completeness scoring                                                                                    |
| `--diataxis-translations` | string     | _(none)_                                      | Path to a JSON file with translated Diátaxis headings and directory names (for non-English documentation). See below for the JSON format. |
| `--quiet`                 | flag       | off                                           | Only print the aggregate score number (no report)                                                                                         |
| `--weight-updated`        | float      | `0.20`                                        | Weight for the "last updated" dimension                                                                                                   |
| `--weight-alignment`      | float      | `0.30`                                        | Weight for the "code-doc alignment" dimension                                                                                             |
| `--weight-links`          | float      | `0.15`                                        | Weight for the "link health" dimension                                                                                                    |
| `--weight-completeness`   | float      | `0.20`                                        | Weight for the "completeness" dimension                                                                                                   |
| `--weight-accuracy`       | float      | `0.15`                                        | Weight for the "accuracy" dimension                                                                                                       |

**Example:**

```bash
python scripts/doc_staleness_scorer.py /path/to/repo --threshold 60 --readme-focus --quiet
```

**Output Formats:**

- **Human-readable** (default): Aggregate score with label, per-file score table sorted worst-first, and dimension breakdown with ASCII bars for the bottom 5 files
- **JSON** (`--json`): Structured object with `aggregate_score`, `aggregate_label`, `total_documents`, and `documents` array (each with `total_score`, `label`, and per-dimension scores/details)
- **Quiet** (`--quiet`): Single line with the aggregate score (e.g., `72.3`)

**Exit Codes:** 0 = score above threshold (or no threshold set), 1 = score below threshold, 2 = tool error

**`--diataxis-translations` JSON format:**

For non-English documentation, the agent translates the English signpost headings and directory names into the documentation language and writes them to a JSON file. The English strings act as signposts — the agent translates each one.

```json
{
  "readme_sections": [
    "installazione",
    "utilizzo",
    "api",
    "contribuire",
    "licenza"
  ],
  "quadrants": {
    "tutorials": {
      "dir_names": ["tutorials", "tutorial", "guide"],
      "required_sections": ["cosa impareremo", "prerequisiti"]
    },
    "how-to": {
      "dir_names": ["come-fare", "guide-pratiche"],
      "any_of_groups": [["prerequisiti", "prima di iniziare"]]
    },
    "reference": {
      "dir_names": ["riferimento", "api"]
    },
    "explanation": {
      "dir_names": ["spiegazione", "design", "architettura"]
    }
  }
}
```

- `readme_sections`: translated equivalents of `installation`, `usage`, `api`, `contributing`, `license` (used for non-Diátaxis docs)
- `quadrants.<name>.dir_names`: **added** to the English defaults (additive merge — both languages are matched)
- `quadrants.<name>.required_sections`: **replaces** the English list (the translated version is authoritative)
- `quadrants.<name>.any_of_groups`: **replaces** the English groups

### api_doc_validator.py

**Purpose:** Extract function and class signatures from Python source files using the `ast` module and compare them against API documentation in markdown files. Detects undocumented items, phantom documentation for removed code, parameter mismatches, and deprecated items.

**Usage:**

```bash
python scripts/api_doc_validator.py <source_path> <doc_path> [options]
```

**Parameters:**

| Flag                | Type       | Default      | Description                                                      |
| ------------------- | ---------- | ------------ | ---------------------------------------------------------------- |
| `source_path`       | positional | _(required)_ | Path to a Python source file or directory                        |
| `doc_path`          | positional | _(required)_ | Path to API documentation file (`.md`) or directory              |
| `--json`            | flag       | off          | Output the validation report as JSON                             |
| `--recursive`       | flag       | off          | Recursively scan the doc directory for markdown files            |
| `--include-private` | flag       | off          | Include `_`-prefixed private functions and classes in validation |

**Example:**

```bash
python scripts/api_doc_validator.py /path/to/src /path/to/docs/ --recursive --include-private --json
```

**Output Formats:**

- **Human-readable** (default): Summary counts (source signatures, documented items, issues), then issues grouped by severity with type tags, source/doc file locations, and a summary-by-type table
- **JSON** (`--json`): Structured object with `summary` (counts by type and severity) and `issues` array (each with `type`, `severity`, `name`, file/line references, and `description`)

**Exit Codes:** 0 = no high-severity issues, 1 = high-severity issues found (e.g., documented items missing from source), 2 = tool error

### link_checker.py

**Purpose:** Scan markdown files for every link type (local files, anchors, cross-document anchors, images, HTML links, reference-style links) and validate them against the filesystem and document headings. Optionally validates external URLs via HTTP HEAD requests. Also detects duplicate heading anchors.

**Usage:**

```bash
python scripts/link_checker.py <path> [options]
```

**Parameters:**

| Flag               | Type       | Default      | Description                                                                         |
| ------------------ | ---------- | ------------ | ----------------------------------------------------------------------------------- |
| `path`             | positional | _(required)_ | File or directory to check (single `.md` file or directory for recursive scan)      |
| `--json`           | flag       | off          | Output the link check report as JSON                                                |
| `--broken-only`    | flag       | off          | Only show broken links in the report (omit valid links from output)                 |
| `--check-external` | flag       | off          | Also validate external URLs via HTTP HEAD requests (slower, makes network requests) |

**Example:**

```bash
python scripts/link_checker.py /path/to/repo --broken-only --json
```

**Output Formats:**

- **Human-readable** (default): Summary counts (total, valid, broken, skipped, duplicate anchors), broken links grouped by source file with line numbers and error messages, duplicate anchor list, and link-type breakdown table
- **JSON** (`--json`): Structured object with `summary` (counts), `broken_links` array (each with source file, line, text, target, type, error), `duplicate_anchors` map, and optionally `all_links` (when `--broken-only` is not set)

**Exit Codes:** 0 = no broken links and no duplicate anchors, 1 = broken links or duplicate anchors found, 2 = tool error
