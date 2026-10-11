---
audience: human, ai
status: stable
skills: []
---

# Explanation

Background, principles, and design choices. Aimed at readers who want context.

## Code review principles

SOLID, structural conventions, error handling, performance, and security.

| Document                                                       | Description                                                              |
|----------------------------------------------------------------|--------------------------------------------------------------------------|
| [General principles](code/general-principles.md)               | SOLID, KISS, composition over inheritance, God class detection           |
| [Structural conventions](code/structural-conventions.md)       | One class per file, test mirroring, naming, test splitting               |
| [False positive prevention](code/false-positive-prevention.md) | Suppression rules to avoid noisy reports                                 |
| [Balanced coupling](code/balanced-coupling.md)                 | Integration strength, distance, volatility, and the balance rule         |
| [Error handling](code/error-handling.md)                       | Custom exceptions, hierarchy, specific catches, finally cleanup          |
| [Performance](code/performance.md)                             | Lazy loading, generators for large datasets                              |
| [Security](code/security.md)                                   | Parameterized queries, output escaping, input validation, secrets in env |

## Language-specific patterns

Strategy autodiscovery, Protocol vs ABC, interface vs abstract, traits.

| Document                                                        | Description                                                                    |
|-----------------------------------------------------------------|--------------------------------------------------------------------------------|
| [Python review patterns](code/python/python-review-patterns.md) | Strategy autodiscovery, Protocol vs ABC                                        |
| [PHP review patterns](code/php/php-review-patterns.md)          | Strategy autodiscovery, interface vs abstract, traits, suppression-with-reason |

## Documentation principles

Docs-as-code, README structure, API docs, changelogs, ADRs, and drift prevention.

| Document                                              | Description                                                 |
|-------------------------------------------------------|-------------------------------------------------------------|
| [Documentation standards](documentation/standards.md) | Docs-as-code principles and the four types of documentation |
| [README structure](documentation/readme.md)           | README best practices and anti-patterns                     |
| [API documentation](documentation/api.md)             | Function, class, and module documentation patterns          |
| [Changelog conventions](documentation/changelog.md)   | Keep-a-Changelog format and rules                           |
| [Architecture Decision Records](documentation/adr.md) | ADR format and best practices                               |
| [Drift prevention](documentation/drift-prevention.md) | Coupling strategies, CI gates, review checklists            |

## Architecture Decision Records

Standing architectural decisions and their rationale. The A in ADR is *Architecture*, not activity — non-architecture records live in `adr/activity/` (an AI-facing log, not published here), and the [ADR directory guide](adr/README.md) routes records to the right folder. The pre-reform ADR-0001–0017 records were consolidated into this corpus or removed, and stay decodable through git history.

| Document                                                                                            | Description                                                        |
|-----------------------------------------------------------------------------------------------------|--------------------------------------------------------------------|
| [ADR-0000 ADRs record architecture](adr/architecture/0000-adrs-record-architecture-not-activity.md) | ADR semantics, status lifecycle, corpus layout                     |
| [ADR-0001 Meta-skill architecture](adr/architecture/0001-meta-skill-architecture.md)                | Meta-skill dispatch, sub-skill grouping, parallel review           |
| [ADR-0002 Configuration architecture](adr/architecture/0002-configuration-architecture.md)          | Single settings source, setup guard, `[--json]` CLIs, immutability |
| [ADR-0003 Diátaxis documentation](adr/architecture/0003-diataxis-documentation-structure.md)        | Diátaxis framework for documentation structure                     |
| [ADR-0004 Scanner constraints](adr/architecture/0004-scanner-constraints.md)                        | Scanners use Python stdlib only and are testable modules           |
| [ADR-0005 Language-neutral engine](adr/architecture/0005-language-neutral-engine-protocol.md)       | LanguageEngine protocol with ModuleInfo model                      |
| [ADR-0006 ADR governance pipeline](adr/architecture/0006-adr-governance-pipeline.md)                | Distillation of Accepted ADRs into review directives               |
| [ADR-0007 Sensor adoption criteria](adr/architecture/0007-sensor-adoption-criteria.md)              | Standing criteria for integrating tools into the pipeline          |
| [ADR-0008 Balanced coupling model](adr/architecture/0008-balanced-coupling-model.md)                | Balanced Coupling model for the patterns review                    |
