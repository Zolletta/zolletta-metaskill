---
audience: human, ai
status: stable
skills: [documentor]
---

# Scoring and Drift Categories

Reference for interpreting staleness scores, classifying drift, deciding what to auto-fix vs fix by hand, wiring the skill into pipelines/release gates, or diagnosing tool issues.

## Staleness Scoring

Documentation freshness is scored on a **0-100 scale** where **100 = perfectly current**. The score is a weighted combination of five dimensions:

| Dimension              | Weight | What It Measures                                                            |
|------------------------|--------|-----------------------------------------------------------------------------|
| **Last Updated**       | 20%    | How recently the doc file was modified relative to its associated code      |
| **Code-Doc Alignment** | 30%    | Whether documented items (functions, classes, files) still exist and match  |
| **Link Health**        | 15%    | Percentage of links that resolve correctly                                  |
| **Completeness**       | 20%    | Whether expected sections are present and non-empty                         |
| **Accuracy**           | 15%    | Whether version strings, file paths, and other verifiable facts are correct |

**Score interpretation:**

| Score  | Label     | Action                             |
|--------|-----------|------------------------------------|
| 90-100 | Excellent | No action needed                   |
| 70-89  | Good      | Minor updates recommended          |
| 50-69  | Stale     | Updates needed before next release |
| 30-49  | Critical  | Immediate attention required       |
| 0-29   | Abandoned | Full rewrite likely needed         |

**Customization:**

```bash
# Override default weights
python src/zolletta_metaskill/documentor/doc_staleness_scorer.py /path/to/repo \
  --weight-updated 0.25 \
  --weight-alignment 0.25 \
  --weight-links 0.15 \
  --weight-completeness 0.20 \
  --weight-accuracy 0.15

# Set staleness thresholds
python src/zolletta_metaskill/documentor/doc_staleness_scorer.py /path/to/repo --threshold 60
```

## Drift Categories

Every detected drift instance is classified into one or more categories:

### Structural Drift

Missing or misorganized sections. A README lacks an Installation section. An API doc is missing an entire module. A CHANGELOG has no entries for the latest version.

**Detection:** Compare actual document headings against expected headings for that document type.

### Factual Drift

Incorrect information. A function signature in the docs has the wrong parameters. An installation command references a removed package. A configuration example uses deprecated options.

**Detection:** Cross-reference documented facts against code analysis (AST parsing, file existence, git tags).

### Referential Drift

Broken references. A link points to a file that was moved. An anchor references a heading that was renamed. An image path is wrong.

**Detection:** Link checker validates every reference against the filesystem and document structure.

### Temporal Drift

Outdated time-sensitive content. Version strings are old. "Last updated" dates are stale. "Coming soon" items that shipped months ago. Roadmap items past their target date.

**Detection:** Extract version strings and dates, compare against git tags, package manifests, and current date.

### Semantic Drift

Technically accurate but misleading. A description says "simple REST API" when the project now has GraphQL, gRPC, and WebSocket endpoints. The architecture overview omits a major new subsystem.

**Detection:** Compare document topic coverage against code directory structure and file counts. Flag when code complexity has grown significantly but documentation scope has not.

> **Note**: Semantic drift is detected heuristically and may produce false positives. Always verify with manual review before acting on semantic drift findings.

## Auto-Fix vs Manual-Fix Classification

Not all drift can be fixed programmatically. The tools classify each issue:

### Auto-Fixable (safe to automate)

- **Version string updates** — replace old version with current from package manifest
- **Date updates** — update "last modified" timestamps
- **Broken local links** — suggest correct path when file was moved (git log tracks renames)
- **Missing table of contents entries** — generate from actual headings
- **Removed file references** — flag for deletion or suggest replacement

### Manual-Fix Required (needs human judgment)

- **Architectural description changes** — requires understanding intent
- **API usage examples** — new examples need domain context
- **Migration guides** — require understanding of breaking changes
- **Getting started rewrites** — narrative flow needs human touch
- **Security documentation updates** — compliance implications require review

### Semi-Automated (template + human review)

- **New function documentation** — generate skeleton from AST, human fills description
- **Changelog entries** — generate from git commits, human edits for clarity
- **README section additions** — provide template, human adds content

The drift report marks each issue with `[AUTO]`, `[MANUAL]`, or `[SEMI]` tags.

## Integration Points

| Integration     | How                                                                          |
|-----------------|------------------------------------------------------------------------------|
| CI/CD           | Non-zero exit codes on issues; scope analysis to changed directories         |
| Code review     | Add drift analysis to PR checks on `src/` changes                            |
| Doc generators  | Run API validation after Sphinx/MkDocs/mdBook generation                     |
| Release process | Block releases if score below threshold; generate drift reports as artifacts |

## Anti-Patterns

- Run drift analysis in CI on every PR, not as a release-day scramble.
- Factual drift is critical; temporal drift is cosmetic — prioritize by category.
- Use `[AUTO]` fixes for version strings and links; reserve human effort for semantic drift.
- Use `fetch-depth: 0` in CI — shallow clone breaks git history comparison.
- Run `link_checker.py` on every markdown change — cross-document anchors break silently.

## Troubleshooting

| Problem                                     | Cause                                                                                                        | Solution                                                                                                                    |
|---------------------------------------------|--------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------|
| `drift_analyzer.py` reports zero docs found | Repository has non-standard doc extensions or docs are in ignored directories (e.g., `node_modules`, `dist`) | Use `--doc-patterns "*.md,*.rst,*.txt"` to specify extensions.                                                              |
| Staleness scores are unexpectedly low       | Docs reference files that were reorganized or moved to new directories                                       | Run `link_checker.py` first to fix broken references, then re-score.                                                        |
| API validator finds no source signatures    | Source path points to a non-Python directory or all functions are `_`-prefixed private                       | Verify `source_path` has `.py` files; add `--include-private` if needed.                                                    |
| Link checker flags valid anchors as broken  | Heading text contains special characters, inline code, or emoji that alter the slug                          | Compare the expected slug (lowercase, special chars stripped, spaces to hyphens) against the actual heading text.           |
| Git history comparison shows no changes     | Shallow clone lacks full commit history (common in CI)                                                       | Clone with `fetch-depth: 0` or pass `--scope` to narrow the analysis window.                                                |
| External URL checks hang or time out        | Target servers are slow or block automated HEAD requests                                                     | Omit `--check-external` for local-only validation, or run external checks in a separate non-blocking job.                   |
| Drift report marks everything as `[MANUAL]` | Most detected drift is semantic or architectural, not auto-fixable                                           | This is expected for large refactors; focus on `[AUTO]` and `[SEMI]` items first, then triage `[MANUAL]` items by severity. |
