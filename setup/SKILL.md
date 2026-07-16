---
name: zolletta-setup
version: 1.0.0
license: MIT + Commons Clause
description: >
  Project initialization for zolletta. Creates the .zolletta-metaskill/ directory, detects the project language, tests tokensave and graphify availability, and writes settings.json. Also adds .zolletta-metaskill/ to .gitignore. Run automatically by the setup guard before any subcommand if settings.json is missing, or manually via /zolletta setup.
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

- `../reference/tool-messages.md` — "not installed" messages for tokensave, graphify, and Python skills

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

### Step 5 — Test graphify availability

1. Try calling `mcp_list_tools` with `server_name: "graphify"`.
   - If the call succeeds (returns a tool list) → `graphify_available: true`
   - If the call fails with server-not-found → proceed to step 2
2. Check for a `graphify-out/` directory in the project root (a previously built graph). If present → `graphify_available: true` (the graph exists and can be queried via the `graphify` skill even without the MCP server).
3. If neither condition is met → `graphify_available: false`

### Step 6 — Test Python skill availability (Python projects only)

If the detected language from Step 3 is **Python**, probe for the two language-specific skills that `review` launches as subagents:

1. Try `skill invoke python-code-style`.
   - If the invoke succeeds (the skill loads) → `python_code_style_available: true`
   - If the invoke fails with "Skill not found" → `python_code_style_available: false`
2. Try `skill invoke python-testing-patterns`.
   - If the invoke succeeds → `python_testing_patterns_available: true`
   - If the invoke fails with "Skill not found" → `python_testing_patterns_available: false`

If the language is **not Python**, set both flags to `false` and skip the probes entirely.

> **Unified approach**: all three steps (tokensave, graphify, Python skills) use the same detection pattern — try the actual tool, catch the not-found error, set the flag. This mirrors the [tool-failure handler](../SKILL.md#tool-failure-handler) at runtime: the same error that triggers the handler during a review is the one we probe for during setup.

### Step 7 — Write settings.json

Read the [settings template](assets/settings_template.json) and write `.zolletta-metaskill/settings.json` with the following fields filled in:

| Field                            | Source                                          |
| -------------------------------- | ----------------------------------------------- |
| `setup_version`                  | `"1.0.0"` (matches the skill version)           |
| `setup_timestamp`                | Current timestamp in ISO 8601 (`date -u +%Y-%m-%dT%H:%M:%S`) |
| `language`                       | Detected language from Step 3                   |
| `tokensave_available`            | Boolean from Step 4                             |
| `graphify_available`             | Boolean from Step 5                             |
| `python_code_style_available`    | Boolean from Step 6 (Python only; `false` otherwise) |
| `python_testing_patterns_available` | Boolean from Step 6 (Python only; `false` otherwise) |
| `external_review_model`          | `"swe"` (default; overridable by env var or settings) |
| `reports_dir`                    | `".zolletta-metaskill/reports"`                 |

Use the `write` tool to create the file. The JSON must be valid and pretty-printed (2-space indent).

### Step 8 — Print "not installed" messages

For each tool or skill that is **not** available, print the corresponding message from `../reference/tool-messages.md`. The message explains why zolletta benefits from the tool/skill and links to the project homepage (where applicable).

This covers:
- `tokensave_available: false` → tokensave message
- `graphify_available: false` → graphify message
- `python_code_style_available: false` (Python only) → python-code-style message
- `python_testing_patterns_available: false` (Python only) → python-testing-patterns message

**Do NOT install anything.** Only inform the user.

### Step 9 — Summary

Print a brief summary to the user:

```text
Zolletta setup complete.

  Language:                        <language>
  tokensave available:             <yes/no>
  graphify available:              <yes/no>
  python-code-style available:     <yes/no>  (Python only)
  python-testing-patterns available: <yes/no>  (Python only)
  Settings file:                   .zolletta-metaskill/settings.json
  Reports directory:               .zolletta-metaskill/reports/
```

If any tools or skills were unavailable, the "not installed" messages from Step 8 will have already been printed above this summary.

## Re-running setup

`/zolletta setup` can be run at any time to re-detect tools and refresh `settings.json`. The previous `settings.json` is overwritten. This is useful after installing tokensave or graphify, or after a project language change.
