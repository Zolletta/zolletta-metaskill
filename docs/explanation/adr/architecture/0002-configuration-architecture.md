---
audience: ai, human
status: stable
skills: [review]
description: "Configuration architecture: single settings.json source, setup guard, [--json]-only CLIs, immutable structs."
---

# ADR-0002: Configuration architecture — settings.json, setup guard, uniform CLI, immutable structs

> **Superseded.** This record is kept as history per
> [ADR-0000](0000-adrs-record-architecture-not-activity.md). Its five rules are carried forward
> unchanged by
> [ADR-0011](0011-configuration-architecture-corrected.md), which corrects two **Neutral** claims
> below. `documentation.cache_dir` is gone — it was honoured in code but declared in no schema, so
> no valid `settings.json` could set it. And `settings.json`, while still generated and still
> gitignored by default, may now be tracked deliberately by a project that needs its review
> thresholds to be reproducible from a fresh clone; this repository does.

## Status

Superseded by [ADR-0011](0011-configuration-architecture-corrected.md)

## Context

Every review subcommand needs project facts: language, tool availability, rule toggles, scan roots, thresholds, documentation paths. Four questions had to be answered as one architecture: where configuration lives, how it stays fresh, how scripts receive it, and how it flows through code internally.

Without a single source, each subcommand re-detects facts (slow, inconsistent), each script grows bespoke CLI flags (`--src`, `--strict`, `--min-*`), and raw `dict[str, Any]` settings get re-inspected at every layer — which produced real defects: two divergent cache paths for the same artifacts and eleven methods exceeding the argument limit because settings-derived values were indistinguishable from ordinary parameters.

## Decision

`.zolletta-metaskill/settings.json` is the single configuration source, guarded for freshness, read via `[--json]`-only CLIs, and resolved once into immutable structs.

The rules:

- **Single source.** Setup writes `.zolletta-metaskill/settings.json` (validated by `settings.schema.json`); every subcommand and script reads from it instead of re-detecting or accepting flags.
- **Setup guard.** Every subcommand runs a guard first: no settings → full setup; stale `pyproject.toml`/`composer.json` (mtime compare) → light re-extraction only.
- **Uniform CLI.** Script surface is `[--json]` only — no positional roots, no `--strict`/`--skip`, no threshold flags. `check_*` toggles replace `--skip`; scripts are report-only (exit 0 with findings) except the designed `staleness_threshold` gate in quality review. Genuinely operational args (`--apply`, `--dry-run`, `--broken-only`, `--show-methods`) and pre-settings setup detectors are exempt.
- **Resolve once, pass down.** A `from_settings` classmethod is the only place each settings key is read, producing `frozen=True` dataclasses; below the entry point a raw `settings` dict is never a parameter. Derived values are properties, not fields; collections are stored as tuples; bundling is by role and lifetime (`GitRunContext` runtime facts ≠ `DocumentorSettings` config), never by argument count.
- **Git-aware enumeration.** `ProjectConfig.iter_files` honours `.gitignore`/excludes — no per-script ignore flags.

## Consequences

**Positive:**

- Detection happens once; scripts start instantly with consistent config and run argument-free from the project root.
- Review policy is declarative and reproducible — thresholds and toggles live in the same file CI and humans read.
- One place reads each key; a settings-derived value is distinguishable by type, which makes arity limits enforceable and contradictory states unrepresentable.

**Negative:**

- Adding a key means touching the schema, template, prose doc, setup skill, struct, resolver, and consumers — more files per key than reading settings inline. Deliberate cost of the boundary.
- Ad-hoc overrides ("scan just this dir once") require editing `settings.json` — deliberately, so overrides are visible and persistent.
- Standalone helper invocations must construct the struct by hand.

**Neutral:**

- `settings.json` is a generated, gitignored artifact; scripts degrade to `src`/`tests`/`docs` defaults without it.
- `documentation.cache_dir` remains an explicit override — the only way to point output outside the repository.
