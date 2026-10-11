---
audience: ai, human
status: stable
skills: [review]
description: "Meta-skill architecture: subcommand dispatch, SUBSKILL.md sub-skill grouping, parallel review subagents."
---

# ADR-0001: Meta-skill architecture — dispatch, parallel subagents, skills/ layout

## Status

Accepted

## Context

A code review skill family must cover many concerns — code style, testing, patterns, documentation — each with its own rules, tools, and report format. Three structural problems had to be solved together: one discoverable entry point instead of N skills, review runs that don't serialize a 10-minute wall-clock cost, and a repository layout that doesn't confuse skill discovery (`**/SKILL.md` globs) or clutter the repo root.

## Decision

A single meta-skill (`/zolletta-metaskill` with a subcommand) dispatches to sub-skills under `skills/`, and review runs parallel background subagents.

The rules:

- **One entry point.** Dispatch maps `/zolletta-metaskill <subcommand>` to `skills/zolletta-metaskill-<subcommand>/SUBSKILL.md`. Subcommand names stay short (`help`, `setup`, `review`, ...).
- **Sub-skills are `SUBSKILL.md`, not `SKILL.md`** — so `**/SKILL.md` discovery in agent tools finds only the root meta-skill. Folder name equals skill `name`.
- **Parallel orchestration.** `/zolletta-metaskill review` launches one background subagent per applicable skill in a single tool-call block; each writes its own report file; the orchestrator aggregates grades into `SUMMARY.md` and a prioritized `TODO.md`. A failed subagent gets a placeholder report — the review continues.
- **Language gating.** General skills (patterns, documentor) always run; language-specific skills run only for matching languages.

## Consequences

**Positive:**

- One mental model for users; shared configuration is detected once and read by every subcommand.
- Wall-clock time of a full review ≈ the slowest skill, not the sum; each subagent has its own context window.
- `ls skills/` is the subcommand inventory; repo root stays clean.

**Negative:**

- Subagents cannot message each other — cross-cutting findings are merged by the orchestrator's TODO aggregation, not by communication.
- `SUBSKILL.md` is a project-specific filename — discovery tools that want to see sub-skills never will; dispatch must read them explicitly.

**Neutral:**

- Subcommands are independent at runtime — the meta-skill is a router, not a monolith. The root `SKILL.md` stays at the repo root as the entry point.
