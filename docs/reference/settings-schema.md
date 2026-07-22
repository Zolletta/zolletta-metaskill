---
audience: human, ai
status: stable
skills: [setup, review, patterns, documentor, external-review, python-code-style, python-testing-patterns]
---

# settings.json schema

[← Back to README](../../README.md)

`.zolletta-metaskill/settings.json` is created by `/zolletta-metaskill setup` and read by every other subcommand. This page documents every field.

## Example (Python project)

```json
{
  "setup_version": "1.0.0",
  "setup_timestamp": "2026-07-16T14:30:00",
  "language": "python",
  "container_name": "myproject",
  "tokensave_available": true,
  "python": {
    "uv": true,
    "ruff": true,
    "pytest": true,
    "ty": true,
    "vulture": true,
    "mypy": true
  },
  "python_config": {
    "pyproject_mtime": 1784223225.47,
    "line_length": 100,
    "target_version": "py312",
    "type_checker": "ty",
    "ruff": {
      "select": ["E", "W", "F", "I", "B", "C4", "D", "UP", "T20", "SIM"],
      "ignore": ["B008", "T201", "D104", "D107", "D203", "D213"]
    },
    "mypy": {
      "strict": true,
      "python_version": "3.12"
    },
    "ty": {
      "python_version": "3.12"
    },
    "pytest": {
      "addopts": ["-ra", "--tb=short"],
      "testpaths": ["tests"],
      "minversion": "8.0"
    }
  },
  "python_code_style_available": true,
  "python_testing_patterns_available": true,
  "python_code_style_rules": {
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
  "python_testing_patterns_rules": {
    "coverage_gap_threshold": 50,
    "coverage_well_covered_threshold": 80,
    "check_test_naming": true
  },
  "external_review_model": "swe",
  "documentation_language": "en",
  "documentation_directory": "docs/",
  "reports_dir": ".zolletta-metaskill/reports"
}
```

## Top-level fields

| Field                               | Type              | Description                                                                                                                                                                    |
| ----------------------------------- | ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `setup_version`                     | string            | Matches the skill version that wrote the file                                                                                                                                  |
| `setup_timestamp`                   | string (ISO 8601) | Timestamp of the last setup run                                                                                                                                                |
| `language`                          | string            | Detected project language (`python`, `php`, `go`, `rust`, etc.)                                                                                                                |
| `container_name`                    | string \| null    | Docker container name for running tools (`null` if no Docker)                                                                                                                  |
| `tokensave_available`               | boolean           | `true` if `tokensave_status` responds (probed directly)                                                                                                                        |
| `python`                            | object \| null    | Tool availability flags (Python only; `null` otherwise) — see below                                                                                                            |
| `python_config`                     | object \| null    | Effective tool configuration extracted from `pyproject.toml` (Python only; `null` otherwise) — see below                                                                       |
| `python_code_style_available`       | boolean           | `true` for Python projects (skill is bundled)                                                                                                                                  |
| `python_testing_patterns_available` | boolean           | `true` for Python projects (skill is bundled)                                                                                                                                  |
| `python_code_style_rules`           | object            | Configurable rule toggles for the `python-code-style` skill — see below                                                                                                        |
| `python_testing_patterns_rules`     | object            | Configurable rule toggles for the `python-testing-patterns` skill — see below                                                                                                  |
| `external_review_model`             | string            | Default model for `external-review` (overridable by front-matter)                                                                                                              |
| `documentation_language`            | string            | ISO 639-1 code for documentation language (default: `"en"`). When not `"en"`, the `documentor` skill translates Diátaxis signpost headings before running the staleness scorer |
| `documentation_directory`           | string            | Directory where project documentation lives (default: `"docs/"`). Used by the `documentor` skill to locate the Diátaxis docs tree for drift detection and staleness scoring     |
| `reports_dir`                       | string            | Directory where review reports are saved                                                                                                                                       |

## `python` — tool availability

| Field            | Type    | Description                    |
| ---------------- | ------- | ------------------------------ |
| `python.uv`      | boolean | `true` if uv is available      |
| `python.ruff`    | boolean | `true` if ruff is available    |
| `python.pytest`  | boolean | `true` if pytest is available  |
| `python.ty`      | boolean | `true` if ty is available      |
| `python.vulture` | boolean | `true` if vulture is available |
| `python.mypy`    | boolean | `true` if mypy is available    |

## `python_config` — effective tool configuration

Extracted by setup from `pyproject.toml`. When a tool's `[tool.*]` section is absent, setup stores the tool's **real built-in defaults** (not skill-invented fallbacks) and prints an "unconfigured" warning. The `pyproject_mtime` field records when `pyproject.toml` was last read — the setup guard uses it to detect staleness and trigger a light refresh.

| Field             | Type           | Description                                                                                                |
| ----------------- | -------------- | ---------------------------------------------------------------------------------------------------------- |
| `pyproject_mtime` | float          | Modification time of `pyproject.toml` at last extraction (Unix timestamp)                                  |
| `line_length`     | integer        | Effective line length (from `[tool.ruff] line-length`, or ruff's default `88` if unconfigured)             |
| `target_version`  | string         | Effective target Python version (from `[tool.ruff] target-version`, or ruff's default `"py310"`)           |
| `type_checker`    | string \| null | Which type checker to use: `"ty"` or `"mypy"` (resolved from config, then availability); `null` if neither |
| `ruff`            | object         | Effective ruff config: `select` (array), `ignore` (array)                                                  |
| `mypy`            | object         | Effective mypy config: `strict` (bool), `python_version` (string \| null)                                  |
| `ty`              | object         | Effective ty config: `python_version` (string \| null)                                                     |
| `pytest`          | object         | Effective pytest config: `addopts` (array), `testpaths` (array), `minversion` (string \| null)             |

## `python_code_style_rules` — configurable rule toggles

These control which checks the `python-code-style` skill enforces. All default to `true` (or `80` for the confidence threshold). Set to `false` to disable a check for the project.

| Key                              | Type    | Default | Area       | Rule                                                         |
| -------------------------------- | ------- | ------- | ---------- | ------------------------------------------------------------ |
| `check_acronym_casing`           | boolean | `true`  | Naming     | Acronyms stay uppercase in class names (`HTTPClientFactory`) |
| `check_no_relative_imports`      | boolean | `true`  | Imports    | Absolute imports only, no relative imports                   |
| `check_one_class_per_file`       | boolean | `true`  | Structure  | One class per file (all classes, not just public)            |
| `check_filename_matches_class`   | boolean | `true`  | Structure  | Filename matches class name (`snake_case.py` → `PascalCase`) |
| `check_public_docstrings`        | boolean | `true`  | Docstrings | Docstrings required on public classes, methods, functions    |
| `check_docstring_no_type_repeat` | boolean | `true`  | Docstrings | No type repetition in docstring Args/Returns                 |
| `check_skip_obvious_docstrings`  | boolean | `true`  | Docstrings | Skip docstrings for obvious one-line functions               |
| `check_line_length`              | boolean | `true`  | Formatting | Line length from `python_config.line_length`                 |
| `vulture_min_confidence`         | integer | `80`    | Dead code  | Minimum confidence for vulture findings (0–100)              |

> Rules not listed here (naming conventions, import order, private/test function docstring exemptions, type hints for public APIs) are **always-on** and cannot be disabled. See `python-code-style/SKILL.md` → Table 1 for the full list.

## `python_testing_patterns_rules` — configurable rule toggles

These control which checks the `python-testing-patterns` skill enforces and the coverage thresholds it uses.

| Key                               | Type    | Default | Area     | Rule                                                         |
| --------------------------------- | ------- | ------- | -------- | ------------------------------------------------------------ |
| `coverage_gap_threshold`          | integer | `50`    | Coverage | Coverage below this % is a gap (0–100)                       |
| `coverage_well_covered_threshold` | integer | `80`    | Coverage | Coverage above this % is well-covered — do not flag (0–100)  |
| `check_test_naming`               | boolean | `true`  | Naming   | Test naming convention (`test_<unit>_<scenario>_<expected>`) |

> Rules not listed here (AAA structure, test isolation, mandatory coverage gap detection, scope boundary with `patterns`) are **always-on** and cannot be disabled. See `python-testing-patterns/SKILL.md` → "Always-on rules" for the full list.

## Setup guard staleness check

When `settings.json` exists and the project is Python, the setup guard compares `pyproject.toml`'s current modification time against `python_config.pyproject_mtime`. If they differ, the guard re-runs **only** the pyproject extraction step (Step 6.5 of setup) and patches `python_config` + `pyproject_mtime` in `settings.json`. Full setup (language detection, Docker probe, tokensave probe) is not re-run.

## Tool-failure handler

If any subcommand calls a tokensave MCP tool and receives a tool-not-found / server-not-found error, it:

1. Updates `tokensave_available` in `settings.json` to `false`
2. Prints the "not installed" message from `tool-messages.md`
3. Continues with grep + targeted reads as fallback

Python skills (`python-code-style`, `python-testing-patterns`) are bundled inside this meta-skill and are always available — the "not found" case does not apply to them.

---

[← Back to README](../../README.md)
