---
audience: ai
status: generated
---

# adr-distilled.md — Architectural Directives

> Auto-generated from the project's ADRs by the adr-distiller.
> Do not edit directly — edit the source ADRs and re-run `/zolletta-metaskill adr-distiller` or `/zolletta-metaskill review`.
> Each directive links to its source ADR for full context. Only Accepted decisions are included.

- [ADR-0001](0001-meta-skill-with-subcommand-dispatch.md) We use a single meta-skill with subcommand dispatch.
- [ADR-0002](0002-settings-json-as-single-config-source.md) Setup writes a single .zolletta-metaskill/settings.json file containing all project-wide configuration.
- [ADR-0003](0003-diataxis-framework-for-documentation.md) We adopt the Diátaxis framework for the project's documentation.
- [ADR-0004](0004-python-stdlib-only-for-scanners.md) All scanning scripts use Python 3.12+ standard library only.
- [ADR-0005](0005-review-orchestrator-with-parallel-subagents.md) The review orchestrator launches one subagent per specialist skill in parallel; each writes its own report, and the orchestrator aggregates grades into SUMMARY.md and a prioritized TODO.md.
- [ADR-0006](0006-setup-guard-pattern.md) Every subcommand runs a setup guard: if settings.json is missing, run full setup first; if pyproject.toml/composer.json changed, re-extract only the tool config.
- [ADR-0007](0007-language-neutral-engine-protocol.md) We introduce a LanguageEngine protocol with a ModuleInfo data model.
- [ADR-0008](0008-skills-directory-grouping.md) All sub-skills (subfolders with SKILL.md) are grouped under a skills/ directory, with ../../ relative paths back to shared resources.
- [ADR-0009](0009-inline-shell-replaced-with-python-scripts.md) Inline shell detection commands in setup are replaced by standalone, testable Python scripts under src/zolletta_metaskill/setup/ (stdlib only, JSON output, unit-tested).
- [ADR-0010](0010-add-adr-distiller.md) An ADR distiller extracts Accepted ADRs into adr-distilled.md (one-line directives with source links), kept in sync via an mtime cache, and read by review subagents as architectural context.
