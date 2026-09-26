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
- [ADR-0005](0005-review-orchestrator-with-parallel-subagents.md) The review skill launches one subagent per command, all in parallel as background subagents.
- [ADR-0006](0006-setup-guard-pattern.md) Every subcommand runs a setup guard: if settings.json is missing, run full setup first; if pyproject.toml/composer.json changed, re-extract only the tool config.
- [ADR-0007](0007-language-neutral-engine-protocol.md) We introduce a LanguageEngine protocol with a ModuleInfo data model.
- [ADR-0008](0008-skills-directory-grouping.md) Sub-skills live under skills/ in folders named after their skill name; files named SUBSKILL.md are hidden from external `**/SKILL.md` discovery.
- [ADR-0009](0009-inline-shell-replaced-with-python-scripts.md) Inline shell detection commands in setup are replaced by standalone, testable Python scripts under src/zolletta_metaskill/setup/ (stdlib only, JSON output, unit-tested).
- [ADR-0010](0010-add-adr-distiller.md) An ADR distiller extracts Accepted ADRs into adr-distilled.md (one-line directives with source links), kept in sync via an mtime cache, and read by review subagents as architectural context.
- [ADR-0011](0011-skip-external-dependency-inspector.md) We do not integrate an external dependency inspector tool into Zolletta-metaskill.
- [ADR-0012](0012-skip-property-based-testing-sensor.md) We do not add a property-based testing sensor to Zolletta-metaskill.
- [ADR-0013](0013-skip-fuzz-testing-sensor.md) We do not add a fuzz testing sensor to Zolletta-metaskill.
- [ADR-0014](0014-add-mutation-testing-sensor.md) We add a conditional mutation-testing sensor: setup detects mutmut (Python) / Infection (PHP) availability; the testing-style skills run it on the `changed` scope when installed, opted-in, and the coverage run is green, with deterministic survived-mutant extraction by mutmut_survived_reporter.py.
- [ADR-0015](0015-standard-script-cli.md) All review scripts share one CLI contract: --json only; scan roots, toggles, and thresholds come from .zolletta-metaskill/settings.json via ProjectConfig.
