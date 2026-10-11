---
audience: ai, human
status: stable
skills: [review]
description: "Language-neutral engine protocol: scanners consume ModuleInfo from LanguageEngine implementations."
---

# ADR-0005: Language-neutral engine protocol

## Status

Accepted

## Context

Scanners (class metrics, SOLID, test structure) originally consumed Python's `ast` module directly. Adding PHP would have meant a parallel implementation per scanner via tree-sitter — doubling maintenance and risking divergence — and each new language another full set of scanner implementations.

## Decision

Scanners consume a language-neutral `ModuleInfo` model produced by `LanguageEngine` implementations, never language-specific ASTs.

- `ModuleInfo` carries what scanners need: classes, functions, imports, and metrics (method/attribute/line counts).
- `LanguageEngine` is the protocol that parses a source file into `ModuleInfo`: `PythonEngine` wraps `ast`, `PHPEngine` wraps tree-sitter with the tree-sitter-php grammar (optional dependency, degrades gracefully).
- An engine registry (`register`/`get`/`get_for_file`/`available_languages`) maps file extensions to engines.

## Consequences

**Positive:**

- A new language requires implementing one engine, not rewriting scanners; scanners are tested once against `ModuleInfo` fixtures.
- The protocol is minimal — engines only owe `ModuleInfo`, not a full language toolchain.

**Negative:**

- `ModuleInfo` is a lowest-common-denominator abstraction: language-specific features that don't map to its fields are invisible to scanners. Engines needing richer data (e.g. `PHPEngine.parse_raw`) bypass the protocol for their own consumers.
- A Python-only scanner pays the indirection cost without benefiting from multi-language support.

**Neutral:**

- Scanners in shared/general packages must not import `ast` or tree-sitter — that dependency is the testable seam of this decision.
