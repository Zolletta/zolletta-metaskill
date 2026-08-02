# ADR-0007: Language-neutral engine protocol

## Status

Accepted

## Context

The scanning scripts (class metrics, SOLID violation detection, test structure validation) originally used Python's `ast` module directly. When PHP support was added, the scripts would need a parallel implementation using tree-sitter — doubling the maintenance burden and risking divergence between language-specific code paths.

Without abstraction, adding a third language would require another full set of scanner implementations.

## Decision

We introduce a `LanguageEngine` protocol with a `ModuleInfo` data model. Scanners consume `ModuleInfo` via the protocol, not language-specific AST directly.

- `ModuleInfo` is a language-neutral data structure containing the information scanners need: classes, functions, imports, metrics (method count, attribute count, line count).
- `LanguageEngine` is a protocol that defines how to parse a source file into `ModuleInfo`.
- `PythonEngine` wraps the `ast` module.
- `PHPEngine` wraps tree-sitter with the tree-sitter-php grammar.
- An engine registry (`register_engine` / `get_engine` / `get_engine_for_file` / `available_languages`) maps file extensions to engines.

Scanners in `shared/` and `patterns/` are now language-agnostic — they operate on `ModuleInfo` and do not know whether the source was Python or PHP.

## Consequences

**Positive:**
- Adding a new language requires implementing an engine, not rewriting scanners. The scanners work with any language that has an engine.
- Scanners are tested once against `ModuleInfo` fixtures, not per-language.
- The protocol is minimal — engines only need to produce `ModuleInfo`, not implement a full language toolchain.

**Negative:**
- `ModuleInfo` is a lowest-common-denominator abstraction. Language-specific features that do not map to `ModuleInfo` fields are invisible to scanners. Engines that need richer data (e.g., PHP's `parse_raw()` for direct tree-sitter access) bypass the protocol.
- The protocol adds an indirection layer — a scanner that only needs Python pays the cost of the abstraction without benefiting from multi-language support.

**Neutral:**
- tree-sitter and tree-sitter-php are optional dependencies. The PHPEngine degrades gracefully if they are not installed — PHP review is skipped with a "not installed" message.
