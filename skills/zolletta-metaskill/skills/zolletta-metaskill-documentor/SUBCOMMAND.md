---
name: zolletta-metaskill-documentor
description: >
  Reviews project documentation for Diátaxis structure, accuracy, consistency, and drift against the codebase; writes dated reports. Use when auditing docs or gating doc quality. Do not use to author documentation.
license: MIT + Commons Clause
---

# Zolletta-metaskill Documentor

A unified documentation review skill that combines:

1. **Diátaxis compliance** — structure, audience clarity, type correctness, voice consistency
2. **Accuracy review** — verify docs match the actual codebase (fields, signatures, commands, paths)
3. **Drift detection** — automated staleness scoring, link integrity, API doc validation via AST

Derived from the [Diátaxis Documentation Expert](https://github.com/github/awesome-copilot/blob/main/skills/documentation-writer/SKILL.md) skill (MIT, github/awesome-copilot) and the [Doc Drift Detector](https://github.com/borghei/Claude-Skills/blob/main/engineering/doc-drift-detector/SKILL.md) (MIT + Commons Clause, borghei/Claude-Skills), merged into a single review pipeline.

> This file narrows down any eventual general rule about code exploration and documentation, i.e. `code-exploration-rules.md`, `tokensave-rules.md`, `documentation-rules.md`. If you maintain rules as part of your agent configuration, those are the single source of truth for their domain.
>
> **Execution protocol**: when running a review, follow `../../docs/reference/code/scripts-first-protocol.md` — run `documentor_client.py`, which executes the quality review (drift + staleness), API doc validation, and link checking, persisting each tool's output to `cache/` (`quality.json`, `api_doc_validator.json`, `link_checker.json`) and printing an aggregated report. Run `quality/unwrapped_prose_scanner.py` separately when `documentation.check_unwrapped_prose` is on — it is opt-in and is **not** part of `documentor_client.py`, so redirect its JSON to `cache/unwrapped_prose.json` yourself. Assemble deterministic report sections from cached output, then run only the judgment pass items (false-positive filtering for known FP patterns — only open source files for FP candidates). Write your report to `reports/documentor.md`. Do not re-read source files the drift tools already validated.

## Shared resources

Read shared guidelines from the meta-skill (parent directory):

- `../../docs/reference/code/code-exploration.md` — code graph tools (tokensave) decision tree
- `../../docs/explanation/documentation/standards.md` — generic doc writing standards (README, API docs, changelogs, ADRs)
- `../../docs/explanation/code/general-principles.md` — SOLID, KISS, composition over inheritance (language-agnostic)
- `../../docs/reference/tool-messages.md` — "not installed" messages for the tool-failure handler
- `../../src/zolletta_metaskill/code_style/general/` — shared code style scanning scripts
- `../../src/zolletta_metaskill/testing_style/general/` — shared testing style scanning scripts
- `../../src/zolletta_metaskill/patterns/` — pattern-specific scanning scripts

**Tool-failure handler**: if a tokensave query fails on every available transport — `tokensave tool <name>` and, where the harness exposes them, the `tokensave_*` MCP tools (the fallback for binaries older than 7.14) — follow the tool-failure handler (`../../SKILL.md#tool-failure-handler`) in the meta-skill — update `settings.json`, print the "not installed" message, and continue with grep/read fallback.

Local scripts and references are in these locations:

- `../../src/zolletta_metaskill/documentor/` — drift detection tools (Python stdlib only)
- `../../docs/reference/documentation/` — drift scoring, workflow, and operational rules
- `../../docs/explanation/documentation/` — drift prevention strategies and documentation standards
- `assets/` — report templates and sample data

---

## GUIDING PRINCIPLES

1. **Clarity:** Write in simple, clear, and unambiguous language.
2. **Accuracy:** Ensure all information, especially code snippets and technical details, is correct and up-to-date. Verify claims against the actual codebase.
3. **User-Centricity:** Always prioritize the user's goal. Every document must help a specific user achieve a specific task.
4. **Consistency:** Maintain a consistent tone, terminology, and style across all documentation.

---

## PART 1: DIÁTAXIS COMPLIANCE REVIEW

### The four document types

Diátaxis defines four quadrants. Each document must belong to exactly one:

- **Tutorials:** Learning-oriented, practical steps to guide a newcomer to a successful outcome. A lesson.
- **How-to Guides:** Problem-oriented, steps to solve a specific problem. A recipe.
- **Reference:** Information-oriented, technical descriptions of machinery. A dictionary.
- **Explanation:** Understanding-oriented, clarifying a particular topic. A discussion.

### Review checklist

For each document, verify:

#### Type correctness

- Document is placed in the correct Diátaxis quadrant
- Content matches the quadrant's purpose (no explanation in reference, no tutorial in how-to, etc.)
- No hybrid content that blurs quadrant boundaries

#### Audience clarity

- Tutorials include "What we will learn" and "Prerequisites"
- How-to guides include "Prerequisites" or "Before Starting"
- Reference docs are factual and structure-focused
- Explanation docs provide context and design rationale

#### Accuracy

- Code snippets match the actual codebase (verify via tokensave first, `read` only as fallback)
- Field names, types, and signatures match the source
- File paths and directory trees reflect the actual repository structure
- CLI commands match the actual entry points and flags
- No documented fields/features that don't exist in the code
- No undocumented fields/features that exist in the code but are missing from docs

#### Consistency

- Voice convention is followed (check AGENTS.md for project-specific voice rules)
- Terminology is consistent across documents (same concept = same term)
- Cross-references and links point to the correct targets
- Flag/option documentation matches across tutorial and reference docs

#### Structural

- Cross-linking between quadrants is present and correct
- No orphaned documents (every doc is reachable from nav or cross-references)
- No orphaned assets (images, diagrams referenced somewhere)

### Accuracy verification rules

When checking accuracy, the agent MUST:

1. **Verify against the actual codebase before flagging a doc issue.** Never assume the doc is wrong based on a pattern match or heuristic alone. Use the fastest available method:
   - **If tokensave is present**: use `tokensave tool search` to check if a documented symbol exists, `tokensave tool context` to get its signature/params without reading the file (or the `tokensave_*` MCP tools on binaries older than 7.14). This is the fastest path — 1-2 calls per symbol, no file I/O.
   - **If tokensave is not present**: use `grep` to find the symbol, then `read` only the relevant file section. Do not read entire files when a targeted grep + partial read suffices.
2. **Understand the distinction between dev-only and user-facing commands.**
   A command mentioned in AGENTS.md as "dev-only" refers to the specific wrapper or invocation described — not to every occurrence of the same binary name. For example, if AGENTS.md says `./mytool` (a bash wrapper) is dev-only but the Docker image internally runs `uv run mytool`, then `uv run mytool` in a tutorial is NOT a dev-only command — it's what the Docker image runs for end users. Always verify the full context before flagging.
3. **Distinguish illustrative from factual content.** Directory trees, schema examples, and protocol definitions may be illustrative. Check whether the document presents them as current state or as hypothetical examples.
4. **Verify previous issues are still present** before carrying them forward. Read the current file state — many issues may have been fixed in recent commits.

---

## PART 2: AUTOMATED DRIFT DETECTION

### Core capabilities

- **Unified quality review** — drift detection and staleness scoring in a single pass: map docs to code, compare git histories, detect renamed files, version drift, and structural gaps; classify each issue by category, severity, and fix type. Per-file factual drift (only flags when specific referenced source files changed). Referential drift suppressed by default (`documentation.include_referential`); `links/link_checker.py` covers broken links more reliably.
- **API doc validation** — AST-based extraction of Python signatures/classes compared against markdown API docs. Reports real drift (phantom docs, parameter mismatches, deprecations) as issues. Undocumented items are separated as prioritized suggestions (high/medium/low/skip) using heuristics — enable `documentation.api_doc_suggest_coverage` to see them. Undocumented items do not affect the exit code or issue count.
- **Staleness scoring** — weighted 0-100 freshness score across five dimensions with an optional `documentation.staleness_threshold` CI gate and README-focused mode. Respects `.gitignore`.
- **Link integrity audit** — validate local files, anchors, cross-document anchors, images, case-sensitivity, and duplicate anchors; optional external URL checks (`documentation.check_external`).
- **Drift classification** — structural, factual, referential, temporal categories (semantic removed as unreliable), each tagged `[AUTO]`/`[SEMI]`/`[MANUAL]` for fix routing.
- **Aggregated reporting** — `documentor_client.py` runs all three tools, each of which writes its own JSON cache file (`quality.json`, `api_doc_validator.json`, `link_checker.json`), then merges them into a single review report via `report_aggregator.py`.
- **Prose formatting audit (opt-in)** — `quality/unwrapped_prose_scanner.py` reports markdown paragraphs broken mid-sentence, one finding per paragraph naming the line span. Enable `documentation.check_unwrapped_prose` to include it; it prints SKIPPED and exits 0 while off, and it is deliberately **not** wired into `documentor_client.py` because an unwrapped-paragraph backlog can be long and would drown the drift report until cleared.
- **CI/CD integration** — JSON output, optional staleness threshold gate, GitHub Actions and pre-commit recipes for ongoing monitoring.

### Scope

Every tool below reads **only the documentation** — the markdown under `documentation.dir` (default `docs/`, from `settings.json`) plus the root documents `README.md`, `CONTRIBUTING.md` and `AGENTS.md` — and the source that documentation describes. `DocumentationFilesFinder` is the one definition of that set: it names the root documents rather than widening a glob, and the set is markdown because the link and reference extractors are markdown-shaped. Markdown elsewhere in the repository is out of scope and a finding against it is a false positive by definition: `skills/` holds subagent contracts rather than documentation, `SKILL.md` is a routing contract, and `CHANGELOG.md` is generated. Do not widen the scan to "find more markdown", and do not report a file the tools did not read. Two deliberate exceptions: `documentation.readme_focus` narrows `quality/quality_review.py` to the README alone, and `links/link_checker.py` reads every markdown file in the repository, because a link is broken wherever it is written and a link checker that skipped `skills/` would report it clean.

### Tools

| Tool                                 | Purpose                                                                               | Command                                                                                      |
|--------------------------------------|---------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------|
| `documentor_client.py`               | Run all documentor tools and aggregate into one report                                | `python ../../src/zolletta_metaskill/documentor/documentor_client.py [--json]`               |
| `quality/quality_review.py`          | Unified drift + staleness review (writes `quality.json`)                              | `python ../../src/zolletta_metaskill/documentor/quality/quality_review.py [--json]`          |
| `api_doc/api_doc_validator.py`       | Validate API docs against Python source (AST)                                         | `python ../../src/zolletta_metaskill/documentor/api_doc/api_doc_validator.py [--json]`       |
| `links/link_checker.py`              | Audit links and anchors in every markdown file                                        | `python ../../src/zolletta_metaskill/documentor/links/link_checker.py [--broken-only]`       |
| `quality/unwrapped_prose_scanner.py` | Flag paragraphs hard-wrapped across lines (opt-in, not run by `documentor_client.py`) | `python ../../src/zolletta_metaskill/documentor/quality/unwrapped_prose_scanner.py [--json]` |

All tools: Python 3.8+ stdlib only, run from the repository root, `[--json]` and `--help`, any OS. Paths and thresholds come from `documentation.*` in `.zolletta-metaskill/settings.json` — see `../../docs/reference/settings-schema.md`. Each tool writes its JSON cache into the current run directory, `<runs_dir>/<YYYY-MM-DD-HH-MM>/cache/` — `.zolletta-metaskill/<timestamp>/cache/` with the default `runs_dir` — so each review keeps its own history instead of overwriting the last; before the first run directory exists, artifacts land in `<runs_dir>/cache/`.

### False positive filtering

When running automated tools, filter out these known false positive patterns:

- **Duplicate anchors inside code blocks** — `links/link_checker.py` does not respect code fences; headings inside `markdown`/`yaml`/`text` code blocks are not real anchors.
- **Phantom docs for class methods** — `api_doc/api_doc_validator.py` uses top-level AST extraction; class methods, stdlib imports, and protocol methods are invisible to it. Verify with grep before reporting.
- **Parameter mismatches from name collisions** — e.g., `Cache.cache(scenario)` vs `BranchCache.cache(templates_by_project, gitlab_manager)`. Verify which class the doc references.
- **Temporal drift on docs updated after source** — if the doc was committed after the source file, the temporal signal is a false positive.
- **Completeness=0 for Diátaxis docs** — `quality/quality_scorer.py` detects Diátaxis quadrant directories and applies quadrant-specific completeness checks. If a doc scores 0 on completeness despite being in a quadrant directory, verify the directory name matches the expected signposts (see `documentation.diataxis_translations` for non-English docs).
- **Illustrative paths in docs** — template placeholders (`<verifier_name>_result.py`), example file names, and glob patterns are intentional, not missing files.
- **adr-distilled.md** — auto-generated by the ADR distiller during review, lives in the ADR directory. Do not flag it for drift or staleness.
- **Prose wrapping inside generated or quoted material** — `quality/unwrapped_prose_scanner.py` skips fenced code, frontmatter, tables, blockquotes and nested lists by design. A paragraph broken mid-sentence inside a ```text template or a quoted sample is not reported; if you see one, the text is a code block the tool correctly left alone.

### References

Load on demand — keep this file lean:

- **`../../docs/reference/documentation/workflows-and-tools.md`** — quick start, 5 core workflows, GitHub Actions + pre-commit recipes, complete per-tool parameter/output/exit-code reference.
- **[docs/reference/documentation/scoring-and-categories.md](../../docs/reference/documentation/scoring-and-categories.md)** — staleness scoring model and weights, drift categories, auto-fix vs manual-fix classification, troubleshooting.
- **[docs/reference/documentation/operational-rules.md](../../docs/reference/documentation/operational-rules.md)** — tool invocation conventions, false positive patterns, real drift patterns, workflow order, and drift report conventions.
- **`../../docs/explanation/documentation/standards.md`** — README structure, API docs, changelogs, ADRs, docs-as-code standards — **shared**
- **[docs/explanation/documentation/drift-prevention.md](../../docs/explanation/documentation/drift-prevention.md)** — coupling strategies, CI gates, review checklists, prevention patterns.

### Assets

| Asset                                              | Description                               |
|----------------------------------------------------|-------------------------------------------|
| [Report Template](assets/report_template.md)       | Template for drift analysis reports       |
| [Sample Drift Data](assets/sample_drift_data.json) | Sample JSON for testing and demonstration |

---

## WORKFLOW

### Phase 1: Automated tools (fast — run first)

1. **Read project rules:** `AGENTS.md` and any documentation rules in your agent configuration.
2. **Run `documentor_client.py`** — fast (seconds), finds most issues, requires no graph index. It runs all three tools, each writing its own `cache/` artifact, and prints the aggregated report:
   - `quality/quality_review.py` — unified drift analysis + freshness score (`cache/quality.json`)
   - `api_doc/api_doc_validator.py` — API doc accuracy against source (AST) (`cache/api_doc_validator.json`)
   - `links/link_checker.py` — broken links and duplicate anchors (`cache/link_checker.json`)
   - `quality/unwrapped_prose_scanner.py` — only when `documentation.check_unwrapped_prose` is `true` in `settings.json`; redirect to `cache/unwrapped_prose.json`. It reports SKIPPED and exits 0 otherwise, so an unconfigured project is unaffected.
   - **Non-English documentation**: if `documentation.language` in `settings.json` is not `"en"`, translate the English signpost headings and directory names before running the quality review. Write a JSON file (see `documentation.diataxis_translations` in `docs/reference/code/scripts.md` for the format) with the translated equivalents and set it via `documentation.diataxis_translations` in `settings.json`. The English signposts (e.g. `"tutorials"`, `"prerequisites"`, `"what we will learn"`) are the keys — translate each to the documentation language. Also translate the README section defaults (`installation`, `usage`, `api`, `contributing`, `license`) and include them as `readme_sections` in the JSON.
3. **Filter false positives** using the rules above.
4. **Inventory docs:** List all `.md` files in the documentation directory (`documentation.dir` from `settings.json`, default `docs/`) and classify by Diátaxis quadrant.
5. **Review each document** against the Diátaxis compliance checklist (this is a doc-internal check — no source reading needed).

### Phase 2: Accuracy verification (split by tool availability)

For each issue that requires verifying a doc claim against source code, choose the fastest path:

#### If tokensave is present (`.tokensave/` exists)

- Use `tokensave tool search` to check if a documented class/function/method exists (1 call, no file I/O).
- Use `tokensave tool context` to get its signature and params without reading the file (1 call).
- Use `tokensave tool callers` / `tokensave tool callees` to verify documented call relationships.
- **Budget**: 3 `tokensave tool context` calls max per project. After 3, fall back to `grep` + targeted `read`.
- For class methods that `api_doc_validator.py` reports as phantom: use `tokensave tool search` with the method name — if it exists as a node, the doc is correct (the validator just can't see class methods via top-level AST).

#### If tokensave is not present

- Use `grep` to find the symbol in source, then `read` only the relevant lines (not the whole file).
- Batch grep queries: search for multiple symbol names in one pass where possible.

### Phase 3: Report

1. **Check previous review issues** (if any) against current file state.
2. **Produce a structured report** with grade, issues, and resolved items.

---

## REPORT FORMAT

Produce a structured markdown report with:

- **Grade** (0-100) with a points breakdown table — **zero findings means 100**; otherwise compute `100 − Σ weight(finding)` (`critical −40 · high −15 · medium −5 · low −2`), adjustable by at most ±5 when the justification names the finding(s) and why. Every deduction must name the finding that cost the points (full rule: `../../docs/reference/code/review-mode.md` → "Grading")
- **Summary** of findings
- **Issues** — each with: file path, line number(s), severity, problem, impact, suggested fix
- **Previous issues verified as resolved** (if applicable)
- **False positives filtered out** (if any tools were run)

For example:

```markdown
## Grade: 78/100 — Good

| Section                     | Points |
|-----------------------------|--------|
| Diátaxis structure          | 24/30  |
| Accuracy vs codebase        | 21/30  |
| Freshness (staleness score) | 18/25  |
| Link integrity              | 15/15  |

Findings: 3 medium, 5 low — see per-file table below.
```

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
- Hard-wrapped prose paragraph detection across `documentation.dir` (opt-in via `documentation.check_unwrapped_prose`)

**Does NOT cover:**

- Non-Python source code API validation — the AST-based validator only parses Python
- External URL uptime monitoring — `documentation.check_external` performs one-shot HEAD requests only
- Automatic documentation rewriting — tools classify issues but do not generate replacement text
- Content quality or readability assessment — staleness scoring measures freshness, not prose quality
