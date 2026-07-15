---
name: zolletta-review
version: 1.0.0
license: MIT + Commons Clause
description: >
  Full project review orchestrator. Detects the project language, then runs the appropriate specialist skills as subagents in parallel batches — general skills (patterns, documentor) always, plus language-specific skills when applicable (e.g. python-code-style and python-testing-patterns for Python). Saves each report to .scratches/reviews/AAMMDDHHMM/, produces an aggregated TODO.md organized by functional priority (dependency changes first, then by severity), and compares with the previous review's TODO to verify completion. Respond in the user's language.
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

- `../reference/code-exploration.md` — code graph tools (tokensave, GitNexus, graphify) decision tree
- `../reference/general-principles.md` — SOLID, KISS, composition over inheritance (language-agnostic)
- `../reference/documentation_standards.md` — generic doc writing standards (README, API docs, changelogs, ADRs)
- `../scripts/` — shared scanning scripts (organised by language subdirectory)

**Respond in the same language the user used to invoke you.** If the user wrote in Italian,
respond in Italian. If in English, respond in English. And so on for any other language.

## Procedure

### Step 1 — Determine the project language

Before launching any subagent, determine the project's primary language:

1. Check for language markers in the project root:
   - `pyproject.toml`, `setup.py`, `setup.cfg`, `requirements*.txt`, `Pipfile`, `uv.lock` → **Python**
   - `package.json`, `tsconfig.json`, `deno.json` → **TypeScript/JavaScript**
   - `composer.json` → **PHP**
   - `go.mod` → **Go**
   - `Cargo.toml` → **Rust**
   - `pom.xml`, `build.gradle` → **Java/Kotlin**
   - `Gemfile`, `*.gemspec` → **Ruby**
   - `CMakeLists.txt`, `Makefile` with `.c`/`.cpp` sources → **C/C++**
2. If no marker is found, inspect the source directory for the most common file extension.
3. If the language cannot be determined, ask the user with `ask_user_question`.
4. Store the detected language for use in subsequent steps.

### Step 2 — Set up the scratches directory

1. Check if `.scratches/` exists in the current project root (the working directory).
   If it does not exist, create it with `mkdir -p .scratches`.
2. Check if `.gitignore` exists in the project root. If it does not, create it.
3. Read `.gitignore` and check if `.scratches/` is already listed. If not, append it
   (with a leading comment like `# AI review scratches` on its own line, then `.scratches/`). Do not duplicate the entry if it's already there.

### Step 3 — Create the review folder

1. Generate a timestamp in `AAMMDDHHMM` format (2-digit year, month, day, hour, minute —
   all in the user's local timezone). Use `date +%y%m%d%H%M` to get this.
2. Create the directory `.scratches/reviews/<AAMMDDHHMM>/`.

### Step 4 — Check for previous reviews

1. List all subdirectories under `.scratches/reviews/` (if any exist).
2. If there are previous review folders, identify the **newest** one (excluding the one
   you just created). Read its `TODO.md` if it exists.
3. Keep this previous TODO for the comparison in Step 7.

### Step 5 — Launch the review subagents in parallel batches

Launch subagents in **batches** using `run_subagent` with `is_background: true`. Within each batch, launch all subagents in a single tool-call block so they run concurrently. After launching a batch, wait for all its subagents to finish (using `read_subagent` with `block: true`) and save their reports before starting the next batch.

**General skills** (always run, regardless of language):

- `/zolletta patterns` — design pattern analysis (language-agnostic principles + language-specific scripts when available)
- `/zolletta documentor` — documentation review (Diátaxis compliance + drift detection)

**Language-specific skills** (run only when the project uses the matching language):

| Language | Skill | Scope |
|----------|-------|-------|
| Python | `python-code-style` | Style, linting, formatting, naming, docstrings, type annotations |
| Python | `python-testing-patterns` | Test isolation, naming, coverage gaps, mocking, fixture design, AAA structure |

> When support for other languages is added, extend this table with the corresponding skills.

**Batching strategy**: group skills into batches of up to 3 parallel background subagents. Place general skills and language-specific skills across batches to maximise parallelism. For Python projects (4 skills total), use two batches:

**Batch 1** (2 parallel background subagents — external skills, Python only):

1. `python-code-style`
2. `python-testing-patterns`

**Batch 2** (2 parallel background subagents — zolletta subcommands, always):

3. `/zolletta patterns`
4. `/zolletta documentor`

For non-Python projects, all skills are general — run them in a single batch of 2.

**Why batching**: at most one foreground subagent can run at a time, so all subagents
in a batch MUST be launched as background (`is_background: true`). Issue all `run_subagent` calls for a batch in a single response (parallel tool calls), then collect each result with `read_subagent` (block: true) in the next turn. Save each report immediately after collecting it.

**Important**: Each subagent must be given the full context of what to review and
must invoke the relevant skill via the `skill` tool. The subagent should:

1. Invoke the skill with `skill invoke <skill-name>`
2. Apply the skill's guidelines to review the specified scope
3. Return a structured markdown report with findings (issues, file paths, line numbers,
   severity, suggested fixes)

**Skill scopes:**

| Skill | Type | Scope |
|-------|------|-------|
| `python-code-style` | external skill (Python only) | Review **all Python source code** in `src/` (and any other source dirs) for style, linting, formatting, naming, docstring, and type annotation issues. **Follow `~/.agents/rules/python-code-style-rules.md`** for the exact uv/Docker workflow, ruff format/ty check order, and the explanation of the `mypy` ignore_missing_imports scope. |
| `python-testing-patterns` | external skill (Python only) | Review **all test code** in `tests/` for testing best practices: test isolation, naming, coverage gaps, mocking patterns, fixture design, AAA structure |
| `/zolletta patterns` | zolletta subcommand (always) | Review **all source code** in `src/` for design pattern issues: KISS violations, SRP violations, tight coupling, composition vs inheritance, God classes, premature abstraction, SOLID principle violations (OCP, LSP, ISP, DIP). Also check structural conventions: one class per file, and test directory structure mirroring source structure. **For Python projects**: run all eight scanning scripts (`scan_class_metrics.py`, `scan_test_classes.py`, `scan_one_class_per_file.py`, `scan_test_structure_mirror.py`, `scan_dependency_inversion.py`, `scan_interface_segregation.py`, `scan_open_closed.py`, and `scan_liskov_substitution.py` from the skill's `scripts/python/` directory) for automated triage, then apply the "reason to change" test to the top candidates. Use `test_splitter.py` if the human decides to split a test God class. **For other languages**: apply the same principles manually (no AST scripts available yet). **If `.tokensave/` or `.gitnexus/` exists, use the code graph tools** (tokensave_context/callees/callers or gitnexus context/impact) to understand class responsibilities and assess blast radius before proposing splits — see the skill's "Code Graph Tools" section for the decision tree. |
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

### Step 6 — Collect and save each report

After launching a batch, collect each subagent's output with `read_subagent` (`block: true`, then `block: false` for incremental reads if needed). Save each report to a markdown file in the review folder as soon as it is collected:

| Subagent | Output file |
|----------|------------|
| python-code-style | `.scratches/reviews/<AAMMDDHHMM>/python-code-style.md` |
| python-testing-patterns | `.scratches/reviews/<AAMMDDHHMM>/python-testing-patterns.md` |
| patterns | `.scratches/reviews/<AAMMDDHHMM>/patterns.md` |
| documentor | `.scratches/reviews/<AAMMDDHHMM>/documentor.md` |

Only the files for skills that were actually launched will be created. Use the `write` tool to save each report. If a subagent returns an error or empty output, still create the file with a note explaining what happened. Do not start the next batch until all reports from the current batch are saved.

### Step 7 — Compare with previous review (if exists)

If a previous review folder was found in Step 4:

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

### Step 8 — Create the executive summary (SUMMARY.md)

Read all report files that were produced and extract the grade from each. Create `.scratches/reviews/<AAMMDDHHMM>/SUMMARY.md` following the [summary template](assets/summary_template.md).

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

### Step 9 — Create the aggregated TODO.md

Read all report files you just saved. Create `.scratches/reviews/<AAMMDDHHMM>/TODO.md` following the [TODO template](assets/todo_template.md).

**Organization rules** (in this exact order):

1. **Dependency changes (under my control)** — any findings that require changes to
   internal/shared packages or other dependencies I own. These go first because everything else may depend on them being released. Mark each with a note: "⚠️ Requires dependency release — do these first, then wait for the release before proceeding."

2. **Critical / blocking issues** — anything that breaks functionality, causes data loss,
   security issues, or prevents the project from working.

3. **High priority** — significant code quality, design, or testing issues that should be
   addressed soon but don't block work.

4. **Medium priority** — style, documentation, and minor design improvements.

5. **Low priority** — nice-to-haves, cosmetic changes, future improvements.

6. **Previous review status** — the carry-forward section from Step 7 (if applicable).

**Numbering**: Assign each issue a unique sequential number starting from 1,
counting continuously across all sections (Critical → High → Medium → Low). Do NOT restart numbering per section. The number goes before the priority tag.

### Step 10 — Summary response

After all files are saved and the SUMMARY.md and TODO.md are created, respond to the user with:

1. The detected project language
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
