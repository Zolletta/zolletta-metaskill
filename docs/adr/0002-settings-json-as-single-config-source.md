# ADR-0002: settings.json as single configuration source

## Status

Accepted

## Context

Every review subcommand needs to know facts about the project: the primary language, which tools are installed (ruff, mypy, phpunit, etc.), rule toggles (e.g., `check_one_class_per_file`), the documentation directory, and the Docker container name for running tools.

Without a central configuration file, each subcommand would have to re-detect these facts on every invocation. This is slow (probing tool availability, parsing pyproject.toml/composer.json), inconsistent (different subcommands might detect differently), and fragile (detection logic duplicated across skills).

## Decision

Setup writes a single `.zolletta-metaskill/settings.json` file containing all project-wide configuration. Every other subcommand reads from this file instead of re-detecting.

The file includes:
- `language` — the detected project language
- `container_name` — Docker container for running tools (or `null`)
- `tokensave_available` — whether the semantic code-graph tool is present
- `python` / `php` — tool availability, effective configuration extracted from pyproject.toml/composer.json, and rule toggles
- `documentation` — language and directory path
- `reports_dir` — where review reports are saved

A JSON Schema (`settings.schema.json`) validates the shape. A prose reference (`docs/reference/settings-schema.md`) documents every field for humans.

## Consequences

**Positive:**
- Detection happens once (during setup) and is reused — subcommands start instantly with consistent config.
- The setup guard ensures `settings.json` exists before any subcommand runs, so subcommands can assume it is present.
- Staleness checks (comparing pyproject.toml/composer.json mtime against stored values) trigger a light refresh without full re-setup.
- The JSON Schema enables CI validation and IDE autocompletion.

**Negative:**
- `settings.json` can become stale if the project changes without re-running setup. The staleness checks mitigate this for Python and PHP, but other config drift is possible.
- Adding a new configuration field requires updating the schema, the template, the prose doc, and the setup skill — four files in sync.

**Neutral:**
- `settings.json` is a generated artifact, gitignored per-user. It is not committed to the repo.
