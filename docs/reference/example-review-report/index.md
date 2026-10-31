---
audience: human
status: stable
skills: [review]
---

# Example Review Report

This is a real output from `/zolletta-metaskill review` run on `playground/` — a seeded-defect fixture inside this repository — so every report contains genuine findings at all severities (overall grade 46/100, "Poor"). The report was generated on 2026-10-24 and is preserved here as a reference for what the review output looks like when the code under review has real problems.

## Files

| File                                                     | Description                                                                                                                  |
|----------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------|
| [SUMMARY.md](SUMMARY.md)                                 | Executive summary: overall grade, grades by area, strengths, weaknesses, prioritized Open/Done items, previous-review status |
| [patterns.md](patterns.md)                               | Design pattern review — God classes, SOLID, coupling, composition vs inheritance                                             |
| [documentor.md](documentor.md)                           | Documentation review — Diátaxis compliance, drift detection, broken links, API validation                                    |
| [python-code-style.md](python-code-style.md)             | Python source code style — ruff, mypy, naming, docstrings, type annotations                                                  |
| [python-testing-patterns.md](python-testing-patterns.md) | Python test code review — isolation, naming, coverage gaps, mutation testing, mocking, fixtures                              |

## Report structure

Every review produces a timestamped run folder under `.zolletta-metaskill/<YYYY-MM-DD-HH-MM>/` containing `reports/` (LLM judgment) and `cache/` (deterministic script outputs). The orchestrator launches subagents for each review area in parallel, each writing its own report to `reports/`. The orchestrator then aggregates grades and collects actionable items into `reports/SUMMARY.md`.

See [Reports](../reports.md) for the file format specification and templates.
