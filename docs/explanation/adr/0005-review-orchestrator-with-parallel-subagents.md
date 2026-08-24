# ADR-0005: Review orchestrator with parallel subagents

## Status

Accepted

## Context

A full project review covers multiple concerns: design patterns, documentation, code style, and testing patterns. Each concern has its own skill, rules, and report format. Running them sequentially would be slow — a full review could take 10+ minutes for a large project.

The orchestrator needs to run all applicable skills, collect their results, and produce an aggregated summary with a grade and a prioritized TODO list.

## Decision

The review skill launches one subagent per command, all in parallel as background subagents. Each subagent:

- Invokes its specialist skill to load guidelines.
- Applies those guidelines to review its scope.
- Writes its report file directly to the review folder.

The orchestrator:

- Launches all subagents in a single tool-call block so they run concurrently.
- Waits for each to finish.
- Reads the report files, extracts grades, and produces SUMMARY.md (executive summary with weighted grade) and TODO.md (prioritized action list organized by severity).

General skills (patterns, documentor) always run. Language-specific skills (python-code-style, python-testing-style, php-code-style, php-testing-style) run only when the project uses the matching language.

## Consequences

**Positive:**

- Parallel execution reduces wall-clock time — a 4-skill review takes roughly the time of the slowest skill, not the sum.
- Each subagent has its own context window, so a large review does not exhaust a single context.
- Subagents write their own reports, so the orchestrator does not need to collect and save large outputs.
- The orchestrator can aggregate grades and produce a cross-cutting TODO that no single skill could produce alone.

**Negative:**

- Subagents cannot communicate with each other — if one finds a coupling issue that another should investigate, there is no inter-subagent messaging. The orchestrator's TODO aggregation partially compensates.
- A subagent failure or timeout must be handled gracefully — the orchestrator creates a placeholder report and continues rather than aborting the entire review.

**Neutral:**

- The orchestrator runs a tokensave pre-flight check before launching subagents to ensure the code-graph index is fresh. This avoids all subagents independently detecting staleness and racing to sync.
