# ADR-0001: Meta-skill with subcommand dispatch

## Status

Accepted

## Context

A code review skill family needs to cover multiple concerns: code style, testing patterns, design patterns, documentation quality, and external LLM review. Each concern has its own rules, tools, and report format.

The obvious approach is to create separate standalone skills, one per concern. Users would invoke the specific skill they need (`/python-code-style`, `/patterns`, `/documentor`, etc.).

However, this creates friction:

- Users must know which skill to invoke for each need.
- A full project review requires manually running several skills and aggregating results.
- Shared configuration (project language, tool availability, rule toggles) must be re-detected or re-specified for each skill.
- Cross-skill concerns (e.g., the documentor needs to know the project language for Diátaxis translations) require duplication or coordination.

## Decision

We use a single meta-skill with subcommand dispatch. One entry point (`/zolletta-metaskill <subcommand>`) routes to specialized review skills. The meta-skill:

- Reads shared configuration from `settings.json` (written by setup) so every subcommand starts with the same context.
- Runs a setup guard before any subcommand to ensure `settings.json` exists and is fresh.
- Dispatches to the appropriate skill based on the subcommand argument.
- Lists available subcommands when invoked with no argument.

## Consequences

**Positive:**

- One entry point, one mental model — users learn `/zolletta-metaskill` and discover subcommands from there.
- Shared configuration is detected once (during setup) and read by every subcommand.
- The orchestrator (`/zolletta-metaskill review`) can launch multiple subagents in parallel and aggregate their reports, which would require external coordination with standalone skills.
- New review concerns are added as new subcommands, not new skills to install.

**Negative:**

- The meta-skill is a large surface area — all subcommands live in one repository and share a version number.
- A user who only wants code style review still installs the entire skill family.

**Neutral:**

- Subcommands are independent at runtime — each reads its own SKILL.md and applies its own rules. The meta-skill is a router, not a monolith.
