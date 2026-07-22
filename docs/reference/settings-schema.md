---
audience: human, ai
status: stable
skills:
  [setup, review, patterns, documentor, external-review, python-code-style, python-testing-patterns]
---

# settings.json schema

[← Back to README](../../README.md)

`.zolletta-metaskill/settings.json` is created by `/zolletta-metaskill setup` and read by every other subcommand. This page documents every field.

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
      "uv": true,
      "ruff": true,
      "pytest": true,
      "ty": true,
      "vulture": true,
      "mypy": true
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
  "external_review_model": "swe",
  "documentation": {
    "language": "en",
    "dir": "docs"
  },
  "reports_dir": ".zolletta-metaskill/reports"
}
```

## Top-level fields

| Field | Type | Description |
| --- | --- | --- |
| `setup_version` | string | Matches the skill version that wrote the file |
| `setup_timestamp` | string (ISO 8601) | Timestamp of the last setup run |
| `language` | string | Detected project language (`python`, `php`, `go`, `rust`, etc.) |
| `container_name` | string \| null | Docker container name for running tools (`null` if no Docker) |
| `tokensave_available` | boolean | `true` if `tokensave_status` responds (probed directly) |
| `acronyms` | array | Project-specific acronyms that must stay uppercase in class names (e.g. `["CITE"]`). Extracted from `AGENTS.md` during setup; merged with the built-in list by `scan_acronym_casing.py`. Always present, even for non-Python projects |
| `python` | object \| null | Python tooling, rule toggles, and effective tool configuration (Python only; `null` otherwise) — see below |
| `external_review_model` | string | Default model for `external-review` (overridable by front-matter) |
| `documentation` | object | Documentation configuration — see below |
| `reports_dir` | string | Directory where review reports are saved |

## `documentation` — documentation configuration

| Field | Type | Description |
| --- | --- | --- |
| `documentation.language` | string | ISO 639-1 code for documentation language (default: `"en"`). When not `"en"`, the `documentor` skill translates Diátaxis signpost headings before running the staleness scorer |
| `documentation.dir` | string | Directory where project documentation lives (default: `"docs"`). Used by the `documentor` skill to locate the Diátaxis docs tree for drift detection and staleness scoring |

## `python` — tooling, rules, and configuration

The `python` object merges three concerns into one place: tool availability (`tools`), configurable rule toggles (`code_style`, `testing`), and the effective tool configuration extracted from `pyproject.toml` (the remaining fields). It is `null` for non-Python projects.

### `python.tools` — tool availability

| Field                  | Type    | Description                    |
| ---------------------- | ------- | ------------------------------ |
| `python.tools.uv`      | boolean | `true` if uv is available      |
| `python.tools.ruff`    | boolean | `true` if ruff is available    |
| `python.tools.pytest`  | boolean | `true` if pytest is available  |
| `python.tools.ty`      | boolean | `true` if ty is available      |
| `python.tools.vulture` | boolean | `true` if vulture is available |
| `python.tools.mypy`    | boolean | `true` if mypy is available    |

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
| `check_line_length` | boolean | `true` | Formatting | Line length from `python.line_length` |
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

### `python.*` — effective tool configuration

Extracted by setup from `pyproject.toml`. When a tool's `[tool.*]` section is absent, setup stores the tool's **real built-in defaults** (not skill-invented fallbacks) and prints an "unconfigured" warning. The `pyproject_mtime` field records when `pyproject.toml` was last read — the setup guard uses it to detect staleness and trigger a light refresh.

| Field | Type | Description |
| --- | --- | --- |
| `python.pyproject_mtime` | float | Modification time of `pyproject.toml` at last extraction (Unix timestamp) |
| `python.line_length` | integer | Effective line length (from `[tool.ruff] line-length`, or ruff's default `88` if unconfigured) |
| `python.target_version` | string | Effective target Python version (from `[tool.ruff] target-version`, or ruff's default `"py310"`) |
| `python.type_checker` | string \| null | Which type checker to use: `"ty"` or `"mypy"` (resolved from config, then availability); `null` if neither |
| `python.ruff` | object | Effective ruff config: `select` (array), `ignore` (array) |
| `python.mypy` | object | Effective mypy config: `strict` (bool), `python_version` (string \| null) |
| `python.ty` | object | Effective ty config: `python_version` (string \| null) |
| `python.pytest` | object | Effective pytest config: `addopts` (array), `testpaths` (array), `minversion` (string \| null) |

## Setup guard staleness check

When `settings.json` exists and the project is Python, the setup guard compares `pyproject.toml`'s current modification time against `python.pyproject_mtime`. If they differ, the guard re-runs **only** the pyproject extraction step (Step 6.5 of setup) and patches the `python.*` configuration fields + `python.pyproject_mtime` in `settings.json`. Full setup (language detection, Docker probe, tokensave probe) is not re-run.

## Tool-failure handler

If any subcommand calls a tokensave MCP tool and receives a tool-not-found / server-not-found error, it:

1. Updates `tokensave_available` in `settings.json` to `false`
2. Prints the "not installed" message from `tool-messages.md`
3. Continues with grep + targeted reads as fallback

Python skills (`python-code-style`, `python-testing-patterns`) are bundled inside this meta-skill and are always available — the "not found" case does not apply to them.

---

[← Back to README](../../README.md)
