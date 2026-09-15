---
audience: human, ai
status: stable
skills: [review, patterns, documentor, python-*, php-*]
---

# Anti-Patterns Audit

This document audits Zolletta-metaskill against the 13 anti-patterns catalogued by [Augmented Coding Patterns](https://lexler.github.io/augmented-coding-patterns/). For each anti-pattern it records the evidence that the skill already addresses it, distinguishes genuine enhancement opportunities from non-gaps, and cites the original source for attribution. Anti-patterns are listed in the same order as the [source catalog](https://lexler.github.io/augmented-coding-patterns/anti-patterns/). The companion [Patterns in Use](patterns.md) maps the patterns already followed, with an appendix of candidates worth considering.

## 1. AI Isolation

> *Retreating into solo AI work — less pairing, less shared knowledge, weaker collective ownership.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/anti-patterns/ai-isolation/>

**Evidence we already do this:**

| Where                             | What                                                     | How it encourages sharing                                                                                                                                                |
|-----------------------------------|----------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `skills/review/SKILL.md` Step 7-8 | SUMMARY.md + TODO.md are designed for team consumption   | SUMMARY is an executive overview with grades and trends; TODO is a prioritized action list — both are meant to be read by humans, not just the person who ran the review |
| `skills/review/SKILL.md` Step 6   | Previous review comparison creates shared history        | The team can see what was found before and what was fixed — creates a shared picture across reviews                                                                      |
| Report structure                  | Each finding links to the detailed specialist report     | Findings are linkable, shareable artifacts — a team member can point to a specific finding in a specific report                                                          |
| `skills/documentor/SKILL.md`      | Reviews documentation — inherently a shared artifact     | Documentation is written for the team; reviewing it reinforces shared understanding                                                                                      |
| Report format                     | Standard markdown, readable in any tool                  | Reports aren't locked into a specific AI platform — they're plain markdown files that anyone can read                                                                    |
| `skills/review/SKILL.md` Step 9   | Summary response includes top 3 strengths and weaknesses | Gives the team talking points — not just a list of problems, but a balanced view to discuss                                                                              |

**Not a gap:**

- ~~Reports are in `.gitignore` — not shared via git.~~ This is by design — committing timestamped review artifacts would clutter the repository with disposable output that has no long-term value. Users who want to share a report will commit it manually, paste it, or ask their AI to do so. Making reports committable by default would force every team to add their own `.gitignore` rule to undo it.

- ~~No "discuss" or "annotate" mechanism in reports.~~ Out of scope — Zolletta-metaskill is a review skill that produces reports, not a collaboration platform. Annotation and discussion belong to the team's existing tools (PR comments, issue trackers, chat).

- ~~No "decision log" for suppressed findings.~~ Out of scope — persisting team decisions across reviews is a workflow concern, not a review skill concern. The suppression reasoning is already in the report; whether the team chooses to persist it is their decision.


## 2. AI Slop

> *Using AI output without adding human judgment — if anyone with your prompt gets the same result, it's slop.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/anti-patterns/ai-slop/>

**Evidence we already do this:**

| Where                                                      | What                                                                              | How it avoids slop                                                                                                      |
|------------------------------------------------------------|-----------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------|
| `docs/reference/code/scripts-first-protocol.md` Phase B    | "Scanner tables copied verbatim from cache into the report"                       | Deterministic sections are not AI-generated — they're copied from script output. The AI can't slop the scanner results. |
| `docs/reference/code/review-mode.md` line 39-49            | "Do not qualify it with 'may be' or 'could be considered'"                        | Findings must be definitive — no hedging that adds words without adding value                                           |
| `docs/explanation/code/false-positive-prevention.md` §1    | "You must NOT report a class as a God class based on size alone"                  | Prevents the AI from parroting scanner output without judgment — size is a signal, not a finding                        |
| `skills/patterns/SKILL.md` line 60-66                      | "Reason to change" test requires domain grouping and analysis                     | Not just "this class is big" (slop) but "this class has reasons to change from 3 different domains" (judgment)          |
| `skills/documentor/SKILL.md` line 102-104                  | "Verify against the actual codebase before flagging a doc issue"                  | Prevents the AI from generating findings without verification — no slop from pattern-matching alone                     |
| `docs/explanation/code/general-principles.md` line 270-279 | "Do Not Overcomplicate Responses"                                                 | "Report each finding once, with the minimum context needed to act on it" — no padding                                   |
| `docs/reference/code/review-mode.md` line 27-28            | Auto-fixable issues are "informational only — do not count them toward the grade" | Prevents padding the report with trivial auto-fixable issues to inflate the finding count                               |
| `docs/explanation/code/false-positive-prevention.md` §5    | "Do not report each `Optional[str]` as a separate finding"                        | Prevents slop through repetitive findings — group by sub-tree, report once                                              |

**Not a gap:**

The slop test inverts for a review tool: "could anyone with your prompt get the same result?" is the goal, not the smell. Two reviews of the same code yielding the same results is the reason Zolletta-metaskill exists. [Determinism is the product](code/determinism.md), so this anti-pattern does not apply in its usual form.

- ~~The judgment pass (Phase C) is where AI slop can creep in.~~ Phase C judgment is explicitly marked as judgment in the scripts-first protocol. It is bounded by the no-hedge rule, FP suppression, the reason-to-change test, and the coverage cross-check. Judgment is not eliminated — it is narrowed to the items scripts defer.

- ~~The grade (0-100) is entirely LLM-generated.~~ Judgment by design ("All subcommands: severity assignment and grade calculation [JUDGMENT]"). Two runs may differ slightly — that is "more or less the same results," the stated design goal. A deterministic grade calculator would add a rule to solve a problem that is not one.

- ~~Suggested fixes are AI-generated and could be generic.~~ Findings already carry file/line references from scanner output; the suggested fix is advisory, and the developer chooses whether and how to act. Requiring a fix-quality rule would feed the Obsess Over Rules anti-pattern.

- ~~The slop test applies to Zolletta-metaskill itself — the judgment sections are not reproducible.~~ Addressed by documenting the boundary: [determinism.md](code/determinism.md) lists what is deterministic (Phase A scripts, cache, Phase B assembly, two-bucket classification) and what is not (Phase C findings, severity, grade, suggested fixes), so readers know what to treat as measurement and what to read as judgment.


## 3. Answer Injection

> *Putting solutions in questions limits AI to your preconceived approach instead of leveraging its breadth.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/anti-patterns/answer-injection/>

**Evidence we already do this:**

| Where                                                      | What                                                                     | How it avoids injecting solutions                                                                                                  |
|------------------------------------------------------------|--------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------|
| `skills/help/SKILL.md`                                     | Subcommands have fixed scopes, not user-specified problems               | The user runs `/zolletta-metaskill patterns` — the scope is "all source code in `src/`", not "look for God classes in UserService" |
| `docs/reference/code/scripts-first-protocol.md`            | Scanners scan everything, not just what the user mentioned               | `class_metrics_scanner.py` scans all classes — the user can't inject "check only UserService"                                      |
| `skills/review/SKILL.md` Step 4                            | Subagent task template describes scope, not a solution                   | "Review all Python source code in src/ for style, linting..." — describes what to check, not what to find                          |
| `skills/patterns/SKILL.md` line 60-66                      | "Reason to change" test lists ALL reasons, not just the scanner's signal | The test is open-ended: "list every change that could require editing the class" — not "confirm whether this class is a God class" |
| `docs/explanation/code/general-principles.md` line 270-279 | "Do not suggest architectural changes for style-level findings"          | Prevents the review from injecting solutions that exceed the finding's scope                                                       |

**Not a gap:**

For a review skill, decided constraints driving findings is the design, not an anti-pattern. The Answer Injection anti-pattern targets a *user* baking their preconception into a prompt to limit AI exploration — it does not apply to a review that enforces constraints the team explicitly decided.

- ~~ADR directives can inject solutions.~~ ADRs are recorded team decisions — enforcing them is the review's job. `skills/review/SKILL.md` Step 4 flags violations of binary directives because the team chose that architecture. A review that second-guesses decided directives would be Silent Misalignment in the other direction: re-litigating settled decisions instead of checking conformance.

- ~~Global rules can inject solutions.~~ Same principle — the rules are the user's own, recorded as configuration. The review is a tool that applies them; authoring and contextualizing the rules is the owner's responsibility, not the reviewer's.

- ~~Suggested fixes in findings can inject solutions.~~ A suggested fix is advisory output, not an injected premise. The finding carries the evidence; the developer decides whether and how to act. The existing "Do not suggest architectural changes for style-level findings" rule already scopes fix suggestions appropriately.


## 4. Big Chunk Working

> *AI generates sweeping changes that are hard to review and easy to merge with hidden damage.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/anti-patterns/big-chunk-working/>

**Evidence we already do this:**

| Where                                                   | What                                                                          | How it slices                                                                                                                             |
|---------------------------------------------------------|-------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------|
| `skills/review/SKILL.md` Step 4                         | One subagent per command, all in parallel                                     | Each review area (patterns, documentor, code-style, testing-style) is a separate subagent writing its own report file                     |
| `skills/review/SKILL.md` Step 7-8                       | SUMMARY.md + TODO.md are separate                                             | SUMMARY is an executive overview that links to detailed reports; TODO is a prioritized action list — neither duplicates the full findings |
| `docs/reference/code/scripts-first-protocol.md`         | Three-phase execution (A: batch scripts, B: mechanical assembly, C: judgment) | Each phase is a small, verifiable step; Phase B explicitly says "no source file reads in this phase"                                      |
| `docs/explanation/code/general-principles.md`           | "Do Not Overcomplicate Responses" (line 270-279)                              | "Report each finding once, with the minimum context needed to act on it"                                                                  |
| `docs/explanation/code/false-positive-prevention.md` §5 | Generational drift grouped by sub-tree                                        | "a single sub-tree-level finding is actionable; 47 individual `Optional[str]` findings are noise"                                         |

**Not a gap:**

- ~~No explicit "top N" cap on findings per report.~~ The TODO is already sorted by priority (critical → high → medium → low), so the reader sees the most important items first. A cap would hide easy wins (e.g., 10 low-severity findings fixable in one `ruff format` run) and obscure correlated findings that share a root cause. The existing mechanisms — priority sections, sub-tree grouping (`false-positive-prevention.md` §5), the "Do Not Overcomplicate Responses" rule, and the SUMMARY/TODO/specialist-report split — reduce noise without hiding information.

- ~~The full `review` re-scans the entire codebase every time.~~ Re-scanning is correct by design — code changes between reviews, so a full scan is necessary to catch new issues. The previous review comparison (`skills/review/SKILL.md` Step 6) already handles the "what changed" question by checking which previous findings were fixed or are still open. An incremental review mode would duplicate Step 6's carry-forward logic without adding value.

- ~~No slicing guidance for the report writer (group findings by theme within priority groups).~~ Priority grouping + sequential numbering already gives the reader enough structure to scan and mentally group findings. Adding a theme-classification rule would introduce a new judgment step (the AI must classify each finding into a theme), risk inconsistency between reviews (different theme names for the same concept — "Type safety" vs "Typing" vs "Type annotations"), and add clutter to short lists. The one case where grouping is clearly valuable — drift items by sub-tree — is already handled by `false-positive-prevention.md` §5. Adding a general theme-grouping rule would feed the Obsess Over Rules anti-pattern for marginal benefit.


## 5. Cognitive Overload

> *Too many open loops, fragmented attention — the team loses a shared picture of what matters.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/anti-patterns/cognitive-overload/>

**Evidence we already do this:**

| Where                                                   | What                                                     | How it limits overload                                                                                      |
|---------------------------------------------------------|----------------------------------------------------------|-------------------------------------------------------------------------------------------------------------|
| `skills/review/SKILL.md` Step 3.6                       | `cache/_context.md` deduplicates shared context          | "Copied once so 4 subagents don't each open settings.json" — eliminates 4x redundant context loading        |
| `docs/reference/code/scripts-first-protocol.md` line 73 | Forbids reading mandatory docs in full at review time    | The judgment-rules digest is inlined in `cache/_context.md` instead — "~30 lines, only the criteria"        |
| `docs/reference/code/review-mode.md` line 37-49         | "No borderline category — emit or suppress, never hedge" | The reader never has to mentally triage "maybe" findings — every finding is either real or suppressed       |
| `docs/explanation/code/false-positive-prevention.md` §5 | Drift items grouped by sub-tree, not per-file            | Prevents the reader from facing 47 identical findings                                                       |
| `skills/review/SKILL.md` Step 4                         | Each subagent has a single, narrow scope                 | A subagent reviewing code style doesn't also think about design patterns or documentation                   |
| `docs/reference/code/scripts-first-protocol.md`         | Anti-patterns section (line 67-73)                       | Explicitly forbids re-reading, re-deriving, sequential runs, re-running cached scripts — keeps context lean |

**Not a gap:**

- ~~The orchestrator itself is a WIP risk.~~ WIP (Work In Progress) risk means too many *concurrent* open loops competing for attention — that's what fragments attention and loses the shared picture. The orchestrator's 9 steps are *sequential* — each finishes before the next starts. At any moment there's exactly one thing in progress. The context grows, but that's accumulation, not WIP. It's the difference between 9 browser tabs you switch between (WIP risk) and 9 pages of a book read in order (not WIP risk). The context accumulation is also inherent to the task — you can't summarize reports you haven't read. Splitting SUMMARY/TODO creation into a subagent would just move the same context to a different agent, adding launch overhead without reducing total context.

- ~~The TODO.md has no "quick wins" or "top 3" section.~~ The priority sections (critical → high → medium → low) *are* the triage. A reader looking for "what to do first" reads critical, then high — that's the triage shortcut. Adding a "top 3" section would duplicate the first few items from the existing priority groups, adding a second layer of prioritization that doesn't help.

- ~~No WIP limit on parallel subagents.~~ The polyglot scenario (6 simultaneous subagents) is unreachable through the normal flow: `language_detector.py` returns a single primary language (first marker match), and the review reads that one `language` field to select the subcommand set — at most 4 subagents (two general + two language-specific). Even hypothetically, parallel subagents have isolated contexts — each has one narrow scope, and the orchestrator launches and waits, so no single agent juggles the parallel work. Fragmented attention cannot occur in isolated workers. A user with a genuinely polyglot repository who wants per-language reviews can run them separately; nothing in the design forces one giant run.


## 6. Distracted Agent

> *One agent doing everything stays shallow and misses what matters.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/anti-patterns/distracted-agent/>

**Evidence we already do this — this is the core architecture:**

| Where                                           | What                                        | How it stays focused                                                                                                           |
|-------------------------------------------------|---------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| `SKILL.md` Dispatch section                     | Meta-skill dispatches to subcommands        | The meta-skill never does the review itself — it routes to a focused subcommand                                                |
| `skills/help/SKILL.md`                          | 11 subcommands, each with a single scope    | `patterns` = God classes/SOLID only; `documentor` = docs only; `python-code-style` = style only; etc.                          |
| `skills/review/SKILL.md` Step 4                 | "One subagent per command, all in parallel" | Each subagent loads only its own SKILL.md and runs only its own scripts                                                        |
| `docs/reference/code/scripts-first-protocol.md` | Per-subcommand script table                 | Each subagent runs only the scripts listed for its subcommand — `patterns` runs 8 scanners, `documentor` runs 4 different ones |
| `skills/adr-distiller/SKILL.md`                 | Separate subcommand for ADR distillation    | Not mixed into the review orchestrator's main flow                                                                             |
| `skills/patterns/SKILL.md` line 68-75           | "Classes that must be suppressed"           | The patterns agent is explicitly told what NOT to report — it doesn't get distracted by false positives                        |

**Not a gap:**

- ~~The orchestrator itself could be a "distracted agent."~~ The orchestrator coordinates but does not review — its 9 steps are sequential coordination, not parallel responsibilities competing for attention. Each subagent has one scope, one set of scripts, and one report to write.

The architecture is a direct implementation of the **Focused Agent** pattern, and the docs cite it where it matters: the dispatch section of `SKILL.md` and Step 4 of `skills/review/SKILL.md` both name the pattern and the anti-pattern, linking to the distilled definitions in [`docs/reference/augmented-coding-patterns.md`](../reference/augmented-coding-patterns.md).


## 7. Flying Blind

> *Accepting AI-generated code without review — bugs accumulate silently, nobody understands what was built.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/anti-patterns/flying-blind/>

**Evidence we already do this — Zolletta-metaskill exists specifically to prevent Flying Blind:**

| Where                                                | What                                                                                            | How it prevents flying blind                                                                                   |
|------------------------------------------------------|-------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------|
| Entire project                                       | A code review skill that audits AI-generated (and human) code                                   | The whole point: someone reviews what was built, instead of rubber-stamping                                    |
| `docs/reference/code/scripts-first-protocol.md`      | Scripts produce deterministic findings before LLM judgment                                      | The LLM cannot report a finding the scanners didn't surface — it builds on verified output, not assumptions    |
| `docs/explanation/code/false-positive-prevention.md` | Mandatory judgment steps (reason-to-change, coverage cross-check, composition-root suppression) | Prevents rubber-stamping scanner output — every finding requires a human-equivalent judgment pass              |
| `docs/reference/code/review-mode.md` line 37-49      | "No borderline category — emit or suppress, never hedge"                                        | Forces a decision on every diagnostic — no "maybe" findings that get rubber-stamped                            |
| `skills/review/SKILL.md` Step 6                      | Previous review comparison                                                                      | Tracks whether previous findings were addressed — prevents findings from being silently ignored across reviews |
| `skills/documentor/SKILL.md` line 102-104            | "Verify against the actual codebase before flagging a doc issue"                                | Documentation review verifies claims against source, preventing docs from drifting silently                    |
| `docs/reference/code/code-exploration.md` step 5     | "Before splitting: run `tokensave_impact` to assess blast radius"                               | Validates that a proposed refactoring is safe before recommending it                                           |

**Not a gap:**

- ~~No CI gate integration in the review skill.~~ The review follows the peer-review model: it reports findings, and how to tackle them is up to the author — exactly like a human peer reviewer. Gating merges on findings is a team workflow choice, not the reviewer's job; teams that want a gate already have recipes in [`docs/reference/ci-cd-workflows.md`](../reference/ci-cd-workflows.md). Forcing one would turn the reviewer into an enforcer.

- ~~No "confidence" field on findings.~~ A finding's evidence is the deterministic scanner output, included verbatim in the report — a fact. What the LLM contributes is the emit/suppress verdict on items the scripts defer and the severity label. A confidence field would reintroduce the borderline category that `review-mode.md` explicitly eliminates ("No borderline category — emit or suppress, never hedge"): a finding that wouldn't survive as confident is suppressed, not published with a hedge.

- ~~The review is read-only by design, so it cannot *prevent* Flying Blind.~~ Read-only is exactly what removes the danger: the review never writes code, so no AI-unvetted code can enter through it. Acting on findings is the author's job — like a peer reviewer who comments but never commits to your branch.


## 8. Obsess Over Rules

> *More rules → more ignored rules; context rot degrades output as the ruleset grows.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/anti-patterns/obsess-over-rules/>

**Evidence we already do this:**

| Where                                                      | What                                                                                                | How it keeps rules lean                                                                                                    |
|------------------------------------------------------------|-----------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------|
| `SKILL.md` line 40                                         | "Sub-skills link back to rules and only narrow behavior — they never override or restate the rules" | Rules are stated once, linked not duplicated                                                                               |
| `skills/review/SKILL.md` Step 3.6                          | Judgment-rules digest is "~30 lines — only the criteria, not the full prose"                        | Deliberately compressed to prevent context bloat                                                                           |
| `docs/reference/code/scripts-first-protocol.md` line 73    | Forbids "Reading mandatory reference docs in full at review time"                                   | The digest replaces the full docs in the subagent context                                                                  |
| `skills/patterns/SKILL.md` line 57                         | "MUST consult the relevant sections" — not read in full                                             | Standalone runs get the same section-only rule as orchestrator runs; the instruction stack no longer disagrees with itself |
| `docs/reference/code/review-mode.md`                       | The entire "no borderline" rule is 13 lines                                                         | One clear principle, not a complex ruleset                                                                                 |
| `docs/explanation/code/false-positive-prevention.md`       | 5 specific mechanisms, each with a clear procedure                                                  | Not a general "be careful" rule — each has a concrete step-by-step                                                         |
| `skills/patterns/SKILL.md` line 101-121                    | "Best Practices Summary" — 18 concise one-liners                                                    | Not paragraphs of rules — scannable, memorable                                                                             |
| `docs/explanation/code/general-principles.md` line 270-279 | "Do Not Overcomplicate Responses"                                                                   | Explicitly tells the agent not to add tangential context or restate rules                                                  |

**Not a gap:**

- ~~Rules accumulate across the stack (task template + `cache/_context.md` + SKILL.md + report template — 4+ documents, no mechanism to verify the agent followed all of them).~~ The layering is the design, not sprawl: each artifact has a distinct, non-overlapping function — the task template defines the scope, `cache/_context.md` deduplicates shared context (it exists precisely to eliminate redundant reads — it *is* the anti-accumulation mechanism), the SKILL.md is the focused agent's own competence, and the report template is the output contract. None restates the others (the no-restate rule). The compliance concern is answered by the report itself: deterministic sections are copied verbatim from cache, suppressions must state their reasoning, and the no-hedge rule makes rule-ignoring visible in the output. A separate verification mechanism would add rules to check rules — feeding the anti-pattern it claims to prevent.

- ~~The patterns skill marks reference files as mandatory reading (★) — a lot of mandatory context for a focused agent; consider moving the "Mandatory Procedure" out of SKILL.md.~~ Fixed by the consult-sections change. The "lot of mandatory context" premise assumed the ★ files were read in full (~1,500 lines); they are now consulted section-by-section, and the orchestrator digest replaces the judgment rules. What is always read is the skill's own SKILL.md (124 lines — the entry point every skill must load, lean by design) plus the ~30-line digest. Moving the "Mandatory Procedure" (~35 lines) into a separate on-demand doc would save nothing: the procedure is needed on every run, so "on demand" just adds an indirection.

- ~~No refinement loop exists.~~ The refinement loop exists in two layers. Within a run, every candidate finding passes the FP-suppression checks (reason-to-change, coverage cross-check, composition-root suppression) before emission — output is verified before it is published, not fire-and-forget. Across runs, the previous-review comparison (`skills/review/SKILL.md` Step 6) verifies which prior findings were fixed (Done/Partial/Not done) and carries forward the rest — the review iterates on its own output over time. A separate "re-read your own report" pass would duplicate the suppression checks that already run inline before emission.

- ~~The general-principles.md is 545+ lines — a context rot risk if read in full, and standalone subcommand runs still read the full doc.~~ That premise no longer holds: the original "you MUST read them before starting any review" wording conflicted with the scripts-first protocol's section-only rule, and was fixed to "you MUST consult the relevant sections" (in both `skills/patterns/SKILL.md` and the review subagent task table). No instruction path reads the doc in full anymore — orchestrator runs get the ~30-line digest, standalone runs consult relevant sections. Splitting the file into topic-specific references would be structural polish with no behavioral change.


## 9. Perfect Recall Fallacy

> *Expecting AI to remember library details from training — give it tools to discover instead.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/anti-patterns/perfect-recall-fallacy/>

**Evidence we already do this:**

| Where                                           | What                                                                             | How it avoids relying on memory                                              |
|-------------------------------------------------|----------------------------------------------------------------------------------|------------------------------------------------------------------------------|
| `docs/reference/code/scripts-first-protocol.md` | Scripts produce deterministic output from the actual codebase                    | The LLM reads scanner output, not its own memory of what the code looks like |
| `skills/documentor/SKILL.md` line 102-104       | "Verify against the actual codebase before flagging a doc issue"                 | Doesn't assume the AI remembers the codebase — reads the actual source       |
| `docs/reference/code/code-exploration.md`       | Uses tokensave to understand classes "without reading the full file"             | Still reads the actual code graph, doesn't rely on memory                    |
| `SKILL.md` Tool-failure handler (line 66-73)    | Falls back to grep + targeted reads when tokensave is unavailable                | Doesn't try to recall from memory — uses actual file I/O                     |
| `skills/setup/SKILL.md` Step 5                  | Tests tokensave by calling `tokensave_status`                                    | Detects tool availability by actual probe, not by assuming what's installed  |
| `skills/setup/SKILL.md` Step 6                  | Runs `pyproject_sections_detector.py` and `<command> --version`                  | Detects tools by running actual commands, not by assuming what's installed   |
| `skills/review/SKILL.md` Step 1.5               | Checks `file_count` vs actual source files, `last_sync_at` staleness             | Validates index freshness against actual filesystem state                    |
| `skills/setup/SKILL.md` Step 6.6-6.7            | Detects `documentation.dir` (`.backstage/…` layouts included) and the ADR folder | The project's own docs and conventions are located by scanning, not assumed  |
| `skills/setup/SKILL.md` acronym extraction      | Reads naming conventions from the project's `AGENTS.md` into `acronyms`          | Project-specific conventions are extracted from the repo, not recalled       |

**Not a gap:**

- ~~No "playground" or experimentation mechanism.~~ Reviews are static analysis by design — the reviewer reads, it does not execute. Runtime behavior verification belongs to tests and CI, which are outside a review skill's scope; structural questions are answered deterministically by the AST scanners. A reviewer that runs experiments would blur the review/fix boundary the read-only design protects.

- ~~The "reason to change" test relies on the LLM's understanding of the class — library behavior assumptions could be wrong.~~ Acceptable: the same risk applies to human reviewers, who can equally misremember a framework decorator's behavior. The test is run against the actual code (not memory), and the safeguards — scanner evidence, stated suppression reasoning, no-hedge — are the ones a human review relies on. Peer review has never required infallible library recall; it requires reasoned judgment on read evidence.

- ~~No reference docs for the project's own conventions.~~ The project's own documentation is already in scope: setup detects `documentation.dir` (default `docs`, `.backstage/…` layouts included) and the ADR folder (Step 6.6-6.7), and even extracts naming conventions from the project's `AGENTS.md` into `acronyms`. The documentor reviews that tree with drift detection and staleness scoring against the codebase — so conventions docs are read where they live and kept honest. ADR directives cover architectural decisions. A separate "conventions reference" would duplicate docs that are already discovered, reviewed, and drift-checked.


## 10. Silent Misalignment

> *AI complies instead of flagging contradictions — misalignment grows silently as it builds on wrong interpretations.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/anti-patterns/silent-misalignment/>

**Evidence we already do this:**

| Where                                                   | What                                                                                                          | How it surfaces misalignment                                                                                      |
|---------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------|
| `docs/reference/code/review-mode.md` line 49            | "If you're not sure whether it's real, the rule definition is not precise enough — that's a skill bug to fix" | Pushes the AI to flag uncertainty rather than silently comply — uncertainty is a skill bug, not something to hide |
| `docs/explanation/code/false-positive-prevention.md` §1 | "Explicitly state 'cohesive — not a God class' in the report"                                                 | The AI must explain its reasoning, not silently suppress — surfaces the mental model                              |
| `skills/patterns/SKILL.md` line 60-66                   | "Reason to change" test: list changes, group by domain, then conclude                                         | The structured procedure surfaces the AI's mental model before it acts                                            |
| `skills/documentor/SKILL.md` line 108                   | "Distinguish illustrative from factual content"                                                               | The AI must state its interpretation, not assume                                                                  |
| `skills/review/SKILL.md` Step 4 line 224                | "If no issues are found, state that explicitly with a brief explanation of what was checked"                  | Forces the AI to explain what it checked, not just say "all good"                                                 |
| `skills/setup/SKILL.md` Step 3                          | "If still undetermined, ask the user with `ask_user_question`"                                                | Setup doesn't silently guess the language — it asks                                                               |
| `skills/review/SKILL.md` Step 1 line 57                 | "If the language cannot be determined, ask the user with `ask_user_question`"                                 | The orchestrator asks rather than assuming                                                                        |

**Not a gap:**

- ~~No "describe the structure you see" step before the review.~~ Out of scope — that solution step targets *changes* ("before changes: describe the structure you see"), and the review doesn't change code. Where the review does conclude anything, the equivalent already exists: the reason-to-change test forces listing what would force edits before any verdict, and the report states what was checked.

- ~~No pushback when the scope doesn't fit (e.g., `patterns` on a non-OO codebase).~~ The patterns scope is broader than OOP — KISS violations, tight coupling, premature abstraction, and structural conventions apply to any code, so a functional codebase still gets reviewed for them. What genuinely doesn't apply (one-class-per-file with no classes) scans to nothing, and the report states what was checked — honest reporting, not silent compliance.

- ~~No "does this make sense?" check during the review.~~ It exists at the rule level: "If you're not sure whether it's real, the rule definition is not precise enough — that's a skill bug to fix" (`review-mode.md`) — doubt is escalated as a documented skill bug instead of being silently absorbed. Beyond that, the skills are human-designed by purpose, and code that genuinely doesn't make sense to the reviewer is exactly what the review reports as findings — that is the product, not a failure to pause.

- ~~The review doesn't ask clarifying questions.~~ By design — the review is not interactive; it is a batch run over a fixed scope. Questions belong to configuration time, and there the design does ask (setup Step 3 and review Step 1 both use `ask_user_question` when the language is undetermined). At review time the scope is already fixed by the subcommand, so there is nothing left to clarify.


## 11. Sunk Cost

> *Pushing AI past diminishing returns — code gets messier with each iteration.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/anti-patterns/sunk-cost/>

**Evidence we already do this:**

| Where                                                   | What                                                                              | How it avoids sunk cost                                                                                                           |
|---------------------------------------------------------|-----------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------------------------------|
| `skills/review/SKILL.md` Step 2                         | Each run creates a new timestamped folder                                         | Every review starts fresh — no "continue from where we left off" that would accumulate sunk cost                                  |
| `skills/review/SKILL.md` Step 6                         | Previous review comparison carries forward unaddressed items                      | But doesn't try to "fix" them — just notes status (Done/Partial/Not done) and carries forward                                     |
| `skills/review/SKILL.md` Step 7                         | SUMMARY "Trend vs previous review" subsection + carried-forward count             | Surfaces stagnation (flat grade, items Not done) without acting on it — the signal is the reviewer's job, the decision the team's |
| `docs/reference/code/review-mode.md`                    | Review is read-only — no fixes applied                                            | The review doesn't iterate on fixes. It reports once and stops — no sunk cost from patching over bad fixes                        |
| `docs/reference/code/scripts-first-protocol.md` line 72 | "Re-running a script whose output is already in cache/ — read from cache instead" | Within a run, no re-derivation. Across runs, everything is fresh.                                                                 |
| `skills/review/SKILL.md` Step 5 line 240                | "If a subagent fails or times out, note it and continue"                          | The orchestrator doesn't retry a failed subagent — it notes the failure and moves on                                              |
| Run folder structure                                    | Reports are disposable, timestamped, in `.gitignore`                              | Each run is a disposable artifact — no pressure to "make this run's report work"                                                  |

**Not a gap:**

- ~~No "parallel implementations" mechanism — no way to run the same subcommand with a different approach and compare.~~ By design. Parallel implementations is a pattern for *non-deterministic generation* — when output varies wildly between runs, generating multiple candidates and picking the best makes sense. Zolletta-metaskill's goal is the opposite: two reviews of the same code should yield the same results ([determinism is the product](code/determinism.md)). The deterministic sections are identical across runs by construction — there is nothing to compare; the judgment sections are deliberately bounded, so comparing them would measure noise, not signal. A user who distrusts a report can simply re-run the subcommand: the timestamped run folders make side-by-side comparison trivial without a skill feature.

- ~~No "diminishing returns" detection — the review will keep producing 45+ findings indefinitely; no mechanism to say "fix them or accept them."~~ The trend is already surfaced: SUMMARY.md's "Trend vs previous review" subsection (grade improved/worsened/stayed), the "Previous review status" section (✅/⚠️/❌ per item), and the summary response's carried-forward count. A reader seeing a flat grade with items carried forward Not done has exactly the diminishing-returns signal. What to do about it — fix, defer, or accept — is the authors' decision: the TODO is a prioritized suggestion list, not an order, and a reviewer that nags or auto-drops would be the enforcer role already rejected. The anti-pattern itself targets *AI iterating past diminishing returns on a task*; the review doesn't iterate on anything — each run is fresh, read-only, and disposable.

- ~~Previous review comparison could create sunk cost pressure — a finding carried forward 5 times is still in the TODO; a "drop stale findings" rule is needed.~~ The mechanism doesn't support the scenario. Step 6 compares only the current run with the *newest* previous run (Step 3) — there is no history chain and no appearance counter, so pressure cannot accumulate by construction; the 2nd and the 10th carry-forward are treated identically. More decisively, each carried item is re-verified against the actual codebase and git history every run ("search the codebase for the files/areas; `git log`/`git diff`") — an item persists only because it is still real in the current code, and a finding that stops being real vanishes naturally when the current scan no longer produces it. The TODO is regenerated from current reality, not accumulated from history. Dropping a still-real finding would hide information (the rejected "top N cap") and pre-empt the team's decision to accept a risk (the rejected suppression log) — the reviewer reports what's true; the team decides what to do about it.


## 12. Tell Me a Lie

> *Forced premises make AI fabricate plausible nonsense to meet an arbitrary requirement.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/anti-patterns/tell-me-a-lie/>

**Evidence we already do this:**

| Where                                                   | What                                                                                                          | How it avoids fabrication                                                                                            |
|---------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------|
| `docs/reference/code/review-mode.md` line 37-49         | "No borderline category — emit or suppress, never hedge"                                                      | Prevents the AI from fabricating "maybe" findings to fill a template — every diagnostic is either real or suppressed |
| `docs/explanation/code/false-positive-prevention.md` §1 | "You must NOT report a class as a God class based on size alone"                                              | Prevents forcing findings to fit the God class template when the class is cohesive                                   |
| `skills/patterns/SKILL.md` line 66                      | "Explicitly state 'cohesive — not a God class'"                                                               | The AI is told to say "not a finding" rather than fabricate one to justify the scanner signal                        |
| `docs/explanation/code/false-positive-prevention.md` §2 | "If coverage >50%, downgrade to informational"                                                                | Prevents forcing a "missing tests" finding when the tests actually exist                                             |
| `skills/documentor/SKILL.md` line 138-146               | False positive filtering: 7 known FP patterns                                                                 | Prevents the AI from reporting phantom findings that the tools produce as artifacts                                  |
| `skills/review/SKILL.md` Step 5 line 240                | "If a subagent fails or times out, note it and continue — do not abort"                                       | The orchestrator doesn't fabricate a report for a failed subagent — it notes the failure honestly                    |
| `docs/reference/code/review-mode.md` line 49            | "If you're not sure whether it's real, the rule definition is not precise enough — that's a skill bug to fix" | The AI is told to NOT hedge — if uncertain, the skill is broken, not the finding                                     |

**Not a gap:**

- ~~No "does my question make sense?" check — the skill should push back when the scope doesn't fit the codebase.~~ Out of scope: questioning which subcommand to run is the user's call, not the review's — the fixed-scope design (see Answer Injection) means the subcommand does what it says, no more. This was a cross-section duplicate of the scope-pushback item already rejected in Silent Misalignment: the patterns scope applies beyond OOP (KISS, tight coupling, premature abstraction, structural conventions), what genuinely doesn't apply scans to nothing, and the report states what was checked — honest reporting, not silent compliance.

- ~~The grading system (0-100) could pressure the AI to fabricate findings to justify a non-perfect score.~~ The causal direction is inverted: grading happens at the end, after the findings exist. Each subagent produces findings first (Phase A/B scanner output + bounded Phase C judgment), assigns severity, then computes the grade *from* what it found — the grade is an output of the findings, never an input, so there is no step where a grade target could precede and motivate a finding. A fabricated finding would also need evidence it doesn't have: findings are grounded in cached scanner output and code references, and the no-hedge rule suppresses anything uncertain. The clean outcome is first-class — the report template says "If no issues are found, state that explicitly with a brief explanation of what was checked," and the scale's top band explicitly covers "minimal *or no issues*": zero findings is a legitimate outcome squarely in the 90-100 band, not a template failure to fill.

- ~~The report template requires findings grouped by severity — empty tables feel incomplete, creating pressure to fill them.~~ Not a real issue: an LLM follows the explicit instruction ("If no issues are found, state that explicitly with a brief explanation of what was checked"), and the no-hedge rule plus FP suppression make a clean report a first-class outcome. The "empty tables feel incomplete" pressure was the same anthropomorphic speculation as the grading-pressure claim, rephrased — an LLM does not experience template-completion anxiety, and a "No findings — clean" template variant would duplicate an instruction that already exists.


## 13. Unvalidated Leaps

> *Building on unverified assumptions about the code — each wrong step compounds.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/anti-patterns/unvalidated-leaps/>

**Evidence we already do this:**

| Where                                                   | What                                                                                        | How it validates before building                                                                                         |
|---------------------------------------------------------|---------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------|
| `docs/reference/code/scripts-first-protocol.md`         | Phase A (scripts) → Phase B (assembly) → Phase C (judgment)                                 | Scripts validate the code's actual state before the LLM builds findings on top of it                                     |
| `docs/explanation/code/false-positive-prevention.md` §2 | Coverage cross-check before reporting "missing tests"                                       | Runs `pytest --cov` to validate the assumption that tests are missing — if coverage >50%, the structural signal is wrong |
| `docs/explanation/code/false-positive-prevention.md` §3 | Composition-root suppression                                                                | Validates that a flagged class is actually a composition root before suppressing — doesn't assume                        |
| `skills/documentor/SKILL.md` line 102-104               | "Never assume the doc is wrong based on a pattern match or heuristic alone"                 | Uses tokensave/grep to verify against actual source before flagging                                                      |
| `skills/documentor/SKILL.md` line 110                   | "Verify previous issues are still present before carrying them forward"                     | Reads current file state — doesn't assume old issues persist                                                             |
| `skills/review/SKILL.md` Step 1.5                       | Tokensave pre-flight check                                                                  | Validates index freshness before subagents use it — prevents subagents from building on stale data                       |
| `docs/reference/code/code-exploration.md` step 5        | "Run `tokensave_impact` to assess blast radius — warn the user if risk is HIGH or CRITICAL" | Validates the assumption that a split is safe before recommending it                                                     |
| `skills/patterns/SKILL.md` line 60-66                   | "Reason to change" test: list, group by domain, then conclude                               | Validates the God class assumption through structured analysis before reporting                                          |

**Not a gap:**

- ~~No incremental validation within a single subagent's judgment pass — a wrong assumption about a class compounds into every subsequent finding about it; a "state your assumption, then verify it" step before each judgment item would help.~~ The remedy is already the shape of Phase C. Each judgment item is evidence-first, not assumption-first: the reason-to-change test is *list the edit reasons from the actual code → group → conclude* — there is no step where a belief precedes evidence-gathering, and the listing appears in the report before the verdict. The chain is short and per-candidate: a wrong model of class A contaminates only findings about class A, not the subsequent items. The reasoning is surfaced for checking (domain groupings, suppression statements), the no-hedge rule forces uncertainty to resolve as a verdict or a suppression — never a silent guess — and the other Phase C items share the same shape: vulture FP review greps for dynamic access, documentor FP filtering checks that the code fence or method exists, the coverage cross-check runs `pytest --cov`. A separate "state your assumption" step would duplicate the evidence-gathering each judgment item structurally requires.

- ~~No "prediction vs reality" check — the LLM should predict what the scanners will find, then check its prediction to surface wrong mental models early.~~ A category error, and it would violate the protocol. Prediction (Predictive TDD) is a generation-time pattern: write code, predict the outcome, get surprised. A review consumes deterministic scanner output — there is nothing to predict, because the foundation is already reality: the LLM builds findings on cached scanner output and cannot report a finding the scanners didn't surface. Predicting what the scanners will find would be re-deriving their output — literally the forbidden anti-pattern in the scripts-first protocol ("Re-deriving a finding the scanner already emits"). Zolletta-metaskill is as deterministic as possible ([determinism is the product](code/determinism.md)); a prediction step would add non-determinism where the design eliminates it.

- ~~The documentor's accuracy verification has a budget — "later doc claims are validated with grep (weaker) instead of tokensave (semantic)."~~ A deliberate token-efficiency tradeoff with a designed degradation path, and the claim overstates what the budget covers. The budget applies to `tokensave_context` only — the heavyweight call that returns full source context. The common verification ("does this documented symbol exist?") uses the cheap, unlimited `tokensave_search`, as does the known phantom-method FP pattern. The bulk of doc-vs-code verification is already deterministic: `api_doc_validator.py`, `drift_analyzer.py`, and `doc_staleness_scorer.py` do the exhaustive pass in Phase A, so the budgeted calls cover only the residual ambiguous claims — typically a handful, which is what "3" encodes. After the budget, the fallback is grep + targeted read — still actual code inspection, not memory. Degradation, not failure.
