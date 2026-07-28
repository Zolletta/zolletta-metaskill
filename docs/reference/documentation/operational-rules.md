---
audience: human, ai
status: stable
skills: [documentor]
---

# Documentor Operational Rules

Shared rules for running documentation drift detection. These rules apply when the `documentor` skill runs its drift detection tools.

## Tool invocation

- **Always run the staleness scorer and drift analyzer with the project root as the repo path**, not the documentation directory. Source code paths in docs (e.g., `src/myproject/...`) are relative to the project root. Running with the docs directory as root makes every source path appear missing, artificially tanking the `code_doc_alignment` and `accuracy` scores.
- Run `drift_analyzer.py` without `--include-referential` by default. Referential drift (renamed files, broken links) is suppressed because `link_checker.py` covers it more reliably. Use `--include-referential` only when specifically auditing file renames.
- Run `link_checker.py` on the documentation directory — it resolves links relative to the docs directory.
- Run `api_doc_validator.py` with the source directory as the first argument and the docs directory as the second: `api_doc_validator.py src/myproject docs --recursive --json`.
- Both `drift_analyzer.py` and `doc_staleness_scorer.py` respect `.gitignore`, so gitignored directories (`.zolletta-metaskill/`, `.devin/`, etc.) are automatically excluded.

## Differences from doc-drift-detector

- **Referential drift is suppressed by default** — `link_checker.py` covers it more reliably. Use `--include-referential` only when auditing file renames.
- **Semantic drift category removed** — code-size vs test-size comparison was pure noise with no correlation to doc accuracy.
- **Undocumented items are suggestions, not issues** — returned via `--suggest-coverage`, do not affect exit code. Focus on high-priority suggestions (entry points, protocols, complex constructors).
- **Known false positives to filter manually:**
  - `link_checker.py` does not respect code fences — headings inside ` ```markdown ` or ` ```yaml ` blocks are flagged as duplicate anchors. Inspect flagged lines before fixing.
  - `api_doc_validator.py` only extracts top-level definitions via AST — class methods, stdlib imports, and protocol methods appear as phantom docs. Always grep the source before treating a phantom doc as real drift.
  - `api_doc_validator.py` matches by basename — methods with the same name in different classes can cause wrong-class parameter mismatches. Check the doc context to see which class is referenced.
  - `doc_staleness_scorer.py` detects Diátaxis quadrant directories (tutorials/, how-to/, reference/, explanation/) and applies quadrant-specific completeness checks automatically. For README-style docs not inside a quadrant directory, it still uses the default sections (`installation`, `usage`, `api`, `contributing`, `license`). Use `--required-sections` to override for non-Diátaxis, non-README structures.
  - `doc_staleness_scorer.py` tries to resolve template placeholders (`<verifier_name>`, `{file_name}`) and example output paths (`tests/results/...`, `generated-specs/*.md`) as real files. These are illustrative, not drift.
  - `doc_staleness_scorer.py` compares version-like strings in docs against the package version — docs describing a domain-specific versioning scheme (e.g., spec grammar versions) will always mismatch. Check whether the version refers to the package or a domain scheme.
  - `doc_staleness_scorer.py` scores every markdown file in the repo when run from the project root. Filter results to the project's doc directory when reviewing.
- **Real drift to act on:** phantom docs (methods refactored to a different class), methods referenced with empty parens missing their parameter list, and stale references in `AGENTS.md` — tools only scan the docs directory, so grep `AGENTS.md` separately.
- **Duplicate anchors:** when real (same heading text in different sections), use the project's explicit anchor syntax `{#id}` to disambiguate rather than renaming headings.

## File path conventions in docs

- **Always use full paths from the project root** in documentation, not package-relative paths.
  - Correct: `src/myproject/engine/metrics/my_prefix.py`
  - Wrong: `engine/metrics/my_prefix.py`
- This ensures the staleness scorer can find the referenced files and score the doc accurately.

## Workflow

1. Run `link_checker.py` first — it's the most reliable (fewest false positives).
2. Run `api_doc_validator.py --json` and filter out the false positive patterns listed above.
3. Run `drift_analyzer.py --json` (without `--include-referential`) for per-file factual drift. The analyzer respects `.gitignore` and only flags docs where specific referenced source files changed.
4. Run `doc_staleness_scorer.py` with the **project root** (not the docs directory) as the repo path. The scorer respects `.gitignore`, so gitignored directories are automatically excluded. Root-level non-doc files (`CHANGELOG.md`, `AGENTS.md`) may still appear — filter those out manually.
5. Manually verify each high-severity issue before fixing — the tools have known false positive patterns.
6. After fixing, re-run the relevant tool to confirm the issue count dropped.
   - **Note:** `api_doc_validator.py` counts are **not monotonically decreasing**. Adding params to a doc reference creates a new "documented item" that the validator tracks, which can increase the total issue count even though you fixed real issues. Compare the specific issue types (phantom, missing_param, extra_param) separately, not just the total.

## Drift report conventions

- For false positives, explain why they are false positives in the report — don't just delete them.

These rules apply only if run in isolation, not as part of a compound skill:

- Save reports to `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/documentor.md`
