---
audience: human, ai
status: stable
skills: [setup, review, patterns, documentor, external-review, python-code-style, python-testing-patterns]
---

# Getting started

Welcome to Zolletta-MetaSkill — a family of generic code review skills with specializations for Python and other languages. This tutorial walks through installing the skill, setting up a project, and running a first review.

## What we will learn

- How to install zolletta-metaskill
- How to set up a project for reviews
- How to run a full review and read the report
- How to run individual review skills

## Prerequisites

- An AI agent that supports skills (Devin, Claude, Cursor, or similar)
- Git
- A project with source code to review

## Step 1 — Install

Clone the repository into the agent's skills directory:

```bash
git clone https://github.com/Zolletta/zolletta-metaskill.git ~/.agents/skills/zolletta-metaskill
```

Verify the installation by invoking the skill with no arguments:

```
/zolletta-metaskill
```

We should see the list of available subcommands: `setup`, `documentor`, `patterns`, `external-review`, `review`, `python-code-style`, `python-testing-patterns`.

## Step 2 — Set up the project

Navigate to the project we want to review and run setup:

```bash
cd /path/to/our/project
```

```
/zolletta-metaskill setup
```

Setup detects the project language, Docker container (if any), tokensave availability, and Python tooling (if Python). It writes `.zolletta-metaskill/settings.json` with all detected values. The file is added to `.gitignore` automatically.

Verify the configuration:

```bash
cat .zolletta-metaskill/settings.json
```

## Step 3 — Run a full review

```
/zolletta-metaskill review
```

The review orchestrator runs all applicable skills in parallel:

- **patterns** — God classes, SOLID violations, structural conventions
- **documentor** — Diátaxis compliance, drift detection, freshness scoring
- **external-review** — external-LLM review of modified files
- **python-code-style** (Python only) — ruff, mypy, naming, docstrings, type annotations
- **python-testing-patterns** (Python only) — test isolation, coverage gaps, mocking, AAA structure

Each skill writes a report to `.zolletta-metaskill/reports/<timestamp>/`. The orchestrator creates `SUMMARY.md` with the overall grade and `TODO.md` with aggregated action items.

## Step 4 — Read the report

Open `.zolletta-metaskill/reports/<timestamp>/SUMMARY.md` to see:

- **Overall grade** (0–100)
- **Grades by area** — patterns, documentor, code style, testing
- **Top strengths** — what the project does well
- **Top weaknesses** — what needs improvement
- **Priority items** — the most important findings to address

Then open `TODO.md` for the aggregated action items sorted by priority (P1 = critical, P2 = high, P3 = medium, P4 = low).

## Step 5 — Run individual skills

We can run any skill individually for a focused review:

```
/zolletta-metaskill patterns       # God classes and SOLID only
/zolletta-metaskill documentor     # Documentation review only
/zolletta-metaskill python-code-style    # Python code style only
/zolletta-metaskill python-testing-patterns  # Python test code only
/zolletta-metaskill external-review      # External-LLM review of changes
```

## Next steps

- [Run a full review](../how-to/run-full-review.md) — detailed guide on the review orchestrator
- [Set up a project](../how-to/setup-project.md) — detailed guide on setup
- [Detect God classes](../how-to/code/detect-god-classes.md) — how the patterns skill works
- [Review Python code style](../how-to/code/python/review-python-style.md) — Python-specific style review
- [Settings schema](../reference/settings-schema.md) — all configuration options
