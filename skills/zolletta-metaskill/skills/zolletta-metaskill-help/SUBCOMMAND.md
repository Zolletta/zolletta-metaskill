---
name: zolletta-metaskill-help
description: >
  Renders the help table listing every zolletta-metaskill subcommand with its path and scope. Use when the user runs /zolletta-metaskill with no argument or asks for help. Do not use to execute a subcommand.
license: MIT + Commons Clause
---

# Zolletta-metaskill Help

Displays the subcommand help table so the user can see what's available.

## Subcommand table

This is the **single source of truth** for the subcommand list. The root `SKILL.md` and `docs/reference/subcommands.md` both reference this table.

| Subcommand             | Path                                                           | Scope                                                                                                                                                                                                     |
|------------------------|----------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `help`                 | `skills/zolletta-metaskill-help/SUBCOMMAND.md`                 | Display the subcommand help table (also shown when no subcommand is given)                                                                                                                                |
| `version`              | `skills/zolletta-metaskill-version/SUBCOMMAND.md`              | Print the installed skill version (from `pyproject.toml` at the skill root) and the project's `setup_version` when `settings.json` exists                                                                 |
| `setup`                | `skills/zolletta-metaskill-setup/SUBCOMMAND.md`                | Project initialization — creates `.zolletta-metaskill/settings.json`, detects language, Docker container, tokensave, and Python/PHP tooling                                                               |
| `documentor`           | `skills/zolletta-metaskill-documentor/SUBCOMMAND.md`           | [Diátaxis](https://diataxis.fr/) compliance + drift detection for project docs                                                                                                                            |
| `grice`                | `skills/zolletta-metaskill-grice/SUBCOMMAND.md`                | Grice's four maxims (Quantity, Quality, Relation, Manner) scored over the documentation corpus as relative indices, plus link/heading defects — opt-in via `documentation.check_grice` in `settings.json` |
| `patterns`             | `skills/zolletta-metaskill-patterns/SUBCOMMAND.md`             | God classes, SOLID, coupling, composition vs inheritance for `src/`                                                                                                                                       |
| `review`               | `skills/zolletta-metaskill-review/SUBCOMMAND.md`               | Orchestrator — reads language from `settings.json`, runs general + language-specific skills in parallel batches, aggregates reports                                                                       |
| `adr-distiller`        | `skills/zolletta-metaskill-adr-distiller/SUBCOMMAND.md`        | Distill Accepted ADRs into `adr-distilled.md` architectural directives (mtime-cached, called by `review` at Step 3.5)                                                                                     |
| `python-code-style`    | `skills/zolletta-metaskill-python-code-style/SUBCOMMAND.md`    | Python source code style review (ruff, mypy, naming, docstrings, type annotations) — adapted from [wshobson/agents](https://github.com/wshobson/agents) (MIT)                                             |
| `python-testing-style` | `skills/zolletta-metaskill-python-testing-style/SUBCOMMAND.md` | Python test code review (isolation, naming, coverage gaps, mocking, fixtures, AAA structure) — adapted from [wshobson/agents](https://github.com/wshobson/agents) (MIT)                                   |
| `php-code-style`       | `skills/zolletta-metaskill-php-code-style/SUBCOMMAND.md`       | PHP source code style review (PSR-12, naming, one class per file, PHPDoc, type declarations)                                                                                                              |
| `php-testing-style`    | `skills/zolletta-metaskill-php-testing-style/SUBCOMMAND.md`    | PHP test code review (PHPUnit naming, mirroring, coverage gaps, mocking, data providers)                                                                                                                  |

## Procedure

1. Verify each listed subcommand exists: check that every `skills/zolletta-metaskill-<name>/SUBCOMMAND.md` path in the table resolves to a real file, and fix the table until it matches the actual `skills/` directory.
2. Print the subcommand table above verbatim.
3. Print a one-line usage reminder:

```text
   Usage: /zolletta-metaskill <subcommand>
   ```

That's it — no setup guard, no settings.json check, no tool execution.
This subcommand is purely informational and always available.

## Anti-patterns

- Never invent or rename subcommands — the table above is the single source of truth.
- Do not add rows for subcommands that have no `SUBCOMMAND.md` on disk.
- Do not execute a subcommand from this skill — display only.
