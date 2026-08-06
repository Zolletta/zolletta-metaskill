---
audience: human 
status: stable
skills: [review]
---

# Example Review Report

This is a real output from `/zolletta-metaskill review` run on the zolletta-metaskill project itself (dogfooding). The report was generated on 2026-08-06 and is preserved here as a reference for what the review output looks like.

## Files

| File | Description |
|------|-------------|
| [SUMMARY.md](SUMMARY.md) | Executive summary with overall grade, grades by area, strengths, weaknesses, and trend vs previous review |
| [TODO.md](TODO.md) | Prioritized action items (critical, high, medium, low) with source, files, problem, and fix |
| [patterns.md](patterns.md) | Design pattern review — God classes, SOLID, coupling, composition vs inheritance |
| [documentor.md](documentor.md) | Documentation review — Diátaxis compliance, drift detection, broken links, API validation |
| [python-code-style.md](python-code-style.md) | Python source code style — ruff, mypy, naming, docstrings, type annotations |
| [python-testing-style.md](python-testing-style.md) | Python test code review — isolation, naming, coverage gaps, mocking, fixtures |

## Report structure

Every review produces a timestamped folder under `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/` containing these files. The orchestrator launches subagents for each review area in parallel, each writing its own report. The orchestrator then aggregates grades into `SUMMARY.md` and collects actionable items into `TODO.md`.

See [Reports](../reports.md) for the file format specification and templates.
