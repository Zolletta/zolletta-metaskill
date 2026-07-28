---
audience: human, ai
status: stable
skills: [patterns, documentor, review, external-review, python-*]
---

# Tokensave

> **Paths in this document are relative to the Zolletta-MetaSkill project root.**

Tokensave is a semantic code-graph MCP server that provides instant exploration, impact analysis, and symbol search from a pre-built knowledge graph. It is the primary code exploration tool for all Zolletta-metaskill review skills.

## MANDATORY: No Explore Agents When Tokensave Is Available

Follow the global no-explore-agents rule from `AGENTS.md` — use tokensave MCP tools, not explore agents.

## Available tools

- `tokensave_context` — first tool for exploration/planning. **Call budget: 3 max per project**, then synthesize. Params: `task`, `mode` (`explore`|`plan`), `keywords`, `include_code`, `path_include`, `path_exclude`.
- `tokensave_search` — find symbols by name/keyword. Use `literal: true` for runtime error strings.
- `tokensave_callers` / `tokensave_callees` — trace call relationships for a node.
- `tokensave_impact` — compute impact radius of a node.
- `tokensave_node` — detailed info about a single node.
- `tokensave_files` — list indexed files without reading contents.
- `tokensave_affected` — find test files affected by changed source files.

## Rules

- Use `tokensave_context` as the first exploration tool for any code question.
- Pass `seen_node_ids` from each response to the next call's `exclude_node_ids` for session deduplication.
- When the 3-call budget is exhausted, synthesize from what you have — do not make more calls.
- If a question cannot be answered by the tools, query the SQLite graph directly at `.tokensave/tokensave.db` (tables: `nodes`, `edges`, `files`).
- If you discover a gap where an extractor, schema, or tool could be improved, propose opening an issue at https://github.com/aovestdipaperino/tokensave. **Remind the user to strip sensitive/proprietary code from the bug description.**

## When you spawn an Explore agent anyway

If spawning an explore agent is unavoidable, include the tokensave-only directive from `AGENTS.md` in the agent prompt.

## Per-project MCP configuration

| Scope                 | Configuration location                           | Example                         |
|-----------------------|--------------------------------------------------|---------------------------------|
| Global (all projects) | `~/.config/devin/config.json` → `mcpServers`     | Default tokensave server        |
| Per-project           | `.devin/config.json` → `mcpServers`              | Project-specific tokensave path |
| Per-session           | Agent CLI flag                                   | `--mcp-server tokensave=...`    |
| Fallback              | Direct SQLite query on `.tokensave/tokensave.db` | Complex structural queries      |

## Maintenance

- After switching branches: `tokensave branch add <branch>` then `tokensave sync`.
- Stale index check: run `tokensave_status` to verify `stale_commits` is 0 before relying on results.
- If a project has no `.tokensave/` at the `--path` root, run `tokensave init` there to create the index.

## See also

- [Code exploration](code-exploration.md) — decision tree for choosing the right exploration tool
- [Tool messages](../tool-messages.md) — "not installed" message printed when tokensave is unavailable
