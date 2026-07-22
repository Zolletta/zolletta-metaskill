---
audience: human, ai
status: stable
skills: [review]
---

# Run a full review

> **Paths in this document are relative to the Zolletta-MetaSkill project root.**

Run a comprehensive code review that combines all available review skills in parallel. The `review` subcommand is the orchestrator — it reads the project language from `settings.json`, runs general and language-specific skills in parallel batches, and aggregates the results into a single summary report.

## Prerequisites

- A project set up with `/zolletta-metaskill setup` (`.zolletta-metaskill/settings.json` must exist)
- The zolletta-metaskill skill installed and available to the agent

## Steps

### Step 1 — Invoke the review

```
/zolletta-metaskill review
```

The orchestrator reads `language` from `settings.json` and determines which skills to run.

### Step 2 — Parallel skill execution

The orchestrator runs skills in parallel batches:

**General skills (always run):**
- `patterns` — God classes, SOLID, coupling, structural conventions
- `documentor` — Diátaxis compliance, drift detection, freshness scoring
- `external-review` — external-LLM review of modified files

**Language-specific skills (run when language matches):**
- `python-code-style` — Python source code style (ruff, mypy, naming, docstrings)
- `python-testing-patterns` — Python test code review (isolation, coverage, mocking)

Each skill runs as a subagent and writes its findings to a markdown report in the timestamped report folder.

### Step 3 — Aggregated report

The orchestrator collects all sub-skill reports and creates:

- `SUMMARY.md` — overall grade, grades by area, top strengths and weaknesses, priority items
- `TODO.md` — aggregated action items from all skills, sorted by priority

The reports are saved to `.zolletta-metaskill/reports/<timestamp>/`.

## Review mode

The full review runs in **read-only mode**: no fixes are applied, all tools run in check-only modes. Every diagnostic is classified as either auto-fixable (informational, not counted toward grade) or a finding (requires human judgment, counts toward grade). See [review mode](../reference/code/review-mode.md) for the full rules.

## Configuration

| Setting | Location | Default | Description |
|---------|----------|---------|-------------|
| `language` | `.zolletta-metaskill/settings.json` | (detected) | Determines which language-specific skills run |
| `reports_dir` | `.zolletta-metaskill/settings.json` | `.zolletta-metaskill/reports/` | Where report folders are created |
| `external_review_model` | `.zolletta-metaskill/settings.json` | `swe` | Model for the external review sub-skill |

## See also

- [Set up a project](setup-project.md) — initialize a project before running reviews
- [Review mode](../reference/code/review-mode.md) — shared rules for read-only reviews
- [Settings schema](../reference/settings-schema.md) — all configuration options
- [Reports](../reference/reports.md) — report folder structure and templates
