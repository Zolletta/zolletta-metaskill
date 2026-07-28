---
audience: human, ai
status: stable
skills: [documentor]
---

# Workflows & Tool Reference

Read this when running a drift analysis end-to-end, wiring tools into CI, or looking up the exact flags, parameters, output formats, and exit codes for each CLI tool.

## Quick Start

```bash
# 1. Run full drift analysis on a repository
python src/zolletta_metaskill/documentor/drift_analyzer.py /path/to/repo

# 2. Score documentation freshness
python src/zolletta_metaskill/documentor/doc_staleness_scorer.py /path/to/repo

# 3. Validate API docs against Python source
python src/zolletta_metaskill/documentor/api_doc_validator.py /path/to/repo/src /path/to/repo/docs/api.md

# 4. Check all markdown links
python src/zolletta_metaskill/documentor/link_checker.py /path/to/repo

# JSON output for any tool
python src/zolletta_metaskill/documentor/drift_analyzer.py /path/to/repo --json

# Set failure threshold for CI
python src/zolletta_metaskill/documentor/doc_staleness_scorer.py /path/to/repo --threshold 60
```

All tools support `--help` for full usage details.

## Core Workflows

### Workflow 1: Full Drift Analysis

Scan all documentation against code changes since each doc was last updated. This is the primary entry point for understanding the overall drift state of a repository.

```bash
# Basic analysis
python src/zolletta_metaskill/documentor/drift_analyzer.py /path/to/repo

# Analyze with custom doc patterns
python src/zolletta_metaskill/documentor/drift_analyzer.py /path/to/repo --doc-patterns "*.md,*.rst,*.txt"

# JSON output for tooling
python src/zolletta_metaskill/documentor/drift_analyzer.py /path/to/repo --json

# Only show high-severity drift
python src/zolletta_metaskill/documentor/drift_analyzer.py /path/to/repo --min-severity high

# Analyze specific directory
python src/zolletta_metaskill/documentor/drift_analyzer.py /path/to/repo --scope src/
```

**What it does:** Maps docs to code, compares git histories, classifies drift by category/severity/fix-type.

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
python src/zolletta_metaskill/documentor/api_doc_validator.py /path/to/src /path/to/docs/api.md

# Scan entire docs directory
python src/zolletta_metaskill/documentor/api_doc_validator.py /path/to/src /path/to/docs/ --recursive

# JSON output
python src/zolletta_metaskill/documentor/api_doc_validator.py /path/to/src /path/to/docs/api.md --json

# Include private methods in validation
python src/zolletta_metaskill/documentor/api_doc_validator.py /path/to/src /path/to/docs/ --include-private
```

**What it detects:** Detects undocumented items, phantom docs, parameter mismatches, deprecations. See [drift-detection-tools.md](drift-detection-tools.md).

### Workflow 3: README Health Check

Validate README sections against the actual project state. This combines drift analysis, link checking, and completeness scoring into a single README-focused report.

```bash
# Check README health
python src/zolletta_metaskill/documentor/doc_staleness_scorer.py /path/to/repo --readme-focus

# Check with custom sections
python src/zolletta_metaskill/documentor/doc_staleness_scorer.py /path/to/repo --required-sections "Installation,Usage,API,Contributing,License"
```

**Validates:** README sections, version strings, file references, badges, code examples, and table of contents. Run with `--help` for the full list.

### Workflow 4: Link Integrity Audit

Check every link in every markdown file -- local file references, anchors, cross-document links, and optionally external URLs.

```bash
# Check all markdown links
python src/zolletta_metaskill/documentor/link_checker.py /path/to/repo

# Include external URL checks (slower, makes HTTP requests)
python src/zolletta_metaskill/documentor/link_checker.py /path/to/repo --check-external

# Check specific file
python src/zolletta_metaskill/documentor/link_checker.py /path/to/repo/README.md

# JSON output
python src/zolletta_metaskill/documentor/link_checker.py /path/to/repo --json

# Only show broken links
python src/zolletta_metaskill/documentor/link_checker.py /path/to/repo --broken-only
```

**What it checks:** Validates local files, anchors, cross-document anchors, images, case-sensitivity, duplicate anchors. See [drift-detection-tools.md](drift-detection-tools.md).

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
        run: python engineering/zolletta-documentor/src/zolletta_metaskill/documentor/drift_analyzer.py . --json > drift-report.json

      - name: Check staleness score
        run: python engineering/zolletta-documentor/src/zolletta_metaskill/documentor/doc_staleness_scorer.py . --threshold 50

      - name: Validate API docs
        run: python engineering/zolletta-documentor/src/zolletta_metaskill/documentor/api_doc_validator.py src/ docs/api.md

      - name: Check links
        run: python engineering/zolletta-documentor/src/zolletta_metaskill/documentor/link_checker.py .

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
python engineering/zolletta-documentor/src/zolletta_metaskill/documentor/doc_staleness_scorer.py . --threshold 30 --quiet
if [ $? -ne 0 ]; then
    echo "Documentation is critically stale. Update docs before committing."
    exit 1
fi
```

## Tool Reference

See [drift-detection-tools.md](drift-detection-tools.md) for the full tool reference (flags, parameters, exit codes).
