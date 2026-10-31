---
audience: ai, human
status: stable
skills: [review, setup]
description: "Entry-point modules that wrap an orchestrator's CLI are named *_client.py — 'cli' as a filename suffix is an abbreviation that violates the class-name-mandates-filename convention."
---

# ADR-0013: CLI entry modules are named `*_client`, not `*_cli`

## Status

Accepted

## Context

`adr_cli.py` and `documentor_cli.py` were the only files in `src/` whose names carried an abbreviation token (`cli`). Under `classes.1` — a class mandates its filename — `ADRCLI` / `DocumentorCLI` also forced mixed-case acronym usage that sits awkwardly with `classes.2`. Repeated reviews flagged the names; the rename kept waiting on an ADR amendment because the files are referenced by AGENTS.md, the SUBSKILL contracts, ~10 documentation pages, scanner docstrings, and three test files.

## Decision

Entry-point modules that wrap an orchestrator's argument handling are named `<domain>_client.py`, and their classes `DomainClient`: `adr_client.py` → `ADRClient`, `documentor_client.py` → `DocumentorClient`. The `cli` token is reserved for describing the *interface* in prose, never as a filename or class-name suffix.

## Consequences

- Class-name ↔ filename alignment restored (classes.1); the acronym token disappears from names entirely.
- Doc references to `documentor_client.py` / `adr_client.py` are repo-root-relative and stable.
- `python3 src/.../<domain>_client.py [--json]` keeps working — ADR-0011's invocation contract is unchanged.
