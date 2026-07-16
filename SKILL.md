---
name: zolletta
version: 1.0.0
license: MIT + Commons Clause
description: 'Zolletta-metaskill — meta-skill and registry for the zolletta-* review family. Lists available skills, shared resources, and orchestration rules.'
argument-hint: "[subcommand]"
---

# Zolletta — Skill Registry

A family of generic code review skills with specializations for

- Python
- Others (Work in progress)

Invoke with `/zolletta <subcommand>` to run a specific review, or `/zolletta` with no argument to see available subcommands.

All paths are relative to where this SKILL.md is found.

## Tools leveraged if available

- [tokensave](https://github.com/aovestdipaperino/tokensave) — semantic code-graph MCP tools for exploration and impact analysis

## Subcommands

| Subcommand | Path | Scope |
|------------|------|-------|
| `setup` | `setup/SKILL.md` | Project initialization — creates `.zolletta-metaskill/settings.json`, detects language, tests tokensave availability |
| `documentor` | `documentor/SKILL.md` | Diátaxis compliance + drift detection for `.backstage/` |
| `patterns` | `patterns/SKILL.md` | God classes, SOLID, coupling, composition vs inheritance for `src/` |
| `external-review` | `external-review/SKILL.md` | External-LLM code review on modified files only (default model: `swe`, override via front-matter, `ZOLLETTA_EXTERNAL_REVIEW_MODEL` env var, or `settings.json`) |
| `review` | `review/SKILL.md` | Orchestrator — reads language from `settings.json`, runs general + language-specific skills in parallel batches, aggregates reports |
| `python-code-style` | `python-code-style/SKILL.md` | Python source code style review (ruff, mypy, naming, docstrings, type annotations) — adapted from [wshobson/agents](https://github.com/wshobson/agents) (MIT) |
| `python-testing-patterns` | `python-testing-patterns/SKILL.md` | Python test code review (isolation, naming, coverage gaps, mocking, fixtures, AAA structure) — adapted from [wshobson/agents](https://github.com/wshobson/agents) (MIT) |

## Shared resources

All subcommands read from this skill's subdirectories:

| Resource | Path | Contents |
|----------|------|----------|
| References | `reference/` | Shared guidelines (Diátaxis, review workflow, grading rubric, tool messages) |
| Scripts | `scripts/python/` | Automated scanning scripts used by multiple skills |
| Settings | `.zolletta-metaskill/settings.json` | Project-wide configuration written by `setup` (language, tool availability, external-review model, reports dir) |

## Rules

All files in `~/.agents/rules/` are the **single source of truth** for their domain and apply to every subcommand. Sub-skills link back to them and only **narrow** behavior for their specific review context — they never override or restate the rules.

## Setup guard

Before dispatching to **any** subcommand (including `setup` itself), check if `.zolletta-metaskill/settings.json` exists in the current project root:

1. If it **exists**, read it and proceed to the requested subcommand. The subcommand may read `language`, `tokensave_available`, `python_code_style_available`, `python_testing_patterns_available`, `external_review_model`, and `reports_dir` from it.
2. If it **does not exist**, run the full `setup` procedure first (read `setup/SKILL.md` and execute every step). Once `settings.json` is written, proceed to the requested subcommand.
3. If the user invoked `/zolletta setup` explicitly, run setup and stop — do not dispatch to another subcommand.

This guarantees that every subcommand can rely on `settings.json` being present without each one reimplementing the detection logic.

## Tool-failure handler

When any subcommand calls a tokensave MCP tool and receives a **tool-not-found** or **server-not-found** error (the MCP server is not registered or not responding):

1. **Update `settings.json`**: set `tokensave_available: false`.
   Use the `edit` tool to update `.zolletta-metaskill/settings.json` in place.
2. **Print the "not installed" message**: read the tokensave message from [`reference/tool-messages.md`](reference/tool-messages.md) and print it. The message explains why zolletta benefits from the tool and links to the project homepage. **Do NOT install anything.**
3. **Continue with fallback**: proceed using grep + targeted reads instead of the graph tool. Do not abort the subcommand — the review can still complete, just with reduced coverage.

This handler applies to every subcommand that uses tokensave (`patterns`, `documentor`, `external-review`, `review`). Each subcommand's SKILL.md links back to this section.

> **Python skills**: `python-code-style` and `python-testing-patterns` are bundled inside this meta-skill, so they are always available — the "not found" case does not apply. The `*_available` flags in `settings.json` only reflect whether the project language is Python.

## Dispatch

When invoked as `/zolletta <subcommand>`:

1. Run the **setup guard** (see above) — ensure `.zolletta-metaskill/settings.json` exists.
2. Read the SKILL.md at `<subcommand>/SKILL.md` and execute its instructions.
3. If no subcommand is given, list the available subcommands from the table above.
