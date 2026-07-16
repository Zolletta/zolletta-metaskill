# Zolletta meta-skill

A family of generic code review skills with specializations for Python (other languages in progress).

Zolletta is a **meta-skill**: it dispatches to subcommands that each perform a specific review task. It leverages [tokensave](https://github.com/aovestdipaperino/tokensave) and [graphify](https://github.com/safishamsi/graphify) when available for semantic code-graph queries, and falls back to grep + targeted reads otherwise.

## Quick start

```text
/zolletta                  # list available subcommands
/zolletta setup            # initialize .zolletta-metaskill/settings.json
/zolletta review           # full project review (orchestrator)
/zolletta patterns         # design pattern analysis
/zolletta documentor       # documentation review (Diátaxis + drift detection)
/zolletta external-review  # external-LLM review of modified files
```

The first time you run any subcommand in a project, the **setup guard** automatically runs `/zolletta setup` if `.zolletta-metaskill/settings.json` does not exist.

## Subcommands

| Subcommand        | Scope                                                                                                                                             |
| ----------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `setup`           | Project initialization — creates `settings.json`, detects language, tests tool availability                                                       |
| `review`          | Full project review orchestrator — runs general + language-specific skills in parallel batches, produces graded SUMMARY.md and aggregated TODO.md |
| `patterns`        | God classes, SOLID violations, coupling, composition vs inheritance for `src/`                                                                    |
| `documentor`      | Diátaxis compliance + drift detection for `.backstage/`                                                                                           |
| `external-review` | External-LLM code review on modified files only (default model: `swe`)                                                                            |

## Skills leveraged if available

| Tool      | Homepage                                      | Why zolletta benefits                                                                                                                                                                                                                          |
| --------- | --------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| tokensave | https://github.com/aovestdipaperino/tokensave | Semantic code-graph index (symbols, call/callee, impact radius). Used by patterns, documentor, review, external-review to understand code without reading full files, assess blast radius, verify documented symbols, and find affected tests. |
| graphify  | https://github.com/safishamsi/graphify        | Persistent knowledge graph with community detection and query/path/explain tools. Used by patterns and review for architecture questions, cross-file relationship tracing, and plain-language node explanations.                               |

When a tool is not installed, zolletta prints a message explaining why it would benefit from the tool and links to the homepage. It does **not** install anything.

## Shared resources

| Resource   | Path              | Contents                                                                                   |
| ---------- | ----------------- | ------------------------------------------------------------------------------------------ |
| References | `reference/`      | Code-exploration decision tree, general principles, documentation standards, tool messages |
| Scripts    | `scripts/python/` | Automated scanning scripts used by multiple skills                                         |

## Setup and settings.json

`/zolletta setup` creates `.zolletta-metaskill/settings.json` in the project root and adds `.zolletta-metaskill/` to `.gitignore`. The file is read by all other subcommands.

### Schema

```json
{
  "setup_version": "1.0.0",
  "setup_timestamp": "2026-07-16T14:30:00",
  "language": "python",
  "tokensave_available": true,
  "graphify_available": false,
  "python_code_style_available": true,
  "python_testing_patterns_available": true,
  "external_review_model": "swe",
  "reports_dir": ".zolletta-metaskill/reports"
}
```

| Field                               | Description                                                                |
| ----------------------------------- | -------------------------------------------------------------------------- |
| `setup_version`                     | Matches the skill version that wrote the file                              |
| `setup_timestamp`                   | ISO 8601 timestamp of the last setup run                                   |
| `language`                          | Detected project language (`python`, `php`, `go`, `rust`, etc.)            |
| `tokensave_available`               | `true` if `tokensave_status` responds (probed directly)                    |
| `graphify_available`                | `true` if `mcp_list_tools` for graphify succeeds or `graphify-out/` exists |
| `python_code_style_available`       | `true` if the `python-code-style` skill is installed (Python only)         |
| `python_testing_patterns_available` | `true` if the `python-testing-patterns` skill is installed (Python only)   |
| `external_review_model`             | Default model for `external-review` (overridable by env var)               |
| `reports_dir`                       | Directory where review reports are saved                                   |

### Tool-failure handler

If any subcommand calls a tokensave or graphify MCP tool and receives a tool-not-found / server-not-found error, or if `skill invoke` returns "Skill not found" for a Python review skill, it:

1. Updates the corresponding `*_available` flag in `settings.json` to `false`
2. Prints the "not installed" message from `reference/tool-messages.md`
3. Continues with grep + targeted reads as fallback (for graph tools) or skips the missing skill's review area (for Python skills)

## Reports

All reports are saved to:

```text
.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/<subcommand>.md
```

The timestamp format (`YYYY-MM-DD-HH-MM`) is lexicographically sortable, so finding the most recent review is a simple directory listing.

## Rules

All files in `~/.agents/rules/` are the **single source of truth** for their domain and apply to every subcommand. Sub-skills link back to them and only narrow behavior for their specific review context.

## License

MIT + Commons Clause. See `SKILL.md` frontmatter in each subcommand.

## Changelog

See [CHANGELOG.md](CHANGELOG.md).
