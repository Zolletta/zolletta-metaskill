---
name: zolletta-metaskill-setup
license: MIT + Commons Clause
description: >
  Project initialization for Zolletta-metaskill. Creates the .zolletta-metaskill/ directory, detects the project language, detects Docker container, tests tokensave availability, detects Python and PHP tooling, and writes settings.json. Also adds .zolletta-metaskill/ to the user's global ~/.gitignore. Run automatically by the setup guard before any subcommand if settings.json is missing, or manually via /zolletta-metaskill setup.
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
    - Write(~/.gitignore)
    - mcp__tokensave__tokensave_status
---

# Zolletta-metaskill Setup

Initialize the `.zolletta-metaskill/` directory and write `settings.json` so that every other subcommand can read project-wide configuration from a single location.

## Shared resources

- `../../docs/reference/tool-messages.md` — "not installed" and "unconfigured" messages
- `../../docs/reference/settings-schema.md` — canonical schema reference for `settings.json` field shapes

## Procedure

### Step 1 — Create the .zolletta-metaskill directory

```bash
mkdir -p .zolletta-metaskill
```

### Step 2 — Add .zolletta-metaskill/ to the global ~/.gitignore

```bash
python3 ../../src/zolletta_metaskill/setup/global_gitignore_ensurer.py
```

Idempotent. Do **not** touch the project's local `.gitignore`.

### Step 3 — Detect the project language

```bash
python3 ../../src/zolletta_metaskill/setup/language_detector.py
```

Prints the detected language and exits 0, or prints nothing and exits 1 if no marker is found. If no marker is found, inspect the source directory for the most common file extension. If still undetermined, ask the user with `ask_user_question`.

### Step 4 — Detect Docker container

1. Check for `docker-compose.yml` or `compose.yml` (also `.yaml` variants) in the project root.
2. If no compose file → `container_name: null`. Skip to Step 5.
3. If found, parse it to extract the service names (keys under `services:`).
4. One service → use it as `container_name`. Multiple services → ask the user with `ask_user_question`.

### Step 5 — Test tokensave availability

Call `tokensave_status` (no arguments). Success → `tokensave_available: true`. Failure → `tokensave_available: false`.

### Step 6 — Detect Python tooling (Python only)

If language is not Python, set `python: null` and skip to Step 6.6.

1. Run:

   ```bash
   python3 ../../src/zolletta_metaskill/setup/pyproject_sections_detector.py
   ```

   Prints JSON mapping each tool (`uv`, `ruff`, `pytest`, `ty`, `vulture`, `mypy`) to `{"available": bool}`.

2. For tools not found in `pyproject.toml`, try calling `<command> --version` to check if the tool is installed. If `uv` is available (from step 1's JSON output), prefer `uv run <command> --version` — many tools (e.g. `ty`) are only accessible through `uv run` and would be missed by a bare `<command> --version`. If `container_name` is set, run inside the container via `docker compose exec <container_name> <command>` instead. If the version check succeeds, mark as available.

### Step 6.5 — Extract Python configuration

Read `pyproject.toml` and extract effective configuration for each available tool. Record `pyproject_mtime` (float) in `python.pyproject_mtime`.

For each available tool, extract its config fields into `python.tools.<tool>`. If a tool has no `[tool.*]` section, store its built-in defaults and print the corresponding "unconfigured" warning from `tool-messages.md`. See the schema doc for the full field list and defaults.

`uv` and `vulture` have no config beyond `available`.

**Write `python.code_style` and `python.testing`** — copy default rule toggles from the schema doc. If re-running setup, merge: preserve existing user-customized values, only add new keys.

**Extract acronyms from `AGENTS.md`**: if the project's `AGENTS.md` contains an "Acronyms stay uppercase" naming convention line (matching `acronyms fully uppercase` followed by examples like `APIGateway`, `MRBranchResolver`), extract the uppercase tokens and store them as the top-level `acronyms` field (e.g. `["API", "MR", "AST"]`). If none found, `acronyms: []`. This field is top-level, always present even for non-Python projects.

### Step 6.6 — Detect documentation configuration

```bash
python3 ../../src/zolletta_metaskill/setup/doc_config_detector.py
```

Reads `documentation.dir` from `settings.json` (default `docs`). Default documentation language is `"en"` (ISO 639-1).

### Step 6.7 — Detect ADR folder

```bash
python3 ../../src/zolletta_metaskill/setup/adr_detector.py <docs_dir>
```

Prints JSON `{"adrs_path": "adr"}` or `{"adrs_path": null}`. Store in `documentation.adrs`.


### Step 7 — Detect PHP tooling (PHP only)

If language is not PHP, set `php: null` and skip to Step 7.6.

1. Run:

   ```bash
   python3 ../../src/zolletta_metaskill/setup/php_tools_detector.py
   ```

   Prints JSON mapping each tool (`phpunit`, `phpstan`, `psalm`, `php_cs_fixer`, `phpcs`) to `{"available": bool}`. A tool is available if found in `composer.json` `require-dev` or if a config file exists.

2. For tools not found by the script, try calling `vendor/bin/<tool> --version` (inside the container if `container_name` is set, otherwise on the host). If it succeeds, mark as available.

### Step 7.5 — Extract PHP configuration

Read `composer.json` and each tool's config file. Record `composer_mtime` (float) in `php.composer_mtime`.

- **`php_version`**: parse `composer.json` `require.php` constraint, store minimum version as string (e.g. `"8.2"`). If absent, `null`.
- **`autoload`**: read `autoload.psr-4` and `autoload-dev.psr-4` into `php.autoload` (empty objects for missing keys).
- **Per-tool config**: for each available tool, extract its config fields into `php.tools.<tool>`. If no config file exists, store built-in defaults and print the "unconfigured" warning. See the schema doc for the full field list and defaults.

**Write `php.code_style` and `php.testing`** — same merge behavior as Python.

### Step 7.6 — Python skill availability (no action needed)

The Python review skills (`python-code-style`, `python-testing-style`) are bundled inside this meta-skill — always available, no flags needed.

### Step 7.7 — Detect companion implementation skills

```bash
python3 ../../src/zolletta_metaskill/setup/companion_skill_detector.py
```

Prints JSON with `php_pro.available` and `python_development.available` booleans.

- For PHP projects: store `php.tools.php_pro_available`
- For Python projects: store `python.tools.python_development_available`

If unavailable, print the corresponding "not installed" message in Step 9.

### Step 8 — Write settings.json

Read the [settings template](assets/settings_template.json) and write `.zolletta-metaskill/settings.json` with the following fields:

| Field                   | Source                                                       |
|-------------------------|--------------------------------------------------------------|
| `setup_version`         | Matches the skill version (see front-matter)                 |
| `setup_timestamp`       | Current timestamp in ISO 8601 (`date -u +%Y-%m-%dT%H:%M:%S`) |
| `language`              | Step 3                                                       |
| `container_name`        | Step 4 (`null` if no Docker)                                 |
| `tokensave_available`   | Step 5                                                       |
| `acronyms`              | Step 6.5 (`[]` if none)                                      |
| `python`                | Steps 6 + 6.5 (Python only; `null` otherwise)                |
| `php`                   | Steps 7 + 7.5 (PHP only; `null` otherwise)                   |
| `external_review_model` | `"swe"` (default; overridable by front-matter)               |
| `documentation`         | Steps 6.6 + 6.7                                              |
| `runs_dir`              | `".zolletta-metaskill"`                                      |

For the full JSON shape of each subobject, see [`../../docs/reference/settings-schema.md`](../../docs/reference/settings-schema.md). Use the `write` tool. JSON must be valid, pretty-printed (2-space indent).

### Step 9 — Print "not installed" and "unconfigured" messages

For each tool that is **not** available, print the corresponding "not installed" message from `../../docs/reference/tool-messages.md`. This covers `tokensave_available: false`, unavailable `python.tools.*` / `php.tools.*`, and companion skills (`php_pro_available`, `python_development_available`).

For each tool that **is** available but has **no configuration section/file** (detected in Steps 6.5 and 7.5), print the corresponding "unconfigured" warning from `../../docs/reference/tool-messages.md`.

**Do NOT install anything.** Only inform the user.

### Step 10 — Summary

Print the following, replacing the path with the absolute path to the project's `settings.json` and making it a clickable file reference:

```text
Zolletta-metaskill setup complete. You can view the configuration by looking at <ref_file file="<project_root>/.zolletta-metaskill/settings.json" />
```

## Re-running setup

`/zolletta-metaskill setup` can be run at any time to re-detect tools and refresh `settings.json`. The previous `settings.json` is overwritten.
