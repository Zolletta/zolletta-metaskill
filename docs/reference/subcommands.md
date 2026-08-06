---
audience: human, ai
status: stable
skills: [help, setup, review, patterns, documentor, external-review, adr-distiller, python-*, php-*]
---

# Subcommands Reference

Zolletta-MetaSkill is invoked as `/zolletta-metaskill <subcommand>`. Each subcommand has its own `SKILL.md` with detailed instructions.

## Subcommand table

The canonical subcommand table is owned by the `help` skill — see [`skills/help/SKILL.md`](../../skills/help/SKILL.md) for the full list.
The table is displayed when the user runs `/zolletta-metaskill` with no argument or `/zolletta-metaskill help`.

## Setup guard

Before dispatching to **any** subcommand (including `setup` itself), the meta-skill checks if `.zolletta-metaskill/settings.json` exists in the current project root:

1. If it **exists**, read it and proceed to the requested subcommand.
2. If it **does not exist**, run the full `setup` procedure first. Once `settings.json` is written, proceed to the requested subcommand.
3. If the user invoked `/zolletta-metaskill setup` explicitly, run setup and stop — do not dispatch to another subcommand.
4. **Staleness check (Python projects only)**: if `settings.json` exists and `python` is not `null`, compare `pyproject.toml`'s current modification time against `python.pyproject_mtime`. If they differ, re-run only the pyproject extraction step and patch the `python.tools.*` configuration fields + `python.pyproject_mtime` in `settings.json`.

## Running tools

Tools run inside the Docker container if `container_name` is set, otherwise on the host. Prefer `uv run <command>` when `python.tools.uv.available` is `true`. See [settings-schema.md](settings-schema.md) for these fields.

## Tool-failure handler

When any subcommand calls a tokensave MCP tool and receives a **tool-not-found** or **server-not-found** error:

1. **Update `settings.json`**: set `tokensave_available: false`.
2. **Print the "not installed" message**: read the tokensave message from [tool-messages.md](tool-messages.md) and print it.
3. **Continue with fallback**: proceed using grep + targeted reads instead of the graph tool. Do not abort the subcommand.

This handler applies to every subcommand that uses tokensave (`patterns`, `documentor`, `external-review`, `review`).

## Dispatch

When invoked as `/zolletta-metaskill <subcommand>`:

1. If no subcommand is given, or the subcommand is `help`, read `skills/help/SKILL.md` and execute its instructions (display the help table). Stop — do not run the setup guard or any other subcommand.
2. Run the **setup guard** — ensure `.zolletta-metaskill/settings.json` exists.
3. Read the SKILL.md at `<subcommand>/SKILL.md` and execute its instructions.
