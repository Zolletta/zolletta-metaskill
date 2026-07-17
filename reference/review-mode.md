# Review mode (read-only)

Shared rules for every subcommand that runs in a **read-only review context** — i.e. when invoked as part of a `/zolletta-metaskill review` or any other read-only review flow. This file is referenced by `python-code-style`, `python-testing-patterns`, and any future language-specific review skill.

## Core rule

**Do NOT apply any fixes.** Run tools in their check-only / no-fix modes. The review reports findings; it does not modify source files.

## Two-bucket classification

Every diagnostic reported by a tool must be classified into one of two buckets:

### Bucket 1 — Auto-fixable (informational)

Issues that the tool could fix automatically (the tool reports the diagnostic as fixable, or a formatter would reformat the file). These are:

- Listed in a separate **"Auto-fixable (informational)"** section of the report.
- **Not** counted toward the grade.
- **Not** listed as findings.

### Bucket 2 — Not auto-fixable (findings)

Issues that require human judgment to fix. These are:

- Listed as actual findings with severity, impact, and a suggested fix.
- **Counted toward the grade.**
- The only issues that affect the review score.

## Tool-specific notes

### ruff

- Run `ruff check` (no `--fix`) for linting.
- Run `ruff format --check` (no formatting) for formatting.
- To distinguish the two buckets: ruff marks each diagnostic with a fix indicator (e.g. `[F]` or `[*]` for fixable, `[--fix]` for unsafe-fixable). Alternatively, run `ruff check --fix --exit-zero` as a dry-run probe to see what would be fixed, then discard the changes (`git checkout -- .`).
- For format: `ruff format --check` lists the files it would reformat — those are auto-fixable (informational).

### ty

- Run `ty check` (no `--fix`).
- ty reports diagnostics as fixable or not — classify accordingly.
- Auto-fixable ty diagnostics → informational. Not auto-fixable → findings.

### mypy

- Run `mypy` as-is (mypy has no auto-fix mode).
- **All** mypy findings are listed as actual findings and scored normally — there is no "auto-fixable" bucket for mypy.

### vulture

- Run `vulture src/ --min-confidence <value>` (value from `python_code_style_rules.vulture_min_confidence` in `settings.json`).
- All vulture findings are listed as low-priority findings (vulture has false positives, especially for dynamically-accessed methods — review each with judgment before flagging).
