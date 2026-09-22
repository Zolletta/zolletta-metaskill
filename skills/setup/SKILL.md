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

### Step 0 — Migration and missing-keys backfill (if needed)

If `.zolletta-metaskill/settings.json` already exists, read it and check `setup_version`:

- **`"3.1.0"` or later** — no migration needed; proceed to the requested subcommand (or re-run setup if invoked explicitly).
- **`"3.0.0"`** — additively backfill the key introduced in v3.1.0, then proceed:
  1. `python.code_style.check_one_class_per_test_file` — copy the default (`true`) from the schema doc.
  2. **Merge only**: preserve every user-customized value; only add keys that are absent.
  3. Set `setup_version` to `"3.1.0"`, write the file, and proceed.
- **`"2.x"`** — additively backfill the keys introduced in v3.0.0 and v3.1.0, then proceed:
  1. `python.paths` — run Step 8's `python_paths_detector.py` and store its output (Python projects only).
  2. `python.patterns`, `php.patterns` — copy the defaults from the schema doc.
  3. New `python.code_style` keys (`check_zero_class_files`, `check_unused_all_exports`, `docstring_strip_*`, `check_one_class_per_test_file`), `python.testing.test_naming_min_segments`, `php.code_style.check_acronym_casing`, and the new `documentation.*` keys — copy the defaults from the schema doc.
  4. **Merge only**: preserve every user-customized value; only add keys that are absent.
  5. Set `setup_version` to `"3.1.0"`, write the file, and proceed.
- **`"1.x"` or absent** — migrate before writing the new file:
  1. If the old `subagent_profile` field exists and is non-null, it applied to all review subagents — set `subcommands.patterns.model`, `subcommands.documentor.model`, `subcommands.python-code-style.model`, `subcommands.python-testing-style.model`, `subcommands.php-code-style.model`, and `subcommands.php-testing-style.model` to its value. If it is `null` or absent, leave all review subcommand models at `null`.
  2. Remove `external_review_model` and `subagent_profile` from the file. (`external_review_model` was for the removed `external-review` subcommand — it is not migrated.)
  3. Add the full `subcommands` object with all six keys, preserving migrated values and defaulting unmigrated ones to `null`.
  4. Apply the v3.0.0 + v3.1.0 backfill described above (`paths`, `patterns`, new `code_style`/`testing`/`documentation` keys).
  5. Set `setup_version` to `"3.1.0"`.
  6. Write the migrated file and proceed.

> **What changed in v3.0.0**: every review script now resolves scan roots and rule knobs from `settings.json` instead of CLI flags (see ADR-0015). New keys: `python.paths` (source/test roots + package — the PHP-autoload equivalent Python lacked), `python.patterns` and `php.patterns` (SOLID-check toggles and thresholds), new `python.code_style`/`python.testing`/`php.code_style` toggles, and the `documentation.*` options that drive the documentor tools. Backfill is additive: user-customized values are preserved, only absent keys are added.
>
> **What changed in v3.1.0**: `one_class_per_file_scanner.py` also scans test roots (one test class per test file, named after its stem) — gated by the new `python.code_style.check_one_class_per_test_file` toggle (default `true`, set `false` to skip test files). Its name check is now case-insensitive, so acronym-cased classes (`ADRCache`, `TestADRCLI`) match their lowercase filenames instead of being reported as false positives.

> **What changed in v2.0.0**: the `external_review_model` scalar (for the removed `external-review` subcommand) and the `subagent_profile` scalar (all review subagents) are replaced by `subcommands` — a per-subcommand map where each entry has a `model` field. The `external-review` subcommand is removed; `external_review_model` is not migrated. This lets the user configure a different model per subcommand (e.g. a strong model for `patterns`/`documentor`, a cheap one for `*-code-style`). See [`../../docs/reference/settings-schema.md`](../../docs/reference/settings-schema.md#subcommands-per-subcommand-model-configuration) for the full schema.

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

If language is not Python, set `python: null` and skip to Step 9.

1. Run:

   ```bash
   python3 ../../src/zolletta_metaskill/setup/pyproject_sections_detector.py
   ```

   Prints JSON mapping each tool (`uv`, `ruff`, `pytest`, `ty`, `vulture`, `mypy`) to `{"available": bool}`.

2. For tools not found in `pyproject.toml`, try calling `<command> --version` to check if the tool is installed. If `uv` is available (from step 1's JSON output), prefer `uv run <command> --version` — many tools (e.g. `ty`) are only accessible through `uv run` and would be missed by a bare `<command> --version`. If `container_name` is set, run inside the container via `docker compose exec <container_name> <command>` instead. If the version check succeeds, mark as available.

### Step 7 — Extract Python configuration

Read `pyproject.toml` and extract effective configuration for each available tool. Record `pyproject_mtime` (float) in `python.pyproject_mtime`.

For each available tool, extract its config fields into `python.tools.<tool>`. If a tool has no `[tool.*]` section, store its built-in defaults and print the corresponding "unconfigured" warning from `tool-messages.md`. See the schema doc for the full field list and defaults.

`uv` and `vulture` have no config beyond `available`.

**Write `python.code_style` and `python.testing`** — copy default rule toggles from the schema doc. If re-running setup, merge: preserve existing user-customized values, only add new keys.

**Extract acronyms from `AGENTS.md`**: if the project's `AGENTS.md` contains an "Acronyms stay uppercase" naming convention line (matching `acronyms fully uppercase` followed by examples like `APIGateway`, `MRBranchResolver`), extract the uppercase tokens and store them as the top-level `acronyms` field (e.g. `["API", "MR", "AST"]`). If none found, `acronyms: []`. This field is top-level, always present even for non-Python projects.

**Write `python.patterns`** — copy the default SOLID-check toggles and thresholds from the schema doc. Same merge behavior: preserve user-customized values, only add new keys.

### Step 8 — Detect Python source layout

```bash
python3 ../../src/zolletta_metaskill/setup/python_paths_detector.py
```

Prints JSON `{"source": ["src"], "tests": ["tests"], "package": "zolletta_metaskill"}`. Store the result in `python.paths` — these are the source/test roots every review script scans (the PHP-autoload equivalent Python lacked). The detector reads `pyproject.toml` (`[tool.hatch.build.targets.wheel] packages` → `[tool.setuptools] package-dir`/`packages.find where` → `[tool.poetry] packages` → pytest `testpaths`) and falls back to the `src/`+`tests/` layout.

Re-run this step whenever `pyproject_mtime` changes (the SKILL.md staleness guard already re-runs Step 7, so `paths` stays fresh when pyproject changes).

### Step 9 — Detect documentation configuration

```bash
python3 ../../src/zolletta_metaskill/setup/doc_config_detector.py
```

Reads `documentation.dir` from `settings.json` (default `docs`). Default documentation language is `"en"` (ISO 639-1).

### Step 10 — Detect ADR folder

```bash
python3 ../../src/zolletta_metaskill/setup/adr_detector.py <docs_dir>
```

Prints JSON `{"adrs_path": "adr"}` or `{"adrs_path": null}`. Store in `documentation.adrs`.


### Step 11 — Detect PHP tooling (PHP only)

If language is not PHP, set `php: null` and skip to Step 13.

1. Run:

   ```bash
   python3 ../../src/zolletta_metaskill/setup/php_tools_detector.py
   ```

   Prints JSON mapping each tool (`phpunit`, `phpstan`, `psalm`, `php_cs_fixer`, `phpcs`) to `{"available": bool}`. A tool is available if found in `composer.json` `require-dev` or if a config file exists.

2. For tools not found by the script, try calling `vendor/bin/<tool> --version` (inside the container if `container_name` is set, otherwise on the host). If it succeeds, mark as available.

### Step 12 — Extract PHP configuration

Read `composer.json` and each tool's config file. Record `composer_mtime` (float) in `php.composer_mtime`.

- **`php_version`**: parse `composer.json` `require.php` constraint, store minimum version as string (e.g. `"8.2"`). If absent, `null`.
- **`autoload`**: read `autoload.psr-4` and `autoload-dev.psr-4` into `php.autoload` (empty objects for missing keys).
- **Per-tool config**: for each available tool, extract its config fields into `php.tools.<tool>`. If no config file exists, store built-in defaults and print the "unconfigured" warning. See the schema doc for the full field list and defaults.

**Write `php.code_style`, `php.testing`, and `php.patterns`** — same merge behavior as Python. PHP source/test roots resolve from `php.autoload` (`psr-4`/`psr-4-dev` values) — no `php.paths` is written.

### Step 13 — Python skill availability (no action needed)

The Python review skills (`python-code-style`, `python-testing-style`) are bundled inside this meta-skill — always available, no flags needed.

### Step 14 — Detect companion implementation skills

```bash
python3 ../../src/zolletta_metaskill/setup/companion_skill_detector.py
```

Prints JSON with `php_pro.available` and `python_development.available` booleans.

- For PHP projects: store `php.tools.php_pro_available`
- For Python projects: store `python.tools.python_development_available`

If unavailable, print the corresponding "not installed" message in Step 16.

### Step 15 — Write settings.json

Read the [settings template](assets/settings_template.json) and write `.zolletta-metaskill/settings.json` with the following fields:

| Field                 | Source                                                                                                                                                                                                                                  |
|-----------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `setup_version`       | Matches the skill version (see front-matter)                                                                                                                                                                                            |
| `setup_timestamp`     | Current timestamp in ISO 8601 (`date -u +%Y-%m-%dT%H:%M:%S`)                                                                                                                                                                            |
| `language`            | Step 3                                                                                                                                                                                                                                  |
| `container_name`      | Step 4 (`null` if no Docker)                                                                                                                                                                                                            |
| `tokensave_available` | Step 5                                                                                                                                                                                                                                  |
| `acronyms`            | Step 7 (`[]` if none)                                                                                                                                                                                                                   |
| `python`              | Steps 6 + 7 + 8 (Python only; `null` otherwise)                                                                                                                                                                                         |
| `php`                 | Steps 11 + 12 (PHP only; `null` otherwise)                                                                                                                                                                                              |
| `subcommands`         | Object with one key per subcommand, each containing `model` (default `null` = harness default). See [`../../docs/reference/settings-schema.md`](../../docs/reference/settings-schema.md#subcommands-per-subcommand-model-configuration) |
| `documentation`       | Steps 9 + 10                                                                                                                                                                                                                            |
| `runs_dir`            | `".zolletta-metaskill"`                                                                                                                                                                                                                 |

For the full JSON shape of each subobject, see [`../../docs/reference/settings-schema.md`](../../docs/reference/settings-schema.md). Use the `write` tool. JSON must be valid, pretty-printed (2-space indent).

### Step 16 — Print "not installed" and "unconfigured" messages

For each tool that is **not** available, print the corresponding "not installed" message from `../../docs/reference/tool-messages.md`. This covers `tokensave_available: false`, unavailable `python.tools.*` / `php.tools.*`, and companion skills (`php_pro_available`, `python_development_available`).

For each tool that **is** available but has **no configuration section/file** (detected in Steps 7 and 12), print the corresponding "unconfigured" warning from `../../docs/reference/tool-messages.md`.

**Do NOT install anything.** Only inform the user.

### Step 17 — Summary

Print the following, replacing the path with the absolute path to the project's `settings.json` and making it a clickable file reference:

```text
Zolletta-metaskill setup complete. You can view the configuration by looking at <ref_file file="<project_root>/.zolletta-metaskill/settings.json" />
```

## Re-running setup

`/zolletta-metaskill setup` can be run at any time to re-detect tools and refresh `settings.json`. The previous `settings.json` is overwritten.
