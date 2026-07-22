---
audience: human, ai
status: stable
skills: [setup]
---

# Set up a project

> **Paths in this document are relative to the Zolletta-MetaSkill project root.**

Initialize a project for use with zolletta-metaskill review skills. Setup creates the `.zolletta-metaskill/` directory and writes `settings.json` with the project's language, tool availability, and configuration. Every other subcommand reads from this file.

## Prerequisites

- The zolletta-metaskill skill installed and available to the agent
- A project directory with source code to review

## Steps

### Step 1 — Run setup

```
/zolletta-metaskill setup
```

The setup procedure runs automatically when any subcommand is invoked and `settings.json` is missing. We can also run it explicitly.

### Step 2 — What setup detects

Setup detects and records the following:

| Detection | What it finds | Stored as |
| --- | --- | --- |
| **Project language** | Python, TypeScript, PHP, Go, Rust, Java, Ruby, C/C++ | `language` |
| **Docker container** | Service name from `compose.yml` / `docker-compose.yml` | `container_name` |
| **tokensave** | Whether the tokensave MCP server is available | `tokensave_available` |
| **Acronyms** | Project-specific acronyms extracted from `AGENTS.md` | `acronyms` |
| **Python tooling** | ruff, pytest, ty, vulture, mypy, uv availability | `python.tools` object |
| **Python config** | Line length, target version, ruff/mypy/ty/pytest config from `pyproject.toml` | `python.*` fields |
| **Python code-style rules** | Configurable rule toggles for `python-code-style` | `python.code_style` object |
| **Python testing rules** | Configurable rule toggles for `python-testing-patterns` | `python.testing` object |
| **Documentation directory** | `.backstage/` if exists, else `docs/` if exists, else default `docs/` | `documentation.directory` |

### Step 3 — settings.json

Setup writes `.zolletta-metaskill/settings.json` with all detected values. The file is added to `.gitignore` so it is not committed. The setup guard checks this file before every subcommand invocation and re-runs the pyproject extraction step if `pyproject.toml` has been modified since the last setup.

### Step 4 — Verify

After setup, verify the configuration:

```bash
cat .zolletta-metaskill/settings.json
```

Check that:

- `language` matches the project's primary language
- `container_name` is correct (or `null` if no container)
- `tokensave_available` is `true` if tokensave is installed
- `acronyms` lists any project-specific acronyms extracted from `AGENTS.md`
- `python.tools` has the correct tool availability flags (Python projects)
- `python.*` has the correct configuration extracted from `pyproject.toml` (Python projects)

## Re-running setup

Setup is idempotent. Re-running it preserves existing user-customized values in `settings.json` and only adds keys that are new. The setup guard automatically re-runs the pyproject extraction step (Step 6.5) when `pyproject.toml` changes, without re-running full setup.

## See also

- [Install Zolletta-MetaSkill](install.md) — install the skill before setting up a project
- [Getting started](../tutorials/getting-started.md) — end-to-end walkthrough
- [Settings schema](../reference/settings-schema.md) — all configuration options
- [Run a full review](run-full-review.md) — what to do after setup
