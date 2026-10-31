---
audience: human, ai
status: stable
skills: [documentor]
---

# Documentor Operational Rules

Shared rules for running documentation drift detection. These rules apply when the `documentor` skill runs its drift detection tools.

## Tool invocation

- **Always run the tools from the project root** — they analyze the repository at the current working directory. Source code paths in docs (e.g., `src/myproject/...`) are relative to the project root.
- `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/documentor_client.py` runs all three tools and aggregates their cache files into one report; run individual tools only when you need a single category of findings.
- Referential drift is off by default (`documentation.include_referential: false`). It is suppressed because `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/links/link_checker.py` covers it more reliably — enable it only when specifically auditing file renames.
- `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/links/link_checker.py` audits the repository at cwd; link resolution follows `documentation.dir`.
- `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/api_doc/api_doc_validator.py` reads source roots from `python.paths.source` and docs from `documentation.dir`.
- `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/quality_review.py` (drift detection + staleness scoring) respects `.gitignore`, so gitignored directories (`.zolletta-metaskill/`, `.devin/`, etc.) are automatically excluded.

## Differences from doc-drift-detector

- **Referential drift is suppressed by default** — `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/links/link_checker.py` covers it more reliably. Enable `documentation.include_referential` only when auditing file renames.
- **Semantic drift category removed** — code-size vs test-size comparison was pure noise with no correlation to doc accuracy.
- **Undocumented items are suggestions, not issues** — emitted when `documentation.api_doc_suggest_coverage` is on, do not affect exit code. Focus on high-priority suggestions (entry points, protocols, complex constructors).
- **Known false positives to filter manually:**
  - `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/links/link_checker.py` does not respect code fences — headings inside ` ```markdown ` or ` ```yaml ` blocks are flagged as duplicate anchors. Inspect flagged lines before fixing.
  - `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/api_doc/api_doc_validator.py` only extracts top-level definitions via AST — class methods, stdlib imports, and protocol methods appear as phantom docs. Always grep the source before treating a phantom doc as real drift.
  - `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/api_doc/api_doc_validator.py` matches by basename — methods with the same name in different classes can cause wrong-class parameter mismatches. Check the doc context to see which class is referenced.
  - `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/quality_review.py` detects Diátaxis quadrant directories (tutorials/, how-to/, reference/, explanation/) and applies quadrant-specific completeness checks automatically. For README-style docs not inside a quadrant directory, it still uses the default sections (`installation`, `usage`, `api`, `contributing`, `license`). Set `documentation.readme_sections` to override for non-Diátaxis, non-README structures.
  - `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/quality_review.py` tries to resolve template placeholders (`<verifier_name>`, `{file_name}`) and example output paths (`tests/results/...`, `generated-specs/*.md`) as real files. These are illustrative, not drift.
  - `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/quality_review.py` compares version-like strings in docs against the package version — docs describing a domain-specific versioning scheme (e.g., spec grammar versions) will always mismatch. Check whether the version refers to the package or a domain scheme.
  - `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/quality_review.py` scores every markdown file in the repo when run from the project root. Filter results to the project's doc directory when reviewing.
- **Real drift to act on:** phantom docs (methods refactored to a different class), methods referenced with empty parens missing their parameter list, and stale references in `AGENTS.md` — tools only scan the docs directory, so grep `AGENTS.md` separately.
- **Duplicate anchors:** when real (same heading text in different sections), use the project's explicit anchor syntax `{#id}` to disambiguate rather than renaming headings.

## File path conventions in docs

- **Always use full paths from the project root** in documentation, not package-relative paths.
  - Correct: `src/myproject/engine/metrics/my_prefix.py`
  - Wrong: `engine/metrics/my_prefix.py`
- This ensures the staleness scorer can find the referenced files and score the doc accurately.

## Workflow

1. Run `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/documentor_client.py --json` — it executes all three tools (quality review, API doc validation, link checking), writes their cache files, and prints the aggregated report.
2. Filter out the false positive patterns listed above from each section.
3. For deeper per-tool inspection, read the individual cache files or re-run a single tool:
   - `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/links/link_checker.py` — the most reliable (fewest false positives).
   - `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/api_doc/api_doc_validator.py --json` — API doc drift and coverage suggestions.
   - `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/quality/quality_review.py --json` — per-file factual drift plus the freshness score. Run with the **project root** (not the docs directory) as the repo path; it respects `.gitignore` and only flags docs where specific referenced source files changed. Root-level non-doc files (`CHANGELOG.md`, `AGENTS.md`) may still appear — filter those out manually.
4. Manually verify each high-severity issue before fixing — the tools have known false positive patterns.
5. After fixing, re-run the relevant tool to confirm the issue count dropped.
   - **Note:** `skills/zolletta-metaskill/src/zolletta_metaskill/documentor/api_doc/api_doc_validator.py` counts are **not monotonically decreasing**. Adding params to a doc reference creates a new "documented item" that the validator tracks, which can increase the total issue count even though you fixed real issues. Compare the specific issue types (phantom, missing_param, extra_param) separately, not just the total.

## Drift report conventions

- For false positives, explain why they are false positives in the report — don't just delete them.

These rules apply only if run in isolation, not as part of a compound skill:

- Save reports to `<runs_dir>/<YYYY-MM-DD-HH-MM>/reports/documentor.md`
