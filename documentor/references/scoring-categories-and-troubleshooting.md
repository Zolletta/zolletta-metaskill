# Scoring, Drift Categories, Integration & Troubleshooting

Read this when interpreting staleness scores, classifying drift, deciding what to auto-fix vs fix by hand, wiring the skill into pipelines/release gates, or diagnosing tool issues against success-criteria targets.

## Staleness Scoring

Documentation freshness is scored on a **0-100 scale** where **100 = perfectly current**. The score is a weighted combination of five dimensions:

| Dimension | Weight | What It Measures |
|-----------|--------|------------------|
| **Last Updated** | 20% | How recently the doc file was modified relative to its associated code |
| **Code-Doc Alignment** | 30% | Whether documented items (functions, classes, files) still exist and match |
| **Link Health** | 15% | Percentage of links that resolve correctly |
| **Completeness** | 20% | Whether expected sections are present and non-empty |
| **Accuracy** | 15% | Whether version strings, file paths, and other verifiable facts are correct |

**Score interpretation:**

| Score | Label | Action |
|-------|-------|--------|
| 90-100 | Excellent | No action needed |
| 70-89 | Good | Minor updates recommended |
| 50-69 | Stale | Updates needed before next release |
| 30-49 | Critical | Immediate attention required |
| 0-29 | Abandoned | Full rewrite likely needed |

**Customization:**

```bash
# Override default weights
python scripts/doc_staleness_scorer.py /path/to/repo \
  --weight-updated 0.25 \
  --weight-alignment 0.25 \
  --weight-links 0.15 \
  --weight-completeness 0.20 \
  --weight-accuracy 0.15

# Set staleness thresholds
python scripts/doc_staleness_scorer.py /path/to/repo --threshold 60
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

## Auto-Fix vs Manual-Fix Classification

Not all drift can be fixed programmatically. The tools classify each issue:

### Auto-Fixable (safe to automate)

- **Version string updates** -- replace old version with current from package manifest
- **Date updates** -- update "last modified" timestamps
- **Broken local links** -- suggest correct path when file was moved (git log tracks renames)
- **Missing table of contents entries** -- generate from actual headings
- **Removed file references** -- flag for deletion or suggest replacement

### Manual-Fix Required (needs human judgment)

- **Architectural description changes** -- requires understanding intent
- **API usage examples** -- new examples need domain context
- **Migration guides** -- require understanding of breaking changes
- **Getting started rewrites** -- narrative flow needs human touch
- **Security documentation updates** -- compliance implications require review

### Semi-Automated (template + human review)

- **New function documentation** -- generate skeleton from AST, human fills description
- **Changelog entries** -- generate from git commits, human edits for clarity
- **README section additions** -- provide template, human adds content

The drift report marks each issue with `[AUTO]`, `[MANUAL]`, or `[SEMI]` tags.

## Integration Points (detailed)

### With CI/CD Pipelines

All tools return non-zero exit codes when issues are found:
- Exit 0: No issues (or all within threshold)
- Exit 1: Issues found exceeding threshold
- Exit 2: Tool error (invalid arguments, missing files)

### With Code Review

Add drift analysis to PR checks. When a PR modifies code in `src/`, automatically check whether docs in `docs/` need updates. The drift analyzer can scope its analysis to only changed directories.

### With Documentation Generators

Pair with tools like Sphinx, MkDocs, or mdBook. Run API validation after doc generation to ensure the generated docs match source. Run link checker on the built output.

### With Release Processes

Add staleness scoring to release checklists. Block releases if documentation score falls below threshold. Generate drift reports as release artifacts.

### With Other Skills

- **code-reviewer** -- include doc drift in PR review reports
- **senior-devops** -- integrate into deployment pipelines
- **senior-qa** -- documentation quality as part of QA checklist

## Anti-Patterns

- **Ignoring drift until release** -- run drift analysis in CI on every PR, not as a release-day scramble
- **Treating all drift as equal** -- factual drift (wrong function signatures) is critical; temporal drift (stale dates) is cosmetic; prioritize by category
- **Manual-only doc updates** -- use `[AUTO]` fixes for version strings and broken links; reserve human effort for semantic and architectural drift
- **Shallow clone in CI** -- `fetch-depth: 1` breaks git history comparison; always use `fetch-depth: 0` for drift analysis
- **Skipping link checks on internal docs** -- cross-document anchor references break silently on refactors; run `link_checker.py` on every markdown change

## Troubleshooting

| Problem | Cause | Solution |
|---------|-------|----------|
| `drift_analyzer.py` reports zero docs found | Repository has non-standard doc extensions or docs are in ignored directories (e.g., `node_modules`, `dist`) | Use `--doc-patterns "*.md,*.rst,*.txt"` to explicitly specify extensions |
| Staleness scores are unexpectedly low | Docs reference files that were reorganized or moved to new directories | Run `link_checker.py` first to identify broken references, fix them, then re-score |
| API validator finds no source signatures | Source path points to a non-Python directory or all functions are `_`-prefixed private | Verify `source_path` contains `.py` files; add `--include-private` if the API surface uses private names |
| Link checker flags valid anchors as broken | Heading text contains special characters, inline code, or emoji that alter the slug | Compare the expected slug (lowercase, special chars stripped, spaces to hyphens) against the actual heading text |
| Git history comparison shows no changes | Shallow clone lacks full commit history (common in CI) | Clone with `fetch-depth: 0` or pass `--scope` to narrow the analysis window |
| External URL checks hang or time out | Target servers are slow or block automated HEAD requests | Omit `--check-external` for local-only validation, or run external checks in a separate non-blocking job |
| Drift report marks everything as `[MANUAL]` | Most detected drift is semantic or architectural, not auto-fixable | This is expected for large refactors; focus on `[AUTO]` and `[SEMI]` items first, then triage `[MANUAL]` items by severity |

## Success Criteria

- **Zero stale docs older than 90 days** -- every documentation file has been updated within the last 90 days relative to its associated code changes
- **Aggregate staleness score above 80/100** -- the repository-wide freshness score stays in the "Good" or "Excellent" range
- **Link integrity above 99%** -- fewer than 1% of internal links (file references, anchors, cross-document links) are broken
- **API doc coverage above 95%** -- at least 95% of public functions and classes have corresponding entries in API documentation
- **Zero high-severity drift issues in CI** -- pull requests with high or critical drift are blocked before merge
- **Version string accuracy at 100%** -- every version reference in documentation matches the current release tag or package manifest
- **Drift report turnaround under 60 seconds** -- full drift analysis completes in under one minute for repositories with up to 500 documentation files
