---
audience: human, ai
status: stable
skills: [setup, review, patterns, documentor, python-*, php-*]
---

# settings.json schema

[← Back to README](../../README.md)

`.zolletta-metaskill/settings.json` is created by `/zolletta-metaskill setup` and read by every other subcommand. This page documents every field.

> **JSON Schema**: the machine-readable source of truth for the shape of `settings.json` lives at [`skills/zolletta-metaskill-setup/assets/settings.schema.json`](../../skills/zolletta-metaskill-setup/assets/settings.schema.json) (JSON Schema draft 2020-12). This prose doc is the human-readable counterpart and must stay in sync — when a field is added, removed, or renamed, update both files in the same change.

## Example (Python project)

```json
{
  "setup_version": "3.0.0",
  "setup_timestamp": "2026-07-16T14:30:00",
  "language": "python",
  "container_name": "myproject",
  "tokensave_available": true,
  "acronyms": ["CITE"],
  "python": {
    "tools": {
      "uv": { "available": true },
      "ruff": {
        "available": true,
        "line_length": 100,
        "target_version": "py312",
        "select": ["E", "W", "F", "I", "B", "C4", "D", "UP", "T20", "SIM"],
        "ignore": ["B008", "T201", "D104", "D107", "D203", "D213"]
      },
      "pytest": {
        "available": true,
        "addopts": ["-ra", "--tb=short"],
        "testpaths": ["tests"],
        "minversion": "8.0"
      },
      "ty": { "available": true, "python_version": "3.12" },
      "vulture": { "available": true },
      "mypy": { "available": true, "strict": true, "python_version": "3.12" }
    },
    "paths": {
      "source": ["src"],
      "tests": ["tests"],
      "package": "myproject"
    },
    "code_style": {
      "check_acronym_casing": true,
      "check_no_relative_imports": true,
      "check_one_class_per_file": true,
      "check_one_class_per_test_file": true,
      "check_zero_class_files": true,
      "check_filename_matches_class": true,
      "check_public_docstrings": true,
      "check_docstring_no_type_repeat": true,
      "check_skip_obvious_docstrings": true,
      "check_line_length": true,
      "check_file_length": true,
      "check_unused_all_exports": true,
      "docstring_strip_private": false,
      "docstring_strip_tests": false,
      "docstring_strip_nested": false,
      "docstring_strip_obvious_init": false,
      "max_file_length": 800,
      "vulture_min_confidence": 80
    },
    "testing": {
      "coverage_gap_threshold": 50,
      "coverage_well_covered_threshold": 80,
      "check_test_naming": true,
      "test_naming_min_segments": 3
    },
    "patterns": {
      "check_ocp": true,
      "check_isp": true,
      "check_dip": true,
      "check_lsp": true,
      "check_test_structure": true,
      "ocp_min_branches": 3,
      "isp_min_methods": 5,
      "dip_entry_points": ["main", "cli", "app", "__main__", "myproject", "manage", "wsgi", "asgi", "conftest"],
      "class_metrics_top": 30,
      "class_metrics_min_lines": 50,
      "test_god_classes_top": 30
    },
    "pyproject_mtime": 1784223225.47
  },
  "subcommands": {
    "patterns": { "model": null },
    "documentor": { "model": null },
    "python-code-style": { "model": null },
    "python-testing-style": { "model": null },
    "php-code-style": { "model": null },
    "php-testing-style": { "model": null }
  },
  "documentation": {
    "language": "en",
    "dir": "docs",
    "adrs": null,
    "min_severity": "high",
    "staleness_threshold": null,
    "readme_focus": false,
    "readme_sections": ["installation", "usage", "api", "contributing", "license"],
    "diataxis_translations": null,
    "staleness_weights": null,
    "doc_patterns": ["*.md", "*.rst", "*.txt", "*.adoc"],
    "check_external": false,
    "include_referential": false,
    "api_doc_recursive": true,
    "api_doc_include_private": false,
    "api_doc_suggest_coverage": false
  },
  "runs_dir": ".zolletta-metaskill"
}
```

## Example (PHP project)

```json
{
  "setup_version": "3.0.0",
  "setup_timestamp": "2026-07-16T14:30:00",
  "language": "php",
  "container_name": "myproject",
  "tokensave_available": true,
  "acronyms": ["CITE"],
  "python": null,
  "php": {
    "tools": {
      "phpunit": {
        "available": true,
        "bootstrap": "vendor/autoload.php",
        "testpaths": ["tests"],
        "coverage_config": true
      },
      "phpstan": {
        "available": true,
        "level": 6,
        "paths": ["src"],
        "memory_limit": "256M"
      },
      "psalm": { "available": false, "error_level": 1, "paths": ["src"] },
      "php_cs_fixer": { "available": true, "config_file": true },
      "phpcs": { "available": false, "standard": "PSR12" }
    },
    "code_style": {
      "check_acronym_casing": true,
      "check_union_types": true,
      "check_intersection_types": true,
      "check_enum_methods": true,
      "check_first_class_callables": true,
      "check_readonly_classes": true,
      "check_typed_constants": true,
      "check_override_attribute": true,
      "check_property_hooks": true,
      "check_asymmetric_visibility": true,
      "check_pipe_operator": true,
      "check_array_functions": true,
      "check_string_functions": true,
      "check_file_length": true,
      "max_file_length": 800
    },
    "testing": {
      "coverage_gap_threshold": 50,
      "coverage_well_covered_threshold": 80,
      "check_test_naming": true
    },
    "patterns": {
      "check_ocp": true,
      "check_isp": true,
      "check_dip": true,
      "ocp_min_branches": 3,
      "isp_min_methods": 7
    },
    "autoload": {
      "psr-4": { "App\\": "src/" },
      "psr-4-dev": { "Tests\\": "tests/" }
    },
    "php_version": "8.2",
    "composer_mtime": 1718700000.0
  },
  "subcommands": {
    "patterns": { "model": null },
    "documentor": { "model": null },
    "python-code-style": { "model": null },
    "python-testing-style": { "model": null },
    "php-code-style": { "model": null },
    "php-testing-style": { "model": null }
  },
  "documentation": {
    "language": "en",
    "dir": "docs",
    "adrs": null,
    "min_severity": "high",
    "staleness_threshold": null,
    "readme_focus": false,
    "readme_sections": ["installation", "usage", "api", "contributing", "license"],
    "diataxis_translations": null,
    "staleness_weights": null,
    "doc_patterns": ["*.md", "*.rst", "*.txt", "*.adoc"],
    "check_external": false,
    "include_referential": false,
    "api_doc_recursive": true,
    "api_doc_include_private": false,
    "api_doc_suggest_coverage": false
  },
  "runs_dir": ".zolletta-metaskill"
}
```

## Top-level fields

| Field                 | Type              | Description                                                                                                                                                                                                                              |
|-----------------------|-------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `setup_version`       | string            | Matches the skill version that wrote the file                                                                                                                                                                                            |
| `setup_timestamp`     | string (ISO 8601) | Timestamp of the last setup run                                                                                                                                                                                                          |
| `language`            | string            | Detected project language (`python`, `php`, `go`, `rust`, etc.)                                                                                                                                                                          |
| `container_name`      | string\|null      | Docker container name for running tools (`null` if no Docker)                                                                                                                                                                            |
| `tokensave_available` | boolean           | `true` if `tokensave_status` responds (probed directly)                                                                                                                                                                                  |
| `acronyms`            | array             | Project-specific acronyms that must stay uppercase in class names (e.g. `["CITE"]`). Extracted from `AGENTS.md` during setup; merged with the built-in list by `acronym_casing_scanner.py`. Always present, even for non-Python projects |
| `python`              | object\|null      | Python tooling, rule toggles, and effective tool configuration (Python only; `null` otherwise) — see below                                                                                                                               |
| `php`                 | object\|null      | PHP tooling, rule toggles, autoload mapping, and effective tool configuration (PHP only; `null` otherwise) — see below                                                                                                                   |
| `subcommands`         | object            | Per-subcommand configuration — see below                                                                                                                                                                                                 |
| `documentation`       | object            | Documentation configuration — see below                                                                                                                                                                                                  |
| `runs_dir`            | string            | Directory where review run folders are created. Each run gets a timestamped subdirectory (`<runs_dir>/<YYYY-MM-DD-HH-MM>/`) containing `reports/` (LLM judgment) and `cache/` (deterministic script outputs)                             |

## `subcommands` — per-subcommand model configuration

Each key is a subcommand name; each value is an object with a `model` field. The review orchestrator reads each subcommand's `model` and passes it to `run_subagent` when launching that subcommand's subagent. When `model` is `null`, the harness default is used — behavior is unchanged from v1.x.

Profile/model ids are harness-specific. The user supplies a value that exists in their harness; the skill never hardcodes one. This is the opt-in mechanism for [Smart Plan, Cheap Execution](../explanation/patterns.md#19-smart-plan-cheap-execution) — set a strong model for judgment-heavy subagents (`patterns`, `documentor`) and a cheaper one for mechanical ones (`*-code-style`, `*-testing-style`), or leave all at `null`.

| Field                      | Type           | Default | Description                                                                         |
|----------------------------|----------------|---------|-------------------------------------------------------------------------------------|
| `subcommands.<name>.model` | string \| null | `null`  | Harness-specific profile/model id for subcommand `<name>`. `null` = harness default |

The six subcommand keys:

| Key                    | Subcommand                       | Default `model` | Notes                                                    |
|------------------------|----------------------------------|-----------------|----------------------------------------------------------|
| `patterns`             | `/zolletta-metaskill patterns`   | `null`          | Judgment-heavy — design pattern analysis                 |
| `documentor`           | `/zolletta-metaskill documentor` | `null`          | Judgment-heavy — documentation review + drift detection  |
| `python-code-style`    | `python-code-style`              | `null`          | Mechanical — linting, formatting, naming (Python only)   |
| `python-testing-style` | `python-testing-style`           | `null`          | Mechanical — test isolation, coverage gaps (Python only) |
| `php-code-style`       | `php-code-style`                 | `null`          | Mechanical — PSR-12, naming, types (PHP only)            |
| `php-testing-style`    | `php-testing-style`              | `null`          | Mechanical — PHPUnit, coverage gaps (PHP only)           |

> **v1.x migration**: the `external_review_model` scalar (for the removed `external-review` subcommand) and the `subagent_profile` scalar (applied to all review subagents) are replaced by `subcommands` — a per-subcommand map. `external_review_model` is simply removed (the subcommand no longer exists); `subagent_profile` migrates to the 6 review subcommand entries. Setup migrates automatically — see `skills/zolletta-metaskill-setup/SUBSKILL.md` → "Step 0 — Migration and missing-keys backfill".
>
> **v3.0.0 backfill**: `python.paths`, `python.patterns`, `php.patterns`, and the new `code_style`/`testing`/`documentation` keys are added to existing settings.json files on the next setup run — additive only, user-customized values are preserved.

## `documentation` — documentation configuration

| Field                                    | Type           | Default                                                       | Description                                                                                                                                                     |
|------------------------------------------|----------------|---------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `documentation.language`                 | string         | `"en"`                                                        | ISO 639-1 code for documentation language. When not `"en"`, the `documentor` skill translates Diátaxis signpost headings before running the staleness scorer    |
| `documentation.dir`                      | string         | `"docs"`                                                      | Directory where project documentation lives. Used by the `documentor` skill to locate the Diátaxis docs tree for drift detection and staleness scoring          |
| `documentation.adrs`                     | string \| null | `null`                                                        | Relative path within `documentation.dir` where ADRs live (e.g. `"adr"`), `""` if scattered in docs root, or `null` if no ADRs found. Auto-detected during setup |
| `documentation.min_severity`             | string         | `"high"`                                                      | Minimum severity reported by `drift_analyzer.py` (`critical`, `high`, `medium`, `low`, `info`)                                                                  |
| `documentation.staleness_threshold`      | number \| null | `null`                                                        | If set, `doc_staleness_scorer.py` exits 1 when the freshness score falls below this value (0–100). `null` = report-only                                         |
| `documentation.readme_focus`             | boolean        | `false`                                                       | When `true`, `doc_staleness_scorer.py` only scores the README                                                                                                   |
| `documentation.readme_sections`          | array          | `["installation", "usage", "api", "contributing", "license"]` | Section names a README is expected to contain (completeness dimension of `doc_staleness_scorer.py`)                                                             |
| `documentation.diataxis_translations`    | string \| null | `null`                                                        | Path to a JSON file mapping Diátaxis signpost headings to translations. `null` = built-in translations                                                          |
| `documentation.staleness_weights`        | object \| null | `null`                                                        | Custom dimension weights for `doc_staleness_scorer.py` (`last_updated`, `code_doc_alignment`, `link_health`, `completeness`, `accuracy`; normalized to sum 1.0) |
| `documentation.doc_patterns`             | array          | `["*.md", "*.rst", "*.txt", "*.adoc"]`                        | Glob patterns for documentation files scanned by `drift_analyzer.py`                                                                                            |
| `documentation.check_external`           | boolean        | `false`                                                       | When `true`, `link_checker.py` verifies external http(s) links too                                                                                              |
| `documentation.include_referential`      | boolean        | `false`                                                       | When `true`, `drift_analyzer.py` also reports referential drift, not just broken links                                                                          |
| `documentation.api_doc_recursive`        | boolean        | `true`                                                        | When `true`, `api_doc_validator.py` scans source roots recursively                                                                                              |
| `documentation.api_doc_include_private`  | boolean        | `false`                                                       | When `true`, `api_doc_validator.py` also checks private/underscore modules                                                                                      |
| `documentation.api_doc_suggest_coverage` | boolean        | `false`                                                       | When `true`, `api_doc_validator.py` suggests a documentation coverage target                                                                                    |

## `python` — tooling, rules, and configuration

The `python` object merges four concerns into one place: tool availability and configuration (`tools`), the project layout (`paths`), configurable rule toggles (`code_style`, `testing`, `patterns`), and `pyproject_mtime` for staleness detection. It is `null` for non-Python projects.

### `python.paths` — source/test layout

The source and test roots every review script scans — the equivalent of what PHP projects get via `composer.json` `autoload` mappings. Detected by `python_paths_detector.py` during setup (Step 8) from `pyproject.toml` build config (`[tool.hatch.build.targets.wheel] packages`, `[tool.setuptools] package-dir`/`packages.find where`, `[tool.poetry] packages`), pytest `testpaths`, and the directory layout.

| Field                  | Type           | Default     | Description                                                                                        |
|------------------------|----------------|-------------|----------------------------------------------------------------------------------------------------|
| `python.paths.source`  | array          | `["src"]`   | Source roots scanned by every source scanner                                                       |
| `python.paths.tests`   | array          | `["tests"]` | Test roots scanned by test scanners (test_naming, test_structure, test_god_classes, test_splitter) |
| `python.paths.package` | string \| null | `null`      | Top-level package name used by mirror-structure checks (`naming_conventions`, `test_structure`)    |

### `python.tools` — tool availability and configuration

Each tool is an object with an `available` boolean. Tools that have configuration (ruff, mypy, ty, pytest) also carry their effective config extracted from `pyproject.toml`. When a tool's `[tool.*]` section is absent, setup stores the tool's **real built-in defaults** (not skill-invented fallbacks) and prints an "unconfigured" warning.

| Field                  | Type   | Description                                                                                                                            |
|------------------------|--------|----------------------------------------------------------------------------------------------------------------------------------------|
| `python.tools.uv`      | object | `{ "available": boolean }` — uv has no config beyond availability                                                                      |
| `python.tools.ruff`    | object | `{ "available": boolean, "line_length": integer, "target_version": string, "select": array, "ignore": array }` — effective ruff config |
| `python.tools.pytest`  | object | `{ "available": boolean, "addopts": array, "testpaths": array, "minversion": string or null }` — effective pytest config               |
| `python.tools.ty`      | object | `{ "available": boolean, "python_version": string or null }` — effective ty config                                                     |
| `python.tools.vulture` | object | `{ "available": boolean }` — vulture has no config beyond availability                                                                 |
| `python.tools.mypy`    | object | `{ "available": boolean, "strict": boolean, "python_version": string or null }` — effective mypy config                                |

> **Type checker resolution**: there is no `type_checker` field. Review skills run all available type checkers: `ty` if `python.tools.ty.available` is `true`, `mypy` if `python.tools.mypy.available` is `true`. When both are available, both run. If neither is available, type checking is skipped.

### `python.code_style` — configurable rule toggles

These control which checks the `python-code-style` skill enforces. All default to `true` (or `80` for the confidence threshold). Set to `false` to disable a check for the project.

| Key                              | Type    | Default | Area       | Rule                                                                                                                                 |
|----------------------------------|---------|---------|------------|--------------------------------------------------------------------------------------------------------------------------------------|
| `check_acronym_casing`           | boolean | `true`  | Naming     | Acronyms stay uppercase in class names (`HTTPClientFactory`)                                                                         |
| `check_no_relative_imports`      | boolean | `true`  | Imports    | Absolute imports only, no relative imports                                                                                           |
| `check_one_class_per_file`       | boolean | `true`  | Structure  | One class per file (all classes, not just public)                                                                                    |
| `check_one_class_per_test_file`  | boolean | `true`  | Structure  | `one_class_per_file_scanner` also scans test roots: one test class per test file, named after its stem (`test_user.py` → `TestUser`) |
| `check_zero_class_files`         | boolean | `true`  | Structure  | Report files with 0 classes (utility/helper modules). Set `false` to hide them — replaces the removed `--ignore-zero` flag           |
| `check_filename_matches_class`   | boolean | `true`  | Structure  | Filename matches class name (`snake_case.py` → `PascalCase`)                                                                         |
| `check_public_docstrings`        | boolean | `true`  | Docstrings | Docstrings required on public classes, methods, functions                                                                            |
| `check_docstring_no_type_repeat` | boolean | `true`  | Docstrings | No type repetition in docstring Args/Returns                                                                                         |
| `check_skip_obvious_docstrings`  | boolean | `true`  | Docstrings | Skip docstrings for obvious one-line functions                                                                                       |
| `check_line_length`              | boolean | `true`  | Formatting | Line length from `python.tools.ruff.line_length`                                                                                     |
| `check_file_length`              | boolean | `true`  | Structure  | Files must not exceed `max_file_length` lines                                                                                        |
| `check_unused_all_exports`       | boolean | `true`  | Dead code  | `__all__` entries must be used outside their module (`unused_all_exports_scanner.py`)                                                |
| `docstring_strip_private`        | boolean | `false` | Docstrings | `docstring_streamliner.py` removes private-function docstrings when applying fixes                                                   |
| `docstring_strip_tests`          | boolean | `false` | Docstrings | `docstring_streamliner.py` removes test-function docstrings when applying fixes                                                      |
| `docstring_strip_nested`         | boolean | `false` | Docstrings | `docstring_streamliner.py` removes nested-function docstrings when applying fixes                                                    |
| `docstring_strip_obvious_init`   | boolean | `false` | Docstrings | `docstring_streamliner.py` removes obvious `__init__` docstrings when applying fixes                                                 |
| `max_file_length`                | integer | `800`   | Structure  | Maximum allowed lines per file (enforced by `file_length_scanner.py`)                                                                |
| `vulture_min_confidence`         | integer | `80`    | Dead code  | Minimum confidence for vulture findings (0–100)                                                                                      |

> Rules not listed here (naming conventions, import order, private/test function docstring exemptions, type hints for public APIs) are **always-on** and cannot be disabled. See `skills/zolletta-metaskill-python-code-style/SUBSKILL.md` → Table 1 for the full list.

### `python.testing` — configurable rule toggles

These control which checks the `python-testing-style` skill enforces and the coverage thresholds it uses.

| Key                               | Type    | Default | Area     | Rule                                                                                            |
|-----------------------------------|---------|---------|----------|-------------------------------------------------------------------------------------------------|
| `coverage_gap_threshold`          | integer | `50`    | Coverage | Coverage below this % is a gap (0–100)                                                          |
| `coverage_well_covered_threshold` | integer | `80`    | Coverage | Coverage above this % is well-covered — do not flag (0–100)                                     |
| `check_test_naming`               | boolean | `true`  | Naming   | Test naming convention (`test_<unit>_<scenario>_<expected>`)                                    |
| `test_naming_min_segments`        | integer | `3`     | Naming   | Minimum underscore-separated segments a test function name must have (`test_naming_scanner.py`) |

> Rules not listed here (AAA structure, test isolation, mandatory coverage gap detection, scope boundary with `patterns`) are **always-on** and cannot be disabled. See `skills/zolletta-metaskill-python-testing-style/SUBSKILL.md` → "Always-on rules" for the full list.

### `python.patterns` — SOLID/pattern scanner configuration

These control which checks the `patterns` skill's deterministic scanners run for Python, and their thresholds. All `check_*` toggles default to `true`.

| Key                       | Type    | Default                                                                                 | Rule                                                                                               |
|---------------------------|---------|-----------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| `check_ocp`               | boolean | `true`                                                                                  | Open/closed: flag if/elif chains that should be polymorphic (`open_closed_scanner.py`)             |
| `check_isp`               | boolean | `true`                                                                                  | Interface segregation: flag fat interfaces (`interface_segregation_scanner.py`)                    |
| `check_dip`               | boolean | `true`                                                                                  | Dependency inversion: flag high-level modules importing low-level concretions                      |
| `check_lsp`               | boolean | `true`                                                                                  | Liskov substitution: flag subclasses that break the parent contract                                |
| `check_test_structure`    | boolean | `true`                                                                                  | Test tree mirrors the source tree (`test_structure_scanner.py`)                                    |
| `ocp_min_branches`        | integer | `3`                                                                                     | Minimum branches in an if/elif chain before `open_closed_scanner.py` flags it                      |
| `isp_min_methods`         | integer | `5`                                                                                     | Minimum methods on an interface/class before `interface_segregation_scanner.py` flags it           |
| `dip_entry_points`        | array   | `["main", "cli", "app", "__main__", "myproject", "manage", "wsgi", "asgi", "conftest"]` | Module names treated as composition roots — exempt from `dependency_inversion_scanner.py` findings |
| `class_metrics_top`       | integer | `30`                                                                                    | How many largest classes `class_metrics_scanner.py` reports                                        |
| `class_metrics_min_lines` | integer | `50`                                                                                    | Minimum class size (lines) `class_metrics_scanner.py` reports                                      |
| `test_god_classes_top`    | integer | `30`                                                                                    | How many largest test classes `test_god_classes_scanner.py` reports                                |

### `python.pyproject_mtime` — staleness detection

Modification time of `pyproject.toml` at last extraction (Unix timestamp). The setup guard uses it to detect staleness and trigger a light refresh.

## `php` — tooling, rules, and configuration

The `php` object mirrors the `python` object and merges the same concerns: tool availability and configuration (`tools`), configurable rule toggles (`code_style`, `testing`, `patterns`), autoload mapping (`autoload` — the source/test roots, so no `php.paths` exists), the minimum PHP version (`php_version`), and `composer_mtime` for staleness detection. It is `null` for non-PHP projects.

### `php.tools` — tool availability and configuration

Each tool is an object with an `available` boolean. Tools that have configuration (phpunit, phpstan, psalm, phpcs) also carry their effective config extracted from `composer.json` and the tool's config file. When a tool's config file is absent, setup stores the tool's **real built-in defaults** (not skill-invented fallbacks) and prints an "unconfigured" warning. The `php_cs_fixer` config file is executable PHP code and is not parsed by setup — the `php-code-style` skill reads it at review time if needed.

| Field                    | Type   | Description                                                                                                                                                             |
|--------------------------|--------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `php.tools.phpunit`      | object | `{ "available": boolean, "bootstrap": string or null, "testpaths": array, "coverage_config": boolean or null }` — effective phpunit config extracted from `phpunit.xml` |
| `php.tools.phpstan`      | object | `{ "available": boolean, "level": integer or null, "paths": array, "memory_limit": string or null }` — effective phpstan config extracted from `phpstan.neon`           |
| `php.tools.psalm`        | object | `{ "available": boolean, "error_level": integer or null, "paths": array }` — effective psalm config extracted from `psalm.xml`                                          |
| `php.tools.php_cs_fixer` | object | `{ "available": boolean, "config_file": boolean }` — `config_file` is `true` if `.php-cs-fixer.php` or `.php-cs-fixer.dist.php` exists                                  |
| `php.tools.phpcs`        | object | `{ "available": boolean, "standard": string or null }` — effective phpcs config extracted from `.phpcs.xml` or `phpcs.xml.dist`                                         |

> **Static analysis resolution**: there is no `static_analyser` field. Review skills run all available static analysers: `phpstan` if `php.tools.phpstan.available` is `true`, `psalm` if `php.tools.psalm.available` is `true`. When both are available, both run. If neither is available, static analysis is skipped.

### `php.code_style` — configurable rule toggles

These control which checks the `php-code-style` skill enforces. All default to `true`. Set to `false` to disable a check for the project. Rules whose minimum PHP version is higher than the detected `php_version` are silently skipped (not flagged) — the skill prints a note listing which rules were skipped.

| Key                           | Type    | Default | Area        | Rule                                                                  | Min PHP |
|-------------------------------|---------|---------|-------------|-----------------------------------------------------------------------|---------|
| `check_acronym_casing`        | boolean | `true`  | Naming      | Acronyms stay uppercase in class names (`HTTPClientFactory`)          | all     |
| `check_union_types`           | boolean | `true`  | Types       | Union types declared where multiple types are possible                | 8.0+    |
| `check_intersection_types`    | boolean | `true`  | Types       | Intersection types for interface composition                          | 8.1+    |
| `check_enum_methods`          | boolean | `true`  | Modern      | Enums with methods instead of class constants for finite sets         | 8.1+    |
| `check_first_class_callables` | boolean | `true`  | Modern      | First-class callable syntax (`$obj->method(...)`)                     | 8.1+    |
| `check_readonly_classes`      | boolean | `true`  | Modern      | Readonly classes for immutable data                                   | 8.2+    |
| `check_typed_constants`       | boolean | `true`  | Modern      | Typed class constants                                                 | 8.3+    |
| `check_override_attribute`    | boolean | `true`  | Modern      | `#[\Override]` attribute on overriding methods                        | 8.3+    |
| `check_property_hooks`        | boolean | `true`  | Modern      | Property hooks for computed properties                                | 8.4+    |
| `check_asymmetric_visibility` | boolean | `true`  | Modern      | Asymmetric visibility (`public-read protected-set`)                   | 8.4+    |
| `check_pipe_operator`         | boolean | `true`  | Modern      | Pipe operator (`\|>`) for function composition                        | 8.5+    |
| `check_array_functions`       | boolean | `true`  | Performance | Use native array functions over manual loops                          | all     |
| `check_string_functions`      | boolean | `true`  | Performance | Use native string functions over regex                                | all     |
| `check_file_length`           | boolean | `true`  | Structure   | Files must not exceed `max_file_length` lines                         | all     |
| `max_file_length`             | integer | `800`   | Structure   | Maximum allowed lines per file (enforced by `file_length_scanner.py`) | all     |

> Rules not listed here (`declare(strict_types=1)`, return/parameter/property type declarations, nullable types, `void`/`never`, avoid `mixed`, constructor promotion, match expression, nullsafe operator, named arguments, attributes, enums, readonly properties, arrow functions, PSR-4 autoloading, PSR-12 coding style, camelCase methods, namespace usage, no `@` suppression, file upload validation) are **always-on** and cannot be disabled. See `skills/zolletta-metaskill-php-code-style/SUBSKILL.md` → "Always-on rules" for the full list.

### `php.testing` — configurable rule toggles

These control which checks the `php-testing-style` skill enforces and the coverage thresholds it uses.

| Key                               | Type    | Default | Area     | Rule                                                                     |
|-----------------------------------|---------|---------|----------|--------------------------------------------------------------------------|
| `coverage_gap_threshold`          | integer | `50`    | Coverage | Coverage below this % is a gap (0–100)                                   |
| `coverage_well_covered_threshold` | integer | `80`    | Coverage | Coverage above this % is well-covered — do not flag (0–100)              |
| `check_test_naming`               | boolean | `true`  | Naming   | PHPUnit test naming convention (`*Test.php`, methods start with `test_`) |

> Rules not listed here (one test class per SUT, test directory mirroring per PSR-4, mandatory coverage gap detection, scope boundary with `patterns`) are **always-on** and cannot be disabled. See `skills/zolletta-metaskill-php-testing-style/SUBSKILL.md` → "Always-on rules" for the full list.

### `php.patterns` — SOLID scanner configuration

Same role as `python.patterns` for the PHP SOLID scanners. PHP has no `check_lsp`/`check_test_structure` (no PHP LSP or mirror-structure scanner) and the ISP threshold defaults to 7.

| Key                | Type    | Default | Rule                                                                                     |
|--------------------|---------|---------|------------------------------------------------------------------------------------------|
| `check_ocp`        | boolean | `true`  | Open/closed: flag if/elseif chains that should be polymorphic                            |
| `check_isp`        | boolean | `true`  | Interface segregation: flag fat interfaces                                               |
| `check_dip`        | boolean | `true`  | Dependency inversion: flag high-level modules depending on low-level concretions         |
| `ocp_min_branches` | integer | `3`     | Minimum branches in an if/elseif chain before `open_closed_scanner.py` flags it          |
| `isp_min_methods`  | integer | `7`     | Minimum methods on an interface/class before `interface_segregation_scanner.py` flags it |

### `php.autoload` — PSR-4 namespace mapping

PSR-4 namespace → directory mapping extracted from `composer.json`. The `php-code-style` and `php-testing-style` skills use this to resolve namespaces to directories (equivalent to how Python skills use `[tool.hatch.build.targets.wheel] packages`).

| Field                    | Type   | Description                                                                                                                         |
|--------------------------|--------|-------------------------------------------------------------------------------------------------------------------------------------|
| `php.autoload.psr-4`     | object | Production namespace → directory mapping from `composer.json` `autoload.psr-4` (e.g. `{"App\\": "src/"}`). Empty object if absent   |
| `php.autoload.psr-4-dev` | object | Test namespace → directory mapping from `composer.json` `autoload-dev.psr-4` (e.g. `{"Tests\\": "tests/"}`). Empty object if absent |

### `php.php_version` — minimum PHP version

Minimum PHP version extracted from `composer.json` `require.php` (e.g. `">=8.2"` → `"8.2"`). Stored as a string. `null` if `require.php` is absent — in that case review skills cannot assume a specific PHP version and version-gated rules are skipped.

### `php.composer_mtime` — staleness detection

Modification time of `composer.json` at last extraction (Unix timestamp). The setup guard uses it to detect staleness and trigger a light refresh.

## Setup guard staleness check

### Python branch

When `settings.json` exists and the project is Python, the setup guard compares `pyproject.toml`'s current modification time against `python.pyproject_mtime`. If they differ, the guard re-runs **only** the pyproject extraction + source layout steps (Steps 7–8 of setup) and patches the `python.tools.*` configuration fields + `python.paths` + `python.pyproject_mtime` in `settings.json`. Full setup (language detection, Docker probe, tokensave probe) is not re-run.

### PHP branch

When `settings.json` exists and `php` is not `null`, the setup guard compares `composer.json`'s current modification time against `php.composer_mtime`. If they differ, the guard re-runs **only** the composer.json + tool config extraction step (Step 12 of setup) and patches the `php.tools.*` configuration fields + `php.autoload` + `php.php_version` + `php.composer_mtime` in `settings.json`. Full setup (language detection, Docker probe, tokensave probe) is not re-run. If `composer.json` does not exist or `php` is `null`, this check is skipped.

## Tool-failure handler

If any subcommand calls a tokensave MCP tool and receives a tool-not-found / server-not-found error, it:

1. Updates `tokensave_available` in `settings.json` to `false`
2. Prints the "not installed" message from `tool-messages.md`
3. Continues with grep + targeted reads as fallback

Python skills (`python-code-style`, `python-testing-style`) and PHP skills (`php-code-style`, `php-testing-style`) are bundled inside this meta-skill and are always available — the "not found" case does not apply to them.

---

[← Back to README](../../README.md)
