---
name: zolletta
version: 1.0.0
license: MIT + Commons Clause
description: 'Zolletta — meta-skill and registry for the zolletta-* review family. Lists available skills, shared resources, and orchestration rules.'
argument-hint: "[subcommand]"
---

# Zolletta — Skill Registry

A family of generic code review skills with specializations for

- Python
- Others (Work in progress)

Invoke with `/zolletta <subcommand>` to run a specific review, or `/zolletta` with no argument to see available subcommands.

All paths are relative to where this SKILL.md is found.

## Skills leveraged if available

- [tokensave](https://github.com/aovestdipaperino/tokensave) — semantic code-graph MCP tools for exploration and impact analysis
- [gitnexus](https://github.com/abhigyanpatwari/GitNexus) — code intelligence MCP tools for impact analysis and execution-flow tracing
- [graphify](https://github.com/safishamsi/graphify) — knowledge-graph MCP tools for architecture and file-relationship queries

## Subcommands

| Subcommand | Path | Scope |
|------------|------|-------|
| `documentor` | `documentor/SKILL.md` | Diátaxis compliance + drift detection for `.backstage/` |
| `patterns` | `patterns/SKILL.md` | God classes, SOLID, coupling, composition vs inheritance for `src/` |
| `external-review` | `external-review/SKILL.md` | External-LLM code review on modified files only (default model: `swe`, override via front-matter or `ZOLLETTA_EXTERNAL_REVIEW_MODEL`) |
| `review` | `review/SKILL.md` | Orchestrator — detects language, runs general + language-specific skills in parallel batches, aggregates reports |

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
