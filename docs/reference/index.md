---
audience: human, ai
status: stable
skills: [setup, review, patterns, documentor, external-review, python-*]
---

# Reference

Accurate technical description of the tools. Aimed at users who need facts.

## Code review tools

Scanners, review conventions, and language-specific style rules.

| Document                                              | Description                                    |
|-------------------------------------------------------|------------------------------------------------|
| [Scripts reference](code/scripts.md)                  | All scanning scripts: usage, options, examples |
| [Review mode](code/review-mode.md)                    | Read-only review conventions                   |
| [Code exploration](code/code-exploration.md)          | tokensave decision tree and task templates     |
| [tokensave](code/tokensave.md)                        | tokensave MCP tools reference                  |
| [Python code style](code/python/python-code-style.md) | Python style rules and configurable toggles    |

## Documentation tools

Drift detection, staleness scoring, and operational conventions.

| Document                                                        | Description                                                   |
|-----------------------------------------------------------------|---------------------------------------------------------------|
| [Drift detection tools](documentation/drift-detection-tools.md) | drift_analyzer, staleness scorer, API validator, link checker |
| [Workflows & tools](documentation/workflows-and-tools.md)       | Quick start, 5 core workflows, CI recipes                     |
| [Scoring & categories](documentation/scoring-and-categories.md) | Staleness scoring model, drift categories, troubleshooting    |
| [Operational rules](documentation/operational-rules.md)         | Tool invocation conventions and drift report format           |

## Project configuration

Settings, subcommands, CI/CD, frontmatter, reports, and tool messages.

| Document                              | Description                                           |
|---------------------------------------|-------------------------------------------------------|
| [Settings schema](settings-schema.md) | Full field-by-field reference for `settings.json`     |
| [Subcommands](subcommands.md)         | All Zolletta-metaskill subcommands                    |
| [CI/CD workflows](ci-cd-workflows.md) | GitHub Actions workflows: scope and triggers          |
| [Frontmatter](frontmatter.md)         | SKILL.md frontmatter fields                           |
| [Reports](reports.md)                 | Report file format and templates                      |
| [Tool messages](tool-messages.md)     | "Not installed" messages for the tool-failure handler |

## Example review report

A real review output from dogfooding — see what the reports look like.

| Document                                                                 | Description                                               |
|--------------------------------------------------------------------------|-----------------------------------------------------------|
| [Overview](example-review-report/index.md)                               | Real review output from dogfooding — overview and files   |
| [SUMMARY.md](example-review-report/SUMMARY.md)                           | Executive summary with overall grade and trend            |
| [TODO.md](example-review-report/TODO.md)                                 | Prioritized action items (critical, high, medium, low)    |
| [patterns.md](example-review-report/patterns.md)                         | Design pattern review — God classes, SOLID, coupling      |
| [documentor.md](example-review-report/documentor.md)                     | Documentation review — Diátaxis compliance, drift         |
| [python-code-style.md](example-review-report/python-code-style.md)       | Python source code style — ruff, mypy, naming, docstrings |
| [python-testing-style.md](example-review-report/python-testing-style.md) | Python test code review — isolation, naming, coverage     |
