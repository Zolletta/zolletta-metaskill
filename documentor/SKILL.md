---
name: zolletta-metaskill-documentor
version: 1.1.0
description: >
  Documentation review combining [Diátaxis](https://diataxis.fr/) compliance checks with automated drift detection. Reviews .backstage/ docs for structure, accuracy, consistency, and freshness against the codebase. Use when reviewing docs, preparing releases, running CI doc gates, or auditing doc quality.
license: MIT + Commons Clause
---

# Zolletta-metaskill Documentor

A unified documentation review skill that combines:

1. **Diátaxis compliance** — structure, audience clarity, type correctness, voice consistency
2. **Accuracy review** — verify docs match the actual codebase (fields, signatures, commands, paths)
3. **Drift detection** — automated staleness scoring, link integrity, API doc validation via AST

Derived from the [Diátaxis Documentation Expert](https://github.com/github/awesome-copilot/blob/main/skills/documentation-writer/SKILL.md) skill (MIT, github/awesome-copilot) and the [Doc Drift Detector](https://github.com/borghei/Claude-Skills/blob/main/engineering/doc-drift-detector/SKILL.md) (MIT + Commons Clause, borghei/Claude-Skills), merged into a single review pipeline.

> This file narrows down any eventual general rule about code exploration and documentation, i.e. [code-exploration-rules.md](~/.agents/rules/code-exploration-rules.md), [tokensave-rules.md](~/.agents/rules/tokensave-rules.md), [documentation-rules.md](~/.agents/rules/documentation-rules.md). All files in `~/.agents/rules/` are the single source of truth for their domain.

## Shared resources

Read shared guidelines from the meta-skill (parent directory):

- `../reference/code-exploration.md` — code graph tools (tokensave) decision tree
- `../reference/documentation_standards.md` — generic doc writing standards (README, API docs, changelogs, ADRs)
- `../reference/general-principles.md` — SOLID, KISS, composition over inheritance (language-agnostic)
- `../reference/tool-messages.md` — "not installed" messages for the tool-failure handler
- `../scripts/python/` — shared scanning scripts

**Tool-failure handler**: if a tokensave MCP call fails with tool-not-found / server-not-found, follow the [tool-failure handler](../SKILL.md#tool-failure-handler) in the meta-skill — update `settings.json`, print the "not installed" message, and continue with grep/read fallback.

Local scripts and references are in this skill's own subdirectories:

- `scripts/` — drift detection tools (Python stdlib only)
- `references/` — drift scoring, workflow, and standards documentation
- `assets/` — report templates and sample data

---

## GUIDING PRINCIPLES

1. **Clarity:** Write in simple, clear, and unambiguous language.
2. **Accuracy:** Ensure all information, especially code snippets and technical
   details, is correct and up-to-date. Verify claims against the actual codebase.
3. **User-Centricity:** Always prioritize the user's goal. Every document must
   help a specific user achieve a specific task.
4. **Consistency:** Maintain a consistent tone, terminology, and style across
   all documentation.

---

## PART 1: DIÁTAXIS COMPLIANCE REVIEW

### The four document types

Diátaxis defines four quadrants. Each document must belong to exactly one:

- **Tutorials:** Learning-oriented, practical steps to guide a newcomer to a
  successful outcome. A lesson.
- **How-to Guides:** Problem-oriented, steps to solve a specific problem. A recipe.
- **Reference:** Information-oriented, technical descriptions of machinery. A dictionary.
- **Explanation:** Understanding-oriented, clarifying a particular topic. A discussion.

### Review checklist

For each document, verify:

**Type correctness**
- Document is placed in the correct Diátaxis quadrant
- Content matches the quadrant's purpose (no explanation in reference, no tutorial in how-to, etc.)
- No hybrid content that blurs quadrant boundaries

**Audience clarity**
- Tutorials include "What we will learn" and "Prerequisites"
- How-to guides include "Prerequisites" or "Before Starting"
- Reference docs are factual and structure-focused
- Explanation docs provide context and design rationale

**Accuracy**
- Code snippets match the actual codebase (verify via tokensave first, `read` only as fallback)
- Field names, types, and signatures match the source
- File paths and directory trees reflect the actual repository structure
- CLI commands match the actual entry points and flags
- No documented fields/features that don't exist in the code
- No undocumented fields/features that exist in the code but are missing from docs

**Consistency**
- Voice convention is followed (check AGENTS.md for project-specific voice rules)
- Terminology is consistent across documents (same concept = same term)
- Cross-references and links point to the correct targets
- Flag/option documentation matches across tutorial and reference docs

**Structural**
- Cross-linking between quadrants is present and correct
- No orphaned documents (every doc is reachable from nav or cross-references)
- No orphaned assets (images, diagrams referenced somewhere)

### Accuracy verification rules

When checking accuracy, the agent MUST:

1. **Verify against the actual codebase before flagging a doc issue.** Never assume the doc is wrong based on a pattern match or heuristic alone. Use the fastest available method:
   - **If tokensave is present**: use `tokensave_search` to check if a documented symbol exists, `tokensave_context` to get its signature/params without reading the file. This is the fastest path — 1-2 calls per symbol, no file I/O.
   - **If tokensave is not present**: use `grep` to find the symbol, then `read` only the relevant file section. Do not read entire files when a targeted grep + partial read suffices.
2. **Understand the distinction between dev-only and user-facing commands.**
   A command mentioned in AGENTS.md as "dev-only" refers to the specific wrapper or invocation described — not to every occurrence of the same binary name. For example, if AGENTS.md says `./mytool` (a bash wrapper) is dev-only but the Docker image internally runs `uv run mytool`, then `uv run mytool` in a tutorial is NOT a dev-only command — it's what the Docker image runs for end users. Always verify the full context before flagging.
3. **Distinguish illustrative from factual content.** Directory trees, schema
   examples, and protocol definitions may be illustrative. Check whether the document presents them as current state or as hypothetical examples.
4. **Verify previous issues are still present** before carrying them forward.
   Read the current file state — many issues may have been fixed in recent commits.

---

## PART 2: AUTOMATED DRIFT DETECTION

### Core capabilities

- **Full drift analysis** — map docs to code, compare git histories, detect renamed files, version drift, and structural gaps; classify each issue by category, severity, and fix type. Per-file factual drift (only flags when specific referenced source files changed). Referential drift suppressed by default (use `--include-referential`); `link_checker.py` covers broken links more reliably.
- **API doc validation** — AST-based extraction of Python signatures/classes compared against markdown API docs. Reports real drift (phantom docs, parameter mismatches, deprecations) as issues. Undocumented items are separated as prioritized suggestions (high/medium/low/skip) using heuristics — use `--suggest-coverage` to see them. Undocumented items do not affect the exit code or issue count.
- **Staleness scoring** — weighted 0-100 freshness score across five dimensions with CI threshold gates and README-focused mode. Respects `.gitignore`.
- **Link integrity audit** — validate local files, anchors, cross-document anchors, images, case-sensitivity, and duplicate anchors; optional external URL checks.
- **Drift classification** — structural, factual, referential, temporal categories (semantic removed as unreliable), each tagged `[AUTO]`/`[SEMI]`/`[MANUAL]` for fix routing.
- **CI/CD integration** — non-zero exit codes, JSON output, GitHub Actions and pre-commit recipes for ongoing monitoring.

### Tools

| Tool | Purpose | Command |
|------|---------|---------|
| `drift_analyzer.py` | Full drift analysis between code and docs | `python scripts/drift_analyzer.py <repo> --min-severity high --json` |
| `doc_staleness_scorer.py` | Score documentation freshness 0-100 | `python scripts/doc_staleness_scorer.py <repo> --threshold 60` |
| `api_doc_validator.py` | Validate API docs against Python source (AST) | `python scripts/api_doc_validator.py <src> <docs> --recursive` |
| `link_checker.py` | Audit all markdown links and anchors | `python scripts/link_checker.py <repo> --broken-only` |

All tools: Python 3.8+ stdlib only, `--json` and `--help`, non-zero exit codes for CI, any OS.

### False positive filtering

When running automated tools, filter out these known false positive patterns:

- **Duplicate anchors inside code blocks** — `link_checker.py` does not respect code fences; headings inside `markdown`/`yaml`/`text` code blocks are not real anchors.
- **Phantom docs for class methods** — `api_doc_validator.py` uses top-level AST extraction; class methods, stdlib imports, and protocol methods are invisible to it. Verify with grep before reporting.
- **Parameter mismatches from name collisions** — e.g., `Cache.cache(scenario)` vs `BranchCache.cache(templates_by_project, gitlab_manager)`. Verify which class the doc references.
- **Temporal drift on docs updated after source** — if the doc was committed after the source file, the temporal signal is a false positive.
- **Completeness=0 for Diátaxis docs** — `doc_staleness_scorer.py` detects Diátaxis quadrant directories and applies quadrant-specific completeness checks. If a doc scores 0 on completeness despite being in a quadrant directory, verify the directory name matches the expected signposts (see `--diataxis-translations` for non-English docs).
- **Illustrative paths in docs** — template placeholders (`<verifier_name>_result.py`), example file names, and glob patterns are intentional, not missing files.

### References

Load on demand — keep this file lean:

- **[references/workflows-and-tool-reference.md](references/workflows-and-tool-reference.md)** — quick start, 5 core workflows, GitHub Actions + pre-commit recipes, complete per-tool parameter/output/exit-code reference.
- **[references/scoring-categories-and-troubleshooting.md](references/scoring-categories-and-troubleshooting.md)** — staleness scoring model and weights, drift categories, auto-fix vs manual-fix classification, troubleshooting.
- **[references/operational-rules.md](references/operational-rules.md)** — tool invocation conventions, false positive patterns, real drift patterns, workflow order, and drift report conventions.
- **[../reference/documentation_standards.md](../reference/documentation_standards.md)** — README structure, API docs, changelogs, ADRs, docs-as-code standards — **shared**
- **[references/drift_prevention_guide.md](references/drift_prevention_guide.md)** — coupling strategies, CI gates, review checklists, prevention patterns.

### Assets

| Asset | Description |
|-------|-------------|
| [Report Template](assets/report_template.md) | Template for drift analysis reports |
| [Sample Drift Data](assets/sample_drift_data.json) | Sample JSON for testing and demonstration |

---

## WORKFLOW

### Phase 1: Automated tools (fast — run first)

1. **Read project rules:** AGENTS.md and any documentation rules in `~/.agents/rules/`.
2. **Run the 4 scripts** from `scripts/` — these are fast (seconds), find most issues, and require no graph index:
   - `link_checker.py` — broken links and duplicate anchors
   - `api_doc_validator.py` — API doc accuracy against source (AST)
   - `drift_analyzer.py` — full drift analysis
   - `doc_staleness_scorer.py` — freshness score
   - **Non-English documentation**: if `documentation_language` in `settings.json` is not `"en"`, translate the English signpost headings and directory names before running the staleness scorer. Write a JSON file (see `--diataxis-translations` in `reference/scripts.md` for the format) with the translated equivalents and pass it via `--diataxis-translations <path>`. The English signposts (e.g. `"tutorials"`, `"prerequisites"`, `"what we will learn"`) are the keys — translate each to the documentation language. Also translate the README section defaults (`installation`, `usage`, `api`, `contributing`, `license`) and include them as `readme_sections` in the JSON.
3. **Filter false positives** using the rules above.
4. **Inventory docs:** List all `.md` files in `.backstage/` and classify by Diátaxis quadrant.
5. **Review each document** against the Diátaxis compliance checklist (this is a doc-internal check — no source reading needed).

### Phase 2: Accuracy verification (split by tool availability)

For each issue that requires verifying a doc claim against source code, choose the fastest path:

#### If tokensave is present (`.tokensave/` exists)

- Use `tokensave_search` to check if a documented class/function/method exists (1 call, no file I/O).
- Use `tokensave_context` to get its signature and params without reading the file (1 call).
- Use `tokensave_callers` / `tokensave_callees` to verify documented call relationships.
- **Budget**: 3 `tokensave_context` calls max per project. After 3, fall back to `grep` + targeted `read`.
- For class methods that `api_doc_validator.py` reports as phantom: use `tokensave_search` with the method name — if it exists as a node, the doc is correct (the validator just can't see class methods via top-level AST).

#### If tokensave is not present

- Use `grep` to find the symbol in source, then `read` only the relevant lines (not the whole file).
- Batch grep queries: search for multiple symbol names in one pass where possible.

### Phase 3: Report

6. **Check previous review issues** (if any) against current file state.
7. **Produce a structured report** with grade, issues, and resolved items.

---

## REPORT FORMAT

Produce a structured markdown report with:

- **Grade** (0-100) with a points breakdown table
- **Summary** of findings
- **Issues** — each with: file path, line number(s), severity, problem, impact, suggested fix
- **Previous issues verified as resolved** (if applicable)
- **False positives filtered out** (if any tools were run)

### Grading scale

- 90-100: Excellent — minimal or no issues
- 75-89: Good — a few issues, overall solid quality
- 60-74: Fair — several issues that should be addressed
- 40-59: Poor — many issues, significant quality gaps
- 0-39: Failing — critical issues throughout

---

## Scope & Limitations

**Covers:**
- Diátaxis compliance, accuracy, consistency, and structure review
- Detection of documentation drift against git history for any git repository
- AST-based validation of Python API documentation
- Internal link validation including local files, anchors, cross-document anchors, images
- Multi-dimensional staleness scoring with configurable weights and CI/CD threshold enforcement

**Does NOT cover:**
- Non-Python source code API validation — the AST-based validator only parses Python
- External URL uptime monitoring — `--check-external` performs one-shot HEAD requests only
- Automatic documentation rewriting — tools classify issues but do not generate replacement text
- Content quality or readability assessment — staleness scoring measures freshness, not prose quality
