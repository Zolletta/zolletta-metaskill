# Documentor Operational Rules

Shared rules for running documentation drift detection. These rules apply when the `documentor` skill runs its drift detection tools.

## Tool invocation

- **Always run the staleness scorer and drift analyzer with the project root as the repo path**, not the
  `.backstage/` directory. Source code paths in docs (e.g., `src/myproject/...`) are relative to the project root. Running with `.backstage` as root makes every source path appear missing, artificially tanking the `code_doc_alignment` and `accuracy` scores.
- Run `drift_analyzer.py` without `--include-referential` by default. Referential drift
  (renamed files, broken links) is suppressed because `link_checker.py` covers it more reliably. Use `--include-referential` only when specifically auditing file renames.
- Run `link_checker.py` on `.backstage/` — it resolves links relative to the docs directory.
- Run `api_doc_validator.py` with the source directory as the first argument and the docs
  directory as the second: `api_doc_validator.py src/myproject .backstage/docs --recursive --json`.
- Both `drift_analyzer.py` and `doc_staleness_scorer.py` respect `.gitignore`,
  so gitignored directories (`.scratches/`, `.devin/`, etc.) are automatically excluded.

## Differences from doc-drift-detector

The `documentor` skill merges the original `doc-drift-detector` and `documentation-writer` skills into a single review pipeline. The drift detection tools (`drift_analyzer.py`, `doc_staleness_scorer.py`, `api_doc_validator.py`, `link_checker.py`) are inherited from doc-drift-detector, but the following changes were made based on insights from real drift analysis runs:

- **Referential drift is suppressed by default.** The original tool flagged any file that was historically renamed in git, even when the markdown links already pointed to the correct current paths. Worse, running a code formatter (e.g. `ruff format`, `php-cs-fixer`) or a linter touch-up can bump the `last_modified` timestamp of source files without any semantic change, making the code appear "newer" than the docs and triggering spurious referential drift. Use `--include-referential` only when you are specifically auditing file renames.
- **Semantic drift category removed.** The original tool compared the size (line count) of source classes against their corresponding test classes and flagged mismatches as "semantic drift." This metric is pure noise: a small class can legitimately have a large test file (many edge cases) and a large class can have a small test file (thin wrapper). There is no correlation between code size and documentation size, and the comparison says nothing about whether the docs are accurate. It is no longer reported.
- **Undocumented items are suggestions, not issues.** The original tool reported every public function/class missing from the docs as an issue. This conflates two different concerns: accuracy (does the doc match the code?) and coverage (is every symbol documented?). Diátaxis documentation is organised by user need (tutorials, how-to, reference, explanation), not by exhaustive API listing — documenting every dataclass, `__init__.py` re-export, or trivial getter adds no value for the reader. Undocumented items are now separated from the issue list and returned as prioritized suggestions (high/medium/low/skip) via `--suggest-coverage`. They do not affect the exit code or issue count. Focus on high-priority suggestions (entry points, protocols, complex constructors) and skip the rest.
- **Known false positives to filter manually:**
  - `link_checker.py` does not respect code fences — headings inside ` ```markdown ` or ` ```yaml ` blocks are flagged as duplicate anchors. Inspect flagged lines before fixing.
  - `api_doc_validator.py` only extracts top-level definitions via AST — class methods, stdlib imports, and protocol methods appear as phantom docs. Always grep the source before treating a phantom doc as real drift.
  - `api_doc_validator.py` matches by basename — methods with the same name in different classes can cause wrong-class parameter mismatches. Check the doc context to see which class is referenced.
  - `doc_staleness_scorer.py` expects README-style sections (`installation`, `usage`, `api`, `contributing`, `license`) — Diátaxis docs use `tutorials`, `how-to`, `reference`, `explanation`, so the completeness score is always 0. Use `--required-sections` to override.
  - `doc_staleness_scorer.py` tries to resolve template placeholders (`<verifier_name>`, `{file_name}`) and example output paths (`tests/results/...`, `generated-specs/*.md`) as real files. These are illustrative, not drift.
  - `doc_staleness_scorer.py` compares version-like strings in docs against the package version — docs describing a domain-specific versioning scheme (e.g., spec grammar versions) will always mismatch. Check whether the version refers to the package or a domain scheme.
  - `doc_staleness_scorer.py` scores every markdown file in the repo when run from the project root. Filter results to the project's doc directory (e.g., `.backstage/`) when reviewing.
- **Real drift to act on:** methods refactored to a different class (phantom docs), methods referenced with empty parens missing their parameter list, and stale references in `AGENTS.md` (the tools only scan `.backstage/`, so always grep `AGENTS.md` for the same patterns after fixing).
- **Duplicate anchors:** when real (same heading text in different sections of the same doc), use the project's explicit anchor syntax `{#id}` to disambiguate rather than renaming headings. Check if the project already uses this convention.

## File path conventions in docs

- **Always use full paths from the project root** in documentation, not package-relative paths.
  - Correct: `src/myproject/engine/metrics/my_prefix.py`
  - Wrong: `engine/metrics/my_prefix.py`
- This ensures the staleness scorer can find the referenced files and score the doc accurately.

## Workflow

1. Run `link_checker.py` first — it's the most reliable (fewest false positives).
2. Run `api_doc_validator.py --json` and filter out the false positive patterns listed above.
3. Run `drift_analyzer.py --json` (without `--include-referential`) for per-file factual drift. The analyzer respects `.gitignore` and only flags docs where specific referenced source files changed.
4. Run `doc_staleness_scorer.py` with the **project root** (not `.backstage`) as the repo path. The scorer respects `.gitignore`, so gitignored directories are automatically excluded. Root-level non-doc files (`CHANGELOG.md`, `AGENTS.md`) may still appear — filter those out manually.
5. Manually verify each high-severity issue before fixing — the tools have known false positive patterns.
6. After fixing, re-run the relevant tool to confirm the issue count dropped.
   - **Note:** `api_doc_validator.py` counts are **not monotonically decreasing**. Adding params to a doc reference creates a new "documented item" that the validator tracks, which can increase the total issue count even though you fixed real issues. Compare the specific issue types (phantom, missing_param, extra_param) separately, not just the total.

## Drift report conventions

- For false positives, explain why they are false positives in the report — don't just delete them.

These rules apply only if run in isolation, not as part of a compound skill:

- Save reports to `.scratches/drift/<AAMMDDHHMM>/drift-report.md`
