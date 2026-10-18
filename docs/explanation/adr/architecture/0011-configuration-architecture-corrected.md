---
audience: ai, human
status: stable
skills: [review]
description: "Configuration architecture, corrected: one settings source, setup guard, [--json]-only CLIs, immutable structs, no cache_dir override, and a tracked settings.json where reproducibility demands it."
---

# ADR-0011: Configuration architecture — corrected, and superseding ADR-0002

## Status

Accepted — supersedes [ADR-0002](0002-configuration-architecture.md)

## Context

[ADR-0002](0002-configuration-architecture.md) settled where configuration lives, how it stays fresh, how scripts receive it, and how it flows internally. Its five rules all still hold and are carried forward unchanged below. Two of its **Neutral** consequences no longer describe the code, and an Accepted record cannot be edited, so they are corrected here.

The first is `documentation.cache_dir`. The override was honoured by `resolve_cache_dir` but declared nowhere — `$defs.documentation` closes with `additionalProperties: false` and never listed the key, so **no valid `settings.json` could ever set it**. A feature nobody can configure is not a feature, and the branch was deleted on 2026-10-11 rather than deprecated. ADR-0002:49 still described it as *"the only way to point output outside the repository"*.

The second is this repository's own behaviour, not a change to the product. ADR-0002:48 stated that `settings.json` is *"a generated, gitignored artifact"*. That is still the default, and setup still generates it. It stopped being true here on 2026-10-18, when `.gitignore` was narrowed from `.zolletta-metaskill/` to `.zolletta-metaskill/*` so that `settings.json` alone is tracked.

The reason is silent-wrong-number behaviour. `ProjectConfig.load_settings` returns `{}` when the file is missing — no error, no warning — so a fresh clone ran every sensor on different numbers than its own rules stated: `max_function_length` fell from 125 to a built-in 100 and `function_length_scanner` reported three functions that are compliant here. The thresholds are local configuration; no setup detector derives them, and `settings_template.json` carries `"python": null`, so regenerating would not restore them.

## Decision

`.zolletta-metaskill/settings.json` is the single configuration source, guarded for freshness, read via `[--json]`-only CLIs, and resolved once into immutable structs.

The rules, carried forward from [ADR-0002](0002-configuration-architecture.md) and unchanged:

- **Single source.** Setup writes `.zolletta-metaskill/settings.json`, validated by `settings.schema.json`; every subcommand and script reads from it instead of re-detecting or accepting flags.
- **Setup guard.** Every subcommand runs a guard first: no settings → full setup; stale `pyproject.toml`/`composer.json` (mtime compare) → light re-extraction only.
- **Uniform CLI.** Script surface is `[--json]` only — no positional roots, no `--strict`/`--skip`, no threshold flags. `check_*` toggles replace `--skip`; scripts are report-only (exit 0 with findings) except the designed `staleness_threshold` gate in quality review. Genuinely operational args (`--apply`, `--dry-run`, `--broken-only`, `--show-methods`) and pre-settings setup detectors are exempt.
- **Resolve once, pass down.** A `from_settings` classmethod is the only place each settings key is read, producing `frozen=True` dataclasses — `DocumentorSettings` is frozen; below the entry point a raw `settings` dict is never a parameter. Derived values are properties, not fields; collections are stored as tuples; bundling is by role and lifetime (`GitRunContext` runtime facts ≠ `DocumentorSettings` config), never by argument count.
- **Git-aware enumeration.** `ProjectConfig.iter_files` honours `.gitignore` and every other exclude source git knows.

Two corrections, both narrow:

- **`documentation.cache_dir` does not exist.** There is no override, and the output directory is not configurable through `settings.json`. Cache resolution is `<runs_dir>/<latest-run>/cache/`, falling back to `<runs_dir>/cache` before any run directory exists.
- **`settings.json` is a generated artifact that a project may deliberately track.** It stays gitignored by default; a project whose review thresholds must be identical on every machine tracks it. Tracking it is what makes the thresholds in this repository reproducible from a fresh clone. The cost is that `setup_timestamp`, `python.tools.*.available` and `pyproject_mtime` are the committing machine's values and churn when a teammate runs setup — accepted deliberately, because reproducible review beats a tidy diff.

## Consequences

**Positive:**

- Detection happens once; scripts start instantly with consistent config and run argument-free from the project root.
- Review policy is declarative and reproducible — thresholds and toggles live in the same file CI and humans read.
- One place reads each key; a settings-derived value is distinguishable by type, which makes arity limits enforceable and contradictory states unrepresentable.
- A tracked `settings.json` makes a project's review policy auditable: the thresholds a review enforced are in the repository, not in one developer's home directory.

**Negative:**

- Adding a key means touching the schema, prose doc, setup skill, struct, resolver, and consumers — more files per key than reading settings inline. Deliberate cost of the boundary.
- Ad-hoc overrides ("scan just this dir once") require editing `settings.json` — deliberately, so overrides are visible and persistent.
- Standalone helper invocations must construct the struct by hand.
- A tracked `settings.json` diffs on every setup run for reasons unrelated to policy. The alternative is a silent fallback to different numbers, which is worse.

**Neutral:**

- A missing `settings.json` degrades to defaults rather than failing. This is the failure mode tracked `settings.json` is meant to prevent, and it remains silent by design: `load_settings` returns `{}` for a missing, unreadable, or non-object file alike.
- `documentation.cache_dir` is not a key, and `additionalProperties: false` means a `settings.json` carrying one is rejected by the schema rather than ignored.
