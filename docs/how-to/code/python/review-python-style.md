---
audience: human, ai
status: stable
skills: [python-*]
---

# How to review Python code style

> **Paths in this document are relative to the Zolletta-MetaSkill project root.**

The `python-code-style` skill inspects Python source for naming conventions, import structure, docstring quality, type annotations, formatting, and dead code. This guide covers what the skill checks, how the rules are organized, and how we configure rule toggles for a project.

## Prerequisites

We need a Python project that has been set up with `/zolletta-metaskill setup`. Setup creates `.zolletta-metaskill/settings.json`, which the skill reads to determine tool availability, effective tool configuration, and rule toggles. The skill reads from the `python` object in `settings.json`: `python.tools.*` objects (each with an `available` boolean and, where applicable, the effective configuration extracted from `pyproject.toml` — ruff carries `line_length`, `target_version`, `select`, `ignore`; mypy carries `strict`, `python_version`; ty carries `python_version`; pytest carries `addopts`, `testpaths`, `minversion`), and `python.code_style` (boolean toggles and the vulture confidence threshold). Project-specific acronyms live in the top-level `acronyms` field. If `settings.json` is missing or these objects are absent, the skill cannot run — we should run setup first so the configuration is explicit and repeatable.

## What the skill checks

The skill runs a combination of automated tools and manual review checks across six areas.

### Linting and formatting (ruff)

If `python.tools.ruff.available` is `true` in `settings.json`, the skill runs `ruff check` for linting and `ruff format --check` for formatting. Ruff enforces the rule set configured in `python.tools.ruff.select` and `python.tools.ruff.ignore`. The skill does not carry its own ruff configuration — it reads everything from `settings.json`, which setup populated from `pyproject.toml`. Import grouping (stdlib, third-party, local) is enforced automatically when the ruff `I` (isort) rule is selected.

### Type checking (mypy or ty)

The skill runs all available type checkers to verify that all public APIs have type annotations. Run `ty` if `python.tools.ty.available` is `true` and `mypy` if `python.tools.mypy.available` is `true` — when both are available, both run. If neither is available, the type-checking step is skipped. Each type checker runs with `disallow_untyped_defs` or equivalent strictness, so missing annotations on public functions, methods, and classes are reported as findings.

### Dead code detection (vulture)

If `python.tools.vulture.available` is `true`, the skill runs `vulture src/ --min-confidence <threshold>` to detect unused code. The confidence threshold comes from `python.code_style.vulture_min_confidence` (default: `80`) — findings below that confidence are not reported. Vulture has known false positives, especially for dynamically-accessed methods, so each finding above the threshold is reviewed with judgment before being flagged. If `python.tools.vulture.available` is `false`, dead-code detection is skipped entirely. In addition to vulture, the skill runs a supplementary `src/zolletta_metaskill/python_code_style/scan_unused_all_exports.py` scanner that cross-references every `__all__` entry against actual imports across the source tree — vulture treats `__all__` entries as "used" and never flags unused exports, so this scanner closes that gap.

### Naming conventions

The skill checks naming conventions across filenames, classes, functions, variables, and module-level constants. Filenames must be descriptive `snake_case` with no abbreviations (`user_repository.py`, not `usr_repo.py`). Class names must be `PascalCase` with acronyms staying uppercase (`HTTPClient`, not `HttpClient`). Functions and variables must be `snake_case`. Module-level constants must be `SCREAMING_SNAKE_CASE`. The acronym casing check uses a configurable acronyms list (see below) — the shipped base list is merged with any project-specific acronyms from `settings.json`.

### Docstrings and type annotations

Public classes, methods, and functions must have Google-style docstrings. The skill checks for missing docstrings and for type repetition in docstring `Args`/`Returns` sections (the types should be in the signature, not restated in the docstring). Private functions (leading `_`) and test functions are exempt from the docstring requirement. Obvious one-line functions may be skipped if `check_skip_obvious_docstrings` is `true`. All public APIs must have type annotations — the type checker enforces this.

### Import structure

Imports must be absolute (no relative imports) when `check_no_relative_imports` is `true`. Import grouping (stdlib, third-party, local) is enforced by ruff's `I` rule if selected in the project's ruff configuration.

## Always-on vs configurable rules

The skill distinguishes between always-on rules and configurable rules. Always-on rules are fundamental standards or fundamental conventions that cannot be disabled — they apply to every project regardless of configuration. Configurable rules are project-specific conventions that can be turned on or off via `settings.json`.

The always-on rules are: descriptive `snake_case` filenames with no abbreviations, `PascalCase` class names, `snake_case` functions and variables, `SCREAMING_SNAKE_CASE` module-level constants, grouped import order (stdlib, third-party, local), private functions exempt from docstrings, test functions exempt from docstrings, and type hints required for all public APIs.

The configurable rules are: acronym casing in class names, absolute imports only (no relative imports), one class per file, filename matches class name, docstrings required on public classes/methods/functions, no type repetition in docstring `Args`/`Returns`, skip docstrings for obvious one-line functions, line length from project config, and vulture minimum confidence for dead-code detection. All configurable rules default to enabled (`true`), and the vulture confidence threshold defaults to `80`.

## Review mode (read-only)

When the skill is invoked as part of a read-only review — for example via `/zolletta-metaskill review` — it follows the shared review-mode rules: it does not apply any fixes, and it runs all tools in their check-only modes. Every diagnostic is classified into one of two buckets. Auto-fixable issues (things a formatter or linter could fix automatically) are listed in a separate "Auto-fixable (informational)" section, are not counted toward the grade, and are not listed as findings. Issues that require human judgment to fix are listed as actual findings with severity, impact, and a suggested fix, and they are the only issues that count toward the review score. There is no third "borderline" bucket — every diagnostic is either a real finding or suppressed. The skill writes its findings to a markdown report file in the timestamped report folder, following the report template with the grade at the top, tool results, auto-fixable issues, and findings grouped by severity.

## How to configure rule toggles

We configure rule toggles by editing the `python.code_style` object in `.zolletta-metaskill/settings.json`. Each configurable rule has a boolean key — set it to `false` to disable that check for the project. The vulture confidence threshold is an integer key (`vulture_min_confidence`) accepting values from 0 to 100. To add project-specific acronyms for the acronym casing check, we set the top-level `acronyms` array; these are merged additively with the shipped base list, not replacing it.

```json
"acronyms": ["CI", "MR", "AST", "DI"],
"python": {
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
  }
}
```

For example, to disable the one-class-per-file check and lower the vulture confidence threshold to 60, we would set `check_one_class_per_file` to `false` and `vulture_min_confidence` to `60`. The always-on rules have no corresponding keys in `settings.json` and cannot be disabled.

## See also

- [Settings schema](../../../reference/settings-schema.md)
- [Review mode](../../../reference/code/review-mode.md)
- [Scripts reference](../../../reference/code/scripts.md)
- [Review Python tests](review-python-tests.md)
- [Detect God classes](../detect-god-classes.md)
