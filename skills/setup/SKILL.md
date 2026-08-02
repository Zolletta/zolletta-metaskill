---
name: zolletta-metaskill-setup
version: 3.1.0
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

Read shared guidelines from the meta-skill (parent directory):

- `../../docs/reference/tool-messages.md` — "not installed" messages for tokensave, Python skills, and PHP skills

## Procedure

### Step 1 — Create the .zolletta-metaskill directory

```bash
mkdir -p .zolletta-metaskill
```

### Step 2 — Add .zolletta-metaskill/ to the global ~/.gitignore

The `.zolletta-metaskill/` directory is a per-user review artifact, not project content, so it is ignored globally rather than per-project. This keeps every project's local `.gitignore` clean.

Run:

```bash
python3 ../../src/zolletta_metaskill/setup/ensure_global_gitignore.py
```

The script is idempotent — it creates `~/.gitignore` if missing, appends the entry only if it is not already present, never duplicates. Do **not** touch the project's local `.gitignore`.

### Step 3 — Detect the project language

Determine the project's primary language by checking for language markers in the project root (the current working directory):

| Marker(s)                                                                            | Language              |
| ------------------------------------------------------------------------------------ | --------------------- |
| `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements*.txt`, `Pipfile`, `uv.lock` | Python                |
| `package.json`, `tsconfig.json`, `deno.json`                                         | TypeScript/JavaScript |
| `composer.json`                                                                      | PHP                   |
| `go.mod`                                                                             | Go                    |
| `Cargo.toml`                                                                         | Rust                  |
| `pom.xml`, `build.gradle`                                                            | Java/Kotlin           |
| `Gemfile`, `*.gemspec`                                                               | Ruby                  |
| `CMakeLists.txt`, `Makefile` with `.c`/`.cpp` sources                                | C/C++                 |

Run:

```bash
python3 ../../src/zolletta_metaskill/setup/detect_language.py
```

The script prints the detected language (first matching marker in the table order above) and exits 0, or prints nothing and exits 1 if no marker is found.

1. If the command prints nothing, inspect the source directory for the most common file extension.
2. If the language still cannot be determined, ask the user with `ask_user_question`.
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

1. **Check `pyproject.toml`** — read the `[tool.*]` sections. If a tool has a configuration section (e.g. `[tool.ruff]`, `[tool.mypy]`, `[tool.pytest.ini_options]`, `[tool.vulture]`), mark it as available (the project uses it). Run:

   ```bash
   python3 ../../src/zolletta_metaskill/setup/detect_pyproject_sections.py
   ```

   The script prints JSON mapping each tool name to `{"available": bool}`. For `uv`, availability is `true` if either `[project]` exists or `uv.lock` is present.

2. **If not found in `pyproject.toml`**, try calling the command — inside the container if `container_name` is set (`docker compose exec <container_name> <command> --version`), otherwise on the host (`<command> --version`). If the command succeeds, mark it as available.

The tools to detect:

| Tool      | pyproject.toml section                    | Command             |
| --------- | ----------------------------------------- | ------------------- |
| `uv`      | n/a (check `[project]` or `uv.lock` file) | `uv --version`      |
| `ruff`    | `[tool.ruff]`                             | `ruff --version`    |
| `pytest`  | `[tool.pytest.ini_options]`               | `pytest --version`  |
| `ty`      | `[tool.ty]`                               | `ty --version`      |
| `vulture` | `[tool.vulture]`                          | `vulture --version` |
| `mypy`    | `[tool.mypy]`                             | `mypy --version`    |

Store each tool as an object in `python.tools` with an `available` boolean (see Step 8). The per-tool configuration fields are populated in Step 6.5.

> **Do NOT install any tool.** If a tool is not present, set `available: false` and print the corresponding "not installed" message in Step 9.

### Step 6.5 — Extract Python configuration from pyproject.toml

If the detected language from Step 3 is **not Python**, skip this step entirely and leave `python: null`.

If the language is **Python**, read `pyproject.toml` and extract the effective configuration for each available tool. Record the file's modification time so the setup guard can detect staleness on future runs. All values extracted in this step are written into the `python.tools.<tool>` objects (alongside the `available` flag from Step 6).

1. **Record `pyproject_mtime`** — use `os.path.getmtime("pyproject.toml")` (or equivalent). Store it as a float in `python.pyproject_mtime`.

2. **For each tool that is `available: true` in `python.tools`** (from Step 6), extract its configuration into the same `python.tools.<tool>` object:

| Tool     | If `[tool.*]` section exists                                                                                                                               | If section is absent                                                                                                                                                                                         |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `ruff`   | Extract `line-length` → `line_length`, `target-version` → `target_version`, `lint.select` → `select`, `lint.ignore` → `ignore` into `python.tools.ruff`    | Store ruff's built-in defaults: `line_length: 88`, `target_version: "py310"`, `select: ["E4","E7","E9","F"]`, `ignore: []`. Print the ruff "unconfigured" warning from `../../docs/reference/tool-messages.md`. |
| `mypy`   | Extract `python_version`, `strict`, `warn_return_any`, `warn_unused_ignores`, `disallow_untyped_defs`, `disallow_incomplete_defs` into `python.tools.mypy` | Store mypy's built-in defaults: `strict: false`, `python_version: null` (uses running interpreter). Print the mypy "unconfigured" warning.                                                                   |
| `ty`     | Extract `python-version` (or `environment.python-version`) → `python_version` into `python.tools.ty`                                                       | Store ty's built-in defaults: `python_version: null` (detected from environment). Print the ty "unconfigured" warning.                                                                                       |
| `pytest` | Extract `addopts`, `testpaths`, `minversion` into `python.tools.pytest`                                                                                    | Store pytest's built-in defaults: `addopts: []`, `testpaths: []`, `minversion: null`. Print the pytest "unconfigured" warning.                                                                               |

   `uv` and `vulture` have no configuration beyond `available` — leave them as `{ "available": true }`.

3. **Type checker resolution** — there is no `type_checker` field in `settings.json`. Review skills run all available type checkers:
   - If `python.tools.ty.available` is `true` → run ty
   - If `python.tools.mypy.available` is `true` → run mypy
   - If neither is available → type checking is skipped

   When both are available, both run. Findings from each are listed separately. This is documented in `skills/python-code-style/SKILL.md`.

4. **Never modify `pyproject.toml`.** Setup only reads it. The "unconfigured" warnings are informational — the user decides whether to add a `[tool.*]` section.

5. **Write `python.code_style`** — copy the default rule toggles (see Step 8 for the shape). If `settings.json` already exists (re-run of setup), **preserve existing user-customized values** and only add keys that are new (i.e. merge, don't overwrite).

   **Extract acronyms from AGENTS.md**: if the project's `AGENTS.md` contains an "Acronyms stay uppercase" naming convention line (matching the pattern `acronyms fully uppercase` followed by a parenthesised list of examples like `APIGateway`, `MRBranchResolver`), extract the uppercase tokens from those examples and store them as the top-level `acronyms` field in `settings.json`. For the example above, the extracted list would be `["API", "MR", "AST"]`. If no such line is found, leave `acronyms` as an empty list — the scanner will use its built-in defaults. The `acronyms` field is **top-level** (not nested under `python`), so it is always present even for non-Python projects.

6. **Write `python.testing`** — copy the default rule toggles (see Step 8 for the shape). Same merge behavior as `python.code_style`: preserve existing user-customized values, only add new keys.

### Step 6.6 — Detect documentation configuration

Determine the project's documentation configuration:

1. **Directory**: check in this order:
   - If `.backstage/` exists in the project root → `dir: ".backstage"`
   - Else if `docs/` exists in the project root → `dir: "docs"`
   - Else → `dir: "docs"` (default — will be created by the `documentor` skill if needed)

   Run:

   ```bash
   python3 ../../src/zolletta_metaskill/setup/detect_doc_config.py
   ```

   The script prints `.backstage` or `docs`.

2. **Language**: default to `"en"` (ISO 639-1). If the project has a `documentation.language` preference, use that instead.

Store both values for writing to the `documentation` object in `settings.json`. The `documentor` skill reads these fields to locate the Diátaxis docs tree and translate signpost headings if needed.

### Step 7 — Detect PHP tooling (PHP projects only)

If the detected language from Step 3 is **not PHP**, skip this step entirely and set `php: null`.

If the language is **PHP**, detect which tools are available. For each tool, check in this order:

1. **Check `composer.json` `require-dev`** and **config files** — run:

   ```bash
   python3 ../../src/zolletta_metaskill/setup/detect_php_tools.py
   ```

   The script prints JSON mapping each tool name to `{"available": bool}`. A tool is marked available if found in `composer.json` `require-dev` **or** if a config file exists in the project root.

2. **If not found by the script**, try calling the command — inside the container if `container_name` is set (`docker compose exec <container_name> vendor/bin/<tool> --version`), otherwise on the host (`vendor/bin/<tool> --version`). If the command succeeds, mark it as available.

3. **If not found in `composer.json` or config file**, try calling the command — inside the container if `container_name` is set (`docker compose exec <container_name> vendor/bin/<tool> --version`), otherwise on the host (`vendor/bin/<tool> --version`). If the command succeeds, mark it as available.

The tools to detect:

| Tool           | `composer.json` require-dev package   | Config file(s)                                          | Command                          |
| -------------- | ------------------------------------- | ------------------------------------------------------- | -------------------------------- |
| `phpunit`      | `phpunit/phpunit`                     | `phpunit.xml`, `phpunit.dist.xml`                       | `vendor/bin/phpunit --version`   |
| `phpstan`      | `phpstan/phpstan`                     | `phpstan.neon`, `phpstan.dist.neon`                     | `vendor/bin/phpstan --version`   |
| `psalm`        | `vimeo/psalm`                         | `psalm.xml`, `psalm.dist.xml`                           | `vendor/bin/psalm --version`     |
| `php_cs_fixer` | `friendsofphp/php-cs-fixer`           | `.php-cs-fixer.php`, `.php-cs-fixer.dist.php`           | `vendor/bin/php-cs-fixer --version` |
| `phpcs`        | `squizlabs/php_codesniffer`           | `.phpcs.xml`, `phpcs.xml.dist`, `.phpcs.xml.dist`       | `vendor/bin/phpcs --version`     |

Store each tool as an object in `php.tools` with an `available` boolean (see Step 8). The per-tool configuration fields are populated in Step 7.5.

> **Do NOT install any tool.** If a tool is not present, set `available: false` and print the corresponding "not installed" message in Step 9.

### Step 7.5 — Extract PHP configuration from composer.json and tool config files

If the detected language from Step 3 is **not PHP**, skip this step entirely and leave `php: null`.

If the language is **PHP**, read `composer.json` and each tool's config file, and extract the effective configuration. Record `composer.json`'s modification time so the setup guard can detect staleness on future runs. All values extracted in this step are written into the `php.tools.<tool>` objects (alongside the `available` flag from Step 7) and the `php.autoload` / `php.php_version` fields.

1. **Record `composer_mtime`** — use `os.path.getmtime("composer.json")` (or equivalent). Store as a float in `php.composer_mtime`.

2. **Extract `php_version`** — read `composer.json` `require.php` (e.g. `">=8.2"`, `"^8.1"`, `"8.3"`). Parse the version constraint and store the minimum version as a string in `php.php_version` (e.g. `"8.2"`, `"8.1"`). If `require.php` is absent, store `null` and print a warning (the PHP version is unknown — review skills cannot assume a specific version).

3. **Extract autoload mapping** — read `composer.json` `autoload.psr-4` and `autoload-dev.psr-4`. Store in `php.autoload`:

   ```json
   "autoload": {
     "psr-4": { "App\\": "src/" },
     "psr-4-dev": { "Tests\\": "tests/" }
   }
   ```

   If `autoload` or `autoload-dev` is absent, store an empty object for the missing key. The `php-code-style` and `php-testing-patterns` skills use this to resolve namespaces to directories (equivalent to how Python skills use `[tool.hatch.build.targets.wheel] packages`).

4. **For each tool that is `available: true` in `php.tools`** (from Step 7), extract its configuration into the same `php.tools.<tool>` object:

   | Tool           | If config file exists                                                                                                                                                     | If config file is absent                                                                                                                              |
   | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
   | `phpunit`      | Parse `phpunit.xml` (XML): extract `bootstrap` → `bootstrap`, `<coverage>` config → `coverage_config`, `<testsuites>` dirs → `testpaths`. Store in `php.tools.phpunit`.   | Store phpunit's built-in defaults: `bootstrap: null`, `testpaths: ["tests"]`, `coverage_config: null`. Print the phpunit "unconfigured" warning.      |
   | `phpstan`      | Parse `phpstan.neon` (NEON): extract `level` → `level` (0–9), `paths` → `paths`, `memory_limit` → `memory_limit`. Store in `php.tools.phpstan`.                           | Store phpstan's built-in defaults: `level: 0`, `paths: ["src"]`, `memory_limit: null`. Print the phpstan "unconfigured" warning.                       |
   | `psalm`        | Parse `psalm.xml` (XML): extract `errorLevel` → `error_level` (1–8), `projectFiles` dirs → `paths`. Store in `php.tools.psalm`.                                           | Store psalm's built-in defaults: `error_level: 1`, `paths: ["src"]`. Print the psalm "unconfigured" warning.                                          |
   | `php_cs_fixer` | Check if `.php-cs-fixer.php` or `.php-cs-fixer.dist.php` exists. Store `config_file: true`. **Do not parse the PHP file** — it is executable PHP code, not a declarative format. The `php-code-style` skill reads it at review time if needed. | Store `config_file: false`. Print the php-cs-fixer "unconfigured" warning (states the built-in default ruleset: `@PSR-12`).                           |
   | `phpcs`        | Parse `.phpcs.xml` or `phpcs.xml.dist` (XML): extract `standard` → `standard` (e.g. `"PSR12"`, `"Custom"`). Store in `php.tools.phpcs`.                                   | Store phpcs's built-in defaults: `standard: "PSR12"`. Print the phpcs "unconfigured" warning.                                                         |

   > **NEON parsing**: `phpstan.neon` uses the NEON format (a YAML-like syntax). If a NEON parser is not available as a Python dependency, parse it as a simplified YAML subset (key: value, nested via indentation, arrays with `-`). PHPStan config files are typically simple enough for this. If parsing fails, store `level: null` and print a warning that the config could not be read.

5. **Static analysis resolution** — parallel to Python's type checker resolution. There is no `static_analyser` field in `settings.json`. Review skills run all available static analysers:
   - If `php.tools.phpstan.available` is `true` → run phpstan
   - If `php.tools.psalm.available` is `true` → run psalm
   - If neither is available → static analysis is skipped

   When both are available, both run. Findings from each are listed separately. This is documented in `skills/php-code-style/SKILL.md`.

6. **Never modify `composer.json` or any tool config file.** Setup only reads them. The "unconfigured" warnings are informational — the user decides whether to add a config file.

7. **Write `php.code_style`** — copy the default rule toggles (see Step 8 for the shape). If `settings.json` already exists (re-run of setup), **preserve existing user-customized values** and only add keys that are new (merge, don't overwrite). Same merge behavior as `python.code_style`.

8. **Write `php.testing`** — copy the default rule toggles. Same merge behavior.

### Step 7.6 — Python skill availability (no action needed)

The two Python review skills (`python-code-style`, `python-testing-patterns`) are bundled inside Zolletta-metaskill, so they are always available — no probing or `*_available` flags are written to `settings.json`. The `review` subcommand dispatches to them automatically when `language` is `python`.

> **Note**: these skills are adapted from [wshobson/agents](https://github.com/wshobson/agents) (MIT License, Copyright (c) 2024 Seth Hobson) and live in `python-code-style/` and `python-testing-patterns/` within this meta-skill.

### Step 7.7 — Detect companion implementation skills

Zolletta-metaskill is a **review** skill — it checks code quality but does not write code. Companion **implementation** skills can be installed separately to provide code generation alongside review. Setup detects their availability and suggests installing them if not present.

1. **For PHP projects** (`language == "php"`):
   - Run:

     ```bash
     python3 ../../src/zolletta_metaskill/setup/detect_companion_skills.py
     ```

     The script prints JSON with `php_pro.available` and `python_development.available` booleans.

   - Store `php.tools.php_pro_available` boolean (add to `php.tools` object)
   - If not available, print the php-pro "not installed" message from `../../docs/reference/tool-messages.md` in Step 9

2. **For Python projects** (`language == "python"`):
   - Use the same script output as above.
   - Store `python.tools.python_development_available` boolean (add to `python.tools` object)
   - If not available, print the python-development "not installed" message from `../../docs/reference/tool-messages.md` in Step 9

> **Do NOT install any skill.** Only inform the user. These are suggestions, not requirements.

### Step 8 — Write settings.json

Read the [settings template](assets/settings_template.json) and write `.zolletta-metaskill/settings.json` with the following fields filled in:

| Field                   | Source                                                                  |
| ----------------------- | ----------------------------------------------------------------------- |
| `setup_version`         | Matches the skill version (current: see front-matter)                   |
| `setup_timestamp`       | Current timestamp in ISO 8601 (`date -u +%Y-%m-%dT%H:%M:%S`)            |
| `language`              | Detected language from Step 3                                           |
| `container_name`        | Container name from Step 4 (`null` if no Docker)                        |
| `tokensave_available`   | Boolean from Step 5                                                     |
| `acronyms`              | Top-level list from Step 6.5 (extracted from `AGENTS.md`; `[]` if none) |
| `python`                | Object from Steps 6 + 6.5 (Python only; `null` otherwise)              |
| `php`                   | Object from Steps 7 + 7.5 (PHP only; `null` otherwise)                 |
| `external_review_model` | `"swe"` (default; overridable by front-matter)                          |
| `documentation`         | Object from Step 6.6                                                    |
| `reports_dir`           | `".zolletta-metaskill/reports"`                                         |

For the full JSON shape of each subobject (`python`, `php`, `documentation`), field-by-field descriptions, and complete Python/PHP examples, see [`../../docs/reference/settings-schema.md`](../../docs/reference/settings-schema.md) — the canonical schema reference. Do not duplicate the examples here; the schema doc is the single source of truth and stays in sync with [`assets/settings.schema.json`](assets/settings.schema.json).

Use the `write` tool to create the file. The JSON must be valid and pretty-printed (2-space indent).

### Step 9 — Print "not installed" and "unconfigured" messages

For each tool that is **not** available, print the corresponding "not installed" message from `../../docs/reference/tool-messages.md`. The message explains why Zolletta-metaskill benefits from the tool and links to the project homepage (where applicable). This covers `tokensave_available: false`, each unavailable `python.tools.*` / `php.tools.*` tool, and the companion implementation skills (`php_pro_available`, `python_development_available`).

For each tool that **is** available but has **no configuration section/file** (detected in Steps 6.5 and 7.5), print the corresponding "unconfigured" warning from `../../docs/reference/tool-messages.md`. The warning states the tool's effective built-in defaults and links to the full options reference.

**Do NOT install anything.** Only inform the user.

### Step 10 — Summary

Print the following, replacing the path with the absolute path to the project's `settings.json` and making it a clickable file reference:

```text
Zolletta-metaskill setup complete. You can view the configuration by looking at <ref_file file="<project_root>/.zolletta-metaskill/settings.json" />
```

## Re-running setup

`/zolletta-metaskill setup` can be run at any time to re-detect tools and refresh `settings.json`. The previous `settings.json` is overwritten.
