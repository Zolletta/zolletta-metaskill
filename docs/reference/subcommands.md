---
audience: human, ai
status: stable
skills: [setup, review, patterns, documentor, external-review, python-code-style, python-testing-patterns]
---

# Subcommands Reference

Zolletta-MetaSkill is invoked as `/zolletta-metaskill <subcommand>`. Each subcommand has its own `SKILL.md` with detailed instructions.

## Subcommand table

| Subcommand | Path | Scope |
|------------|------|-------|
| `setup` | `setup/SKILL.md` | Project initialization — creates `.zolletta-metaskill/settings.json`, detects language, Docker container, tokensave, and Python tooling |
| `documentor` | `documentor/SKILL.md` | [Diátaxis](https://diataxis.fr/) compliance + drift detection for the configured documentation directory (default: `docs/`) |
| `patterns` | `patterns/SKILL.md` | God classes, SOLID, coupling, composition vs inheritance for `src/` |
| `external-review` | `external-review/SKILL.md` | External-LLM code review on modified files only (default model: `swe`, override via `external_review_model` in `settings.json` or front-matter) |
| `review` | `review/SKILL.md` | Orchestrator — reads language from `settings.json`, runs general + language-specific skills in parallel batches, aggregates reports |
| `python-code-style` | `python-code-style/SKILL.md` | Python source code style review (ruff, mypy, naming, docstrings, type annotations) — adapted from [wshobson/agents](https://github.com/wshobson/agents) (MIT) |
| `python-testing-patterns` | `python-testing-patterns/SKILL.md` | Python test code review (isolation, naming, coverage gaps, mocking, fixtures, AAA structure) — adapted from [wshobson/agents](https://github.com/wshobson/agents) (MIT) |

## Setup guard

Before dispatching to **any** subcommand (including `setup` itself), the meta-skill checks if `.zolletta-metaskill/settings.json` exists in the current project root:

1. If it **exists**, read it and proceed to the requested subcommand.
2. If it **does not exist**, run the full `setup` procedure first. Once `settings.json` is written, proceed to the requested subcommand.
3. If the user invoked `/zolletta-metaskill setup` explicitly, run setup and stop — do not dispatch to another subcommand.
4. **Staleness check (Python projects only)**: if `settings.json` exists and `python_config` is not `null`, compare `pyproject.toml`'s current modification time against `python_config.pyproject_mtime`. If they differ, re-run only the pyproject extraction step and patch `python_config` + `pyproject_mtime` in `settings.json`.

## Running tools

This convention applies to **every** subcommand that invokes external tools (ruff, mypy, ty, pytest, vulture, etc.):

- If `container_name` is set in `settings.json` (not `null`), run tools inside the container via `docker compose exec <container_name> <command>`.
- If `container_name` is `null`, run tools directly on the host.
- If `python.uv` is `true`, prefer `uv run <command>` to ensure the project environment is used.

Subcommands do not restate this convention — they follow it.

## Tool-failure handler

When any subcommand calls a tokensave MCP tool and receives a **tool-not-found** or **server-not-found** error:

1. **Update `settings.json`**: set `tokensave_available: false`.
2. **Print the "not installed" message**: read the tokensave message from [tool-messages.md](tool-messages.md) and print it.
3. **Continue with fallback**: proceed using grep + targeted reads instead of the graph tool. Do not abort the subcommand.

This handler applies to every subcommand that uses tokensave (`patterns`, `documentor`, `external-review`, `review`).

## Dispatch

When invoked as `/zolletta-metaskill <subcommand>`:

1. Run the **setup guard** — ensure `.zolletta-metaskill/settings.json` exists.
2. Read the SKILL.md at `<subcommand>/SKILL.md` and execute its instructions.
3. If no subcommand is given, list the available subcommands from the table above.
