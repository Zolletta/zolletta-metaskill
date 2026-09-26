# ADR-0014: Add a mutation testing sensor (mutmut / Infection)

## Status

Accepted

## Context

Issue #47 asks for the "incremental mutation testing" sensor from Martin Fowler's *Maintainability sensors for coding agents*. Coverage tells you what was *executed*; mutation testing tells you what was *verified*. For AI-generated code where tests achieve high coverage but may be shallow, it is the sensor that separates "tests exist" from "tests protect against bugs."

Both target tools are zero-config: [mutmut](https://github.com/boxed/mutmut) (Python) mutates at AST level and auto-detects pytest; [Infection](https://infection.codes/) (PHP) mutates via AST and reads `phpunit.xml` automatically. Only installation detection is needed in setup.

This is the positive counterpart to ADR-0012 and ADR-0013, which rejected property-based and fuzz sensors for lacking a "run tool → parse structured output" pipeline. Mutation testing fits that pipeline.

## Decision

Add a conditional mutation-testing sensor:

1. **Setup detection only** — `pyproject_sections_detector.py` detects `mutmut` (`[tool.mutmut]` section or a quoted dependency specifier); `php_tools_detector.py` detects `infection/infection` in `composer.json` or `infection.json*` config files. Both are stored as `{available: boolean}` — availability only, no config extraction.
2. **Testing-style integration** — `python-testing-style` runs `mutmut` and `php-testing-style` runs Infection, gated by tool availability AND a new `check_mutation_testing` toggle (default `true`) AND a green coverage run — the tools execute the test suite per mutant, so a red suite makes results meaningless.
3. **Incremental by default** — `mutation_target: "changed"` restricts mutation to files changed vs the default branch plus the working tree (`mutmut run <module-patterns>` / `infection --git-diff-filter=AM --git-diff-base=<base>`). When the changed set can't be resolved, the sensor skips with a note rather than silently running the expensive `all` target.
4. **Deterministic survived-mutant extraction** — `mutmut_survived_reporter.py` (stdlib-only, `[--json]`-only CLI per ADR-0015) wraps `mutmut results` + `mutmut show` into status counts, a `Mutation score: X% (threshold: Y%) — PASS/FAIL` line, and a per-mutant `file:line` + diff table capped at `mutation_max_mutants`. For Infection, the "Escaped Mutants" table is parsed from the stdout cache — no PHP script.
5. **Severity mapping** — score below `mutation_score_threshold` (default 80) → high finding; each survived mutant → medium finding with a suggested test name; timeout mutants → low/informational.

## Consequences

**Positive:**

- The "tests exist but don't catch bugs" gap becomes visible during review — the missing layer above coverage.
- Zero-config tools mean setup needs only availability detection, matching the existing `vulture`/`phpunit` pattern.
- `changed` default + `check_mutation_testing` toggle keep the sensor fast and opt-out-able without uninstalling the tool.
- The sensor follows the same pipeline every other tool uses: run → cache output → deterministic parse → judgment only for fix suggestions.

**Negative:**

- Mutation runs multiply the test suite's runtime by the mutant count — even incremental runs are heavy, which is why the sensor is conditional rather than mandatory like coverage.
- mutmut 3.x CLI details (result line format, `run` taking mutant-name patterns) may drift across versions; the reporter tolerates the `--all` spelling variants.
- New required schema keys make older `settings.json` files stale until the next setup run — handled by the existing additive backfill (setup_version 3.2.0).
- `mutmut run` writes a `mutants/` directory and Infection may write `infection.log`/`infection.json` — documented as disposable artifacts, not auto-installed.

**Neutral:**

- Report files keep their `python-testing-patterns.md` / `php-testing-patterns.md` names; the Mutation Testing section is omitted entirely when the sensor is skipped.
