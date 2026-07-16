# Changelog

All notable changes to the Zolletta skill family are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-07-15

### Added

- **zolletta** meta-skill with subcommand dispatch (`/zolletta <subcommand>`)
- **zolletta-setup** subcommand — project initialization that creates `.zolletta-metaskill/settings.json` with the detected project language, tool/skill availability flags, external-review model, and reports directory. Adds `.zolletta-metaskill/` to `.gitignore` (creating it if absent). Tool and skill availability is probed with a unified approach — try the actual tool (`tokensave_status`, `mcp_list_tools` for graphify, `skill invoke` for Python skills), catch the not-found error, set the flag. For each unavailable tool or skill, prints a message explaining why zolletta benefits from it with a link to the project homepage. Does not install anything.
- **zolletta-documentor** subcommand — unified documentation review combining Diátaxis compliance checks with automated drift detection (staleness scoring, link integrity, API doc validation, drift analysis) with `assets/drift_report_template.md`
- **zolletta-patterns** subcommand — language-agnostic design pattern analysis with automated class metrics scanning (God classes, SOLID violations, coupling, composition vs inheritance) with `assets/report_template.md`
- **zolletta-external-review** subcommand — external-LLM code review on modified files only, with configurable model (default: `swe`, override via `ZOLLETTA_EXTERNAL_REVIEW_MODEL` env var, `settings.json`, or front-matter)
- **zolletta-review** subcommand — full project review orchestrator that reads the project language from `settings.json`, runs general skills (patterns, documentor) plus language-specific skills (python-code-style, python-testing-patterns for Python) in parallel batches, and produces an aggregated TODO.md with graded SUMMARY.md using `assets/summary_template.md` and `assets/todo_template.md`
- **Setup guard** — before dispatching to any subcommand, the meta-skill checks for `.zolletta-metaskill/settings.json` and runs the full setup procedure if it is missing, guaranteeing that every subcommand can rely on settings being present
- **Tool-failure handler** — when any subcommand calls a tokensave or graphify MCP tool and receives a tool-not-found / server-not-found error, or when `skill invoke` returns "Skill not found" for a Python review skill, it updates the corresponding `*_available` flag in `settings.json` to `false`, prints the "not installed" message explaining why zolletta benefits from the tool/skill, and continues with grep/read fallback or skips the missing skill's review area
- **`reference/tool-messages.md`** — shared "not installed" messages for tokensave, graphify, python-code-style, and python-testing-patterns, explaining why zolletta benefits from each tool/skill with homepage links (where applicable), used by both setup and the tool-failure handler
- Shared resources: `reference/` (code-exploration decision tree, general principles, documentation standards, tool messages) and `scripts/python/` (automated scanning scripts)
- Skills leveraged if available: [tokensave](https://github.com/aovestdipaperino/tokensave), [graphify](https://github.com/safishamsi/graphify)
- `license: MIT + Commons Clause` and `version: 1.0.0` in all SKILL.md frontmatter
- `CHANGELOG.md` following Keep a Changelog format
- `README.md` with project overview, subcommands table, leveraged skills, shared resources, setup behavior, settings.json schema, and reports location
