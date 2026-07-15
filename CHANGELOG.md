# Changelog

All notable changes to the Zolletta skill family are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-15

### Added

- **zolletta** meta-skill with subcommand dispatch (`/zolletta <subcommand>`)
- **zolletta-documentor** subcommand — unified documentation review combining Diátaxis compliance checks with automated drift detection (staleness scoring, link integrity, API doc validation, drift analysis) with `assets/drift_report_template.md`
- **zolletta-patterns** subcommand — language-agnostic design pattern analysis with automated class metrics scanning (God classes, SOLID violations, coupling, composition vs inheritance) with `assets/report_template.md`
- **zolletta-external-review** subcommand — external-LLM code review on modified files only, with configurable model (default: `swe`, override via front-matter or `ZOLLETTA_EXTERNAL_REVIEW_MODEL` env var)
- **zolletta-review** subcommand — full project review orchestrator that detects the project language, runs general skills (patterns, documentor) plus language-specific skills (python-code-style, python-testing-patterns for Python) in parallel batches, and produces an aggregated TODO.md with graded SUMMARY.md using `assets/summary_template.md` and `assets/todo_template.md`
- Shared resources: `reference/` (code-exploration decision tree, general principles, documentation standards) and `scripts/python/` (automated scanning scripts)
- Skills leveraged if available: [tokensave](https://github.com/aovestdipaperino/tokensave), [GitNexus](https://github.com/abhigyanpatwari/GitNexus), [graphify](https://github.com/safishamsi/graphify)
- `license: MIT + Commons Clause` and `version: 1.0.0` in all SKILL.md frontmatter
- `CHANGELOG.md` following Keep a Changelog format
