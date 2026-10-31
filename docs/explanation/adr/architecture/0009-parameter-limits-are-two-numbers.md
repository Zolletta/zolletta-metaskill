---
audience: ai, human
status: stable
skills: [review]
description: "Why max_arguments measures declared parameters and dataclass fields get their own limit, max_dataclass_fields."
---

# ADR-0009: Parameter limits are two numbers, not one

## Status

Accepted

## Context

`max_arguments` counted only *declared* function and method parameters, so a `@dataclass` with ten fields — an implicit `__init__` of ten parameters — was invisible to it. Teaching the scanner to read dataclass fields closed the blind spot, but at the shared limit of 5 it immediately reported every value object in the codebase: `DocumentorSettings` (10), `SourceSignature` (10), `ClassInfo`, `ModuleInfo`, `MethodInfo` (8), three `Finding`s, `ADRRecord`, `DistillReport`, `TestStructureResults` (6+). Frozen DTOs are data, not complex callables — splitting them would break their contracts to satisfy a rule aimed at function arity.

## Decision

A dataclass's annotated fields count as constructor parameters, with a separate limit, `code_style.max_dataclass_fields`, set per language and defaulting to 10. Function and method signatures stay at `max_arguments` (5).

## Consequences

- A value object over 10 fields is flagged; one under is not — the 11 known structs pass.
- A project that wants DTOs held tighter can lower the key without touching function arity.
- The finding kind is `Dataclass` so reports distinguish "function grew too many params" from "value object grew too wide".
