---
audience: human, ai
status: stable
skills: [python-code-style, review]
---

# Review code style

> **Language-agnostic**: this guide covers conventions that apply across all supported languages. Language-specific tooling details (e.g. Python's ruff, mypy, vulture) are in the language-specific guides.

Review source code for naming conventions, docstring quality, type annotations, formatting, and dead code. This guide covers the general rules that apply to all languages; language-specific guides narrow these for their tooling.

## Prerequisites

- A project that has been set up with `/zolletta-metaskill setup`
- The zolletta-metaskill skill installed and available to the agent

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

The review distinguishes between always-on rules and configurable rules:

**Always-on rules** (cannot be disabled):
- Descriptive filenames with no abbreviations
- Class names follow the language's PascalCase convention
- Functions and variables follow the language's naming convention
- Module-level constants follow the language's constant convention
- Import grouping (stdlib, third-party, local)
- Private functions exempt from documentation
- Test functions exempt from documentation
- Type hints required for all public APIs

**Configurable rules** (can be toggled via `settings.json`):
- Acronym casing in class names
- Absolute imports only (no relative imports)
- One class per file
- Filename matches class name
- Documentation required on public classes/methods/functions
- No type repetition in documentation
- Skip documentation for obvious one-line functions
- Line length from project config
- Dead-code detection confidence threshold

All configurable rules default to enabled. See the language-specific guides for the exact `settings.json` keys.

## Review mode (read-only)

When the review runs as part of a read-only review — for example via `/zolletta-metaskill review` — it follows the shared [review mode](../../reference/code/review-mode.md) rules: it does not apply any fixes, and it runs all tools in their check-only modes. Every diagnostic is classified into one of two buckets:

- **Auto-fixable** (informational) — things a formatter or linter could fix automatically. Listed in a separate section, not counted toward the grade.
- **Findings** — issues that require human judgment to fix. Listed with severity, impact, and a suggested fix. These are the only issues that count toward the review score.

There is no third "borderline" bucket — every diagnostic is either a real finding or suppressed.

## See also

- [Review Python style](python/review-python-style.md) — Python-specific tooling and configuration
- [Review test code](review-test-code.md) — general test code review guide
- [Review mode](../../reference/code/review-mode.md) — shared rules for read-only reviews
- [Settings schema](../../reference/settings-schema.md) — all configuration options
