# Changelog

All notable changes to the Zolletta-metaskill skill family are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- `.install` script — one-command installer that copies the skill to `~/.agents/skills/` and symlinks it into every detected agent tool's skills directory
- Frontmatter wildcard syntax (`python-*`, `php-*`) for the `skills:` field — language-specific skills no longer need to be listed individually
- `php-pro` companion skill suggestion — when a PHP project is detected, setup prints a "not installed" message suggesting php-pro as an implementation skill
- Language-agnostic explanation docs: `docs/explanation/code/error-handling.md`, `docs/explanation/code/performance.md`, `docs/explanation/code/security.md` — 10 rules promoted from php-best-practices with both PHP and Python examples
- **PHP language support** — `PHPEngine` (tree-sitter-php), PHP SOLID scanners (`scan_php_dependency_inversion`, `scan_php_interface_segregation`, `scan_php_open_closed`), `php-code-style` skill (33 PHP-specific rules: 21 always-on + 12 configurable, version-gated by detected `php_version`), `php-testing-patterns` skill (PHPUnit naming, mirroring, coverage gaps, mocking, data providers)
- **Language-neutral common infrastructure** — `ModuleInfo` data model, `LanguageEngine` protocol, and engine registry (`register_engine` / `get_engine` / `get_engine_for_file` / `ensure_engine` / `available_languages`) in `src/zolletta_metaskill/common/`
- **`PythonEngine`** wrapping the `ast` module in `src/zolletta_metaskill/engines/`
- **`PHPEngine`** wrapping tree-sitter with the tree-sitter-php grammar in `src/zolletta_metaskill/engines/` — includes `parse_raw()` for scanners needing direct tree-sitter AST access
- PHP-specific SOLID scanners in `src/zolletta_metaskill/php_patterns/` (DIP, ISP, OCP via `instanceof` chains)
- PHP tooling detection in setup (phpunit, phpstan, psalm, php-cs-fixer, phpcs) with `php` object in `settings.json`
- `setup/assets/settings.schema.json` — machine-readable JSON Schema (draft 2020-12) for `settings.json`
- `tree-sitter` / `tree-sitter-php` optional dependencies (`pip install zolletta-metaskill[php]`)
- Recovered test suite — 846+ tests at ≥90% coverage per file

### Changed

- **7 scanners refactored** to consume `ModuleInfo` via the `LanguageEngine` protocol instead of Python `ast` directly — scanners in `shared/` and `patterns/` are now language-agnostic
- **Setup detection now supports PHP** — detects `composer.json`, PSR-4 autoload mappings, PHPStan, PHPUnit, Psalm, PHP CS Fixer, and PHPCS configuration
- **Settings schema extended** with a `php` configuration section (`php.code_style` toggles expanded from 3 to 12 configurable rules matching the php-code-style skill, `php.composer_mtime` for staleness checks)
- "Supported languages" line updated from "Python / Others (Work in progress)" to "Python, PHP / Others (Work in progress)"
- Setup guard extended with PHP staleness check (`composer.json` mtime vs `php.composer_mtime`)

## [1.0.0] - 2026-07-17

### Added

#### Core

- **Meta-skill with subcommand dispatch** — one entry point (`/zolletta-metaskill <subcommand>`) routes to specialized review skills
- **Full project review orchestrator** — runs all applicable skills in parallel (patterns, documentor, python-code-style, python-testing-patterns) and produces a graded SUMMARY.md with an actionable TODO.md linking to detailed per-skill reports
- **Review mode rules** — strict two-bucket classification: auto-fixable issues are informational (not graded), real findings get severity/impact/suggested fix (graded). No "borderline" hedging

#### Project setup

- **Project setup** — auto-detects language, Docker container, tokensave availability, and Python tooling (uv, ruff, pytest, ty, vulture, mypy). Creates `.zolletta-metaskill/settings.json` with effective tool configuration extracted from `pyproject.toml`. Prints helpful "not installed" messages for missing tools — never installs anything
- **Setup guard** — every subcommand checks for `settings.json` before running. If missing, setup runs automatically. For Python projects, a staleness check re-extracts `pyproject.toml` configuration when the file changes — no full re-setup needed
- **Settings schema documentation** — full field-by-field reference for `settings.json` at `docs/reference/settings-schema.md`, covering tool availability, effective configuration, and all configurable rule toggles

#### Documentation review

- **Documentation review** — structure, accuracy, consistency, and freshness checks with automated drift detection (staleness scoring, broken links, API doc validation). Supports [Diátaxis](https://diataxis.fr/)-structured docs (detects quadrant directories and applies appropriate completeness checks) and falls back to README-style sections for other layouts
- **Multi-language documentation support** — `documentation_language` field in `settings.json` (ISO 639-1 code, default: `"en"`). When not English, the `documentor` skill translates the Diátaxis signpost headings before running the staleness scorer. `--diataxis-translations` flag in `doc_staleness_scorer.py` accepts a JSON file with translated directory names and section headings

#### Design pattern analysis

- **Design pattern analysis** — automated class metrics scanning for God classes, SOLID violations, coupling, and composition vs inheritance. Semantic composition-root detection excludes DI containers to prevent false positives. Mandatory "reason to change" judgment step prevents verdict oscillation between reviews

#### Python code style review

- **Python code style review** — ruff, mypy/ty, vulture integration plus 22 naming, docstring, import, and structure rules. Configurable rule toggles in `settings.json` for project-specific overrides

#### Python testing patterns review

- **Python testing patterns review** — coverage gap analysis with threshold-based detection, test naming enforcement, isolation and mocking checks, AAA structure validation

#### External LLM review

- **External LLM review** — sends modified files to an external model (default: `swe`) for a second opinion. Model configurable via `settings.json` or front-matter

#### Deterministic scanners

- **`scan_acronym_casing.py`** — flags acronyms not fully uppercase in PascalCase class names. Ships with 57 common SE acronyms, mergeable with project-specific lists
- **`scan_unused_all_exports.py`** — catches dead code exported via `__all__` that vulture misses
- **`scan_test_naming.py`** — enforces descriptive test function names
- **`scan_class_metrics.py`**, **`scan_tests.py`**, **`scan_dependency_inversion.py`** — class size triage, test structure validation, DIP violation detection

#### Tokensave integration

- **Tokensave integration** — leverages [tokensave](https://github.com/aovestdipaperino/tokensave) semantic code-graph queries when available, with a pre-flight freshness check before review subagents launch. Falls back to grep + targeted reads otherwise
- **Tool-failure handler** — if tokensave becomes unavailable mid-session, automatically updates `settings.json`, prints a helpful message, and continues with fallback

#### Reports and references

- **Report templates** — each skill ships a markdown report template with grade, tool results, severity tables, and recommendations. The Zolletta-metaskill logo is embedded as a base64 data URI in every report footer
- **Shared references** — code-exploration decision tree, general review principles, documentation standards, tool messages, review-mode rules, and scripts reference — all in `docs/`, linked from every skill
