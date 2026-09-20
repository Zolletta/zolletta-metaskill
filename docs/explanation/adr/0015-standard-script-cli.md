# ADR-0015: Standard script CLI — settings.json as the only config source

## Status

Accepted

## Context

Every review script used to carry its own bespoke CLI surface: positional source/test directories, `--strict`/`--skip` toggles, per-check threshold flags (`--min-methods`, `--min-branches`, `--top`, `--min-lines`, `--min-segments`), path flags (`--src`, `--tests`, `--docs-dir`, `--adrs-path`, `--cache-dir`), and behavior flags (`--recursive`, `--include-private`, `--suggest-coverage`, `--check-external`, `--weight-*`). Problems with that approach:

- The same project facts (source roots, test roots, docs dir) were re-specified on every invocation — easy to get wrong, impossible to keep consistent across a review.
- `--strict`/`--skip` duplicated what `check_*` settings already express, and let individual invocations diverge from the configured review policy.
- New knobs meant new flags in every script's parser plus doc updates — the CLI surface grew without bound.
- Scripts hardcoded `src`/`tests` defaults even though `settings.json` already knew the real roots (PHP via Composer autoload; Python had no equivalent until `python.paths`).

ADR-0002 established `settings.json` as the single configuration source for *setup-time* facts. This ADR extends it to *all* script configuration.

## Decision

All review scripts share one CLI contract:

- **Common surface is `[--json]` only.** No positional directories, no `--strict`, no `--skip`, no per-check threshold/path/behavior flags.
- **Everything else comes from `.zolletta-metaskill/settings.json`** via `ProjectConfig` (`core/project_config.py`): per-language scan roots (`python.paths.*`, PHP Composer `autoload`/`autoload-dev` PSR-4 mappings), thresholds (`<lang>.patterns.*`, `<lang>.code_style.*`, `<lang>.testing.*`), check toggles (`<lang>.<area>.check_*`), and `documentation.*` options for the documentor tools.
- **Report-only by default.** Findings never fail the run — scripts exit 0 with violations present. Exit 1 is reserved for usage errors (no configured roots on disk). The one exception is `doc_staleness_scorer.py`, which keeps a threshold gate via `documentation.staleness_threshold` because a CI freshness gate is its purpose.
- **`check_*` toggles replace `--skip`.** A check disabled for every configured language reports SKIPPED and exits 0 — same result, but the policy lives in settings, not in whoever typed the command.
- **File enumeration is git-aware.** `ProjectConfig.iter_files` honours `.gitignore`/`.git/info/exclude`/`core.excludesFile`, so `vendor/`, `node_modules/`, `__pycache__/`, and build output never need per-script `--ignore-dirs` flags.
- **Genuinely operational arguments stay.** `test_splitter.py` keeps `test_file`/`--mapping`/`--class`/`--dry-run` (per-invocation inputs, not configuration), `docstring_streamliner.py` keeps `--apply`, `link_checker.py` keeps `--broken-only`, `doc_staleness_scorer.py` keeps `--quiet`, `test_god_classes_scanner.py` keeps `--show-methods`. These are display or action modifiers, not project configuration.
- **Setup detectors are exempt.** `language_detector`, `python_paths_detector`, `doc_config_detector`, etc. keep their optional positional directory — they run *before* `settings.json` exists, so they cannot read from it (chicken-and-egg).

The setup skill (v3.0.0) detects and backfills the new keys additively, preserving user-customized values.

## Consequences

**Positive:**

- One consistent invocation pattern: `python3 <script>.py [--json]`, runnable from the project root with zero arguments.
- Review policy is declarative and reproducible — thresholds and toggles live in the same file CI and humans read, not scattered across invocation sites.
- Removing `--strict` eliminates the "same violations, different exit code depending on who ran it" inconsistency.
- New checks need only a schema key, not a parser flag.
- Scripts work without `settings.json` too — `ProjectConfig` falls back to registered engines and `src`/`tests`/`docs` defaults.

**Negative:**

- Ad-hoc overrides ("scan just this directory once") now require editing `settings.json` or accepting the whole configured scope — deliberately, so overrides are visible and persistent rather than ephemeral.
- The settings schema grew substantially (`python.paths`, per-language `patterns`/`code_style`/`testing` knobs, `documentation.*`); the schema, template, prose doc, and setup skill must stay in sync (already a known cost from ADR-0002).
- Threshold gating in CI is only available where it was designed in (staleness scorer); other checks need the orchestrator or CI to interpret findings.

**Neutral:**

- Generated artifacts (split tests, run reports) move under `runs_dir` (default `.zolletta-metaskill/`), keeping the working tree clean.
