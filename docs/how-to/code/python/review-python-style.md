---
audience: human, ai
status: stable
skills: [python-*]
---

# How to review Python code style

> **Paths in this document are relative to the Zolletta-MetaSkill project root.**

The `python-code-style` skill inspects Python source for naming conventions, import structure, docstring quality, type annotations, formatting, and dead code. This guide covers what the skill checks, how the rules are organized, and how to configure rule toggles for a project.

## Prerequisites

Requires a Python project set up via `/zolletta-metaskill setup`. Reads `python.tools.*` and `python.code_style` from `settings.json`.

## What the skill checks

The skill runs a combination of automated tools and manual review checks across six areas.

### Linting and formatting (ruff)

If `python.tools.ruff.available` is `true` in `settings.json`, the skill runs `ruff check` for linting and `ruff format --check` for formatting. Ruff enforces the rule set configured in `python.tools.ruff.select` and `python.tools.ruff.ignore`. The skill does not carry its own ruff configuration — it reads everything from `settings.json`, which setup populated from `pyproject.toml`. Import grouping (stdlib, third-party, local) is enforced automatically when the ruff `I` (isort) rule is selected.

### Type checking (mypy or ty)

The skill runs all available type checkers to verify that all public APIs have type annotations. Run `ty` if `python.tools.ty.available` is `true` and `mypy` if `python.tools.mypy.available` is `true` — when both are available, both run. If neither is available, the type-checking step is skipped. Each type checker runs with `disallow_untyped_defs` or equivalent strictness, so missing annotations on public functions, methods, and classes are reported as findings.

### Dead code detection (vulture)

If `python.tools.vulture.available` is `true`, the skill runs `vulture src/ --min-confidence <threshold>` to detect unused code. The confidence threshold comes from `python.code_style.vulture_min_confidence` (default: `80`) — findings below that confidence are not reported. Vulture has known false positives, especially for dynamically-accessed methods, so each finding above the threshold is reviewed with judgment before being flagged. If `python.tools.vulture.available` is `false`, dead-code detection is skipped entirely. In addition to vulture, the skill runs a supplementary `src/zolletta_metaskill/code_style/python/unused_all_exports_scanner.py` scanner that cross-references every `__all__` entry against actual imports across the source tree — vulture treats `__all__` entries as "used" and never flags unused exports, so this scanner closes that gap.

### Naming conventions

The skill checks naming conventions across filenames, classes, functions, variables, and module-level constants. Filenames must be descriptive `snake_case` with no abbreviations (`user_repository.py`, not `usr_repo.py`). Class names must be `PascalCase` with acronyms staying uppercase (`HTTPClient`, not `HttpClient`). Functions and variables must be `snake_case`. Module-level constants must be `SCREAMING_SNAKE_CASE`. The acronym casing check uses a configurable acronyms list (see below) — the shipped base list is merged with any project-specific acronyms from `settings.json`.

### Docstrings and type annotations

Public classes, methods, and functions must have Google-style docstrings. The skill checks for missing docstrings and for type repetition in docstring `Args`/`Returns` sections (the types should be in the signature, not restated in the docstring). Private functions (leading `_`) and test functions are exempt from the docstring requirement. Obvious one-line functions may be skipped if `check_skip_obvious_docstrings` is `true`. All public APIs must have type annotations — the type checker enforces this.

### Import structure

Imports must be absolute (no relative imports) when `check_no_relative_imports` is `true`. Import grouping (stdlib, third-party, local) is enforced by ruff's `I` rule if selected in the project's ruff configuration.

## Always-on vs configurable rules

The rules above are tagged **always-on** (cannot be disabled) or **configurable** (toggled via `settings.json`, all default to enabled).

## Review mode (read-only)

Follows [review mode](../../../reference/code/review-mode.md) — read-only, two-bucket classification, no fixes applied.

## How to configure rule toggles

Configure rule toggles by editing the `python.code_style` object in `.zolletta-metaskill/settings.json`. Each configurable rule has a boolean key — set it to `false` to disable that check for the project. The vulture confidence threshold is an integer key (`vulture_min_confidence`) accepting values from 0 to 100. To add project-specific acronyms for the acronym casing check, set the top-level `acronyms` array; these are merged additively with the shipped base list, not replacing it.

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

For example, to disable the one-class-per-file check and lower the vulture confidence threshold to 60, set `check_one_class_per_file` to `false` and `vulture_min_confidence` to `60`. The always-on rules have no corresponding keys in `settings.json` and cannot be disabled.

## See also

- [Settings schema](../../../reference/settings-schema.md)
- [Review mode](../../../reference/code/review-mode.md)
- [Scripts reference](../../../reference/code/scripts.md)
- [Review Python tests](review-python-tests.md)
- [Detect God classes](../detect-god-classes.md)
