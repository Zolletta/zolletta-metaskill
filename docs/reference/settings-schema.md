---
audience: human, ai
status: stable
skills: [setup, review, patterns, documentor, external-review, python-*, php-*]
---

# settings.json schema

[← Back to README](../../README.md)

`.zolletta-metaskill/settings.json` is created by `/zolletta-metaskill setup` and read by every other subcommand. This page documents every field.

> **JSON Schema**: the machine-readable source of truth for the shape of `settings.json` lives at [`setup/assets/settings.schema.json`](../../setup/assets/settings.schema.json) (JSON Schema draft 2020-12). This prose doc is the human-readable counterpart and must stay in sync — when a field is added, removed, or renamed, update both files in the same change.

## Example (Python project)

```json
{
  "setup_version": "1.2.0",
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
    "code_style": {
      "check_acronym_casing": true,
      "check_no_relative_imports": true,
      "check_one_class_per_file": true,
      "check_filename_matches_class": true,
      "check_public_docstrings": true,
      "check_docstring_no_type_repeat": true,
      "check_skip_obvious_docstrings": true,
      "check_line_length": true,
      "vulture_min_confidence": 80
    },
    "testing": {
      "coverage_gap_threshold": 50,
      "coverage_well_covered_threshold": 80,
      "check_test_naming": true
    },
    "pyproject_mtime": 1784223225.47
  },
  "external_review_model": "swe",
  "documentation": {
    "language": "en",
    "dir": "docs"
  },
  "reports_dir": ".zolletta-metaskill/reports"
}
```

## Example (PHP project)

```json
{
  "setup_version": "1.3.0",
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
      "check_string_functions": true
    },
    "testing": {
      "coverage_gap_threshold": 50,
      "coverage_well_covered_threshold": 80,
      "check_test_naming": true
    },
    "autoload": {
      "psr-4": { "App\\": "src/" },
      "psr-4-dev": { "Tests\\": "tests/" }
    },
    "php_version": "8.2",
    "composer_mtime": 1718700000.0
  },
  "external_review_model": "swe",
  "documentation": {
    "language": "en",
    "dir": "docs"
  },
  "reports_dir": ".zolletta-metaskill/reports"
}
```

## Top-level fields

| Field | Type | Description |  |
| --- | --- | --- | --- |
| `setup_version` | string | Matches the skill version that wrote the file |  |
| `setup_timestamp` | string (ISO 8601) | Timestamp of the last setup run |  |
| `language` | string | Detected project language (`python`, `php`, `go`, `rust`, etc.) |  |
| `container_name` | string \  | null | Docker container name for running tools (`null` if no Docker) |
| `tokensave_available` | boolean | `true` if `tokensave_status` responds (probed directly) |  |
| `acronyms` | array | Project-specific acronyms that must stay uppercase in class names (e.g. `["CITE"]`). Extracted from `AGENTS.md` during setup; merged with the built-in list by `scan_acronym_casing.py`. Always present, even for non-Python projects |  |
| `python` | object \  | null | Python tooling, rule toggles, and effective tool configuration (Python only; `null` otherwise) — see below |
| `php` | object \  | null | PHP tooling, rule toggles, autoload mapping, and effective tool configuration (PHP only; `null` otherwise) — see below |
| `external_review_model` | string | Default model for `external-review` (overridable by front-matter) |  |
| `documentation` | object | Documentation configuration — see below |  |
| `reports_dir` | string | Directory where review reports are saved |  |

## `documentation` — documentation configuration

| Field | Type | Description |
| --- | --- | --- |
| `documentation.language` | string | ISO 639-1 code for documentation language (default: `"en"`). When not `"en"`, the `documentor` skill translates Diátaxis signpost headings before running the staleness scorer |
| `documentation.dir` | string | Directory where project documentation lives (default: `"docs"`). Used by the `documentor` skill to locate the Diátaxis docs tree for drift detection and staleness scoring |

## `python` — tooling, rules, and configuration

The `python` object merges three concerns into one place: tool availability and configuration (`tools`), configurable rule toggles (`code_style`, `testing`), and `pyproject_mtime` for staleness detection. It is `null` for non-Python projects.

### `python.tools` — tool availability and configuration

Each tool is an object with an `available` boolean. Tools that have configuration (ruff, mypy, ty, pytest) also carry their effective config extracted from `pyproject.toml`. When a tool's `[tool.*]` section is absent, setup stores the tool's **real built-in defaults** (not skill-invented fallbacks) and prints an "unconfigured" warning.

| Field | Type | Description |
| --- | --- | --- |
| `python.tools.uv` | object | `{ "available": boolean }` — uv has no config beyond availability |
| `python.tools.ruff` | object | `{ "available": boolean, "line_length": integer, "target_version": string, "select": array, "ignore": array }` — effective ruff config |
| `python.tools.pytest` | object | `{ "available": boolean, "addopts": array, "testpaths": array, "minversion": string or null }` — effective pytest config |
| `python.tools.ty` | object | `{ "available": boolean, "python_version": string or null }` — effective ty config |
| `python.tools.vulture` | object | `{ "available": boolean }` — vulture has no config beyond availability |
| `python.tools.mypy` | object | `{ "available": boolean, "strict": boolean, "python_version": string or null }` — effective mypy config |

> **Type checker resolution**: there is no `type_checker` field. Review skills run all available type checkers: `ty` if `python.tools.ty.available` is `true`, `mypy` if `python.tools.mypy.available` is `true`. When both are available, both run. If neither is available, type checking is skipped.

### `python.code_style` — configurable rule toggles

These control which checks the `python-code-style` skill enforces. All default to `true` (or `80` for the confidence threshold). Set to `false` to disable a check for the project.

| Key | Type | Default | Area | Rule |
| --- | --- | --- | --- | --- |
| `check_acronym_casing` | boolean | `true` | Naming | Acronyms stay uppercase in class names (`HTTPClientFactory`) |
| `check_no_relative_imports` | boolean | `true` | Imports | Absolute imports only, no relative imports |
| `check_one_class_per_file` | boolean | `true` | Structure | One class per file (all classes, not just public) |
| `check_filename_matches_class` | boolean | `true` | Structure | Filename matches class name (`snake_case.py` → `PascalCase`) |
| `check_public_docstrings` | boolean | `true` | Docstrings | Docstrings required on public classes, methods, functions |
| `check_docstring_no_type_repeat` | boolean | `true` | Docstrings | No type repetition in docstring Args/Returns |
| `check_skip_obvious_docstrings` | boolean | `true` | Docstrings | Skip docstrings for obvious one-line functions |
| `check_line_length` | boolean | `true` | Formatting | Line length from `python.tools.ruff.line_length` |
| `vulture_min_confidence` | integer | `80` | Dead code | Minimum confidence for vulture findings (0–100) |

> Rules not listed here (naming conventions, import order, private/test function docstring exemptions, type hints for public APIs) are **always-on** and cannot be disabled. See `python-code-style/SKILL.md` → Table 1 for the full list.

### `python.testing` — configurable rule toggles

These control which checks the `python-testing-patterns` skill enforces and the coverage thresholds it uses.

| Key | Type | Default | Area | Rule |
| --- | --- | --- | --- | --- |
| `coverage_gap_threshold` | integer | `50` | Coverage | Coverage below this % is a gap (0–100) |
| `coverage_well_covered_threshold` | integer | `80` | Coverage | Coverage above this % is well-covered — do not flag (0–100) |
| `check_test_naming` | boolean | `true` | Naming | Test naming convention (`test_<unit>_<scenario>_<expected>`) |

> Rules not listed here (AAA structure, test isolation, mandatory coverage gap detection, scope boundary with `patterns`) are **always-on** and cannot be disabled. See `python-testing-patterns/SKILL.md` → "Always-on rules" for the full list.

### `python.pyproject_mtime` — staleness detection

Modification time of `pyproject.toml` at last extraction (Unix timestamp). The setup guard uses it to detect staleness and trigger a light refresh.

## `php` — tooling, rules, and configuration

The `php` object mirrors the `python` object and merges the same concerns: tool availability and configuration (`tools`), configurable rule toggles (`code_style`, `testing`), autoload mapping (`autoload`), the minimum PHP version (`php_version`), and `composer_mtime` for staleness detection. It is `null` for non-PHP projects.

### `php.tools` — tool availability and configuration

Each tool is an object with an `available` boolean. Tools that have configuration (phpunit, phpstan, psalm, phpcs) also carry their effective config extracted from `composer.json` and the tool's config file. When a tool's config file is absent, setup stores the tool's **real built-in defaults** (not skill-invented fallbacks) and prints an "unconfigured" warning. The `php_cs_fixer` config file is executable PHP code and is not parsed by setup — the `php-code-style` skill reads it at review time if needed.

| Field | Type | Description |
| --- | --- | --- |
| `php.tools.phpunit` | object | `{ "available": boolean, "bootstrap": string or null, "testpaths": array, "coverage_config": boolean or null }` — effective phpunit config extracted from `phpunit.xml` |
| `php.tools.phpstan` | object | `{ "available": boolean, "level": integer or null, "paths": array, "memory_limit": string or null }` — effective phpstan config extracted from `phpstan.neon` |
| `php.tools.psalm` | object | `{ "available": boolean, "error_level": integer or null, "paths": array }` — effective psalm config extracted from `psalm.xml` |
| `php.tools.php_cs_fixer` | object | `{ "available": boolean, "config_file": boolean }` — `config_file` is `true` if `.php-cs-fixer.php` or `.php-cs-fixer.dist.php` exists |
| `php.tools.phpcs` | object | `{ "available": boolean, "standard": string or null }` — effective phpcs config extracted from `.phpcs.xml` or `phpcs.xml.dist` |

> **Static analysis resolution**: there is no `static_analyser` field. Review skills run all available static analysers: `phpstan` if `php.tools.phpstan.available` is `true`, `psalm` if `php.tools.psalm.available` is `true`. When both are available, both run. If neither is available, static analysis is skipped.

### `php.code_style` — configurable rule toggles

These control which checks the `php-code-style` skill enforces. All default to `true`. Set to `false` to disable a check for the project. Rules whose minimum PHP version is higher than the detected `php_version` are silently skipped (not flagged) — the skill prints a note listing which rules were skipped.

| Key | Type | Default | Area | Rule | Min PHP |
| --- | --- | --- | --- | --- | --- |
| `check_union_types` | boolean | `true` | Types | Union types declared where multiple types are possible | 8.0+ |
| `check_intersection_types` | boolean | `true` | Types | Intersection types for interface composition | 8.1+ |
| `check_enum_methods` | boolean | `true` | Modern | Enums with methods instead of class constants for finite sets | 8.1+ |
| `check_first_class_callables` | boolean | `true` | Modern | First-class callable syntax (`$obj->method(...)`) | 8.1+ |
| `check_readonly_classes` | boolean | `true` | Modern | Readonly classes for immutable data | 8.2+ |
| `check_typed_constants` | boolean | `true` | Modern | Typed class constants | 8.3+ |
| `check_override_attribute` | boolean | `true` | Modern | `#[\Override]` attribute on overriding methods | 8.3+ |
| `check_property_hooks` | boolean | `true` | Modern | Property hooks for computed properties | 8.4+ |
| `check_asymmetric_visibility` | boolean | `true` | Modern | Asymmetric visibility (`public-read protected-set`) | 8.4+ |
| `check_pipe_operator` | boolean | `true` | Modern | Pipe operator (`\|>`) for function composition | 8.5+ |
| `check_array_functions` | boolean | `true` | Performance | Use native array functions over manual loops | all |
| `check_string_functions` | boolean | `true` | Performance | Use native string functions over regex | all |

> Rules not listed here (`declare(strict_types=1)`, return/parameter/property type declarations, nullable types, `void`/`never`, avoid `mixed`, constructor promotion, match expression, nullsafe operator, named arguments, attributes, enums, readonly properties, arrow functions, PSR-4 autoloading, PSR-12 coding style, camelCase methods, namespace usage, no `@` suppression, file upload validation) are **always-on** and cannot be disabled. See `php-code-style/SKILL.md` → "Always-on rules" for the full list.

### `php.testing` — configurable rule toggles

These control which checks the `php-testing-patterns` skill enforces and the coverage thresholds it uses.

| Key | Type | Default | Area | Rule |
| --- | --- | --- | --- | --- |
| `coverage_gap_threshold` | integer | `50` | Coverage | Coverage below this % is a gap (0–100) |
| `coverage_well_covered_threshold` | integer | `80` | Coverage | Coverage above this % is well-covered — do not flag (0–100) |
| `check_test_naming` | boolean | `true` | Naming | PHPUnit test naming convention (`*Test.php`, methods start with `test_`) |

> Rules not listed here (one test class per SUT, test directory mirroring per PSR-4, mandatory coverage gap detection, scope boundary with `patterns`) are **always-on** and cannot be disabled. See `php-testing-patterns/SKILL.md` → "Always-on rules" for the full list.

### `php.autoload` — PSR-4 namespace mapping

PSR-4 namespace → directory mapping extracted from `composer.json`. The `php-code-style` and `php-testing-patterns` skills use this to resolve namespaces to directories (equivalent to how Python skills use `[tool.hatch.build.targets.wheel] packages`).

| Field | Type | Description |
| --- | --- | --- |
| `php.autoload.psr-4` | object | Production namespace → directory mapping from `composer.json` `autoload.psr-4` (e.g. `{"App\\": "src/"}`). Empty object if absent |
| `php.autoload.psr-4-dev` | object | Test namespace → directory mapping from `composer.json` `autoload-dev.psr-4` (e.g. `{"Tests\\": "tests/"}`). Empty object if absent |

### `php.php_version` — minimum PHP version

Minimum PHP version extracted from `composer.json` `require.php` (e.g. `">=8.2"` → `"8.2"`). Stored as a string. `null` if `require.php` is absent — in that case review skills cannot assume a specific PHP version and version-gated rules are skipped.

### `php.composer_mtime` — staleness detection

Modification time of `composer.json` at last extraction (Unix timestamp). The setup guard uses it to detect staleness and trigger a light refresh.

## Setup guard staleness check

### Python branch

When `settings.json` exists and the project is Python, the setup guard compares `pyproject.toml`'s current modification time against `python.pyproject_mtime`. If they differ, the guard re-runs **only** the pyproject extraction step (Step 6.5 of setup) and patches the `python.tools.*` configuration fields + `python.pyproject_mtime` in `settings.json`. Full setup (language detection, Docker probe, tokensave probe) is not re-run.

### PHP branch

When `settings.json` exists and `php` is not `null`, the setup guard compares `composer.json`'s current modification time against `php.composer_mtime`. If they differ, the guard re-runs **only** the composer.json + tool config extraction step (Step 7.5 of setup) and patches the `php.tools.*` configuration fields + `php.autoload` + `php.php_version` + `php.composer_mtime` in `settings.json`. Full setup (language detection, Docker probe, tokensave probe) is not re-run. If `composer.json` does not exist or `php` is `null`, this check is skipped.

## Tool-failure handler

If any subcommand calls a tokensave MCP tool and receives a tool-not-found / server-not-found error, it:

1. Updates `tokensave_available` in `settings.json` to `false`
2. Prints the "not installed" message from `tool-messages.md`
3. Continues with grep + targeted reads as fallback

Python skills (`python-code-style`, `python-testing-patterns`) and PHP skills (`php-code-style`, `php-testing-patterns`) are bundled inside this meta-skill and are always available — the "not found" case does not apply to them.

---

[← Back to README](../../README.md)
