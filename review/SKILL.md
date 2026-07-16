---
name: zolletta-review
version: 1.0.0
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
---

# Zolletta Review — Orchestrator

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

### Step 2 — Create the review folder

1. Generate a timestamp in `YYYY-MM-DD-HH-MM` format. Use `date +%Y-%m-%d-%H-%M` to get this.
2. Create the directory `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/`.

### Step 3 — Check for previous reviews

1. List all subdirectories under `.zolletta-metaskill/reports/` (if any exist).
2. If there are previous review folders, identify the **newest** one (excluding the one you just created). Read its `TODO.md` if it exists.
3. Keep this previous TODO for the comparison in Step 6.

### Step 4 — Launch the review subagents in parallel batches

Launch subagents in **batches** using `run_subagent` with `is_background: true`. Within each batch, launch all subagents in a single tool-call block so they run concurrently. After launching a batch, wait for all its subagents to finish (using `read_subagent` with `block: true`) and save their reports before starting the next batch.

**General skills** (always run, regardless of language):

- `/zolletta patterns` — design pattern analysis (language-agnostic principles + language-specific scripts when available)
- `/zolletta documentor` — documentation review (Diátaxis compliance + drift detection)

**Language-specific skills** (run only when the project uses the matching language **and** the skill is available):

| Language | Skill | Settings flag | Scope |
|----------|-------|---------------|-------|
| Python | `python-code-style` | `python_code_style_available` | Style, linting, formatting, naming, docstrings, type annotations |
| Python | `python-testing-patterns` | `python_testing_patterns_available` | Test isolation, naming, coverage gaps, mocking, fixture design, AAA structure |

> When support for other languages is added, extend this table with the corresponding skills.

**Checking skill availability**: before launching Batch 1, read `python_code_style_available` and `python_testing_patterns_available` from `settings.json`. If a flag is `false` (non-Python project), **skip that skill** — do not launch a subagent for it. The SUMMARY.md and TODO.md should note that the area was not reviewed. The Python skills are bundled inside this meta-skill, so they are always available for Python projects — no "Skill not found" handling is needed.

**Batching strategy**: group skills into batches of up to 3 parallel background subagents. Place general skills and language-specific skills across batches to maximise parallelism. For Python projects with both skills available (4 skills total), use two batches:

**Batch 1** (up to 2 parallel background subagents — bundled Python skills, Python only):

1. `python-code-style` (skip if `python_code_style_available: false`)
2. `python-testing-patterns` (skip if `python_testing_patterns_available: false`)

**Batch 2** (2 parallel background subagents — zolletta subcommands, always):

3. `/zolletta patterns`
4. `/zolletta documentor`

If both Python skills are unavailable, skip Batch 1 entirely and only run Batch 2. For non-Python projects, all skills are general — run them in a single batch of 2.

**Why batching**: at most one foreground subagent can run at a time, so all subagents in a batch MUST be launched as background (`is_background: true`). Issue all `run_subagent` calls for a batch in a single response (parallel tool calls), then collect each result with `read_subagent` (block: true) in the next turn. Save each report immediately after collecting it.

**Important**: Each subagent must be given the full context of what to review and must invoke the relevant skill via the `skill` tool. The subagent should:

1. Invoke the skill with `skill invoke <skill-name>`
2. Apply the skill's guidelines to review the specified scope
3. Return a structured markdown report with findings (issues, file paths, line numbers, severity, suggested fixes)

**Skill scopes:**

| Skill | Type | Scope |
|-------|------|-------|
| `python-code-style` | bundled skill (Python only) | Review **all Python source code** in `src/` (and any other source dirs) for style, linting, formatting, naming, docstring, and type annotation issues. **Follow `~/.agents/rules/python-code-style-rules.md`** for the exact uv/Docker workflow, ruff format/ty check order, and the explanation of the `mypy` ignore_missing_imports scope. |
| `python-testing-patterns` | bundled skill (Python only) | Review **all test code** in `tests/` for testing best practices: test isolation, naming, mocking patterns, fixture design, AAA structure. **Coverage gap analysis**: run `pytest --cov` (mandatory) and flag only modules with coverage below 50% AND no direct test references AND all callers mocked. Do NOT duplicate the structural "missing test file" check from `scan_tests.py` — that is owned by `/zolletta patterns`. If `scan_tests.py` already flagged a file as structurally missing a test, reference that finding but focus on whether the code is actually covered via `pytest --cov`. |
| `/zolletta patterns` | zolletta subcommand (always) | Review **all source code** in `src/` for design pattern issues: KISS violations, SRP violations, tight coupling, composition vs inheritance, God classes, premature abstraction, SOLID principle violations (OCP, LSP, ISP, DIP). Also check structural conventions: one class per file, and test directory structure mirroring source structure. **For Python projects**: run all eight scanning scripts (`scan_class_metrics.py`, `scan_test_god_classes.py`, `scan_one_class_per_file.py`, `scan_tests.py`, `scan_dependency_inversion.py`, `scan_interface_segregation.py`, `scan_open_closed.py`, and `scan_liskov_substitution.py` from the skill's `scripts/python/` directory) for automated triage, then apply the "reason to change" test to the top candidates. **Use the `scan_tests.py` markdown output directly in the report**: its five tables (misnamed tests, misplaced tests, orphaned tests, multi-class tests, missing tests) are **structural** findings — they check file naming and directory mirroring, not actual code coverage. Copy them into the report's findings section. **Do not flag coverage gaps** — that is owned by `python-testing-patterns` which runs `pytest --cov`. Use `test_splitter.py` if the human decides to split a test God class. **For other languages**: apply the same principles manually (no AST scripts available yet). **If `.tokensave/` exists, use the code graph tools** (tokensave_context/callees/callers or tokensave_impact) to understand class responsibilities and assess blast radius before proposing splits — see the skill's "Code Graph Tools" section for the decision tree. |
| `/zolletta documentor` | zolletta subcommand (always) | Review **documentation in `.backstage/` only**: Diátaxis compliance (document type correctness, audience clarity, structure, accuracy, consistency) **and** drift detection (staleness, broken links, API doc validation, structural gaps) in a single pass. **Follow `documentor/references/operational-rules.md`** for false positive patterns, correct tool invocation (project root as repo path for staleness scorer), and the recommended workflow order. |

**Subagent task template** (adapt for each):

```
You are performing a code review on a <language> project.

First, invoke the skill "<skill-name>" using the skill tool to load its guidelines.
Then apply those guidelines to review the following scope:

<scope description>

Project root: <current working directory>
AGENTS.md: Read the project's AGENTS.md (and ~/.agents/AGENTS.md) for project-specific and global rules.
For `python-code-style` reviews: also read `~/.agents/rules/python-code-style-rules.md` and apply the uv/Docker workflow, ruff format, ruff check --fix, ty check --fix, and mypy verification order described there.

Produce a structured markdown report with:
- A summary section
- A **grade** section at the top with a numeric score from 0 to 100 for the project's
  performance in the scope you reviewed. Justify the score with a brief breakdown of
  what earned points and what lost points.
- Each issue as a section with: file path, line number(s), severity (critical/high/medium/low),
  problem description, impact, and suggested fix
- If no issues are found, state that explicitly with a brief explanation of what was checked

**Grading scale** (0-100):
- 90-100: Excellent — minimal or no issues, follows best practices consistently
- 75-89: Good — a few issues, overall solid quality
- 60-74: Fair — several issues that should be addressed, quality is acceptable but needs work
- 40-59: Poor — many issues, significant quality gaps
- 0-39: Failing — critical issues throughout, major rework needed

Return ONLY the markdown report as your final output.
```

### Step 5 — Collect and save each report

After launching a batch, collect each subagent's output with `read_subagent` (`block: true`, then `block: false` for incremental reads if needed). Save each report to a markdown file in the review folder as soon as it is collected:

| Subagent | Output file |
|----------|------------|
| python-code-style | `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/python-code-style.md` |
| python-testing-patterns | `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/python-testing-patterns.md` |
| patterns | `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/patterns.md` |
| documentor | `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/documentor.md` |

Only the files for skills that were actually launched will be created. Use the `write` tool to save each report. If a subagent returns an error or empty output, still create the file with a note explaining what happened. Do not start the next batch until all reports from the current batch are saved.

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

Read all report files that were produced and extract the grade from each. Create `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/SUMMARY.md` following the [summary template](assets/summary_template.md).

**Overall grade calculation**: use a weighted average of the sub-grades. Only include areas that were actually run. Suggested weights for a Python project (4 skills):

| Area | Weight |
|------|--------|
| Code style | 30% |
| Testing | 30% |
| Design patterns | 25% |
| Documentation | 15% |

For non-Python projects (2 skills — patterns + documentor only):

| Area | Weight |
|------|--------|
| Design patterns | 60% |
| Documentation | 40% |

If the project has no `.backstage/` directory, redistribute the documentation weight equally across the other areas.

If a previous review exists, include a "Trend vs previous review" subsection noting whether the overall grade improved, worsened, or stayed the same, and by how many points.

### Step 8 — Create the aggregated TODO.md

Read all report files you just saved. Create `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/TODO.md` following the [TODO template](assets/todo_template.md).

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
