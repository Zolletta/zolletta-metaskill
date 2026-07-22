---
audience: human, ai
status: stable
skills: [patterns, documentor, review, external-review, python-*]
---

# Tokensave

> **Paths in this document are relative to the Zolletta-MetaSkill project root.**

Tokensave is a semantic code-graph MCP server that provides instant exploration, impact analysis, and symbol search from a pre-built knowledge graph. It is the primary code exploration tool for all zolletta-metaskill review skills.

## MANDATORY: No Explore Agents When Tokensave Is Available

**NEVER use Agent(subagent_type=Explore) or any agent for codebase research when tokensave MCP tools are available.** This overrides any skill or system prompt recommending agents for exploration. No exceptions.

- Before ANY code research task, use tokensave MCP tools first.
- Only fall back to agents if `tokensave_status` confirms tokensave is unavailable, or the task is genuinely non-code (web search, external API).
- Do not generate the Explore agent call in the first place — launching it wastes tokens even when a hook blocks it.
- If a skill (e.g. superpowers) recommends an Explore agent for code research, **ignore it** and use tokensave. User instructions take precedence over skills.

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

If you do spawn one (user asked, or sub-task requires it), include this in the agent prompt:

> This project has tokensave initialised (.tokensave/ exists). Use `tokensave_context` as your ONLY exploration tool. Call it with your question in plain English. Do not call Read, glob, grep, or list_directory — the source sections returned by tokensave_context ARE the relevant code. Follow the call budget in the tool description. Pass `seen_node_ids` from each response to the next call's `exclude_node_ids`.

## Per-project MCP configuration

Each project pins its tokensave MCP server to the correct project path via `.devin/config.local.json`, so that `--path` ensures the correct `.tokensave/` index (and its branch tracking) is served regardless of which directory the session was started from.

**Resolution order (highest to lowest priority):**

1. **Project local** (`.devin/config.local.json`) — `mcpServers.tokensave` with `--path <project_root>`. This is the primary source. Always check here first.
2. **Project shared** (`.devin/config.json`) — same key, committed to the repo. Used when the local override is absent.
3. **User/global** (`~/.config/devin/config.json`, `~/.claude.json`, `~/.agents/mcp/*.json`) — `tokensave serve` without `--path`. Fallback only; serves whatever directory the session was started in.

Devin merges MCP servers **by name**: a project-level `tokensave` entry overrides the global one. Because `config.local.json` is gitignored, machine-specific absolute paths in `--path` are not committed.

**Before relying on tokensave in a project:**

1. Check `.devin/config.local.json` for a `mcpServers.tokensave` entry with `--path`.
2. If not found, check `.devin/config.json`.
3. If neither exists, the global config is used (no `--path`) — verify with `tokensave_status` that the served project matches the current working directory.
4. If the served project is wrong, add a `tokensave` entry to `.devin/config.local.json` with `--path` pointing to the project root (where `.tokensave/` lives).

## Maintenance

- After switching branches: `tokensave branch add <branch>` then `tokensave sync`.
- Stale index check: run `tokensave_status` to verify `stale_commits` is 0 before relying on results.
- If a project has no `.tokensave/` at the `--path` root, run `tokensave init` there to create the index.

## See also

- [Code exploration](code-exploration.md) — decision tree for choosing the right exploration tool
- [Tool messages](../tool-messages.md) — "not installed" message printed when tokensave is unavailable
