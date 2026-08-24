---
audience: human, ai
status: stable
skills: [review, patterns, documentor, python-*, php-*]
---

# Scripts-first execution protocol

Shared rules for every subcommand that runs deterministic scanning scripts (scanners, ruff, mypy, ty, vulture, drift tools). This file is referenced by `python-code-style`, `python-testing-style`, `patterns`, `documentor`, and the `review` orchestrator. It applies identically to **standalone subcommand invocations** (i.e. `/zolletta-metaskill documentor`) and to subcommand subagents launched by `/zolletta-metaskill review`.

> **Companion to [review-mode.md](review-mode.md)**: review-mode defines *what* to do with diagnostics (two-bucket classification, no fixes). This protocol defines *how* to run the scripts that produce those diagnostics — batch-run them, cache their output, then apply judgment only to the items scripts defer.

## Principle

Scripts produce deterministic findings. The LLM consumes their cached output and only applies judgment where the scripts explicitly defer to judgment (marked **JUDGMENT** below). Everything else is mechanical report assembly from cached output — no source file reads, no re-derivation.

## Run directory structure

Every review run (standalone or orchestrated) creates a timestamped run folder:

```
<runs_dir>/<YYYY-MM-DD-HH-MM>/
├── reports/          ← LLM judgment (subcommand reports, SUMMARY.md, TODO.md)
└── cache/            ← deterministic artifacts (script outputs + shared context)
```

`runs_dir` is read from `settings.json` (default `.zolletta-metaskill`). The timestamp is the run start time, obtained via `date +%Y-%m-%d-%H-%M`.

- **`reports/`** — what a human reads: findings, severity, grades, TODOs. Written by the LLM.
- **`cache/`** — what the LLM reads instead of re-running scripts and re-reading source files. Written by Phase A. Also useful for audit/debugging.

## Three-phase execution

### Phase A — Batch script run + cache

1. **Create the run folder**: `<runs_dir>/<ts>/reports/` and `<runs_dir>/<ts>/cache/`.
2. **Enumerate applicable scripts** from the per-subcommand table below.
3. **Run all scripts in a single tool-call block of parallel `exec` calls.** Do not run them sequentially. Prefer `--json` output where available.
4. **Persist every script's output to `cache/<script_name>.{json,txt,md}`** — one file per script. Use the cache filenames listed in the per-subcommand table.
5. If a script is unavailable (tool not installed, `*.available: false` in `settings.json`), skip it and note "SKIPPED" in the cache file.

### Phase B — Mechanical report assembly (from cache)

1. **Read the cached script outputs from `cache/`** — do not re-run scripts, do not read source files.
2. **Populate the report's deterministic sections directly**:
   - Scanner tables copied verbatim from cache into the report.
   - Tool diagnostics classified into auto-fixable (informational) vs findings using the tool's own fix indicator (ruff `[F]`/`[*]`, ty fixable flag) — see [review-mode.md](review-mode.md) for the two-bucket rules.
   - Coverage gaps from `cache/pytest_cov.txt`.
3. **Write the report to `reports/<subcommand>.md`** following the report template.
4. **No source file reads in this phase.** Everything comes from cache.

### Phase C — Judgment pass (minimal)

Only for items the scripts explicitly defer to judgment. Read source files **only** for these specific items, not broadly. The judgment items per subcommand:

| Subcommand             | Judgment items (Phase C)                                                                                                                                                                                                                                                                                                                                            |
|------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `patterns`             | "Reason to change" test on top-N `class_metrics` candidates **[JUDGMENT]**; DIP composition-root suppression for flagged classes that wire DI containers **[JUDGMENT]**; "Missing tests" coverage cross-check (compare `cache/test_structure.md` "Missing tests" table against `cache/pytest_cov.txt` — downgrade to informational if coverage >50%) **[JUDGMENT]** |
| `documentor`           | False-positive filtering for known FP patterns (code-fence anchors in `cache/link_checker.json`, phantom class methods in `cache/api_doc_validator.json`, parameter name collisions) — only open source files for FP candidates **[JUDGMENT]**                                                                                                                      |
| `python-testing-style` | Indirect-coverage tracing for modules below the gap threshold in `cache/pytest_cov.txt` (use `tokensave_callers` or grep to check if callers are real vs mocked) **[JUDGMENT]**                                                                                                                                                                                     |
| `python-code-style`    | Vulture false-positive review for dynamically-accessed methods in `cache/vulture.txt` **[JUDGMENT]**                                                                                                                                                                                                                                                                |
| `php-code-style`       | PHPStan/Psalm false-positive review for dynamically-accessed methods **[JUDGMENT]**                                                                                                                                                                                                                                                                                 |
| `php-testing-style`    | PHPUnit coverage gap indirect-coverage tracing **[JUDGMENT]**                                                                                                                                                                                                                                                                                                       |

**All subcommands**: severity assignment and grade calculation **[JUDGMENT]**.

## Anti-patterns (forbidden)

- **Re-reading a source file the scanner already parsed**, unless the scanner flagged it AND judgment is required for that specific item.
- **Re-deriving a finding the scanner already emits** (e.g. manually listing one-class-per-file violations when `one_class_per_file_scanner.py` already listed them in cache).
- **Running scripts sequentially** when they could run in parallel — always batch in one tool-call block.
- **Re-running a script whose output is already in `cache/`** for this run — read from cache instead.
- **Reading mandatory reference docs in full at review time** — for orchestrator runs, the judgment-rules digest is inlined in `cache/_context.md`. For standalone runs, read only the specific judgment section you need, not the whole doc.

## Per-subcommand script table

The canonical script reference is [`scripts.md`](scripts.md) — refer to it for usage, options, and examples. The table below lists which scripts each subcommand must batch in Phase A and their cache filenames.

### `python-code-style`

| Script                                 | Cache file                      | Condition                                    |
|----------------------------------------|---------------------------------|----------------------------------------------|
| `ruff check`                           | `cache/ruff.txt`                | `python.tools.ruff.available`                |
| `ruff format --check`                  | `cache/ruff_format.txt`         | `python.tools.ruff.available`                |
| `ty check`                             | `cache/ty.txt`                  | `python.tools.ty.available`                  |
| `mypy`                                 | `cache/mypy.txt`                | `python.tools.mypy.available`                |
| `vulture src/ --min-confidence N`      | `cache/vulture.txt`             | `python.tools.vulture.available`             |
| `acronym_casing_scanner.py --json`     | `cache/acronym_casing.json`     | `python.code_style.check_acronym_casing`     |
| `unused_all_exports_scanner.py --json` | `cache/unused_all_exports.json` | always                                       |
| `one_class_per_file_scanner.py`        | `cache/one_class_per_file.txt`  | `python.code_style.check_one_class_per_file` |

### `python-testing-style`

| Script                                      | Cache file               | Condition                          |
|---------------------------------------------|--------------------------|------------------------------------|
| `pytest --cov --cov-report=term-missing -q` | `cache/pytest_cov.txt`   | `python.tools.pytest.available`    |
| `test_naming_scanner.py --json`             | `cache/test_naming.json` | `python.testing.check_test_naming` |

### `patterns`

| Script                             | Cache file                        | Condition       |
|------------------------------------|-----------------------------------|-----------------|
| `class_metrics_scanner.py`         | `cache/class_metrics.txt`         | always (Python) |
| `test_god_classes_scanner.py`      | `cache/test_god_classes.txt`      | always (Python) |
| `one_class_per_file_scanner.py`    | `cache/one_class_per_file.txt`    | always (Python) |
| `test_structure_scanner.py`        | `cache/test_structure.md`         | always (Python) |
| `dependency_inversion_scanner.py`  | `cache/dependency_inversion.txt`  | always (Python) |
| `interface_segregation_scanner.py` | `cache/interface_segregation.txt` | always (Python) |
| `open_closed_scanner.py`           | `cache/open_closed.txt`           | always (Python) |
| `liskov_substitution_scanner.py`   | `cache/liskov_substitution.txt`   | always (Python) |

For PHP projects, run the PHP equivalents from `src/zolletta_metaskill/patterns/php/` instead.

### `documentor`

| Script                           | Cache file                        | Condition |
|----------------------------------|-----------------------------------|-----------|
| `link_checker.py --json`         | `cache/link_checker.json`         | always    |
| `api_doc_validator.py --json`    | `cache/api_doc_validator.json`    | always    |
| `drift_analyzer.py --json`       | `cache/drift_analyzer.json`       | always    |
| `doc_staleness_scorer.py --json` | `cache/doc_staleness_scorer.json` | always    |

See [`documentation/operational-rules.md`](../documentation/operational-rules.md) for tool invocation conventions (project root as repo path, `--include-referential` suppression, etc.).

### `php-code-style`

| Script                                  | Cache file               | Condition                          |
|-----------------------------------------|--------------------------|------------------------------------|
| `vendor/bin/phpstan analyse`            | `cache/phpstan.txt`      | `php.tools.phpstan.available`      |
| `vendor/bin/psalm`                      | `cache/psalm.txt`        | `php.tools.psalm.available`        |
| `vendor/bin/php-cs-fixer fix --dry-run` | `cache/php_cs_fixer.txt` | `php.tools.php_cs_fixer.available` |
| `vendor/bin/phpcs`                      | `cache/phpcs.txt`        | `php.tools.phpcs.available`        |

### `php-testing-style`

| Script                               | Cache file              | Condition                     |
|--------------------------------------|-------------------------|-------------------------------|
| `vendor/bin/phpunit --coverage-text` | `cache/phpunit_cov.txt` | `php.tools.phpunit.available` |

## Shared scripts (orchestrator only)

When running as part of `/zolletta-metaskill review`, the orchestrator runs these shared scripts once and writes them to `cache/` before launching subagents. Subagents read from cache instead of re-running them:

| Script                          | Cache file                     | Used by                         |
|---------------------------------|--------------------------------|---------------------------------|
| `one_class_per_file_scanner.py` | `cache/one_class_per_file.txt` | `patterns`, `python-code-style` |
| `test_structure_scanner.py`     | `cache/test_structure.md`      | `patterns`                      |

## Standalone vs orchestrator

The protocol applies identically in both contexts:

- **Standalone** (`/zolletta-metaskill documentor`): the subcommand creates the run folder, runs Phase A (all its scripts), assembles Phase B from cache, runs Phase C judgment. No `_context.md` is written (not needed — there's only one LLM instance).
- **Orchestrator** (`/zolletta-metaskill review`): the orchestrator creates the run folder, writes `cache/_context.md` (settings + ADR directives + judgment-rules digest), runs shared scripts to cache, then launches subagents. Each subagent reads `cache/_context.md` + its subcommand-specific cache files, runs any remaining Phase A scripts not already cached, assembles Phase B, runs Phase C.

## Relationship to code exploration tools

When tokensave is available, use it **only in Phase C** for the judgment items that require understanding context (e.g. `tokensave_callers` for indirect-coverage tracing, `tokensave_context` for the "reason to change" test). Do not use tokensave in Phase A or B — the scripts are faster and produce deterministic output. See [`code-exploration.md`](code-exploration.md) for the tokensave decision tree, and note that this protocol takes precedence for review runs: scripts first, tokensave only for Phase C judgment candidates.
