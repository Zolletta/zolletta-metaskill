---
audience: human, ai
status: stable
skills: [help, version, setup, review, patterns, documentor, grice, adr-distiller, python-*, php-*]
---

# Subcommands Reference

Zolletta-MetaSkill is invoked as `/zolletta-metaskill <subcommand>`. Each subcommand has its own `SUBSKILL.md` with detailed instructions.

## Subcommand table

The canonical subcommand table is owned by the `help` skill — see [`skills/zolletta-metaskill/skills/zolletta-metaskill-help/SUBSKILL.md`](../../skills/zolletta-metaskill/skills/zolletta-metaskill-help/SUBSKILL.md) for the full list. The table is displayed when the user runs `/zolletta-metaskill` with no argument or `/zolletta-metaskill help`.

## Setup guard

Before dispatching to **any** subcommand (including `setup` itself), the meta-skill checks if `.zolletta-metaskill/settings.json` exists in the current project root:

1. If it **exists**, read it and proceed to the requested subcommand.
2. If it **does not exist**, run the full `setup` procedure first. Once `settings.json` is written, proceed to the requested subcommand.
3. If the user invoked `/zolletta-metaskill setup` explicitly, run setup and stop — do not dispatch to another subcommand.
4. **Staleness check (Python projects only)**: if `settings.json` exists and `python` is not `null`, compare `pyproject.toml`'s current modification time against `python.pyproject_mtime`. If they differ, re-run **only** Steps 7–8 of setup (pyproject extraction + source layout detection) and patch the `python.tools.*` configuration fields + `python.paths` + `python.pyproject_mtime` in `settings.json` — not the full setup.
5. **Staleness check (PHP projects only)**: if `settings.json` exists and `php` is not `null`, compare `composer.json`'s current modification time against `php.composer_mtime`. If they differ, re-run **only** Step 12 of setup (composer.json + tool config extraction) and patch the `php.tools.*` configuration fields + `php.autoload` + `php.php_version` + `php.composer_mtime` in `settings.json` — not the full setup.

## Running tools

Tools run inside the Docker container if `container_name` is set, otherwise on the host. Prefer `uv run <command>` when `python.tools.uv.available` is `true`. See [settings-schema.md](settings-schema.md) for these fields.

## Tool-failure handler

When any subcommand cannot query tokensave — `tokensave tool <name>` fails (binary not on `PATH`, non-zero exit, or the `tool` subcommand does not exist on binaries older than 7.14) and the `tokensave_*` MCP tools are not exposed by the harness or also fail:

1. **Update `settings.json`**: set `tokensave_available: false`.
2. **Print the "not installed" message**: read the tokensave message from [tool-messages.md](tool-messages.md) and print it.
3. **Continue with fallback**: proceed using grep + targeted reads instead of the graph tool. Do not abort the subcommand.

This handler applies to every subcommand that uses tokensave (`patterns`, `documentor`, `review`).

## Dispatch

When invoked as `/zolletta-metaskill <subcommand>`:

1. If no subcommand is given, or the subcommand is `help`, read `skills/zolletta-metaskill/skills/zolletta-metaskill-help/SUBSKILL.md` and execute its instructions (display the help table). If the subcommand is `version`, read `skills/zolletta-metaskill/skills/zolletta-metaskill-version/SUBSKILL.md` and execute its instructions (print the installed version). Both are purely informational — stop, do not run the setup guard or any other subcommand.
2. Run the **setup guard** — ensure `.zolletta-metaskill/settings.json` exists.
3. Read `skills/zolletta-metaskill/skills/zolletta-metaskill-<subcommand>/SUBSKILL.md` and execute its instructions.
