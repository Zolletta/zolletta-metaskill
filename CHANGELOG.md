# Changelog

All notable changes to the Zolletta-metaskill skill family are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.1.0] - 2026-07-17

### Added

#### Multi-language documentation support

- **`documentation_language` field in `settings.json`** — ISO 639-1 code (default: `"en"`). When not English, the `documentor` skill translates the Diátaxis signpost headings before running the staleness scorer
- **`--diataxis-translations` flag in `doc_staleness_scorer.py`** — accepts a JSON file with translated directory names and section headings. Directory names are merged additively (English + translated), section headings are replaced (translated is authoritative). Also supports translated README section defaults
- **English signposts as translation keys** — the built-in English strings (`"tutorials"`, `"prerequisites"`, `"what we will learn"`, etc.) act as signposts. The agent translates each to the documentation language and writes the translations to a JSON file. This keeps the scorer deterministic while supporting any language

## [1.0.0] - 2026-07-17

### Added

#### Core

- **Meta-skill with subcommand dispatch** — one entry point (`/zolletta-metaskill <subcommand>`) routes to specialized review skills
- **Full project review orchestrator** — runs all applicable skills in parallel (patterns, documentor, python-code-style, python-testing-patterns) and produces a graded SUMMARY.md with an actionable TODO.md linking to detailed per-skill reports
- **Review mode rules** — strict two-bucket classification: auto-fixable issues are informational (not graded), real findings get severity/impact/suggested fix (graded). No "borderline" hedging

#### Project setup

- **Project setup** — auto-detects language, Docker container, tokensave availability, and Python tooling (uv, ruff, pytest, ty, vulture, mypy). Creates `.zolletta-metaskill/settings.json` with effective tool configuration extracted from `pyproject.toml`. Prints helpful "not installed" messages for missing tools — never installs anything
- **Setup guard** — every subcommand checks for `settings.json` before running. If missing, setup runs automatically. For Python projects, a staleness check re-extracts `pyproject.toml` configuration when the file changes — no full re-setup needed
- **Settings schema documentation** — full field-by-field reference for `settings.json` at `reference/settings-schema.md`, covering tool availability, effective configuration, and all configurable rule toggles

#### Documentation review

- **Documentation review** — structure, accuracy, consistency, and freshness checks with automated drift detection (staleness scoring, broken links, API doc validation). Supports [Diátaxis](https://diataxis.fr/)-structured docs (detects quadrant directories and applies appropriate completeness checks) and falls back to README-style sections for other layouts

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

- **Report templates** — each skill ships a markdown report template with grade, tool results, severity tables, and recommendations. The zolletta-metaskill logo is embedded as a base64 data URI in every report footer
- **Shared references** — code-exploration decision tree, general review principles, documentation standards, tool messages, review-mode rules, and scripts reference — all in `reference/`, linked from every skill
