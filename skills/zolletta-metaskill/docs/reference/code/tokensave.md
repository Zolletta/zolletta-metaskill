---
audience: human, ai
status: stable
skills: [patterns, documentor, review, python-*]
---

# Tokensave

> **Paths in this document are relative to the Zolletta-MetaSkill project root.**

Tokensave is a semantic code-graph index that provides instant exploration, impact analysis, and symbol search from a pre-built knowledge graph. It is the primary code exploration tool for all Zolletta-metaskill review skills.

## MANDATORY: No Explore Agents When Tokensave Is Available

Follow the global no-explore-agents rule from `AGENTS.md` — query the tokensave graph, do not spawn explore agents.

## How to query

The canonical transport is the CLI: `tokensave tool <name>` — it exposes the same tool surface as the MCP server with identical output, works in every harness, and requires tokensave ≥ 7.14. Run `tokensave tool` with no arguments to list every tool, and `tokensave tool <name> --help` for a tool's parameters.

- Parameters are `--key value` pairs in kebab-case (`--node-id`, `--max-depth`). Reserved flags: `--json` wraps the result in the MCP envelope (the default output is already the tool payload), `--project <path>` sets the project root (defaults to cwd), `--args '<json>'` passes the whole argument object for complex shapes (mutually exclusive with `--key value` flags). A value starting with `@` is read from the file at that path.
- On binaries older than 7.14, the same tools are exposed as the `tokensave_*` MCP tools where the server is registered — `tokensave tool context` ≡ `tokensave_context`, `tokensave tool callers` ≡ `tokensave_callers`, and so on for every name below. See [MCP fallback](#mcp-fallback-pre-714-binaries).

## Available tools

- `context` — first tool for exploration/planning. **Call budget: 3 max per project**, then synthesize. Params: `task`, `mode` (`explore`|`plan`), `keywords`, `include_code`, `path_include`, `path_exclude`.
- `search` — find symbols by name/keyword. Use `literal: true` for runtime error strings.
- `callers` / `callees` — trace call relationships for a node.
- `impact` — compute impact radius of a node.
- `node` — detailed info about a single node.
- `files` — list indexed files without reading contents.
- `affected` — find test files affected by changed source files.

## Rules

- Use `tokensave tool context` as the first exploration tool for any code question.
- Pass `seen_node_ids` from each response to the next call's `exclude_node_ids` for session deduplication.
- When the 3-call budget is exhausted, synthesize from what you have — do not make more calls.
- If a question cannot be answered by the tools, query the SQLite graph directly at `.tokensave/tokensave.db` (tables: `nodes`, `edges`, `files`).
- If you discover a gap where an extractor, schema, or tool could be improved, propose opening an issue at <https://github.com/aovestdipaperino/tokensave>. **Remind the user to strip sensitive/proprietary code from the bug description.**

## When you spawn an Explore agent anyway

If spawning an explore agent is unavoidable, include the tokensave-only directive from `AGENTS.md` in the agent prompt, and run the subagent under an exec-capable profile — `tokensave tool` is a shell command, so a read-only profile cannot run it.

## MCP fallback (pre-7.14 binaries)

The `tokensave_*` MCP tools expose the same tool surface through `tokensave serve`. Where a server is registered they are fully equivalent to the CLI forms above; the CLI is canonical in this documentation because it works whether or not the server is registered.

| Scope                 | Configuration location                           | Example                         |
| --------------------- | ------------------------------------------------ | ------------------------------- |
| Global (all projects) | `~/.config/devin/config.json` → `mcpServers`     | Default tokensave server        |
| Per-project           | `.devin/config.json` → `mcpServers`              | Project-specific tokensave path |
| Per-session           | Agent CLI flag                                   | `--mcp-server tokensave=...`    |
| Fallback              | Direct SQLite query on `.tokensave/tokensave.db` | Complex structural queries      |

## Maintenance

- After switching branches: `tokensave branch add <branch>` then `tokensave sync`.
- Stale index check: run `tokensave tool status` to verify `stale_commits` is 0 before relying on results.
- If a project has no `.tokensave/` at the `--path` root, run `tokensave init` there to create the index.
- `tokensave tool` requires tokensave ≥ 7.14 — run `tokensave upgrade` on an older binary, or use the MCP fallback above.

## See also

- [Code exploration](code-exploration.md) — decision tree for choosing the right exploration tool
- [Tool messages](../tool-messages.md) — "not installed" message printed when tokensave is unavailable
