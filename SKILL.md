---
name: zolletta
description: 'Zolletta — meta-skill and registry for the zolletta-* review family. Lists available skills, shared resources, and orchestration rules.'
argument-hint: "[subcommand]"
---

# Zolletta — Skill Registry

A family of code review skills for Python projects. Invoke with `/zolletta <subcommand>` to run a specific review, or `/zolletta` with no argument to see available subcommands.

All paths are relative to where this SKILL.md is found.

## Subcommands

| Subcommand | Path | Scope |
|------------|------|-------|
| `documentor` | `documentor/SKILL.md` | Diátaxis compliance + drift detection for `.backstage/` |
| `patterns` | `patterns/SKILL.md` | God classes, SOLID, coupling, composition vs inheritance for `src/` |
| `external-review` | `external-review/SKILL.md` | Code review following Pepita project conventions |
| `review` | `review/SKILL.md` | Orchestrator — runs all skills in parallel batches, aggregates reports |

## Shared resources

All subcommands read from this skill's subdirectories:

| Resource | Path | Contents |
|----------|------|----------|
| References | `reference/` | Shared guidelines (Diátaxis, review workflow, grading rubric) |
| Scripts | `scripts/python/` | Automated scanning scripts used by multiple skills |

## Rules

All files in `~/.agents/rules/` are the **single source of truth** for their domain and apply to every subcommand. Sub-skills link back to them and only **narrow** behavior for their specific review context — they never override or restate the rules.

## Dispatch

When invoked as `/zolletta <subcommand>`, read the SKILL.md at `<subcommand>/SKILL.md` and execute its instructions. If no subcommand is given, list the available subcommands from the table above.
