---
name: zolletta-metaskill-review
license: MIT + Commons Clause
description: >
  Runs full project reviews: dispatches specialist skills as parallel subagents, writes dated reports, and builds a prioritized TODO.md. Use for whole-project reviews. Do not use for single-aspect checks — invoke the specialist directly.
allowed-tools: read grep glob exec edit write skill run_subagent read_subagent todo_write ask_user_question mcp_call_tool mcp_list_tools
metadata:
  subagent: true
  permissions:
    allow:
      - Bash(tokensave *)
      - mcp__tokensave__tokensave_status
      - mcp__tokensave__tokensave_files
---

# Zolletta-metaskill Review — Orchestrator

You are an orchestrator that runs a full project review by invoking specialist skills in parallel batches, collecting each output, and producing an aggregated, prioritized TODO.

The set of skills depends on the project's primary language: **general skills** (design patterns, documentation) always run, while **language-specific skills** run only when the project uses the matching language.

## Shared resources

Read shared guidelines from the meta-skill (parent directory):

- `../../docs/reference/code/code-exploration.md` — code graph tools (tokensave) decision tree
- `../../docs/reference/code/scripts-first-protocol.md` — batch-run scripts, cache output, judgment only on deferred items
- `../../docs/explanation/code/general-principles.md` — SOLID, KISS, composition over inheritance (language-agnostic)
- `../../docs/explanation/documentation/standards.md` — generic doc writing standards (README, API docs, changelogs, ADRs)
- `../../docs/reference/tool-messages.md` — "not installed" messages for the tool-failure handler
- `../../src/zolletta_metaskill/shared/` — shared scanning scripts
- `../../src/zolletta_metaskill/patterns/` — pattern-specific scanning scripts

**Tool-failure handler**: if a tokensave query fails on every available transport — `tokensave tool <name>` and, where the harness exposes them, the `tokensave_*` MCP tools (the fallback for binaries older than 7.14) — follow the tool-failure handler (`../../SKILL.md#tool-failure-handler`) in the meta-skill — update `settings.json`, print the "not installed" message, and continue with grep/read fallback.

**Respond in the same language the user used to invoke you.** If the user wrote in Italian, respond in Italian. If in English, respond in English. And so on for any other language.

## Model selection

When spawning a subagent, look up `subcommands.<subcommand-name>.model` in `.zolletta-metaskill/settings.json` to find the model to use:

- If the value is **non-null**, pass it as the `profile` argument to `run_subagent`.
- If the value is **null** (the default), omit `profile` and let the harness pick its default.

The orchestrator itself always runs on the model it was invoked with — only the subagents inherit the configured model. Model/profile ids are harness-specific; the skill never hardcodes one. See `../../docs/explanation/patterns.md` → "Smart Plan, Cheap Execution" for the rationale.

## Procedure

### Step 1 — Read the project language from settings.json

The setup guard (see the meta-skill's setup guard, `../../SKILL.md#setup-guard`) guarantees that `.zolletta-metaskill/settings.json` exists before this subcommand runs.

1. Read `.zolletta-metaskill/settings.json` and extract the `language` field.
2. If `settings.json` is missing or `language` is empty, fall back to detecting the language using the marker list in `skills/zolletta-metaskill-setup/SUBCOMMAND.md` Step 3.
3. If the language cannot be determined, ask the user with `ask_user_question`.
4. Store the detected language for use in subsequent steps.

### Step 1.5 — Tokensave pre-flight check (before launching subagents)

This step ensures the tokensave index is fresh before any subagent uses it. Stale indices cause subagents to silently fall back to direct file reads, degrading review quality without warning. This check runs **in the orchestrator**, not in each subagent, to avoid redundant checks and race conditions on `tokensave sync`.

> **Parallelization**: issue the `tokensave tool status` exec from this step and the `adr_orchestrator.py` exec from Step 3.5 in the **same tool-call block** so they run concurrently. Only the tokensave re-sync (if needed) blocks subsequent steps; ADR distillation is independent.

**Only run this step if `tokensave_available` is `true` in `settings.json`.** If `tokensave_available` is `false`, skip this step — subagents will use the grep/read fallback as usual.

1. **Verify tokensave is runnable**: run `tokensave doctor`, which checks that the binary is on `PATH` and the installation is healthy. A static `tokensave_available: true` written by setup is not evidence — it is only a claim. If `tokensave doctor` fails, set `tokensave_available` to `false` in `settings.json` and continue to Step 2; subagents will use the grep/read fallback per the tool-failure handler. If the doctor output names a newer version than the one installed, note it in the SUMMARY.md warning but do not treat it as a failure.
2. **Read the freshness signals**: run `tokensave tool status` and `tokensave branch list` — on binaries older than 7.14 (`tool` subcommand unsupported), call `tokensave_status` via the MCP server instead. The two responses carry every signal this step needs.
3. **Check index freshness** using those responses:
   - **`files_by_language.<lang>` vs a like-for-like count**: count the primary-language files under the configured source roots (`python.paths.source` / `php.autoload.psr-4`) and compare that against the matching entry of `files_by_language`, never against the whole-repo `file_count`, which also counts documents, config and vendored files. A ratio below 0.8 means the index is stale.
   - **Branch tracked**: `tokensave branch list` returns the tracked branches, and an empty list means multi-branch tracking is off. If the list does not contain the current branch (`git branch --show-current`), the branch is untracked and the index is stale.
   - **`stale_commits`**: commits since the last sync — any value above zero means the index is stale (the `stale_warning` field spells it out).
   - **`last_full_sync_at` vs `last_sync_at`**: an incremental `tokensave sync` refreshes `last_sync_at` without re-reading files git considers unchanged, so a recent `last_sync_at` alone proves nothing about a weeks-old index. Treat the index as stale when `last_sync_at` is more than 1 hour old **or** `last_full_sync_at` is more than 24 hours old.
4. **Name the outcome and act on it**:
   - **PASS** — `tokensave doctor` succeeded, the branch is tracked, `stale_commits` is 0, and both timestamps are fresh. Proceed to Step 2 with no warning.
   - **DEGRADED** — at least one signal is off but a sync is possible. Run `tokensave branch add <current_branch>` when the branch is untracked, then run `tokensave sync` and wait for it to complete, then re-check with `tokensave tool status` (or `tokensave_status` via MCP on pre-7.14 binaries) and `tokensave branch list`. If the re-check clears every signal, proceed as PASS.
   - **UNRECOVERABLE** — `tokensave doctor` failed, or `tokensave sync` failed, or the index is still stale after a sync. Print a warning at the top of SUMMARY.md ("⚠️ tokensave index is stale — review quality may be degraded for code exploration tasks") and continue. Do not abort the review. Each subagent will use the grep/read fallback per the tool-failure handler.

> **Why this runs in the orchestrator**: running `tokensave sync` inside a subagent would risk concurrent syncs if multiple subagents detect staleness simultaneously. The orchestrator syncs once, before any subagent launches, so all subagents see a consistent fresh index.

### Step 2 — Create the run directory

1. Read `runs_dir` from `settings.json` (default `.zolletta-metaskill`).
2. Generate a timestamp in `YYYY-MM-DD-HH-MM` format. Use `date +%Y-%m-%d-%H-%M` to get this.
3. Create the run directory structure:
   - `<runs_dir>/<YYYY-MM-DD-HH-MM>/reports/` — for LLM judgment (subcommand reports, SUMMARY.md)
   - `<runs_dir>/<YYYY-MM-DD-HH-MM>/cache/` — for deterministic artifacts (script outputs + shared context)

### Step 3 — Check for previous reviews

1. List all timestamp subdirectories directly under `<runs_dir>/` (i.e. `<runs_dir>/*/`, excluding `settings.json` and other non-directory files).
2. If there are previous run directories, identify the **newest** one (excluding the one you just created). Read its `reports/TODO.md` if it exists.
3. Keep this previous TODO for the comparison in Step 6.

### Step 3.5 — Refresh ADR directives

1. Read `documentation.adrs` and `documentation.dir` from `settings.json`.
2. If `documentation.adrs` is `null`, skip this step — no ADRs in the project.
3. Run the `adr-distiller` subcommand:

```text
   /zolletta-metaskill adr-distiller
   ```

   Read `skills/zolletta-metaskill-adr-distiller/SUBCOMMAND.md` and execute its procedure. The distiller uses the `adrs` field to locate ADRs, compares mtimes against the cache, and refreshes `adr-distilled.md`. On first run (no cache), it creates the file and cache from scratch.
4. Parse the JSON report. If `has_adrs` is false, skip ADR directives for this review.
5. For each ADR in `stale` and `new`: read the source ADR file, refine the mechanically-extracted directive in `adr-distilled.md` into a concise one-liner. Preserve category headings if present.
6. The refreshed `adr-distilled.md` is now ready for subagents to read.

> ADR distillation inspired by [Architectural Governance at AI Speed](https://www.infoq.com/articles/architectural-governance-ai-speed/) (InfoQ, 2026).

### Step 3.6 — Write shared context + run shared scripts to cache/

This step deduplicates work that every subagent would otherwise repeat: reading settings.json, ADR directives, mandatory reference docs, and running shared scanners. The orchestrator does it once and writes the results to `cache/`.

1. **Write `cache/_context.md`** containing:
   - **Settings extract**: relevant `settings.json` fields — `language`, `container_name`, `tokensave_available`, `python.tools.*` (availability + config), `python.code_style` / `python.testing` toggles, `acronyms`, `documentation.*`. Copied once so 4 subagents don't each open `settings.json`. When tokensave is available, also note which transport Step 1.5 verified — `tokensave tool <name>` (CLI) or the `tokensave_*` MCP tools (pre-7.14 binaries) — so subagents use the working transport directly.
   - **ADR directives**: the full content of `adr-distilled.md` (if ADRs exist from Step 3.5). Inlined so subagents don't each open the file.
   - **Judgment-rules digest**: a verbatim extract (not paraphrase) of the criteria lists from:
     - `../../docs/explanation/code/general-principles.md` — God class detection procedure + "What is NOT a God class" criteria
     - `../../docs/explanation/code/structural-conventions.md` — one-class-per-file + test mirroring rules
     - `../../docs/reference/code/review-mode.md` — two-bucket classification (auto-fixable vs findings)
     - `../../docs/explanation/code/balanced-coupling.md` — balance rule + strength/distance/volatility summaries
     Keep this to ~30 lines — only the criteria, not the full prose. Subagents that need more context can drill down to the full docs.

2. **Run shared scripts once** and persist to `cache/` (these are used by multiple subagents):
   - `one_class_per_file_scanner.py` → `cache/one_class_per_file.txt` (used by `patterns` and `python-code-style`)
   - `test_structure_scanner.py` → `cache/test_structure.md` (used by `patterns`)

   Run both in a single tool-call block of parallel `exec` calls. Subagents read from `cache/` instead of re-running them.

3. The `cache/` directory is now ready for subagents. Each subagent will:
   - Read `cache/_context.md` for shared context (settings, ADR directives, judgment rules)
   - Read shared scanner outputs from `cache/` (already populated)
   - Run its own subcommand-specific scripts (Phase A per the scripts-first protocol) and write them to `cache/`
   - Assemble its report from cache (Phase B) and apply judgment (Phase C)

### Step 4 — Launch the review subagents in parallel

> One subagent per command follows the **Focused Agent** pattern, avoiding the **Distracted Agent** anti-pattern. See `../../docs/reference/augmented-coding-patterns.md` for distilled definitions.

Launch **one subagent per command**, all in parallel as background subagents (`is_background: true`). Issue all `run_subagent` calls in a single tool-call block so they run concurrently. Each subagent writes its own report file directly to the review directory — the orchestrator does not collect and save reports on their behalf. Apply the [Model selection](#model-selection) rules above for each `run_subagent` call.

**General skills** (always run, regardless of language):

- `/zolletta-metaskill patterns` — design pattern analysis (language-agnostic principles + language-specific scripts when available)
- `/zolletta-metaskill documentor` — documentation review (Diátaxis compliance + drift detection)
- `/zolletta-metaskill grice` — Grice maxims scoring (corpus-relative indices + link/heading defects), **only when `documentation.check_grice` is `true`** in `settings.json`. When the toggle is off, do not skip the subagent silently: write `reports/grice.md` containing `SKIPPED (check_grice disabled in settings.json)` and no grade, so the summary records that the area was not reviewed rather than that it passed.

**Language-specific skills** (run only when the project uses the matching language):

| Language | Skill                  | Scope                                                                         |
|----------|------------------------|-------------------------------------------------------------------------------|
| Python   | `python-code-style`    | Style, linting, formatting, naming, docstrings, type annotations              |
| Python   | `python-testing-style` | Test isolation, naming, coverage gaps, mocking, fixture design, AAA structure |
| PHP      | `php-code-style`       | PSR-12, naming, one class per file, PHPDoc, type declarations                 |
| PHP      | `php-testing-style`    | PHPUnit naming, mirroring, coverage gaps, mocking, data providers             |

> When support for other languages is added, extend this table with the corresponding skills.

**Checking skill availability**: the Python review skills (`python-code-style`, `python-testing-style`) and the PHP review skills (`php-code-style`, `php-testing-style`) are bundled inside this meta-skill, so they are always available — no `*_available` flags are read from `settings.json`. Dispatch to them when `language` is `python` or `php` respectively; skip them otherwise. The SUMMARY.md and TODO.md should note any area that was not reviewed (non-Python/PHP project). No "Skill not found" handling is needed.

**Skill scopes:**

| Skill                            | Type                                                                 | Scope                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
|----------------------------------|----------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `python-code-style`              | bundled skill (Python only)                                          | Review **all Python source code** in `src/` (and any other source dirs) for style, linting, formatting, naming, docstring, and type annotation issues. Run in **review mode (read-only)** per [`../../docs/reference/code/review-mode.md`](../../docs/reference/code/review-mode.md): use `ruff check` (no `--fix`), `ruff format --check`, `ty check` (no `--fix`), and `mypy` as-is. Auto-fixable issues are informational only — do not count them toward the grade. Read rule toggles from `python.code_style` in `settings.json` and effective tool config from the `python.tools.*` fields.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `python-testing-style`           | bundled skill (Python only)                                          | Review **all test code** in `tests/` for testing best practices: test isolation, naming, mocking patterns, fixture design, AAA structure. **Coverage gap analysis**: run `pytest --cov` (mandatory) and flag only modules with coverage below 50% AND no direct test references AND all callers mocked. Do NOT duplicate the structural "missing test file" check from `test_structure_scanner.py` — that is owned by `/zolletta-metaskill patterns`.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| `/zolletta-metaskill patterns`   | zolletta-metaskill subcommand (always)                               | Review **all source code** in `src/` for design pattern issues: KISS violations, SRP violations, tight coupling, composition vs inheritance, God classes, premature abstraction, SOLID principle violations (OCP, LSP, ISP, DIP). Also check structural conventions: one class per file, and test directory structure mirroring source structure. **For Python projects**: run all nine scanning scripts (`class_metrics_scanner.py`, `test_god_classes_scanner.py`, `one_class_per_file_scanner.py`, `test_structure_scanner.py`, `dependency_inversion_scanner.py`, `interface_segregation_scanner.py`, `open_closed_scanner.py`, `liskov_substitution_scanner.py`, and `integration_graph_scanner.py` from `src/zolletta_metaskill/{patterns,code_style,testing_style}/`) for automated triage, then apply the "reason to change" test to the top candidates. **This is a mandatory step, not optional.** See `skills/zolletta-metaskill-patterns/SUBCOMMAND.md` → "Mandatory Procedure" for the full procedure. You MUST consult the relevant sections of `../../docs/explanation/code/general-principles.md` (God class detection procedure + "What is NOT a God class") before evaluating any class. **You must NOT report a class as a God class based on size alone** — size is a triage signal, never a verdict. Classes that are parsers, strategies, orchestrators, or factories serving a single domain must be suppressed. **Use the `test_structure_scanner.py` markdown output directly in the report**: its five tables (misnamed tests, misplaced tests, orphaned tests, multi-class tests, missing tests) are **structural** findings — they check file naming and directory mirroring, not actual code coverage. Copy them into the report's findings section **except the "Missing tests" table**: before reporting any file from the "Missing tests" table as a finding, run `pytest --cov` and check the file's coverage. If coverage >50%, downgrade to informational. Only report as a finding if coverage <50% AND no indirect references. **Do not flag coverage gaps** — that is owned by `python-testing-style` which runs `pytest --cov`. **The DIP scanner excludes composition roots** (entry points by filename + classes that create DI containers via `make_container()`/`Container()` detected semantically). If the scanner still flags a class that is clearly a composition root, suppress it and note "composition root — not a DIP violation". **Coupling assessment**: after the "reason to change" test, consume `cache/integration_graph.json` (from `integration_graph_scanner.py`) — classify each cross-module edge's strength/distance/volatility per `balanced-coupling.md`, apply the balance rule, flag only unbalanced+volatile integrations, and note inferred classifications as assumptions. Use `test_splitter.py` if the human decides to split a test God class. **For other languages**: apply the same principles manually (no AST scripts available yet). **If `.tokensave/` exists, use the code graph tools** (tokensave_context/callees/callers or tokensave_impact) to understand class responsibilities and assess blast radius before proposing splits — see the skill's "Code Graph Tools" section for the decision tree. |
| `/zolletta-metaskill documentor` | zolletta-metaskill subcommand (always)                               | Review **project documentation** (from `documentation.dir` in `settings.json`, and nothing outside it — `skills/`, root markdown, and `CHANGELOG.md` are contracts, contributor material, and generated files, so a finding against them is a false positive by definition): [Diátaxis](https://diataxis.fr/) compliance (document type correctness, audience clarity, structure, accuracy, consistency) **and** drift detection (staleness, broken links, API doc validation, structural gaps) in a single pass. **Follow `documentor/references/operational-rules.md`** for false positive patterns, correct tool invocation (project root as repo path for staleness scorer), and the recommended workflow order.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `/zolletta-metaskill grice`      | zolletta-metaskill subcommand (opt-in — `documentation.check_grice`) | Score **project documentation** against Grice's four maxims — Quantity, Quality, Relation, Manner — as indices relative to the corpus itself, over the same document set `documentor` reviews (`documentation.dir` plus `README.md`, `CONTRIBUTING.md`, `AGENTS.md`; `skills/`, `SKILL.md` and `CHANGELOG.md` are out of scope). Run `grice/grice_scanner.py --json`, persist the payload to `cache/grice.json`, and assemble `reports/grice.md` from it — do NOT re-read the documents. Indices are **relative**: 50 is the corpus mean, never a pass mark, so the grade is advisory and does not enter the weighted overall score. Findings are only defects that carry a line — broken internal links/anchors and headings that skip a level. When `documentation.check_grice` is off the scanner prints `SKIPPED` and exits 0; record that in the report instead of grading it.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |

**Each subagent writes its own report file.** The subagent is given the output path and must use the `write` tool to save its report directly. The orchestrator does not collect subagent output and save it — that is the subagent's responsibility.

| Subagent                | Output file                                                        |
|-------------------------|--------------------------------------------------------------------|
| python-code-style       | `<runs_dir>/<YYYY-MM-DD-HH-MM>/reports/python-code-style.md`       |
| python-testing-patterns | `<runs_dir>/<YYYY-MM-DD-HH-MM>/reports/python-testing-patterns.md` |
| patterns                | `<runs_dir>/<YYYY-MM-DD-HH-MM>/reports/patterns.md`                |
| documentor              | `<runs_dir>/<YYYY-MM-DD-HH-MM>/reports/documentor.md`              |
| grice                   | `<runs_dir>/<YYYY-MM-DD-HH-MM>/reports/grice.md`                   |

**Subagent task template** (adapt for each):

```text
You are performing a code review on a <language> project.

First, invoke the skill "<skill-name>" using the skill tool to load its guidelines.
Then apply those guidelines to review the following scope:

<scope description>

Project root: <current working directory>
AGENTS.md: Read the project's AGENTS.md (and ~/.agents/AGENTS.md) for project-specific and global rules.

**Execution protocol**: follow ../../docs/reference/code/scripts-first-protocol.md —
batch-run the scripts listed in the per-subcommand table, persist their output to cache/,
assemble deterministic report sections from cached output, then run only the judgment
pass items listed for this subcommand.

**Shared context**: Read <runs_dir>/<YYYY-MM-DD-HH-MM>/cache/_context.md FIRST — it contains
settings.json extracts, ADR directives, and a judgment-rules digest. Do NOT re-read
settings.json, adr-distilled.md, or the mandatory reference docs separately — they are
already inlined in _context.md.

**Shared scanner outputs**: some scripts were already run by the orchestrator and are in
cache/ (one_class_per_file.txt, test_structure.md). Read those from cache — do NOT re-run
them. Run only the scripts listed for your subcommand that are not already in cache/.

Review mode: follow ../../docs/reference/code/review-mode.md — read-only, no fixes applied.
Auto-fixable issues are informational only and do not count toward the grade.

Architectural directives: use the ADR directives from cache/_context.md. Use judgment to
check whether the code you're reviewing aligns with each directive:
- Binary directives (e.g., "use PostgreSQL", "use async events for inter-service communication") — flag clear violations as findings.
- Nuanced directives (e.g., "adopt microservices", "prefer composition over inheritance") — note deviations as observations with context, not findings.
The directive's content tells you whether it's binary or nuanced.

You MUST write your report to this file using the write tool:
  <output_file_path>

Follow the report template for this skill (linked in the skill's "Output" section):
  - python-code-style: assets/report_template.md
  - python-testing-style: assets/report_template.md
  - patterns: assets/report_template.md
  - documentor: assets/report_template.md
  - grice: the "Report format" and "Output" sections of skills/zolletta-metaskill-grice/SUBCOMMAND.md

The report must include:
- A **grade** section at the top with a numeric score from 0 to 100 for the project's performance in the scope you reviewed. Justify the score with a brief breakdown of what earned points and what lost points.
- The skill-specific sections from the report template (tool results, coverage tables, scanning script results, etc. as applicable)
- Findings grouped by severity (critical/high/medium/low) using the template's table format, **numbered with a single progressive sequence across all severities**. All four sections are always present — an empty section reads `*None.*`, never disappears — `S1`, `S2`, `S3`… for code-style, `T1`, `T2`… for testing, `P1`, `P2`… for patterns, `D1`, `D2`… for documentor, `G1`, `G2`… for grice. The id never resets when the section changes and carries no severity letter, so `[T7]` is unambiguous across the whole run. Each finding row includes its id in the first column so the orchestrator's TODO can link it.
- If no issues are found, state that explicitly with a brief explanation of what was checked

**Grading** (0-100) — computed, not felt (see `../../docs/reference/code/review-mode.md` → "Grading" for the full rule):
- **Zero findings means 100** — if every check in scope passed clean, the grade is 100. Do not deduct points "just in case" or to signal humility: a grade below 100 must name the finding that cost the points.
- Baseline: `100 − Σ weight(finding)` with `critical −40 · high −15 · medium −5 · low −2` (informational/suppressed weigh 0).
- Judgment adjustment: at most **±5** off the baseline, and only when the justification names the finding(s) and why (e.g. a low that is systemic across many files; a high already mitigated by a compensating control).
- Interpretation bands: 90-100 Excellent · 75-89 Good · 60-74 Fair · 40-59 Poor · 0-39 Failing

Write the report to <output_file_path> using the write tool. Do NOT return the report as your final output — write it to the file. Return only a one-line confirmation that the file was written, along with the grade you assigned.
```

### Step 5 — Wait for all subagents to complete

After launching all subagents in parallel, wait for each one to finish using `read_subagent` (`block: true`). Each subagent writes its own report file — the orchestrator only needs to confirm completion and collect the grade from each subagent's one-line confirmation.

If a subagent fails or times out, create its report file with a note explaining what happened, and continue — do not abort the entire review.

### Step 6 — Compare with previous review (if exists)

If a previous review directory was found in Step 3:

1. Read the previous `SUMMARY.md` (the `Open`/`Done`/`Previous review status` sections).
2. For each item in the previous TODO, check whether it has been addressed:
   - **A previous "❌ Not done" is a claim to verify, not a fact.** Never carry an item forward on the strength of its checkbox alone — items are fixed between reviews without the TODO being updated, and an unchecked box is only evidence that nobody marked it done.
   - Run `git log --oneline -- <files the item names>` and `git log --grep=<keywords>` over the item's file paths and symbols. A fix commit often names the defect it closes (e.g. "do not flag parser vocabulary", "a rename that was undone is not a stale reference").
   - Read the current implementation of the named functions/classes. If the mechanism the item asked for exists in code — the exemption, the extra state, the shared helper — the item is ✅ Done regardless of what the old TODO says, and you cite the commit or the code as evidence.
   - Re-run the relevant scanner/tool when one exists. Silent/clean output means "no violations", not "still broken" — do not interpret an empty report as a residual defect.
   - Only then decide: ✅ Done (with evidence) / ⚠️ Partially done / ❌ Not done.
3. Create a section in the new SUMMARY.md called "## Previous review status" that lists each previous TODO item with its status: ✅ Done / ⚠️ Partially done / ❌ Not done.
   - **Group items by status** — three tables (✅ Done, ⚠️ Partially done, ❌ Not done), each ordered by the item's number in the **previous** TODO. The `#` column always refers to the previous numbering, never the new one.
   - **Every ⚠️ or ❌ row must name where it was carried forward** — a "Carried into" column reading `→ new #N`, so a reader can jump straight from the old item to its new TODO entry without searching.
   - ✅ rows carry a short evidence column (commit hash, code symbol, or check that proved it done); ⚠️ rows name what remains; ❌ rows name the evidence that it is still unfixed.
4. Any items that are ❌ Not done or ⚠️ Partially done should be carried forward into the new TODO as high-priority items (they were already identified and not resolved).

If no previous review exists, skip this step (note in SUMMARY.md that this is the first review).

### Step 7 — Create the executive summary (SUMMARY.md)

Read all report files that were produced by the subagents and extract the grade from each. Create `<runs_dir>/<YYYY-MM-DD-HH-MM>/reports/SUMMARY.md` following the summary template (`assets/summary_template.md`).

The SUMMARY.md is an executive overview — it contains grades, strengths, weaknesses, and trends. It does **not** duplicate the detailed findings from the specialist reports. Instead, it links to them in a "Detailed reports" section so the reader can drill down.

**Overall grade calculation**: use a weighted average of the sub-grades. Only include areas that were actually run. Suggested weights for a Python project (4 skills):

| Area            | Weight |
|-----------------|--------|
| Code style      | 30%    |
| Testing         | 30%    |
| Design patterns | 25%    |
| Documentation   | 15%    |

For non-Python projects (2 skills — patterns + documentor only):

| Area            | Weight |
|-----------------|--------|
| Design patterns | 60%    |
| Documentation   | 40%    |

If the project has no documentation directory, redistribute the documentation weight equally across the other areas.

**The grice grade is advisory and carries no weight.** It is a corpus-relative index — 50 is the middle of the corpus, not a pass mark — so folding it into the weighted average would make the overall grade depend on how many documents the project happens to have. Report it beside the weights, note its trend, and leave it out of the arithmetic. Its findings do count like any other finding: a broken link is a defect whatever the index says.

If a previous review exists, include a "Trend vs previous review" subsection noting whether the overall grade improved, worsened, or stayed the same, and by how many points.

### Step 8 — Create the aggregated SUMMARY.md

Read all report files produced by the subagents. Create `<runs_dir>/<YYYY-MM-DD-HH-MM>/reports/SUMMARY.md` following the summary template (`assets/summary_template.md`).

SUMMARY.md is both the executive summary and the prioritized action list — it does **not** duplicate the full findings from the specialist reports. Each item links to the relevant specialist report for full details (file path, line numbers, impact, suggested fix).

**Organization rules** (in this exact order):

1. **Dependency changes (under my control)** — any findings that require changes to internal/shared packages or other dependencies I own. These go first because everything else may depend on them being released. Mark each with a note: "⚠️ Requires dependency release — do these first, then wait for the release before proceeding."

2. **Critical / blocking issues** — anything that breaks functionality, causes data loss, security issues, or prevents the project from working.

3. **High priority** — significant code quality, design, or testing issues that should be addressed soon but don't block work.

4. **Medium priority** — style, documentation, and minor design improvements.

5. **Low priority** — nice-to-haves, cosmetic changes, future improvements.

6. **Previous review status** — the carry-forward section from Step 6 (if applicable).

**Recommendations must not restate findings** — that section carries only process/tooling advice the findings do not imply directly (heuristic gaps to feed back, workflow notes). If a recommendation is just "fix the finding," drop it.

**Numbering**: Assign each issue a unique sequential number starting from 1, counting continuously across all sections (Critical → High → Medium → Low). Do NOT restart numbering per section. The number goes before the priority tag.

**Format**: each severity section is a table `# | Reported in | Description` — not a checklist. **Reported in** links every item to the source findings in the specialist reports using per-report prefixes defined in the template (`PA` patterns, `D` documentor, `G` grice, `CS` python-code-style, `TP` python-testing-patterns), e.g. `[CS-M1](python-code-style.md#findings)`. Carried-forward items use `prev-#N`. Completed items move to a **Done** table at the bottom of their section.

### Step 9 — Summary response

After all files are saved and the SUMMARY.md is created, respond to the user with:

1. The project language (from `settings.json`)
2. A brief summary of what was reviewed and where the reports are saved
3. **The overall grade** (from SUMMARY.md) with a one-line interpretation
4. The grades by area (from the SUMMARY.md table)
5. The total number of findings by severity
6. The number of items carried forward from the previous review (if any) and their status
7. The top 3 strengths and top 3 weaknesses (from SUMMARY.md)
8. The top 3 priority items from the TODO
9. The path to SUMMARY.md files

Keep the summary concise. The full details are in the report files.

## Error handling

- If a subagent fails or times out, note it in the corresponding report file and continue with the next subagent in the sequence. Do not abort the entire review.
- If the documentation directory does not exist, the `documentor` and `grice` subagents should report that there is nothing to review (not an error). The grice scanner says so itself: `Result: SKIPPED (no documentation files found)`, exit 0.
- If `src/` or `tests/` directories don't exist, adapt the scope to whatever source directories are present in the project.
- If the project language cannot be determined automatically, ask the user before proceeding.
