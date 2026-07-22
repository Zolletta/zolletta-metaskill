---
name: zolletta-metaskill-review
version: 1.1.0
license: MIT + Commons Clause
description: >
  Full project review orchestrator. Reads the project language from .zolletta-metaskill/settings.json (written by setup), then runs the appropriate specialist skills as subagents in parallel batches — general skills (patterns, documentor) always, plus language-specific skills when applicable (e.g. python-code-style and python-testing-patterns for Python). Saves each report to .zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/, produces an aggregated TODO.md organized by functional priority (dependency changes first, then by severity), and compares with the previous review's TODO to verify completion. Respond in the user's language.
allowed-tools:
  - read
  - grep
  - glob
  - exec
  - edit
  - write
  - skill
  - run_subagent
  - read_subagent
  - todo_write
  - ask_user_question
  - mcp_call_tool
  - mcp_list_tools
permissions:
  allow:
    - mcp__tokensave__tokensave_status
    - mcp__tokensave__tokensave_files
---

# Zolletta-metaskill Review — Orchestrator

You are an orchestrator that runs a full project review by invoking specialist skills in parallel batches, collecting each output, and producing an aggregated, prioritized TODO.

The set of skills depends on the project's primary language: **general skills** (design patterns, documentation) always run, while **language-specific skills** run only when the project uses the matching language.

## Shared resources

Read shared guidelines from the meta-skill (parent directory):

- `../reference/code-exploration.md` — code graph tools (tokensave) decision tree
- `../reference/general-principles.md` — SOLID, KISS, composition over inheritance (language-agnostic)
- `../reference/documentation_standards.md` — generic doc writing standards (README, API docs, changelogs, ADRs)
- `../reference/tool-messages.md` — "not installed" messages for the tool-failure handler
- `../scripts/` — shared scanning scripts (organised by language subdirectory)

**Tool-failure handler**: if a tokensave MCP call fails with tool-not-found / server-not-found, follow the [tool-failure handler](../SKILL.md#tool-failure-handler) in the meta-skill — update `settings.json`, print the "not installed" message, and continue with grep/read fallback.

**Respond in the same language the user used to invoke you.** If the user wrote in Italian,
respond in Italian. If in English, respond in English. And so on for any other language.

## Procedure

### Step 1 — Read the project language from settings.json

The setup guard (see the meta-skill's [setup guard](../SKILL.md#setup-guard)) guarantees that `.zolletta-metaskill/settings.json` exists before this subcommand runs.

1. Read `.zolletta-metaskill/settings.json` and extract the `language` field.
2. If `settings.json` is missing or `language` is empty, fall back to detecting
   the language using the marker list in `setup/SKILL.md` Step 3.
3. If the language cannot be determined, ask the user with `ask_user_question`.
4. Store the detected language for use in subsequent steps.

### Step 1.5 — Tokensave pre-flight check (before launching subagents)

This step ensures the tokensave index is fresh before any subagent uses it. Stale indices cause subagents to silently fall back to direct file reads, degrading review quality without warning. This check runs **in the orchestrator**, not in each subagent, to avoid redundant checks and race conditions on `tokensave sync`.

**Only run this step if `tokensave_available` is `true` in `settings.json`.** If `tokensave_available` is `false`, skip this step — subagents will use the grep/read fallback as usual.

1. **Call `tokensave_status`** (no arguments) via the tokensave MCP server.
2. **Check index freshness** using the response fields:
   - **`file_count` vs actual source files**: count `.py` files (or the project's primary language extension) under `src/` using `find src/ -name '*.py' | wc -l` (adapt the extension for the project language). If the indexed `file_count` is significantly lower than the actual count (ratio < 0.8), the index is stale.
   - **`branch_fallback` / `branch_warning`**: if `branch_fallback` is `true` or a `branch_warning` string is present, the current branch is not tracked. Run `tokensave branch add <current_branch>` (use `git branch --show-current` to get the branch name) before syncing.
   - **`last_sync_at` staleness**: if the last sync was more than 1 hour ago (compare `last_sync_at` epoch timestamp to current time), the index is stale.
3. **If any check fails, re-sync the index**:
   - If `branch_fallback` is `true`: run `tokensave branch add <current_branch>` first.
   - Then run `tokensave sync` and wait for it to complete.
   - After sync, call `tokensave_status` again to confirm the index is now fresh.
4. **If `tokensave sync` fails or the index remains stale after sync**: print a warning at the top of the SUMMARY.md ("⚠️ tokensave index is stale — review quality may be degraded for code exploration tasks") and continue. Do not abort the review. Each subagent will use the grep/read fallback per the tool-failure handler.
5. **If all checks pass**: proceed to Step 2. No warning is needed.

> **Why this runs in the orchestrator**: running `tokensave sync` inside a subagent would risk concurrent syncs if multiple subagents detect staleness simultaneously. The orchestrator syncs once, before any subagent launches, so all subagents see a consistent fresh index.

### Step 2 — Create the review folder

1. Generate a timestamp in `YYYY-MM-DD-HH-MM` format. Use `date +%Y-%m-%d-%H-%M` to get this.
2. Create the directory `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/`.

### Step 3 — Check for previous reviews

1. List all subdirectories under `.zolletta-metaskill/reports/` (if any exist).
2. If there are previous review folders, identify the **newest** one (excluding the one you just created). Read its `TODO.md` if it exists.
3. Keep this previous TODO for the comparison in Step 6.

### Step 4 — Launch the review subagents in parallel

Launch **one subagent per command**, all in parallel as background subagents (`is_background: true`). Issue all `run_subagent` calls in a single tool-call block so they run concurrently. Each subagent writes its own report file directly to the review folder — the orchestrator does not collect and save reports on their behalf.

**General skills** (always run, regardless of language):

- `/zolletta-metaskill patterns` — design pattern analysis (language-agnostic principles + language-specific scripts when available)
- `/zolletta-metaskill documentor` — documentation review (Diátaxis compliance + drift detection)

**Language-specific skills** (run only when the project uses the matching language **and** the skill is available):

| Language   | Skill                     | Settings flag                       | Scope                                                                         |
|---|---|---|---|
| Python     | `python-code-style`       | `python_code_style_available`       | Style, linting, formatting, naming, docstrings, type annotations              |
| Python     | `python-testing-patterns` | `python_testing_patterns_available` | Test isolation, naming, coverage gaps, mocking, fixture design, AAA structure |

> When support for other languages is added, extend this table with the corresponding skills.

**Checking skill availability**: before launching, read `python_code_style_available` and `python_testing_patterns_available` from `settings.json`. If a flag is `false` (non-Python project), **skip that skill** — do not launch a subagent for it. The SUMMARY.md and TODO.md should note that the area was not reviewed. The Python skills are bundled inside this meta-skill, so they are always available for Python projects — no "Skill not found" handling is needed.

**Skill scopes:**

| Skill                            | Type                                   | Scope                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                              |
|---|---|---|
| `python-code-style`              | bundled skill (Python only)            | Review **all Python source code** in `src/` (and any other source dirs) for style, linting, formatting, naming, docstring, and type annotation issues. Run in **review mode (read-only)** per [`../reference/review-mode.md`](../reference/review-mode.md): use `ruff check` (no `--fix`), `ruff format --check`, `ty check` (no `--fix`), and `mypy` as-is. Auto-fixable issues are informational only — do not count them toward the grade. Read rule toggles from `python_code_style_rules` in `settings.json` and effective tool config from `python_config`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| `python-testing-patterns`        | bundled skill (Python only)            | Review **all test code** in `tests/` for testing best practices: test isolation, naming, mocking patterns, fixture design, AAA structure. **Coverage gap analysis**: run `pytest --cov` (mandatory) and flag only modules with coverage below 50% AND no direct test references AND all callers mocked. Do NOT duplicate the structural "missing test file" check from `scan_tests.py` — that is owned by `/zolletta-metaskill patterns`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| `/zolletta-metaskill patterns`   | zolletta-metaskill subcommand (always) | Review **all source code** in `src/` for design pattern issues: KISS violations, SRP violations, tight coupling, composition vs inheritance, God classes, premature abstraction, SOLID principle violations (OCP, LSP, ISP, DIP). Also check structural conventions: one class per file, and test directory structure mirroring source structure. **For Python projects**: run all eight scanning scripts (`scan_class_metrics.py`, `scan_test_god_classes.py`, `scan_one_class_per_file.py`, `scan_tests.py`, `scan_dependency_inversion.py`, `scan_interface_segregation.py`, `scan_open_closed.py`, and `scan_liskov_substitution.py` from `src/zolletta_metaskill/scanners/`) for automated triage, then apply the "reason to change" test to the top candidates. **This is a mandatory step, not optional.** See `patterns/SKILL.md` → "Mandatory Procedure" for the full procedure. You MUST read `../reference/general-principles.md` (God class detection procedure + "What is NOT a God class") before evaluating any class. **You must NOT report a class as a God class based on size alone** — size is a triage signal, never a verdict. Classes that are parsers, strategies, orchestrators, or factories serving a single domain must be suppressed. **Use the `scan_tests.py` markdown output directly in the report**: its five tables (misnamed tests, misplaced tests, orphaned tests, multi-class tests, missing tests) are **structural** findings — they check file naming and directory mirroring, not actual code coverage. Copy them into the report's findings section **except the "Missing tests" table**: before reporting any file from the "Missing tests" table as a finding, run `pytest --cov` and check the file's coverage. If coverage >50%, downgrade to informational. Only report as a finding if coverage <50% AND no indirect references. **Do not flag coverage gaps** — that is owned by `python-testing-patterns` which runs `pytest --cov`. **The DIP scanner excludes composition roots** (entry points by filename + classes that create DI containers via `make_container()`/`Container()` detected semantically). If the scanner still flags a class that is clearly a composition root, suppress it and note "composition root — not a DIP violation". Use `test_splitter.py` if the human decides to split a test God class. **For other languages**: apply the same principles manually (no AST scripts available yet). **If `.tokensave/` exists, use the code graph tools** (tokensave_context/callees/callers or tokensave_impact) to understand class responsibilities and assess blast radius before proposing splits — see the skill's "Code Graph Tools" section for the decision tree. |
| `/zolletta-metaskill documentor` | zolletta-metaskill subcommand (always) | Review **documentation in `.backstage/` only**: [Diátaxis](https://diataxis.fr/) compliance (document type correctness, audience clarity, structure, accuracy, consistency) **and** drift detection (staleness, broken links, API doc validation, structural gaps) in a single pass. **Follow `documentor/references/operational-rules.md`** for false positive patterns, correct tool invocation (project root as repo path for staleness scorer), and the recommended workflow order.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |

**Each subagent writes its own report file.** The subagent is given the output path and must use the `write` tool to save its report directly. The orchestrator does not collect subagent output and save it — that is the subagent's responsibility.

| Subagent                | Output file                                                                 |
|---|---|
| python-code-style       | `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/python-code-style.md`       |
| python-testing-patterns | `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/python-testing-patterns.md` |
| patterns                | `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/patterns.md`                |
| documentor              | `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/documentor.md`              |

**Subagent task template** (adapt for each):

```
You are performing a code review on a <language> project.

First, invoke the skill "<skill-name>" using the skill tool to load its guidelines.
Then apply those guidelines to review the following scope:

<scope description>

Project root: <current working directory>
AGENTS.md: Read the project's AGENTS.md (and ~/.agents/AGENTS.md) for project-specific and global rules.
Review mode: follow ../reference/review-mode.md — read-only, no fixes applied. Auto-fixable
issues are informational only and do not count toward the grade.

settings.json: Read .zolletta-metaskill/settings.json for tool availability (python.*),
effective tool config (python_config.*), and rule toggles (python_code_style_rules.*).

You MUST write your report to this file using the write tool:
  <output_file_path>

Follow the report template for this skill (linked in the skill's "Output" section):
  - python-code-style: assets/report_template.md
  - python-testing-patterns: assets/report_template.md
  - patterns: assets/report_template.md
  - documentor: assets/report_template.md

The report must include:
- A **grade** section at the top with a numeric score from 0 to 100 for the project's
  performance in the scope you reviewed. Justify the score with a brief breakdown of
  what earned points and what lost points.
- The skill-specific sections from the report template (tool results, coverage tables,
  scanning script results, etc. as applicable)
- Findings grouped by severity (critical/high/medium/low) using the template's table format
- If no issues are found, state that explicitly with a brief explanation of what was checked

**Grading scale** (0-100):
- 90-100: Excellent — minimal or no issues, follows best practices consistently
- 75-89: Good — a few issues, overall solid quality
- 60-74: Fair — several issues that should be addressed, quality is acceptable but needs work
- 40-59: Poor — many issues, significant quality gaps
- 0-39: Failing — critical issues throughout, major rework needed

Write the report to <output_file_path> using the write tool. Do NOT return the report
as your final output — write it to the file. Return only a one-line confirmation that
the file was written, along with the grade you assigned.
```

### Step 5 — Wait for all subagents to complete

After launching all subagents in parallel, wait for each one to finish using `read_subagent` (`block: true`). Each subagent writes its own report file — the orchestrator only needs to confirm completion and collect the grade from each subagent's one-line confirmation.

If a subagent fails or times out, create its report file with a note explaining what happened, and continue — do not abort the entire review.

### Step 6 — Compare with previous review (if exists)

If a previous review folder was found in Step 3:

1. Read the previous `TODO.md`.
2. For each item in the previous TODO, check whether it has been addressed:
   - Search the codebase for the files/areas mentioned in the item
   - Use `git log --oneline -20` and `git diff` to see recent changes
   - Determine if the issue described has been fixed, partially fixed, or is still open
3. Create a section in the new TODO.md called "## Previous review status" that lists
   each previous TODO item with its status: ✅ Done / ⚠️ Partially done / ❌ Not done.
4. Any items that are ❌ Not done or ⚠️ Partially done should be carried forward into
   the new TODO as high-priority items (they were already identified and not resolved).

If no previous review exists, skip this step (note in the TODO that this is the first review).

### Step 7 — Create the executive summary (SUMMARY.md)

Read all report files that were produced by the subagents and extract the grade from each. Create `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/SUMMARY.md` following the [summary template](assets/summary_template.md).

The SUMMARY.md is an executive overview — it contains grades, strengths, weaknesses, and trends. It does **not** duplicate the detailed findings from the specialist reports. Instead, it links to them in a "Detailed reports" section so the reader can drill down.

**Overall grade calculation**: use a weighted average of the sub-grades. Only include areas that were actually run. Suggested weights for a Python project (4 skills):

| Area            | Weight   |
|---|---|
| Code style      | 30%      |
| Testing         | 30%      |
| Design patterns | 25%      |
| Documentation   | 15%      |

For non-Python projects (2 skills — patterns + documentor only):

| Area            | Weight   |
|---|---|
| Design patterns | 60%      |
| Documentation   | 40%      |

If the project has no `.backstage/` directory, redistribute the documentation weight equally across the other areas.

If a previous review exists, include a "Trend vs previous review" subsection noting whether the overall grade improved, worsened, or stayed the same, and by how many points.

### Step 8 — Create the aggregated TODO.md

Read all report files produced by the subagents. Create `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/TODO.md` following the [TODO template](assets/todo_template.md).

The TODO.md is a prioritized action list — it does **not** duplicate the full findings from the specialist reports. Each item links to the relevant specialist report for full details (file path, line numbers, impact, suggested fix).

**Organization rules** (in this exact order):

1. **Dependency changes (under my control)** — any findings that require changes to
   internal/shared packages or other dependencies I own. These go first because everything else may depend on them being released. Mark each with a note: "⚠️ Requires dependency release — do these first, then wait for the release before proceeding."

2. **Critical / blocking issues** — anything that breaks functionality, causes data loss,
   security issues, or prevents the project from working.

3. **High priority** — significant code quality, design, or testing issues that should be
   addressed soon but don't block work.

4. **Medium priority** — style, documentation, and minor design improvements.

5. **Low priority** — nice-to-haves, cosmetic changes, future improvements.

6. **Previous review status** — the carry-forward section from Step 6 (if applicable).

**Numbering**: Assign each issue a unique sequential number starting from 1, counting continuously across all sections (Critical → High → Medium → Low). Do NOT restart numbering per section. The number goes before the priority tag.

### Step 9 — Summary response

After all files are saved and the SUMMARY.md and TODO.md are created, respond to the user with:

1. The project language (from `settings.json`)
2. A brief summary of what was reviewed and where the reports are saved
3. **The overall grade** (from SUMMARY.md) with a one-line interpretation
4. The grades by area (from the SUMMARY.md table)
5. The total number of findings by severity
6. The number of items carried forward from the previous review (if any) and their status
7. The top 3 strengths and top 3 weaknesses (from SUMMARY.md)
8. The top 3 priority items from the TODO
9. The paths to the SUMMARY.md and TODO.md files

Keep the summary concise. The full details are in the report files.

## Error handling

- If a subagent fails or times out, note it in the corresponding report file and continue
  with the next subagent in the sequence. Do not abort the entire review.
- If the `.backstage/` directory does not exist, the `documentor` subagent should report
  that there is nothing to review (not an error).
- If `src/` or `tests/` directories don't exist, adapt the scope to whatever source
  directories are present in the project.
- If the project language cannot be determined automatically, ask the user before proceeding.
