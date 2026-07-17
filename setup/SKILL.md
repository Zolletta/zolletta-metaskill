---
name: zolletta-metaskill-setup
version: 1.1.0
license: MIT + Commons Clause
description: >
  Project initialization for zolletta-metaskill. Creates the .zolletta-metaskill/ directory, detects the project language, detects Docker container, tests tokensave availability, detects Python tooling, and writes settings.json. Also adds .zolletta-metaskill/ to .gitignore. Run automatically by the setup guard before any subcommand if settings.json is missing, or manually via /zolletta-metaskill setup.
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

# Zolletta-metaskill Setup

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
   # Zolletta-metaskill review artifacts
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

### Step 4 — Detect Docker container

Search for a Docker Compose file in the project root:

1. Check for `docker-compose.yml` or `compose.yml` (also `.yaml` variants) in the project root.
2. If **no compose file is found** → `container_name: null` (commands run on the host). Skip to Step 5.
3. If a compose file is found, parse it to extract the service names (the keys under `services:`).
4. If **exactly one service** → use that service name as `container_name`.
5. If **more than one service** → ask the user with `ask_user_question` which container to use for running commands. Store the selected service name as `container_name`.

> The `container_name` is used by other subcommands (e.g. `python-code-style`) to run tools inside the container via `docker compose exec <container_name> <command>`. If `container_name` is `null`, tools are run directly on the host.

### Step 5 — Test tokensave availability

1. Try calling `tokensave_status` (no arguments) directly.
   - If the call succeeds → `tokensave_available: true`
   - If the call fails with tool-not-found / server-not-found → `tokensave_available: false`

### Step 6 — Detect Python tooling (Python projects only)

If the detected language from Step 3 is **not Python**, skip this step entirely and set `python: null`.

If the language is **Python**, detect which tools are available. For each tool, check in this order:

1. **Check `pyproject.toml`** — read the `[tool.*]` sections. If a tool has a configuration section (e.g. `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`, `[tool.vulture]`), mark it as `true` (the project uses it).
2. **If not found in `pyproject.toml`**, try calling the command — inside the container if `container_name` is set (`docker compose exec <container_name> <command> --version`), otherwise on the host (`<command> --version`). If the command succeeds, mark it as `true`.

The tools to detect:

| Tool | pyproject.toml section | Command |
| ---- | ---------------------- | ------- |
| `uv` | n/a (check `[project]` or `uv.lock` file) | `uv --version` |
| `ruff` | `[tool.ruff]` | `ruff --version` |
| `pytest` | `[tool.pytest.ini_options]` | `pytest --version` |
| `ty` | `[tool.ty]` | `ty --version` |
| `vulture` | `[tool.vulture]` | `vulture --version` |
| `mypy` | `[tool.mypy]` | `mypy --version` |

Store the results as a `python` subobject in `settings.json` (see Step 8).

> **Do NOT install any tool.** If a tool is not present, set it to `false` and print the corresponding "not installed" message in Step 9.

### Step 6.5 — Extract Python configuration from pyproject.toml

If the detected language from Step 3 is **not Python**, skip this step entirely and set `python_config: null`.

If the language is **Python**, read `pyproject.toml` and extract the effective configuration for each available tool. Record the file's modification time so the setup guard can detect staleness on future runs.

1. **Record `pyproject_mtime`** — use `os.path.getmtime("pyproject.toml")` (or equivalent). Store it as a float in `python_config.pyproject_mtime`.

2. **For each tool that is `true` in the `python` object** (from Step 6), extract its configuration:

   | Tool | If `[tool.*]` section exists | If section is absent |
   | ---- | ---------------------------- | -------------------- |
   | `ruff` | Extract `line-length`, `target-version`, `lint.select`, `lint.ignore` into `python_config.ruff` | Store ruff's built-in defaults: `line_length: 88`, `target_version: "py310"`, `select: ["E4","E7","E9","F"]`, `ignore: []`. Print the ruff "unconfigured" warning from `../reference/tool-messages.md`. |
   | `mypy` | Extract `python_version`, `strict`, `warn_return_any`, `warn_unused_ignores`, `disallow_untyped_defs`, `disallow_incomplete_defs` into `python_config.mypy` | Store mypy's built-in defaults: `strict: false`, `python_version: null` (uses running interpreter). Print the mypy "unconfigured" warning. |
   | `ty` | Extract `python-version` (or `environment.python-version`) into `python_config.ty` | Store ty's built-in defaults: `python_version: null` (detected from environment). Print the ty "unconfigured" warning. |
   | `pytest` | Extract `addopts`, `testpaths`, `minversion` into `python_config.pytest` | Store pytest's built-in defaults: `addopts: []`, `testpaths: []`, `minversion: null`. Print the pytest "unconfigured" warning. |

3. **Determine `type_checker`** — the tool the review skills should use for type checking:
   - If `[tool.ty]` is configured in `pyproject.toml` → `"ty"`
   - Else if `[tool.mypy]` is configured → `"mypy"`
   - Else if `ty` is available (from Step 6) → `"ty"`
   - Else if `mypy` is available → `"mypy"`
   - Else → `null` (type checking is skipped)

4. **Extract top-level values**:
   - `line_length`: from `[tool.ruff] line-length` if present, else ruff's default `88`.
   - `target_version`: from `[tool.ruff] target-version` if present, else ruff's default `"py310"`.

5. **Never modify `pyproject.toml`.** Setup only reads it. The "unconfigured" warnings are informational — the user decides whether to add a `[tool.*]` section.

6. **Write `python_code_style_rules`** — copy the default rule toggles from `settings_template.json`. If `settings.json` already exists (re-run of setup), **preserve existing user-customized values** and only add keys that are new (i.e. merge, don't overwrite).

   **Extract acronyms from AGENTS.md**: if the project's `AGENTS.md` contains an "Acronyms stay uppercase" naming convention line (matching the pattern `acronyms fully uppercase` followed by a parenthesised list of examples like `CITesterEngine`, `MRBranchResolver`), extract the uppercase tokens from those examples and store them as `python_code_style_rules.acronyms`. For the example above, the extracted list would be `["CI", "MR", "AST"]`. If no such line is found, leave `acronyms` as an empty list — the scanner will use its built-in defaults.

7. **Write `python_testing_patterns_rules`** — copy the default rule toggles from `settings_template.json`. Same merge behavior as `python_code_style_rules`: preserve existing user-customized values, only add new keys.

### Step 7 — Set Python skill availability

The two Python review skills (`python-code-style`, `python-testing-patterns`) are bundled inside zolletta-metaskill, so they are always available — no probing needed.

- If the detected language from Step 3 is **Python** → set both `python_code_style_available: true` and `python_testing_patterns_available: true`
- If the language is **not Python** → set both flags to `false`

> **Note**: these skills are adapted from [wshobson/agents](https://github.com/wshobson/agents) (MIT License, Copyright (c) 2024 Seth Hobson) and live in `python-code-style/` and `python-testing-patterns/` within this meta-skill.

### Step 8 — Write settings.json

Read the [settings template](assets/settings_template.json) and write `.zolletta-metaskill/settings.json` with the following fields filled in:

| Field                            | Source                                          |
| -------------------------------- | ----------------------------------------------- |
| `setup_version`                  | `"1.0.0"` (matches the skill version)           |
| `setup_timestamp`                | Current timestamp in ISO 8601 (`date -u +%Y-%m-%dT%H:%M:%S`) |
| `language`                       | Detected language from Step 3                   |
| `container_name`                 | Container name from Step 4 (`null` if no Docker) |
| `tokensave_available`            | Boolean from Step 5                             |
| `python`                         | Object from Step 6 (Python only; `null` otherwise) — see below |
| `python_config`                  | Object from Step 6.5 (Python only; `null` otherwise) — see below |
| `python_code_style_available`    | Boolean from Step 7 (Python only; `false` otherwise) |
| `python_testing_patterns_available` | Boolean from Step 7 (Python only; `false` otherwise) |
| `python_code_style_rules`        | Object from Step 6.5 (Python only; defaults from `settings_template.json`) — see below |
| `python_testing_patterns_rules`  | Object from Step 6.5 (Python only; defaults from `settings_template.json`) — see below |
| `external_review_model`          | `"swe"` (default; overridable by front-matter) |
| `documentation_language`         | `"en"` (default; ISO 639-1 code for documentation language) |
| `reports_dir`                    | `".zolletta-metaskill/reports"`                 |

The `python` subobject has this shape:

```json
{
  "uv": true,
  "ruff": true,
  "pytest": true,
  "ty": false,
  "vulture": false,
  "mypy": true
}
```

The `python_config` subobject has this shape (Python only; `null` otherwise):

```json
{
  "pyproject_mtime": 1718700000.0,
  "line_length": 100,
  "target_version": "py312",
  "type_checker": "ty",
  "ruff": { "select": ["E","W","F","I","B","UP","SIM"], "ignore": ["E501"] },
  "mypy": { "strict": true, "python_version": "3.12" },
  "ty": { "python_version": "3.12" },
  "pytest": { "addopts": ["-ra"], "testpaths": ["tests"], "minversion": "8.0" }
}
```

The `python_code_style_rules` subobject has this shape (Python only):

```json
{
  "check_acronym_casing": true,
  "check_no_relative_imports": true,
  "check_one_class_per_file": true,
  "check_filename_matches_class": true,
  "check_public_docstrings": true,
  "check_docstring_no_type_repeat": true,
  "check_skip_obvious_docstrings": true,
  "check_line_length": true,
  "vulture_min_confidence": 80
}
```

The `python_testing_patterns_rules` subobject has this shape (Python only):

```json
{
  "coverage_gap_threshold": 50,
  "coverage_well_covered_threshold": 80,
  "check_test_naming": true
}
```

Use the `write` tool to create the file. The JSON must be valid and pretty-printed (2-space indent).

### Step 9 — Print "not installed" and "unconfigured" messages

For each tool that is **not** available, print the corresponding "not installed" message from `../reference/tool-messages.md`. The message explains why zolletta-metaskill benefits from the tool and links to the project homepage (where applicable).

For each Python tool that **is** available but has **no `[tool.*]` section in `pyproject.toml`** (detected in Step 6.5), print the corresponding "unconfigured" warning from `../reference/tool-messages.md`. The warning states the tool's effective built-in defaults and links to the full options reference.

This covers:
- `tokensave_available: false` → tokensave "not installed" message
- For Python projects, each tool in `python` that is `false` → corresponding "not installed" message
- For Python projects, each tool in `python` that is `true` but unconfigured → corresponding "unconfigured" warning

(The Python review skills are bundled inside this meta-skill, so no "not installed" message is needed for them.)

**Do NOT install anything.** Only inform the user.

### Step 10 — Summary

Print a brief summary to the user:

```text
Zolletta-metaskill setup complete.

  Language:                        <language>
  Container:                       <container_name or none>
  tokensave available:             <yes/no>
  Python tooling:                  (Python only)
    uv:                            <yes/no>
    ruff:                          <yes/no>
    pytest:                        <yes/no>
    ty:                            <yes/no>
    vulture:                       <yes/no>
    mypy:                          <yes/no>
  Python config:                   (Python only)
    type_checker:                  <ty/mypy/none>
    line_length:                   <value>
    target_version:                <value>
  python-code-style available:     <yes/no>  (Python only)
  python-testing-patterns available: <yes/no>  (Python only)
  Settings file:                   .zolletta-metaskill/settings.json
  Reports directory:               .zolletta-metaskill/reports/
```

If any tools or skills were unavailable, the "not installed" messages from Step 8 will have already been printed above this summary.

## Re-running setup

`/zolletta-metaskill setup` can be run at any time to re-detect tools and refresh `settings.json`. The previous `settings.json` is overwritten. This is useful after installing tokensave or Python tooling, after adding/removing a Docker container, or after a project language change.
