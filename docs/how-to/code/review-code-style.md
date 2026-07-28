---
audience: human, ai
status: stable
skills: [python-*, review]
---

# Review code style

> **Language-agnostic**: this guide covers conventions that apply across all supported languages. Language-specific tooling details (e.g. Python's ruff, mypy, vulture) are in the language-specific guides.

Review source code for naming conventions, docstring quality, type annotations, formatting, and dead code. This guide covers the general rules that apply to all languages; language-specific guides narrow these for their tooling.

## Prerequisites

- A project that has been set up with `/zolletta-metaskill setup`

## What the review checks

### Naming conventions

The review checks naming conventions across filenames, classes, functions, variables, and module-level constants. The conventions are language-specific but follow the same principles:

- **Filenames** must be descriptive, no abbreviations (`user_repository`, not `usr_repo`)
- **Class names** use the language's PascalCase equivalent with acronyms staying uppercase (`HTTPClient`, not `HttpClient`)
- **Functions and variables** use the language's snake_case or camelCase convention consistently
- **Module-level constants** use SCREAMING_SNAKE_CASE or the language's constant convention

### Docstrings and documentation

Public classes, methods, and functions must have documentation. The documentation style follows the language's convention (e.g. Google-style docstrings for Python, PHPDoc for PHP). The review checks for:

- Missing documentation on public APIs
- Type repetition in documentation (types should be in the signature, not restated in the docs)
- Obvious one-line functions may be skipped if the configurable toggle is enabled

Private functions and test functions are exempt from the documentation requirement.

### Type annotations

All public APIs must have type annotations. The review uses the project's configured type checker to verify this. Missing annotations on public functions, methods, and classes are reported as findings.

### Formatting

The review runs the project's configured linter and formatter in check-only mode. Line length and target version are read from the project configuration (not hardcoded). Import grouping (stdlib, third-party, local) is enforced when the linter's import-sorting rule is selected.

### Dead code

The review runs the project's configured dead-code detector. Findings below the confidence threshold are not reported. Each finding above the threshold is reviewed with judgment before being flagged — dead-code detectors have known false positives for dynamically-accessed methods.

## Always-on vs configurable rules

**Always-on** (cannot be disabled): descriptive filenames, class naming convention, function/variable naming, constant naming, import grouping, private functions exempt from docs, test functions exempt from docs, type hints for public APIs.

**Configurable** (toggled via `settings.json`, all default to enabled): acronym casing, absolute imports, one class per file, filename matches class, public docstrings, no type repetition in docs, skip obvious one-liner docs, line length, dead-code confidence threshold.

See the language-specific guides for the exact `settings.json` keys.

## Review mode (read-only)

Follows [review mode](../../reference/code/review-mode.md) — read-only, two-bucket classification (auto-fixable vs findings), no fixes applied.

## See also

- [Review Python style](python/review-python-style.md) — Python-specific tooling and configuration
- [Review test code](review-test-code.md) — general test code review guide
- [Review mode](../../reference/code/review-mode.md) — shared rules for read-only reviews
- [Settings schema](../../reference/settings-schema.md) — all configuration options
