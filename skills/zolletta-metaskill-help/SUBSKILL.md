---
name: zolletta-metaskill-help
description: >
  Display the zolletta-metaskill subcommand help table. Lists every
  available subcommand with its path and scope. Invoked when the user
  runs /zolletta-metaskill with no argument or /zolletta-metaskill help.
license: MIT + Commons Clause
---

# Zolletta-metaskill Help

Displays the subcommand help table so the user can see what's available.

## Subcommand table

This is the **single source of truth** for the subcommand list. The root `SKILL.md` and `docs/reference/subcommands.md` both reference this table.

| Subcommand             | Path                                   | Scope                                                                                                                                                                   |
|------------------------|----------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `help`                 | `skills/zolletta-metaskill-help/SUBSKILL.md`                 | Display the subcommand help table (also shown when no subcommand is given)                                                                                              |
| `setup`                | `skills/zolletta-metaskill-setup/SUBSKILL.md`                | Project initialization — creates `.zolletta-metaskill/settings.json`, detects language, Docker container, tokensave, and Python/PHP tooling                             |
| `documentor`           | `skills/zolletta-metaskill-documentor/SUBSKILL.md`           | [Diátaxis](https://diataxis.fr/) compliance + drift detection for project docs                                                                                          |
| `patterns`             | `skills/zolletta-metaskill-patterns/SUBSKILL.md`             | God classes, SOLID, coupling, composition vs inheritance for `src/`                                                                                                     |
| `review`               | `skills/zolletta-metaskill-review/SUBSKILL.md`               | Orchestrator — reads language from `settings.json`, runs general + language-specific skills in parallel batches, aggregates reports                                     |
| `adr-distiller`        | `skills/zolletta-metaskill-adr-distiller/SUBSKILL.md`     | Distill Accepted ADRs into `adr-distilled.md` architectural directives (mtime-cached, called by `review` at Step 3.5)                                                   |
| `python-code-style`    | `skills/zolletta-metaskill-python-code-style/SUBSKILL.md`    | Python source code style review (ruff, mypy, naming, docstrings, type annotations) — adapted from [wshobson/agents](https://github.com/wshobson/agents) (MIT)           |
| `python-testing-style` | `skills/zolletta-metaskill-python-testing-style/SUBSKILL.md` | Python test code review (isolation, naming, coverage gaps, mocking, fixtures, AAA structure) — adapted from [wshobson/agents](https://github.com/wshobson/agents) (MIT) |
| `php-code-style`       | `skills/zolletta-metaskill-php-code-style/SUBSKILL.md`       | PHP source code style review (PSR-12, naming, one class per file, PHPDoc, type declarations)                                                                            |
| `php-testing-style`    | `skills/zolletta-metaskill-php-testing-style/SUBSKILL.md`    | PHP test code review (PHPUnit naming, mirroring, coverage gaps, mocking, data providers)                                                                                |

## Procedure

1. Print the subcommand table above verbatim.
2. Print a one-line usage reminder:

   ```
   Usage: /zolletta-metaskill <subcommand>
   ```

That's it — no setup guard, no settings.json check, no tool execution.
This subcommand is purely informational and always available.
