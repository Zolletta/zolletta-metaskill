---
name: zolletta-metaskill
license: MIT + Commons Clause
description: 'Zolletta-metaskill — meta-skill and registry for the zolletta-* review family. Lists available skills, shared resources, and orchestration rules.'
argument-hint: "[subcommand]"
---

# Zolletta-metaskill — Skill Registry

A family of generic code review skills with specializations for

- Python
- Others (Work in progress)

Invoke with `/zolletta-metaskill <subcommand>` to run a specific review, `/zolletta-metaskill help` to list available subcommands, or `/zolletta-metaskill` with no argument to see the help table.

All paths are relative to where this SKILL.md is found.

## Tools leveraged if available

- [tokensave](https://github.com/aovestdipaperino/tokensave) — semantic code-graph MCP tools for exploration and impact analysis

## Subcommands

The subcommand table is owned by the `help` skill — see [`skills/help/SKILL.md`](skills/help/SKILL.md) for the canonical list.
When no subcommand is given, or the subcommand is `help`, the help table is displayed (see [Dispatch](#dispatch) below).

## Shared resources

All subcommands read from this skill's subdirectories:

| Resource   | Path                                | Contents                                                                                                        |
| ---------- | ----------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| References | `docs/`                             | Shared guidelines (Diátaxis, review workflow, grading rubric, tool messages)                                    |
| Scripts    | `src/zolletta_metaskill/`           | Scanning scripts organized by skill (patterns/, code_style/, testing_style/, documentor/, adr/, core/, setup/)  |
| Settings   | `.zolletta-metaskill/settings.json` | Project-wide configuration written by `setup` (language, tool availability, external-review model, reports dir) |

## Rules

If you maintain rules as part of your agent configuration, those are the **single source of truth** for their domain and apply to every subcommand. Sub-skills link back to them and only **narrow** behavior for their specific review context — they never override or restate the rules.

## Setup guard

Before dispatching to **any** subcommand (including `setup` itself), check if `.zolletta-metaskill/settings.json` exists in the current project root:

1. If it **exists**, read it and proceed to the requested subcommand. The subcommand may read `language`, `container_name`, `tokensave_available`, `acronyms`, `python` (which merges `python.tools`, `python.code_style`, `python.testing`, and `python.pyproject_mtime`), `php` (which merges `php.tools`, `php.code_style`, `php.testing`, `php.autoload`, `php.php_version`, and `php.composer_mtime`), `external_review_model`, and `reports_dir` from it.
2. If it **does not exist**, run the full `setup` procedure first (read `skills/setup/SKILL.md` and execute every step). Once `settings.json` is written, proceed to the requested subcommand.
3. If the user invoked `/zolletta-metaskill setup` explicitly, run setup and stop — do not dispatch to another subcommand.
4. **Staleness check (Python projects only)**: if `settings.json` exists and `python` is not `null`, compare `pyproject.toml`'s current modification time against `python.pyproject_mtime`. If they differ (the file was modified after the last setup), re-run **only** Step 6.5 of setup (pyproject extraction) and patch the `python.tools.*` configuration fields + `python.pyproject_mtime` in `settings.json`. Do not re-run full setup (language detection, Docker probe, tokensave probe). If `pyproject.toml` does not exist or `python` is `null`, skip this check.
5. **Staleness check (PHP projects only)**: if `settings.json` exists and `php` is not `null`, compare `composer.json`'s current modification time against `php.composer_mtime`. If they differ (the file was modified after the last setup), re-run **only** Step 7.5 of setup (composer.json + tool config extraction) and patch the `php.tools.*` configuration fields + `php.autoload` + `php.php_version` + `php.composer_mtime` in `settings.json`. Do not re-run full setup (language detection, Docker probe, tokensave probe). If `composer.json` does not exist or `php` is `null`, skip this check.

This guarantees that every subcommand can rely on `settings.json` being present and up-to-date without each one reimplementing the detection logic.

## Running tools

This convention applies to **every** subcommand that invokes external tools (ruff, mypy, ty, pytest, vulture, etc.):

- If `container_name` is set in `settings.json` (not `null`), run tools inside the container via `docker compose exec <container_name> <command>`.
- If `container_name` is `null`, run tools directly on the host.
- If `python.tools.uv.available` is `true`, prefer `uv run <command>` to ensure the project environment is used.

Subcommands do not restate this convention — they follow it.

## Tool-failure handler

When any subcommand calls a tokensave MCP tool and receives a **tool-not-found** or **server-not-found** error (the MCP server is not registered or not responding):

1. **Update `settings.json`**: set `tokensave_available: false`.
   Use the `edit` tool to update `.zolletta-metaskill/settings.json` in place.
2. **Print the "not installed" message**: read the tokensave message from [`docs/reference/tool-messages.md`](docs/reference/tool-messages.md) and print it. The message explains why Zolletta-metaskill benefits from the tool and links to the project homepage. **Do NOT install anything.**
3. **Continue with fallback**: proceed using grep + targeted reads instead of the graph tool. Do not abort the subcommand — the review can still complete, just with reduced coverage.

This handler applies to every subcommand that uses tokensave (`patterns`, `documentor`, `external-review`, `review`). Each subcommand's SKILL.md links back to this section.

> **Bundled language skills**: `python-code-style`, `python-testing-style`, `php-code-style`, and `php-testing-style` are bundled inside this meta-skill, so they are always available — the "not found" case does not apply. The `*_available` flags in `settings.json` only reflect whether the project language is Python or PHP.

## Dispatch

When invoked as `/zolletta-metaskill <subcommand>`:

1. If no subcommand is given, or the subcommand is `help`, read `skills/help/SKILL.md` and execute its instructions (display the help table). Stop — do not run the setup guard or any other subcommand.
2. Run the **setup guard** (see above) — ensure `.zolletta-metaskill/settings.json` exists.
3. Read the SKILL.md at `skills/<subcommand>/SKILL.md` and execute its instructions.
