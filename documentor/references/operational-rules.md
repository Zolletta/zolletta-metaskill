# Doc Drift Detector Rules

Shared rules for running documentation drift detection across all Pepita projects. These rules capture insights from real drift analysis runs on the `ci-tester-engine` project's `.backstage` documentation set.

> **Skill:** `zolletta-doc-drift-detector` v2.2.0 — renamed from `doc-drift-detector` in v2.2.0.

## Tool invocation

- **Always run the staleness scorer and drift analyzer with the project root as the repo path**, not the
  `.backstage/` directory. Source code paths in docs (e.g., `src/pepita/ci/testerengine/...`) are relative to the project root. Running with `.backstage` as root makes every source path appear missing, artificially tanking the `code_doc_alignment` and `accuracy` scores.
- Run `drift_analyzer.py` without `--include-referential` by default. Referential drift
  (renamed files, broken links) is suppressed because `link_checker.py` covers it more reliably. Use `--include-referential` only when specifically auditing file renames.
- Run `link_checker.py` on `.backstage/` — it resolves links relative to the docs directory.
- Run `api_doc_validator.py` with the source directory as the first argument and the docs
  directory as the second: `api_doc_validator.py src/pepita/ci/testerengine .backstage/docs --recursive --json`.
- Both `drift_analyzer.py` and `doc_staleness_scorer.py` respect `.gitignore` (v2.1.1+),
  so gitignored directories (`.scratches/`, `.devin/`, etc.) are automatically excluded.

## False positive patterns

### drift_analyzer.py — renamed-file references (suppressed by default in v2.2.0)

The analyzer matches by **basename** (e.g., `scenarios.md`) and flags any file that was historically renamed in git history. If the actual markdown links already use the correct current paths, these are false positives. **Always cross-check with `link_checker.py`** — if it reports 0 broken links, the "renamed file" issues are false positives.

> **v2.2.0:** Referential drift is now suppressed by default. Use `--include-referential`
> to re-enable. The only referential issue reported by default is the edge case where a
> doc references a renamed file but the old name still exists as a different file.

### drift_analyzer.py — semantic category removed in v2.2.0

The semantic category (doc/code size comparison) was removed in v2.2.0. It produced 1,728 false positives (89% of all issues) because there's no correlation between code size and documentation size. If you're using an older version, ignore all semantic issues.

### link_checker.py — duplicate anchors in code blocks

The link checker does **not** respect code fences. It flags headings inside ` ```markdown ` and ` ```yaml ` code blocks as duplicate anchors. Before fixing, inspect the flagged lines: if they are inside a code block, they are false positives.

### link_checker.py — fixing real duplicate anchors

When duplicate anchors are real (same heading text used in different sections of the same doc), use the project's explicit anchor syntax `{#id}` to disambiguate rather than renaming headings. Check if the project already uses this convention (e.g., grep for `{#` in `.backstage/`). Use a descriptive suffix that reflects the section context (e.g., `{#in-ci-ssh}` vs `{#in-ci-api}` for `#### In CI` under SSH vs API token sections).

### api_doc_validator.py — phantom docs (documented_not_in_source)

The validator only extracts **top-level** function/class definitions via AST. It cannot see:

- **Class methods** — methods defined inside a class (e.g., `Orchestrator._emit_scenario_metrics`,
  `CitePrefix._resolve_context`) are invisible to the validator even though they exist in source.
- **Stdlib imports** — `ThreadPoolExecutor` from `concurrent.futures` is used in docs but not
  found in engine source because it's an import, not a local definition.
- **Protocol methods** — statsd client methods (`incr`, `gauge`, `timing`) exist on the client
  protocol, not in the engine source directly.

Always grep the source for the flagged name before treating a phantom doc as real drift.

### api_doc_validator.py — undocumented items are suggestions, not issues (v2.2.0)

As of v2.2.0, undocumented items are **separated from issues** and returned as prioritized suggestions instead. They do not affect the exit code or the issue count. The JSON output has a separate `"suggestions"` key (only when `--suggest-coverage` is passed) and the `"summary"` includes `"undocumented_count"` and `"undocumented_by_priority"`.

Priority heuristics:

- **high** — entry-point functions (`main`, `run`), protocol definitions, classes with >3
  constructor params
- **medium** — public classes, functions with >3 params
- **low** — simple functions (<=2 params), methods
- **skip** — dataclasses, `__init__.py` re-exports

Use `--suggest-coverage` to see the full prioritized list. Without the flag, only a summary count is shown. Diátaxis documentation does not aim for 100% API coverage — focus on high-priority suggestions and skip the rest.

### api_doc_validator.py — parameter mismatches from name collisions

The validator matches by **basename**. If two classes have methods with the same name (e.g., `Cache.cache(scenario)` in `tested_pipeline/cache.py` and `BranchCache.cache(templates_by_project, gitlab_manager)` in `templates/branch_cache.py`), the validator may flag the wrong method. Check the doc context to see which class is actually referenced.

### doc_staleness_scorer.py — completeness dimension

The scorer expects README-style sections (`installation`, `usage`, `api`, `contributing`, `license`) by default. Diátaxis documentation does not have these sections — it uses `tutorials`, `how-to`, `reference`, `explanation`. The completeness score is always 0 for Diátaxis docs and should be treated as a false positive. Use `--required-sections` to override if needed.

### doc_staleness_scorer.py — template placeholders

Docs that contain `<verifier_name>`, `{file_name}`, or similar placeholder syntax will have "missing file path" issues because the scorer tries to resolve these as real paths. These are intentional template syntax, not drift.

### doc_staleness_scorer.py — example output paths

Docs often show example output file paths (e.g., `tests/results/python/A01-...json`, `generated-specs/*.md`) to illustrate what the engine produces. The accuracy check extracts these from backticks and tries to resolve them as real files. They are illustrative examples, not real files. Glob patterns (e.g., `*.md`) are also matched but are not real paths.

### doc_staleness_scorer.py — manifest version mismatch (spec grammar vs package version)

The accuracy check extracts all version-like strings (`v1.0.0`, `version 2.0.0`) from docs and compares them against the package version in `pyproject.toml`. Docs that describe a
**spec grammar versioning scheme** (e.g., 1.0.0, 1.1.0, 2.0.0) will always mismatch because
grammar versions are independent of the package version. Check whether the version numbers in the doc refer to the package version or a domain-specific versioning scheme before treating the mismatch as real drift.

### doc_staleness_scorer.py — code_doc_alignment with code changes

When a doc has no explicit file references, the scorer checks how many code files changed in the doc's directory since the doc was last updated. A low score (40-60) from this check means "code changed since the doc was last touched" — this is expected in active projects and does not necessarily mean the doc content is stale. Only treat as actionable if the doc content actually contradicts the current code.

### doc_staleness_scorer.py — scans entire repo, not just docs

When run with the project root as repo path, the scorer scores **every** markdown file in the repo. As of v2.1.1, the scorer respects `.gitignore` (simple entries only — no wildcards or negation), so `.scratches/`, `.devin/`, `.pytest_cache/` etc. are automatically excluded. Root-level non-doc files like `CHANGELOG.md` and `AGENTS.md` may still appear — filter results to `.backstage/` (or the project's doc directory) when reviewing the output.

## Real drift patterns (not false positives)

### Renamed methods moved to a different class

Methods may be refactored from one class to another (e.g., `_create_merge_request` moved from `TypeMixin` to `Repository` and lost its leading underscore). The `api_doc_validator.py` flags these as phantom docs (documented but not in source). To fix:

1. Grep the source for the method name (without class prefix) to find where it now lives.
2. Update the doc to reference the correct class and method name.
3. Check `AGENTS.md` for the same stale reference — the tools only scan `.backstage/`, so
   stale references in `AGENTS.md` won't be caught automatically.

### Empty parens in method references

Docs often reference methods with empty parens (e.g., `Orchestrator.run()`) even when the method has parameters. The `api_doc_validator.py` flags these as missing params. To fix, add the current parameter list inside the parens (e.g., `Orchestrator.run(scenarios_by_branch, start_time, scenario_collection, results_manager)`). Only fix docs that are intended to show signatures — high-level architectural descriptions may intentionally omit params.

### AGENTS.md is not scanned

The drift tools only scan `.backstage/` documentation. `AGENTS.md` (and other root-level docs) can contain the same stale references. After fixing references in `.backstage/` docs, always grep `AGENTS.md` for the same patterns.

## File path conventions in docs

- **Always use full paths from the project root** in documentation, not package-relative paths.
  - Correct: `src/pepita/ci/testerengine/engine/metrics/cite_prefix.py`
  - Wrong: `engine/metrics/cite_prefix.py`
- This ensures the staleness scorer can find the referenced files and score the doc accurately.

## Workflow

1. Run `link_checker.py` first — it's the most reliable (fewest false positives).
2. Run `api_doc_validator.py --json` and filter out the false positive patterns above.
3. Run `drift_analyzer.py --json` (without `--include-referential`) for per-file factual drift. The analyzer now respects `.gitignore` and only flags docs where specific referenced source files changed.
4. Run `doc_staleness_scorer.py` with the **project root** (not `.backstage`) as the repo path. The scorer respects `.gitignore` (v2.1.1+), so gitignored directories are automatically excluded. Root-level non-doc files (`CHANGELOG.md`, `AGENTS.md`) may still appear — filter those out manually.
5. Manually verify each high-severity issue before fixing — the tools have known false positive patterns.
6. After fixing, re-run the relevant tool to confirm the issue count dropped.
   - **Note:** `api_doc_validator.py` counts are **not monotonically decreasing**. Adding params to a doc reference creates a new "documented item" that the validator tracks, which can increase the total issue count even though you fixed real issues. Compare the specific issue types (phantom, missing_param, extra_param) separately, not just the total.
   - **Note:** `api_doc_validator.py` counts are **not monotonically decreasing**. Adding params to a doc reference creates a new "documented item" that the validator tracks, which can increase the total issue count even though you fixed real issues. Compare the specific issue types (phantom, missing_param, extra_param) separately, not just the total.

## Drift report conventions

These rules applies only if run in isolation not part of a compound skills:

- Save reports to `.scratches/drift/<AAMMDDHHMM>/drift-report.md`
- Mark fixed items with strikethrough (`~~text~~`) and move them to a "Done" section.
- For false positives, explain why they are false positives in the report — don't just delete them.
- Keep the executive summary table updated with current counts after each fix session.
- Renumber sections when items are removed (e.g., if section 3 is deleted, section 4 becomes 3).
