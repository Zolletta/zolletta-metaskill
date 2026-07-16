---
name: zolletta-setup
version: 1.0.0
license: MIT + Commons Clause
description: >
  Project initialization for zolletta. Creates the .zolletta-metaskill/ directory, detects the project language, tests tokensave availability, and writes settings.json. Also adds .zolletta-metaskill/ to .gitignore. Run automatically by the setup guard before any subcommand if settings.json is missing, or manually via /zolletta setup.
allowed-tools:
  - read
  - grep
  - glob
  - exec
  - edit
  - write
  - mcp_call_tool
  - mcp_list_tools
  - skill
permissions:
  allow:
    - Write(.zolletta-metaskill/**)
    - Write(.gitignore)
    - mcp__tokensave__tokensave_status
---

# Zolletta Setup

Initialize the `.zolletta-metaskill/` directory and write `settings.json` so that every other subcommand can read project-wide configuration from a single location.

## Shared resources

Read shared guidelines from the meta-skill (parent directory):

- `../reference/tool-messages.md` — "not installed" messages for tokensave and Python skills

## Procedure

### Step 1 — Create the .zolletta-metaskill directory

```bash
mkdir -p .zolletta-metaskill
```

### Step 2 — Add .zolletta-metaskill/ to .gitignore

1. Check if `.gitignore` exists in the project root. If it does not, create it.
2. Read `.gitignore` and check if `.zolletta-metaskill/` is already listed. If not, append it with a leading comment on its own line:

   ```gitignore
   # Zolletta review artifacts
   .zolletta-metaskill/
   ```

   Do not duplicate the entry if it's already there. Do not modify an existing `.gitignore` beyond appending this entry.

### Step 3 — Detect the project language

Determine the project's primary language by checking for language markers in the project root (the current working directory):

| Marker(s)                                                        | Language             |
| ---------------------------------------------------------------- | -------------------- |
| `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements*.txt`, `Pipfile`, `uv.lock` | Python           |
| `package.json`, `tsconfig.json`, `deno.json`                     | TypeScript/JavaScript|
| `composer.json`                                                  | PHP                  |
| `go.mod`                                                         | Go                   |
| `Cargo.toml`                                                     | Rust                 |
| `pom.xml`, `build.gradle`                                        | Java/Kotlin          |
| `Gemfile`, `*.gemspec`                                           | Ruby                 |
| `CMakeLists.txt`, `Makefile` with `.c`/`.cpp` sources            | C/C++               |

1. If no marker is found, inspect the source directory for the most common file extension.
2. If the language cannot be determined, ask the user with `ask_user_question`.
3. Store the detected language (lowercase) for writing to `settings.json`.

### Step 4 — Test tokensave availability

1. Try calling `tokensave_status` (no arguments) directly.
   - If the call succeeds → `tokensave_available: true`
   - If the call fails with tool-not-found / server-not-found → `tokensave_available: false`

### Step 5 — Set Python skill availability

The two Python review skills (`python-code-style`, `python-testing-patterns`) are bundled inside zolletta-metaskill, so they are always available — no probing needed.

- If the detected language from Step 3 is **Python** → set both `python_code_style_available: true` and `python_testing_patterns_available: true`
- If the language is **not Python** → set both flags to `false`

> **Note**: these skills are adapted from [wshobson/agents](https://github.com/wshobson/agents) (MIT License, Copyright (c) 2024 Seth Hobson) and live in `python-code-style/` and `python-testing-patterns/` within this meta-skill.

### Step 6 — Write settings.json

Read the [settings template](assets/settings_template.json) and write `.zolletta-metaskill/settings.json` with the following fields filled in:

| Field                            | Source                                          |
| -------------------------------- | ----------------------------------------------- |
| `setup_version`                  | `"1.0.0"` (matches the skill version)           |
| `setup_timestamp`                | Current timestamp in ISO 8601 (`date -u +%Y-%m-%dT%H:%M:%S`) |
| `language`                       | Detected language from Step 3                   |
| `tokensave_available`            | Boolean from Step 4                             |
| `python_code_style_available`    | Boolean from Step 5 (Python only; `false` otherwise) |
| `python_testing_patterns_available` | Boolean from Step 5 (Python only; `false` otherwise) |
| `external_review_model`          | `"swe"` (default; overridable by env var or settings) |
| `reports_dir`                    | `".zolletta-metaskill/reports"`                 |

Use the `write` tool to create the file. The JSON must be valid and pretty-printed (2-space indent).

### Step 7 — Print "not installed" messages

For each tool or skill that is **not** available, print the corresponding message from `../reference/tool-messages.md`. The message explains why zolletta benefits from the tool/skill and links to the project homepage (where applicable).

This covers:
- `tokensave_available: false` → tokensave message

(The Python skills are bundled inside this meta-skill, so no "not installed" message is needed for them — `python_code_style_available` and `python_testing_patterns_available` are `false` only when the project language is not Python.)

**Do NOT install anything.** Only inform the user.

### Step 8 — Summary

Print a brief summary to the user:

```text
Zolletta setup complete.

  Language:                        <language>
  tokensave available:             <yes/no>
  python-code-style available:     <yes/no>  (Python only)
  python-testing-patterns available: <yes/no>  (Python only)
  Settings file:                   .zolletta-metaskill/settings.json
  Reports directory:               .zolletta-metaskill/reports/
```

If any tools or skills were unavailable, the "not installed" messages from Step 8 will have already been printed above this summary.

## Re-running setup

`/zolletta setup` can be run at any time to re-detect tools and refresh `settings.json`. The previous `settings.json` is overwritten. This is useful after installing tokensave, or after a project language change.
