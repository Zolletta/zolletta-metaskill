---
name: zolletta-review
description: >
  Full Python project review orchestrator. Runs python-code-style, zolletta-design-patterns, python-testing-patterns, documentation-writer, and zolletta-doc-drift-detector as subagents in parallel batches of up to 3, saves each report to .scratches/reviews/AAMMDDHHMM/, produces an aggregated TODO.md organized by functional priority (dependency changes first, then by severity), and compares with the previous review's TODO to verify completion. Respond in the user's language.
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

# Zolletta Python Review — Orchestrator

You are an orchestrator that runs a full Python project review by invoking five specialist skills in parallel batches, collecting each output, and producing an aggregated, prioritized TODO.

## Shared resources

Read shared guidelines from the meta-skill (parent directory):

- `../reference/code-exploration.md` — code graph tools (tokensave, GitNexus, graphify) decision tree
- `../reference/general-principles.md` — SOLID, KISS, composition over inheritance (language-agnostic)
- `../reference/documentation_standards.md` — generic doc writing standards (README, API docs, changelogs, ADRs)
- `../scripts/python/` — shared scanning scripts

**Respond in the same language the user used to invoke you.** If the user wrote in Italian,
respond in Italian. If in English, respond in English. And so on for any other language.

## Procedure

### Step 1 — Set up the scratches directory

1. Check if `.scratches/` exists in the current project root (the working directory).
   If it does not exist, create it with `mkdir -p .scratches`.
2. Check if `.gitignore` exists in the project root. If it does not, create it.
3. Read `.gitignore` and check if `.scratches/` is already listed. If not, append it
   (with a leading comment like `# AI review scratches` on its own line, then `.scratches/`). Do not duplicate the entry if it's already there.

### Step 2 — Create the review folder

1. Generate a timestamp in `AAMMDDHHMM` format (2-digit year, month, day, hour, minute —
   all in the user's local timezone). Use `date +%y%m%d%H%M` to get this.
2. Create the directory `.scratches/reviews/<AAMMDDHHMM>/`.

### Step 3 — Check for previous reviews

1. List all subdirectories under `.scratches/reviews/` (if any exist).
2. If there are previous review folders, identify the **newest** one (excluding the one
   you just created). Read its `TODO.md` if it exists.
3. Keep this previous TODO for the comparison in Step 6.

### Step 4 — Launch the five review subagents in parallel batches

Launch subagents in **two batches** using `run_subagent` with `is_background: true`. Within each batch, launch all subagents in a single tool-call block so they run concurrently. After launching a batch, wait for all its subagents to finish (using `read_subagent` with `block: true`) and save their reports before starting the next batch.

**Batch 1** (3 parallel background subagents):

1. `python-code-style`
2. `zolletta-design-patterns`
3. `python-testing-patterns`

**Batch 2** (2 parallel background subagents):

4. `documentation-writer`
5. `zolletta-doc-drift-detector`

**Why batching**: at most one foreground subagent can run at a time, so all subagents
in a batch MUST be launched as background (`is_background: true`). Issue all `run_subagent` calls for a batch in a single response (parallel tool calls), then collect each result with `read_subagent` (block: true) in the next turn. Save each report immediately after collecting it.

**Important**: Each subagent must be given the full context of what to review and
must invoke the relevant skill via the `skill` tool. The subagent should:

1. Invoke the skill with `skill invoke <skill-name>`
2. Apply the skill's guidelines to review the specified scope
3. Return a structured markdown report with findings (issues, file paths, line numbers,
   severity, suggested fixes)

The five subagents and their scopes:

| Order | Skill to invoke | Scope |
|-------|----------------|-------|
| 1  | `python-code-style` | Review **all Python source code** in `src/` (and any other source dirs) for style, linting, formatting, naming, docstring, and type annotation issues. **Follow `~/.agents/rules/python-code-style-rules.md`** for the exact uv/Docker workflow, ruff format/ty check order, and the explanation of the `mypy` ignore_missing_imports scope. |
| 2 | `zolletta-design-patterns` | Review **all Python source code** in `src/` for design pattern issues: KISS violations, SRP violations, tight coupling, composition vs inheritance, God classes, premature abstraction, SOLID principle violations (OCP, LSP, ISP, DIP). Also check structural conventions: one class per file, and test directory structure mirroring source structure. **Run all eight scanning scripts** (`scan_class_metrics.py`, `scan_test_classes.py`, `scan_one_class_per_file.py`, `scan_test_structure_mirror.py`, `scan_dependency_inversion.py`, `scan_interface_segregation.py`, `scan_open_closed.py`, and `scan_liskov_substitution.py` from the skill's `scripts/python/` directory) for automated triage, then apply the "reason to change" test to the top candidates. Use `test_splitter.py` if the human decides to split a test God class. **If `.tokensave/` or `.gitnexus/` exists, use the code graph tools** (tokensave_context/callees/callers or gitnexus context/impact) to understand class responsibilities and assess blast radius before proposing splits — see the skill's "Code Graph Tools" section for the decision tree. |
| 3 | `python-testing-patterns` | Review **all test code** in `tests/` for testing best practices: test isolation, naming, coverage gaps, mocking patterns, fixture design, AAA structure |
| 4 | `documentation-writer` | Review **documentation in `.backstage/` only** for Diátaxis compliance: document type correctness, audience clarity, structure, accuracy, consistency |
| 5 | `zolletta-doc-drift-detector` | Run drift detection on **`.backstage/` documentation only** against the codebase: staleness, broken links, API doc validation, structural gaps. **Follow `documentor/references/operational-rules.md`** for false positive patterns, correct tool invocation (project root as repo path for staleness scorer), and the recommended workflow order. |

**Subagent task template** (adapt for each):

```
You are performing a code review on a Python project.

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
| python-code-style | `.scratches/reviews/<AAMMDDHHMM>/python-code-style.md` |
| zolletta-design-patterns | `.scratches/reviews/<AAMMDDHHMM>/zolletta-design-patterns.md` |
| python-testing-patterns | `.scratches/reviews/<AAMMDDHHMM>/python-testing-patterns.md` |
| documentation-writer | `.scratches/reviews/<AAMMDDHHMM>/documentation-writer.md` |
| zolletta-doc-drift-detector | `.scratches/reviews/<AAMMDDHHMM>/doc-drift-detector.md` |

Use the `write` tool to save each report. If a subagent returns an error or empty output, still create the file with a note explaining what happened. Do not start Batch 2 until all Batch 1 reports are saved.

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

Read all five report files and extract the grade from each. Create `.scratches/reviews/<AAMMDDHHMM>/SUMMARY.md` with an executive summary of the project's strengths and weaknesses.

**SUMMARY.md structure:**

```markdown
# Executive Summary — Review <AAMMDDHHMM>

**Overall grade: <XX>/100** (weighted average of the five sub-grades below)

## Grades by area

| Area | Skill | Grade | Trend |
|------|-------|-------|-------|
| Code style | python-code-style | XX/100 | ↑/↓/→ vs previous |
| Design patterns | zolletta-design-patterns | XX/100 | ↑/↓/→ vs previous |
| Testing | python-testing-patterns | XX/100 | ↑/↓/→ vs previous |
| Documentation | documentation-writer | XX/100 | ↑/↓/→ vs previous |
| Doc drift | zolletta-doc-drift-detector | XX/100 | ↑/↓/→ vs previous |

> Trend compares each grade with the previous review's grade for the same area
> (↑ improved, ↓ worsened, → unchanged, — no previous review).

## Strengths

- <strength 1 — what the project does well>
- <strength 2>
- ...

## Weaknesses

- <weakness 1 — what needs improvement>
- <weakness 2>
- ...

## Grade rationale

<1-3 paragraphs explaining how the overall grade was derived: which areas pulled it up,
which pulled it down, and what would have the biggest impact on improving the score.>
```

**Overall grade calculation**: use a weighted average of the five sub-grades. Suggested
weights (adjust if the project has no documentation, in which case doc grades are excluded):

| Area | Weight |
|------|--------|
| Code style | 25% |
| Design patterns | 25% |
| Testing | 25% |
| Documentation | 12.5% |
| Doc drift | 12.5% |

If the project has no `.backstage/` directory, redistribute the documentation weights equally across the other three areas (33% each).

If a previous review exists, include a "Trend vs previous review" subsection noting whether the overall grade improved, worsened, or stayed the same, and by how many points.

### Step 8 — Create the aggregated TODO.md

Read all five report files you just saved. Create `.scratches/reviews/<AAMMDDHHMM>/TODO.md` that aggregates all findings into a single, functionally organized todo list.

**Organization rules** (in this exact order):

1. **Dependency changes (under my control)** — any findings that require changes to
   `pepita-ci-packages` (ci-repositories, utils, metrics) or other dependencies I own. These go first because everything else may depend on them being released. Mark each with a note: "⚠️ Requires dependency release — do these first, then wait for the release before proceeding."

2. **Critical / blocking issues** — anything that breaks functionality, causes data loss,
   security issues, or prevents the project from working.

3. **High priority** — significant code quality, design, or testing issues that should be
   addressed soon but don't block work.

4. **Medium priority** — style, documentation, and minor design improvements.

5. **Low priority** — nice-to-haves, cosmetic changes, future improvements.

6. **Previous review status** — the carry-forward section from Step 6 (if applicable).

**Numbering**: Assign each issue a unique sequential number starting from 1,
counting continuously across all sections (Critical → High → Medium → Low). Do NOT restart numbering per section. The number goes before the priority tag.

**TODO format** for each item:

```markdown
- [ ] **<N>. [P0/P1/P2/P3]** <short title>
  - **Source**: <which skill report found this>
  - **Files**: <file paths and line numbers>
  - **Problem**: <brief description>
  - **Fix**: <suggested approach>
  - **Blocked by**: <if depends on a dependency release or another item>
```

Where `<N>` is the sequential issue number (1, 2, 3, …).

### Step 9 — Summary response

After all files are saved and the SUMMARY.md and TODO.md are created, respond to the user with:

1. A brief summary of what was reviewed and where the reports are saved
2. **The overall grade** (from SUMMARY.md) with a one-line interpretation
3. The grades by area (from the SUMMARY.md table)
4. The total number of findings by severity
5. The number of items carried forward from the previous review (if any) and their status
6. The top 3 strengths and top 3 weaknesses (from SUMMARY.md)
7. The top 3 priority items from the TODO
8. The paths to the SUMMARY.md and TODO.md files

Keep the summary concise. The full details are in the report files.

## Error handling

- If a subagent fails or times out, note it in the corresponding report file and continue
  with the next subagent in the sequence. Do not abort the entire review.
- If the `.backstage/` directory does not exist, the documentation subagents should report
  that there is nothing to review (not an error).
- If `src/` or `tests/` directories don't exist, adapt the scope to whatever Python
  directories are present in the project.
