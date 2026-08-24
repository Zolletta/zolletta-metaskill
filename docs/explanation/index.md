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
| [Error handling](code/error-handling.md)                       | Custom exceptions, hierarchy, specific catches, finally cleanup          |
| [Performance](code/performance.md)                             | Lazy loading, generators for large datasets                              |
| [Security](code/security.md)                                   | Parameterized queries, output escaping, input validation, secrets in env |

## Language-specific patterns

Strategy autodiscovery, Protocol vs ABC, interface vs abstract, traits.

| Document                                                        | Description                                           |
|-----------------------------------------------------------------|-------------------------------------------------------|
| [Python review patterns](code/python/python-review-patterns.md) | Strategy autodiscovery, Protocol vs ABC               |
| [PHP review patterns](code/php/php-review-patterns.md)          | Strategy autodiscovery, interface vs abstract, traits |

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

Design decisions and their rationale, captured as numbered ADRs.

| Document                                                                               | Description                                       |
|----------------------------------------------------------------------------------------|---------------------------------------------------|
| [ADR-0001 Meta-skill dispatch](adr/0001-meta-skill-with-subcommand-dispatch.md)        | Single meta-skill with subcommand dispatch        |
| [ADR-0002 Settings.json](adr/0002-settings-json-as-single-config-source.md)            | Single config source for project-wide settings    |
| [ADR-0003 Diátaxis framework](adr/0003-diataxis-framework-for-documentation.md)        | Diátaxis framework for documentation structure    |
| [ADR-0004 Python stdlib only](adr/0004-python-stdlib-only-for-scanners.md)             | Scanners use Python stdlib only, no external deps |
| [ADR-0005 Parallel subagents](adr/0005-review-orchestrator-with-parallel-subagents.md) | Review orchestrator with parallel subagents       |
| [ADR-0006 Setup guard](adr/0006-setup-guard-pattern.md)                                | Setup guard pattern for settings staleness        |
| [ADR-0007 Language-neutral engine](adr/0007-language-neutral-engine-protocol.md)       | LanguageEngine protocol with ModuleInfo model     |
| [ADR-0008 Skills directory](adr/0008-skills-directory-grouping.md)                     | Sub-skills grouped under skills/ directory        |
| [ADR-0009 Python scripts](adr/0009-inline-shell-replaced-with-python-scripts.md)       | Inline shell replaced by testable Python scripts  |
| [ADR-0010 ADR distiller](adr/0010-add-adr-distiller.md)                                | ADR distiller for extracting accepted directives  |
