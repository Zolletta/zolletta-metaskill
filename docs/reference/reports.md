---
audience: human, ai
status: stable
skills: [setup, review, patterns, documentor, external-review, python-code-style, python-testing-patterns]
---

# Reports Reference

All review reports are saved to a timestamped directory under the reports path configured in `settings.json` (default: `.zolletta-metaskill/reports/`).

## Directory structure

```text
<reports_dir>/<YYYY-MM-DD-HH-MM>/<subcommand>.md
```

The timestamp format (`YYYY-MM-DD-HH-MM`) is lexicographically sortable, so finding the most recent review is a simple directory listing.

## Report files

Each subcommand writes its own report file:

| Subcommand                | Report file                  | Content                                                                                 |
|---|---|---|
| `patterns`                | `patterns.md`                | God class findings, SOLID violations, coupling analysis, structural convention results  |
| `documentor`              | `documentor.md`              | Diátaxis compliance findings, drift detection results, staleness scores, link integrity |
| `python-code-style`       | `python-code-style.md`       | Linting findings, formatting issues, naming violations, docstring gaps, type errors     |
| `python-testing-patterns` | `python-testing-patterns.md` | Coverage gaps, test isolation issues, naming violations, fixture design findings        |
| `external-review`         | `external-review.md`         | External LLM review of modified files                                                   |

## Orchestrator output

When running `/zolletta-metaskill review`, the orchestrator produces two additional files:

| File         | Content                                                                                                         |
|---|---|
| `SUMMARY.md` | Graded summary of all sub-reviews, with links to each specialist report                                         |
| `TODO.md`    | Aggregated, prioritized TODO list organized by functional priority (dependency changes first, then by severity) |

## Report format

Each report follows the [report template](../../assets/report_template.md) structure:

1. **Grade** at the top (A–F or numeric score)
2. **Scanning script results** (tables of raw output)
3. **Findings** grouped by severity (critical, high, medium, low)
4. Each finding includes: file, line, issue, principle violated, suggested fix

## Previous review comparison

The orchestrator reads the previous review's `TODO.md` (if it exists) and compares it with the current one. Items that were in the previous TODO but are no longer found are marked as "completed" in the new SUMMARY.md. This provides a feedback loop for tracking review-driven improvements over time.

## Report conventions

- Reports are written in markdown for readability in any text editor or GitHub renderer.
- File paths in findings are relative to the project root.
- Findings are never hedged — see [review-mode.md](code/review-mode.md) for the anti-hedging rules.
- Auto-fixable issues are listed in a separate informational section and do not count toward the grade.
