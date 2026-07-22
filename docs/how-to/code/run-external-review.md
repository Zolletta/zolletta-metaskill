---
audience: human, ai
status: stable
skills: [external-review]
---

# Run an external-LLM code review

Run a code review on the modified files of a change using an external LLM that follows the global rules and the project's AGENTS.md. This is the fastest way to get a focused, convention-aware review of only the files touched by a change.

## Prerequisites

- A git repository with uncommitted or committed-but-unreviewed changes
- The zolletta-metaskill skill installed and available to the agent
- Global rules present in `~/.agents/` (markdown files covering language, style, and documentation conventions)

## Steps

### Step 1 — Identify the modified files

```bash
git diff --name-only HEAD
```

If there are no uncommitted changes, compare against the base branch:

```bash
git diff --name-only main...HEAD
```

### Step 2 — Gather the review context

Read the following to build the review context:

1. The project's `AGENTS.md` (if present) — project-specific rules and conventions
2. The global rules from `~/.agents/` — language rules, code style rules, documentation rules, commit rules
3. The modified files from Step 1 — read each file in full

### Step 3 — Run the external review

Send the modified files and the review context to an external LLM. The default model is `swe`; override via `external_review_model` in `.zolletta-metaskill/settings.json` or in the skill's front-matter.

The external reviewer should:
- Follow the global rules and project AGENTS.md exactly
- Review only the modified files (not the entire codebase)
- Report findings with severity, file, line number, and suggested fix
- Classify findings as actionable (require human judgment) or auto-fixable (formatter/linter could fix)

### Step 4 — Collect the report

The external reviewer writes its findings to a markdown report in the timestamped report folder, following the standard report template with the grade at the top, tool results, auto-fixable issues, and findings grouped by severity.

## Configuration

| Setting                 | Location                            | Default | Description                                  |
| ----------------------- | ----------------------------------- | ------- | -------------------------------------------- |
| `external_review_model` | `.zolletta-metaskill/settings.json` | `swe`   | The external LLM model to use for the review |

## See also

- [Review mode](../../reference/code/review-mode.md) — shared rules for read-only reviews
- [Settings schema](../../reference/settings-schema.md) — all configuration options
- [Run a full review](../run-full-review.md) — orchestrator that runs all skills in parallel
