---
audience: ai, human
status: stable
skills: [review]
description: "Engine capabilities are separate protocols: LanguageEngine for ModuleInfo, RawAstEngine for parser trees, no concrete engine in a scanner."
---

# ADR-0010: Engine capabilities are separate protocols

## Status

Accepted — supersedes [ADR-0005](0005-language-neutral-engine-protocol.md)

## Context

ADR-0005 established that scanners consume a language-neutral `ModuleInfo` produced by a
`LanguageEngine`, never a language-specific AST. That decision holds and is not in question here.

Two things had drifted away from it since.

**The protocol declared capabilities nobody used.** `LanguageEngine` carried six members. Three of
them — `is_test_file`, `is_source_file`, `test_file_glob` — were implemented by both engines and
called by nothing. `EngineRegistry` used `file_extensions()`; every other consumer went through
`ProjectConfig`, which is where file classification already lives. The only callers were the members'
own tests, which is how dead surface stays alive: the tests are the sole proof of existence.

**Scanners reached past the protocol to get a parser tree.** ADR-0005 recorded this as an accepted
negative: *"Engines needing richer data (e.g. `PHPEngine.parse_raw`) bypass the protocol for their
own consumers."* Four scanners took the bypass literally and guarded with
`isinstance(engine, PHPEngine)` to obtain `parse_raw`. Three of them were language-general —
`cyclomatic_complexity_scanner` lives in `code_style/general/` — so a general scanner coupled itself
to one language's engine in order to express "I need the parser's own tree". A fifth guard in
`acronym_casing_scanner` asserted the same type but called `parse_module`, which the protocol already
declared, so it bought nothing.

## Decision

An engine's capabilities are stated by separate, narrow protocols. A consumer depends on the
capability it needs, never on a concrete engine.

- **`LanguageEngine`** keeps only what scanners actually use: `language`, `parse_module`,
  `file_extensions`. File classification is `ProjectConfig`'s job and is deliberately not on any
  protocol.
- **`RawAstEngine`** is a second protocol, declared in its own module, for engines that can return
  their parser's own tree: `parse_raw(path) -> tuple[Any, bytes]`.
- **No scanner imports a concrete engine to obtain a capability.** A scanner that needs a parser tree
  asks for `RawAstEngine`; one that needs `ModuleInfo` asks for `LanguageEngine`. Whether a given
  language satisfies either is the registry's problem.
- `parse_raw` returns `Any` for the tree. A tree-sitter tree is not a Python `ast.AST`, so naming
  either concrete type would put one engine's language into a protocol meant to stay neutral.

## Consequences

**Positive:**

- A language-general scanner no longer imports a specific language's engine. `cyclomatic_complexity_scanner`
  and `integration_graph_scanner` are general, and now say only what they require.
- A future engine that ships a tree — JavaScript, for instance — satisfies `RawAstEngine` with no
  change to any scanner.
- The protocol is now minimal in fact as well as in intent: three members, all used.

**Negative:**

- An engine providing both capabilities implements two protocols. That is two declarations, not two
  implementations — the methods are written once.
- `Any` in `parse_raw`'s return means the type checker cannot verify the tree's shape. This is the
  price of neutrality; naming `Tree` would import one parser into a shared protocol.
- The fifth guard was deleted rather than rewritten. `acronym_casing_scanner` calls `parse_module`,
  which `LanguageEngine` declares, so its `isinstance` check was removable outright.

**Neutral:**

- `is_test_file`, `is_source_file` and `test_file_glob` now exist nowhere in the engine layer. If a
  future consumer needs them, it should ask `ProjectConfig`, not resurrect them on a protocol.

## Supersession

This record supersedes ADR-0005, which remains in the corpus as history per
[ADR-0000](0000-adrs-record-architecture-not-activity.md). ADR-0005's central decision — scanners
consume a neutral `ModuleInfo` — is carried forward here unchanged; what changed is the protocol's
surface and the addition of a second, narrower capability protocol for parser trees.