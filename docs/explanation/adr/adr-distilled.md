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
- [ADR-0008](0008-skills-directory-grouping.md) All subfolders containing a sub-skill are grouped under a skills/ directory.
- [ADR-0009](0009-inline-shell-replaced-with-python-scripts.md) Inline shell detection commands in setup are replaced by standalone, testable Python scripts under src/zolletta_metaskill/setup/ (stdlib only, JSON output, unit-tested).
- [ADR-0010](0010-add-adr-distiller.md) An ADR distiller extracts Accepted ADRs into adr-distilled.md (one-line directives with source links), kept in sync via an mtime cache, and read by review subagents as architectural context.
- [ADR-0011](0011-skip-external-dependency-inspector.md) We do not integrate an external dependency inspector tool into Zolletta-metaskill.
- [ADR-0012](0012-skip-property-based-testing-sensor.md) We do not add a property-based testing sensor to Zolletta-metaskill.
- [ADR-0013](0013-skip-fuzz-testing-sensor.md) We do not add a fuzz testing sensor to Zolletta-metaskill.
- [ADR-0014](0014-add-mutation-testing-sensor.md) Mutation testing is a **conditional** sensor: setup detects mutmut/Infection availability only; the testing-style skills run it incrementally (`mutation_target: "changed"`) gated by `check_mutation_testing` **and** a green coverage run; a stdlib-only reporter parses survived mutants deterministically, and score below `mutation_score_threshold` is a high finding.
- [ADR-0015](0015-standard-script-cli.md) Every review script's CLI surface is `[--json]` only — scan roots, thresholds and `check_*` toggles come exclusively from `settings.json` via `ProjectConfig`; scripts are report-only (exit 0 with findings), file enumeration is git-aware, and only genuinely operational args (`--apply`, `--broken-only`, `--dry-run`, `--show-methods`) plus pre-`settings.json` setup detectors are exempt.
- [ADR-0017](0017-balanced-coupling-model.md) Adopt the Balanced Coupling model in the patterns review as deterministic triage (integration_graph_scanner.py emits internal edges) plus a judgment pass that flags only unbalanced-and-volatile integrations.
