---
audience: ai, human
status: stable
skills: [review]
description: "Scanner constraints: Python stdlib only, unit-testable modules, deliberate dependency kinds."
---

# ADR-0004: Scanner constraints — stdlib-only, unit-tested scripts

## Status

Accepted

## Context

The project ships scanning and detection scripts that must be fast, portable, and deterministic inside the review pipeline — including on machines with limited network access or strict dependency policies. Two failure modes had to be designed out: external dependencies adding install friction and supply-chain risk, and logic embedded in skill files (inline shell in SKILL.md steps) being untestable, non-portable, and impossible to debug in isolation.

## Decision

All scanning and detection scripts use the Python standard library only and are unit-testable modules, never inline skill logic.

The rules:

- **Stdlib only for runtime.** `tomllib` for TOML, `ast` for Python source, `json`/`pathlib`/`subprocess` everywhere. Dev tooling (`uv`, `ruff`, `pytest`, `mypy`, `vulture`) is a dev dependency, never a runtime one.
- **Every script is a testable unit** — a standalone module with a `main()` CLI (see ADR-0002 for the `[--json]`-only surface) covered by its own test file under the mirrored `tests/` layout; the setup package holds 100% coverage.
- **Deliberate dependency kinds.** Optional language support may declare extras (`zolletta-metaskill[php]` for `tree-sitter-php`, imported lazily with a clear `ImportError`); hard dependencies are imported at module scope and declared — never smuggled as runtime-optional.

## Consequences

**Positive:**

- Zero install friction for Python-only projects; deterministic behavior across shells and platforms; minimal supply-chain surface.
- Each detection/scan step is unit-testable against temp fixtures — a failure is debugged in a test, not by re-running a whole skill.

**Negative:**

- Some tasks are harder with stdlib only (no rich output, no third-party parsers) — accepted tradeoff.
- Optional-dependency paths (PHP tree-sitter) need lazy imports and graceful degradation code — a small, bounded complexity cost per engine.

**Neutral:**

- The constraint applies to scripts' runtime, not to skill infrastructure or documentation tooling (mkdocs, link checkers, etc.).
