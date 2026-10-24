---
audience: ai, human
status: stable
skills: [review, setup]
description: "Why max_cyclomatic_complexity defaults to 12 and max_function_length to 125 — skill defaults chosen for parser-shaped code, not ruff C901 parity."
---

# ADR-0012: Thresholds are skill defaults, not ruff defaults

## Status

Accepted

## Context

Two scanner thresholds were raised during a review-driven refactor: `max_cyclomatic_complexity` from 10 to 12 and `max_function_length` from 100 to 125. The only recorded justification at the time claimed that 12 "matches ruff `C901`" — which is false: ruff's built-in `C901` default is 10. A threshold raised on an incorrect justification is indistinguishable from silent suppression, and three consecutive reviews flagged it.

The legitimate rationale exists but was never written down. The codebase this skill scans — including itself — is dominated by parser-shaped code: AST walkers, tree-sitter dispatchers, and scanner emit functions whose branchiness is the shape of a closed grammar, not mixed responsibility. At 10 and 100 the sensors flag exactly those cohesive dispatchers — the same class of false positive the God-class rules already warn against. At 12 and 125 the sensors still catch genuine growth past the dispatch shape without crying wolf on every visitor method.

## Decision

`max_cyclomatic_complexity` defaults to 12 and `max_function_length` to 125 as **this skill's own defaults**, deliberately above ruff's `C901` default of 10 and not claimed to mirror any external tool. Setup seeds `max_cyclomatic_complexity` from `python.tools.ruff.max_complexity` when a project configures it, so a project that *does* want ruff parity sets it in `[tool.ruff.lint.mccabe]` and the skill follows.

## Consequences

- All documentation and schema text must state the default as "this skill's own default; ruff's built-in `C901` default is 10" — any future "matches ruff" claim is a regression to be reverted.
- Functions at complexity 11–12 pass by decision, not by accident; a function at 13 is still a finding and cannot appeal to the dispatch exception without refactor.
- A project that needs the stricter bound lowers the key in `settings.json`; no scanner code changes.
