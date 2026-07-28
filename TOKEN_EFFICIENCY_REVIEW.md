# Token Efficiency Review

> Reviewer: AI (self-review). Goal: minimize input tokens for AI consumers without sacrificing clearness. Code examples are not under review.

## Scope

42 docs total (all `.md` files in `docs/`), all read in full:

- **A docs** (`audience: human, ai`): 41 files — optimized for AI, readable for humans
- **B docs** (`audience: ai`): 1 file — optimized for AI only (caveman style acceptable)

---

## B Docs (audience: ai only)

### `reference/tool-messages.md` — 242 lines

**Issue**: written in human prose, not AI-optimized. The code blocks (verbatim messages) are correct and must stay. The surrounding prose is token waste for an AI-only audience.

**Token waste**:

| Lines   | Content                                                                                    | Problem                                                               |
|---------|--------------------------------------------------------------------------------------------|-----------------------------------------------------------------------|
| 9–13    | Intro paragraph explaining what the messages are for                                       | AI reading this file already knows why it's here — the skill loads it |
| 19–23   | "Tool unconfigured warnings" intro — 5 lines explaining the concept                        | 1 line would suffice: "Warnings for tools available but unconfigured" |
| 208–211 | "Companion skill not installed" intro — 4 lines explaining review vs implementation skills | AI already knows this distinction                                     |

**Recommendation**: strip all prose intros to one-liners. Keep the code blocks verbatim. Estimated saving: ~40 lines, ~300 tokens.

---

## A Docs (audience: human, ai)

### Critical: duplicated content

#### `explanation/documentation/standards.md` — lines 69–83

The "No artificial line breaks" section is **duplicated verbatim** (lines 69–75 and 77–83). This is a bug — 15 lines of pure duplication.

**Fix**: delete the second copy. Saving: 15 lines, ~120 tokens.

---

### High: verbose prose where terse would do

#### `how-to/code/python/review-python-style.md` — 86 lines

| Lines | Problem                                                                         | Saving                                                                                                                                        |
|-------|---------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------|
| 15    | Prerequisites: single 150-word paragraph restating every `python.tools.*` field | Cut to 2 lines: "Python project set up via `/zolletta-metaskill setup`. Reads `python.tools.*` and `python.code_style` from `settings.json`." |
| 55    | Review mode: 120-word paragraph restating `review-mode.md` rules                | Replace with: "Follows [review mode](../../../reference/code/review-mode.md) — read-only, two-bucket classification."                         |
| 47–51 | Always-on vs configurable: restates the same lists as lines 20–43               | Consolidate into one list with `(always-on)` / `(configurable)` tags                                                                          |

**Total estimated saving**: ~250 tokens.

#### `how-to/code/python/review-python-tests.md` — 70 lines

| Lines | Problem                                                                   | Saving            |
|-------|---------------------------------------------------------------------------|-------------------|
| 15    | Prerequisites: 120-word paragraph, same pattern as review-python-style.md | Cut to 2 lines    |
| 62    | Review mode: restates `review-mode.md`                                    | Replace with link |

**Total estimated saving**: ~140 tokens.

#### `how-to/code/review-code-style.md` — 94 lines

| Lines | Problem                                                                                                    | Saving                     |
|-------|------------------------------------------------------------------------------------------------------------|----------------------------|
| 80–87 | Review mode: 8 lines restating `review-mode.md`                                                            | Replace with one-line link |
| 51–78 | Always-on vs configurable: two separate lists that overlap with the "What the review checks" section above | Merge into one tagged list |

**Total estimated saving**: ~120 tokens.

#### `how-to/code/review-test-code.md` — 89 lines

| Lines | Problem                                                          | Saving                                               |
|-------|------------------------------------------------------------------|------------------------------------------------------|
| 80–82 | Review mode: restates `review-mode.md`                           | Replace with link                                    |
| 20–42 | "What the review checks": 6 subsections, each 2–3 lines of prose | Collapse to a bullet list with one-line descriptions |

**Total estimated saving**: ~70 tokens.

---

### High: massive reference files with redundant content

#### `reference/documentation/workflows-and-tools.md` — 422 lines

The largest doc in the tree. Significant overlap with `drift-detection-tools.md` and `scoring-and-categories.md`.

| Lines   | Content                                                | Problem                                                                    | Saving      |
|---------|--------------------------------------------------------|----------------------------------------------------------------------------|-------------|
| 58–66   | "What it does" 6-step numbered list for drift_analyzer | Restates the tool's --help output                                          | ~60 tokens  |
| 111–119 | "What it detects" 6-bullet list for api_doc_validator  | Duplicated in `drift-detection-tools.md` line 61                           | ~50 tokens  |
| 120–122 | "How it works" 3-line explanation of AST parsing       | AI doesn't need implementation details to use the tool                     | ~40 tokens  |
| 136–144 | "Validates" 6-bullet list for README health check      | Restates --help                                                            | ~50 tokens  |
| 166–175 | "What it checks" 7-bullet list for link checker        | Duplicated in `drift-detection-tools.md` line 80                           | ~50 tokens  |
| 176–228 | Workflow 5: full CI YAML + pre-commit hook             | Duplicated conceptually in `scoring-and-categories.md` integration section | ~200 tokens |
| 232–422 | Tool reference section (flags, params, exit codes)     | **Entirely duplicated** in `drift-detection-tools.md`                      | ~800 tokens |

**Recommendation**: cut the tool reference section entirely (it's in `drift-detection-tools.md`). Cut the "What it does/detects/checks" lists. Keep only the workflow recipes and CI examples that are unique to this file.

**Total estimated saving**: ~1250 tokens.

#### `reference/documentation/scoring-and-categories.md` — 167 lines

| Lines   | Content                                                       | Problem                                   | Saving     |
|---------|---------------------------------------------------------------|-------------------------------------------|------------|
| 112–132 | "Integration Points" — 4 subsections, each 2–3 lines of prose | Collapse to a 4-row table                 | ~60 tokens |
| 134–146 | "Anti-Patterns" — 5 bullets, each 1–2 lines                   | Keep as bullets but trim each to one line | ~40 tokens |
| 148–167 | "Troubleshooting" — wide table with long cells                | Keep but trim cell text                   | ~50 tokens |

**Total estimated saving**: ~150 tokens.

#### `reference/documentation/operational-rules.md` — 60 lines

| Lines | Content                                                    | Problem                                                                       | Saving      |
|-------|------------------------------------------------------------|-------------------------------------------------------------------------------|-------------|
| 19–35 | "Differences from doc-drift-detector" — historical context | AI doesn't need merge history to run the tools. Move to a footnote or delete. | ~200 tokens |
| 23    | Single bullet that is 5 lines long                         | Break into a rule + one-line rationale                                        | ~40 tokens  |
| 25    | Single bullet that is 6 lines long                         | Break into a rule + one-line rationale                                        | ~50 tokens  |

**Total estimated saving**: ~290 tokens.

#### `explanation/documentation/drift-prevention.md` — 176 lines

| Lines   | Content                                               | Problem                                                                                   | Saving                  |
|---------|-------------------------------------------------------|-------------------------------------------------------------------------------------------|-------------------------|
| 144–172 | "Common Drift Patterns" — 7 patterns, each 2–3 lines  | Collapse to a 3-column table (Pattern / Drift / Prevention)                               | ~80 tokens              |
| 73–111  | CI/CD gates — 4 YAML blocks + pipeline recommendation | Code examples not under review, but the 4 separate blocks could be one consolidated block | ~60 tokens (prose only) |
| 115–141 | Review checklists — 3 sections of checkbox lists      | Keep but trim to essential items only                                                     | ~40 tokens              |

**Total estimated saving**: ~180 tokens.

---

### High: reference docs with verbose prose

#### `reference/code/scripts.md` — 434 lines

The largest reference doc. Mostly well-structured (command + options table + notes), but several sections have prose that restates what the options table already says.

| Lines   | Content                                                                              | Problem                                                                                                                         | Saving      |
|---------|--------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------|-------------|
| 94–98   | `scan_tests.py` "File matching convention" — 5 lines explaining prefix matching      | The options table + one-line note would suffice                                                                                 | ~60 tokens  |
| 124–126 | `scan_naming_conventions.py` "Matching logic" — 3-line paragraph                     | Restates what the script does; the table + one line is enough                                                                   | ~40 tokens  |
| 146     | `scan_dependency_inversion.py` "Exclusions" — 3-line paragraph                       | Restates the `--entry-points` default from the table                                                                            | ~30 tokens  |
| 313–315 | `scan_unused_all_exports.py` "How it works" + "Use alongside vulture" — 2 paragraphs | AI doesn't need implementation details to run the command                                                                       | ~50 tokens  |
| 333–335 | `scan_test_naming.py` "How it works" + "Why this exists" — 2 paragraphs              | Same — implementation detail                                                                                                    | ~50 tokens  |
| 389–409 | "Complete Workflow" — 17-step numbered list                                          | Restates every script in the file in order. An AI reading this file already sees the scripts; the list adds no new information. | ~120 tokens |

**Total estimated saving**: ~350 tokens.

#### `reference/code/python/python-code-style.md` — 266 lines

A reference doc with numbered rules. Well-structured but several rules have multi-paragraph explanations where one line would do.

| Lines   | Content                                                                          | Problem                                                                                                   | Saving                  |
|---------|----------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|-------------------------|
| 15      | Rule 1.1 — "Always run inside the dev container" with 2-line explanation         | The command block is self-explanatory                                                                     | ~20 tokens              |
| 65–67   | Rule 3.3 — mypy overrides explanation, 3 lines                                   | Could be 1 line: "Override blocks apply only to listed modules; unlisted modules use the global default." | ~30 tokens              |
| 102     | Rule 6 — "Do not use `TYPE_CHECKING` blocks" with 2-line explanation             | Could be 1 line                                                                                           | ~20 tokens              |
| 106–130 | Rule 7 "Comments" — 24 lines with 6 bad examples + 3 good examples + explanation | Code examples not under review, but the prose (lines 106, 119–121, 130) could be trimmed to 3 lines       | ~40 tokens (prose only) |
| 183     | Rule 8.5 — "Ruff enforcement" paragraph listing 4 SIM rules                      | Restates ruff docs; a link would suffice                                                                  | ~30 tokens              |
| 219–227 | Rule 9.2 — "Rules of thumb" 5-bullet list                                        | Each bullet could be half its length                                                                      | ~30 tokens              |

**Total estimated saving**: ~170 tokens.

#### `reference/settings-schema.md` — 302 lines

A field-by-field reference. Mostly tables, which are token-efficient. But the top-level fields table (lines 138–149) has broken formatting — the `|` separators create phantom columns, making the table hard to parse for both humans and AI.

| Lines   | Content                                                                                 | Problem                                                                                               | Saving            |
|---------|-----------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------|-------------------|
| 138–149 | Top-level fields table — `string \| null` in cells creates extra `\|` column separators | Broken markdown table — the `\|` is interpreted as a column separator, creating empty phantom columns | Fix, not a saving |
| 146–147 | `python` and `php` rows — descriptions span 2 lines each due to the broken table        | Fix the table so each row is one line                                                                 | ~20 tokens        |

**Recommendation**: fix the table by escaping `\|` as `\\\|` or using HTML entities. This is a correctness fix, not a token saving.

#### `reference/code/code-exploration.md` — 74 lines

| Lines | Content                                                                         | Problem                                                                    | Saving     |
|-------|---------------------------------------------------------------------------------|----------------------------------------------------------------------------|------------|
| 9–13  | Intro — 5 lines restating what tokensave is                                     | `tokensave.md` already covers this; this file should focus on the workflow | ~40 tokens |
| 26–30 | "Patterns-specific narrowing" — 3 bullets that restate the workflow steps above | Redundant with lines 19–24                                                 | ~30 tokens |

**Total estimated saving**: ~70 tokens.

#### `reference/code/tokensave.md` — 74 lines

| Lines | Content                                                               | Problem                                                                                                            | Saving     |
|-------|-----------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------|------------|
| 13–20 | "MANDATORY: No Explore Agents" — 5-bullet block                       | Duplicated from `AGENTS.md` / `CLAUDE.md` global rules. An AI loading this skill already has those rules injected. | ~80 tokens |
| 40–44 | "When you spawn an Explore agent anyway" — 5-line blockquote template | Also duplicated from global rules                                                                                  | ~40 tokens |
| 46–63 | "Per-project MCP configuration" — 18 lines of config resolution order | Valuable but could be a 4-row table instead of nested prose                                                        | ~60 tokens |

**Total estimated saving**: ~180 tokens.

#### `reference/subcommands.md` — 58 lines

| Lines | Content                                                      | Problem                                                                         | Saving     |
|-------|--------------------------------------------------------------|---------------------------------------------------------------------------------|------------|
| 34–40 | "Running tools" — 7 lines explaining container/uv convention | Duplicated in every SKILL.md that runs tools. Could be a one-liner with a link. | ~40 tokens |

**Total estimated saving**: ~40 tokens.

#### `reference/reports.md` — 67 lines

| Lines | Content                                        | Problem                                                                                                        | Saving     |
|-------|------------------------------------------------|----------------------------------------------------------------------------------------------------------------|------------|
| 4–13  | Frontmatter `skills` list — 10-line YAML array | Inconsistent with other docs that use inline `[a, b, c]` syntax. The multi-line format costs ~10 extra tokens. | ~10 tokens |

**Total estimated saving**: ~10 tokens (minor, but a consistency fix).

---

### Medium: explanation docs with verbose patterns

#### `explanation/documentation/standards.md` — 83 lines (after dedup fix: ~68 lines)

Beyond the duplication bug, the "Core Principles" section (lines 17–21) is a 5-item numbered list where each item is a one-liner — this is fine. But the "Four Types of Documentation" table (lines 43–51) duplicates the Diátaxis framework that's already linked and explained in `docs/index.md`.

| Lines | Content                                     | Problem                                                         | Saving     |
|-------|---------------------------------------------|-----------------------------------------------------------------|------------|
| 41–52 | "Four Types of Documentation" table + intro | Duplicated in `docs/index.md` lines 13–20. Replace with a link. | ~60 tokens |

**Total estimated saving**: ~60 tokens (after the dedup fix).

#### `explanation/documentation/drift-prevention.md` — 176 lines

Additional finding from full read:

| Lines | Content                    | Problem                                                                                             | Saving    |
|-------|----------------------------|-----------------------------------------------------------------------------------------------------|-----------|
| 176   | "Last Updated: 2026-03-18" | Stale metadata line — the git history is the source of truth for last update. AI doesn't need this. | ~5 tokens |

---

### Medium: how-to docs with restated content

#### `how-to/code/detect-god-classes.md` — 94 lines

| Lines | Content                                                                                                                                      | Problem                         | Saving     |
|-------|----------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------|------------|
| 72–86 | Phase 2 — restates the "reason to change" test from `general-principles.md` and the false-positive rules from `false-positive-prevention.md` | Replace with links to both docs | ~80 tokens |
| 84–86 | Coverage cross-check — restates `false-positive-prevention.md` rule 2 verbatim                                                               | Replace with link               | ~40 tokens |

**Total estimated saving**: ~120 tokens.

#### `how-to/code/split-god-test-class.md` — 83 lines

| Lines | Content                                               | Problem                                                      | Saving     |
|-------|-------------------------------------------------------|--------------------------------------------------------------|------------|
| 61–67 | "What gets copied to each split file" — 6-bullet list | Duplicated in `scripts.md` lines 373–380. Replace with link. | ~40 tokens |
| 69–74 | "What the splitter does NOT do" — 5-bullet list       | Duplicated in `scripts.md` lines 382–387. Replace with link. | ~40 tokens |

**Total estimated saving**: ~80 tokens.

#### `how-to/documentation/review-documentation.md` — 97 lines

| Lines | Content                                                                                        | Problem                                                                                                                 | Saving     |
|-------|------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|------------|
| 20–48 | "What the review checks" — 3 subsections (Diátaxis, drift, freshness) each with 4-bullet lists | The drift and freshness bullets restate `scoring-and-categories.md` and `drift-detection-tools.md`. Replace with links. | ~60 tokens |

**Total estimated saving**: ~60 tokens.

#### `how-to/run-full-review.md` — 71 lines

| Lines | Content                                                                                 | Problem                                                  | Saving     |
|-------|-----------------------------------------------------------------------------------------|----------------------------------------------------------|------------|
| 28–43 | "Parallel skill execution" — lists general + language-specific skills with descriptions | Duplicated in `subcommands.md` table. Replace with link. | ~50 tokens |
| 54–56 | Review mode — restates `review-mode.md`                                                 | Replace with link                                        | ~30 tokens |

**Total estimated saving**: ~80 tokens.

#### `how-to/setup-project.md` — 74 lines

| Lines | Content                             | Problem                                                                                                                                                                      | Saving     |
|-------|-------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|------------|
| 30–43 | "What setup detects" — 10-row table | Duplicated in `settings-schema.md` (which documents every field). Keep the table but remove the "Stored as" column — it's the field name, which `settings-schema.md` covers. | ~30 tokens |

**Total estimated saving**: ~30 tokens.

#### `tutorials/getting-started.md` — 106 lines

| Lines | Content                                                                                | Problem                                                                     | Saving     |
|-------|----------------------------------------------------------------------------------------|-----------------------------------------------------------------------------|------------|
| 66–74 | "The review orchestrator runs all applicable skills" — 5-bullet list with descriptions | Duplicated in `run-full-review.md` and `subcommands.md`. Replace with link. | ~50 tokens |

**Total estimated saving**: ~50 tokens.

---

### Medium: missing "Why this matters" + external links

Two explanation docs have no "Why this matters" sections or external links, breaking the pattern established across the other explanation docs:

#### `explanation/code/security.md` — 138 lines

4 rules (parameterized queries, escape output, validate input, store secrets in env vars). None has a "Why this matters" or external link.

**Add**: one-line "Why this matters" + link to each rule (OWASP, PHP manual, Python docs). ~8 lines added, ~60 tokens — but this is a **consistency fix**, not a saving.

#### `explanation/code/performance.md` — 119 lines

2 rules (lazy loading, generators). None has a "Why this matters" or external link.

**Add**: one-line "Why this matters" + link to each rule (PHP generators, Python itertools). ~4 lines added, ~30 tokens — consistency fix.

---

### Medium: "we" voice in A docs

Multiple how-to docs use first-person plural ("we") throughout:

- `tutorials/getting-started.md`: "What we will learn", "We should see", "We can run"
- `how-to/code/python/review-python-style.md`: "We need a Python project", "We configure rule toggles"
- `how-to/code/python/review-python-tests.md`: "We need a Python project", "We report a coverage gap"
- `how-to/code/review-test-code.md`: "We use fixtures", "We never flag"
- `how-to/setup-project.md`: "We can also run it explicitly"

For AI consumption, imperative or declarative voice is more token-efficient and equally clear for humans. "We need a Python project" → "Requires a Python project". "We can run any skill" → "Run any skill".

**Estimated saving across all docs**: ~100 tokens (minor per-instance, but ~40 instances).

---

### Medium: restated prerequisites

Almost every how-to doc includes:

```
- The Zolletta-metaskill skill installed and available to the agent
```

This is implied by the skill system — the AI is loading the skill, so it's installed. Removing this line across ~10 how-to docs saves ~10 lines, ~80 tokens.

---

### Low: "See also" sections

Every how-to doc ends with 3–5 "See also" links. These are useful for human navigation but are token overhead for an AI loading a single doc as reference material.

**Recommendation**: keep them — they're valuable for human readers and the token cost is low (~15 tokens per section). Not worth removing.

---

## Cross-Cutting Patterns

### 1. Review-mode restatement (4 docs)

`review-code-style.md`, `review-test-code.md`, `review-python-style.md`, `review-python-tests.md` all restate the review-mode rules (two-bucket classification, no fixes, no hedging) that are fully specified in `reference/code/review-mode.md`.

**Recommendation**: replace all restatements with: "Follows [review mode](../../reference/code/review-mode.md) — read-only, two-bucket classification, no hedging."

**Estimated saving**: ~250 tokens across 4 files.

### 2. How-to ↔ language-specific overlap

The general how-to docs (`review-code-style.md`, `review-test-code.md`) and the Python-specific how-to docs (`review-python-style.md`, `review-python-tests.md`) describe the same checks at different levels of detail. The general doc says "checks naming conventions" and the Python doc says "checks `snake_case` filenames, `PascalCase` classes, `SCREAMING_SNAKE_CASE` constants".

This is intentional Diátaxis layering (general → specific). The overlap is acceptable but the general docs could be shorter — they don't need to list every check, just point to the language-specific doc.

**Recommendation**: trim the general how-to docs to focus on what's language-agnostic (the workflow, the always-on vs configurable distinction), and defer all specifics to the language-specific docs.

**Estimated saving**: ~100 tokens across 2 files.

### 3. `workflows-and-tools.md` ↔ `drift-detection-tools.md` duplication

These two files cover the same 4 tools. `workflows-and-tools.md` has workflows + tool reference. `drift-detection-tools.md` has tool reference only. The tool reference sections are nearly identical.

**Recommendation**: `workflows-and-tools.md` should contain only workflows and CI recipes. The tool reference (flags, params, exit codes) should live exclusively in `drift-detection-tools.md`. Add a cross-link.

**Estimated saving**: ~800 tokens.

---

## Summary Table

| File                                                | Current   | Estimated Saving                     | Priority |
|-----------------------------------------------------|-----------|--------------------------------------|----------|
| `reference/documentation/workflows-and-tools.md`    | 422 lines | ~1250 tokens                         | High     |
| `reference/documentation/operational-rules.md`      | 60 lines  | ~290 tokens                          | High     |
| `how-to/code/python/review-python-style.md`         | 86 lines  | ~250 tokens                          | High     |
| `explanation/documentation/standards.md`            | 83 lines  | ~180 tokens (dup bug + Diátaxis dup) | Critical |
| `reference/code/scripts.md`                         | 434 lines | ~350 tokens                          | High     |
| `reference/code/tokensave.md`                       | 74 lines  | ~180 tokens                          | High     |
| `how-to/code/python/review-python-tests.md`         | 70 lines  | ~140 tokens                          | High     |
| `explanation/documentation/drift-prevention.md`     | 176 lines | ~185 tokens                          | Medium   |
| `reference/documentation/scoring-and-categories.md` | 167 lines | ~150 tokens                          | Medium   |
| `how-to/code/review-code-style.md`                  | 94 lines  | ~120 tokens                          | Medium   |
| `how-to/code/detect-god-classes.md`                 | 94 lines  | ~120 tokens                          | Medium   |
| `reference/code/python/python-code-style.md`        | 266 lines | ~170 tokens                          | Medium   |
| `how-to/code/split-god-test-class.md`               | 83 lines  | ~80 tokens                           | Medium   |
| `how-to/run-full-review.md`                         | 71 lines  | ~80 tokens                           | Medium   |
| `how-to/code/review-test-code.md`                   | 89 lines  | ~70 tokens                           | Medium   |
| `reference/code/code-exploration.md`                | 74 lines  | ~70 tokens                           | Medium   |
| `how-to/documentation/review-documentation.md`      | 97 lines  | ~60 tokens                           | Medium   |
| `tutorials/getting-started.md`                      | 106 lines | ~50 tokens                           | Medium   |
| `reference/subcommands.md`                          | 58 lines  | ~40 tokens                           | Medium   |
| `how-to/setup-project.md`                           | 74 lines  | ~30 tokens                           | Low      |
| `reference/tool-messages.md` (B doc)                | 242 lines | ~300 tokens                          | Medium   |
| `reference/reports.md`                              | 67 lines  | ~10 tokens (consistency)             | Low      |
| `reference/settings-schema.md`                      | 302 lines | fix (broken table)                   | Medium   |
| `explanation/code/security.md`                      | 138 lines | +60 tokens (consistency fix)         | Medium   |
| `explanation/code/performance.md`                   | 119 lines | +30 tokens (consistency fix)         | Medium   |
| "we" voice across how-to docs                       | —         | ~100 tokens                          | Low      |
| Restated prerequisites                              | —         | ~80 tokens                           | Low      |
| Review-mode restatement (4 docs)                    | —         | ~250 tokens                          | Medium   |

**Total estimated token saving**: ~4400 tokens (after accounting for the +90 tokens added by consistency fixes).

**Total estimated token saving if all recommendations applied**: ~4400 input tokens per full docs load.

---

## Methodology

- Read all 42 docs in `docs/` (41 A + 1 B), every file in full including previously truncated sections
- Identified token waste patterns: duplication, verbose prose, restated rules, human-voice filler
- Code examples excluded from review per instructions
- "Why this matters" + external link pattern treated as the established standard (see commits `7b2ca2d`, `a979312`)
- Estimated savings are approximate, based on ~0.75 tokens per word
