---
audience: human, ai
status: stable
skills: [review, patterns, documentor, python-*, php-*]
---

# Patterns in Use

This document maps the patterns from [Augmented Coding Patterns](https://lexler.github.io/augmented-coding-patterns/) that Zolletta-metaskill already follows, with evidence. Only patterns in use are listed, in the same order as the [source catalog](https://lexler.github.io/augmented-coding-patterns/patterns/). Patterns considered but ruled out are listed at the end.

Companion to the [Anti-patterns audit](anti-patterns.md), which rules on all 13 anti-patterns. Distilled definitions for the patterns cited by skills live in [`docs/reference/augmented-coding-patterns.md`](../reference/augmented-coding-patterns.md).

**Source**: <https://github.com/lexler/augmented-coding-patterns>


## 1. Active Partner

> *Transform the command relationship into two-way dialogue — AI pushes back, flags contradictions, proposes alternatives.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/active-partner/>

**Evidence we already do this:**

| Where                                                           | What                                                                                                          | How it follows the pattern                                    |
|-----------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------|
| `docs/reference/code/review-mode.md` line 49                    | "If you're not sure whether it's real, the rule definition is not precise enough — that's a skill bug to fix" | Pushes back on the instruction instead of silently complying  |
| `docs/reference/code/review-mode.md` line 37-49                 | "No borderline category — emit or suppress, never hedge"                                                      | Forces a position instead of compliance with ambiguity        |
| `skills/setup/SKILL.md` Step 3, `skills/review/SKILL.md` Step 1 | `ask_user_question` when language is undetermined                                                             | Asks instead of guessing                                      |
| `skills/patterns/SKILL.md` "Classes that must be suppressed"    | Explicit suppression with stated reasoning                                                                    | Flags contradictions rather than parroting the scanner signal |


## 2. Background Agent

> *Delegate standalone tasks to background agents running in parallel while the main thread stays focused.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/background-agent/>

**Evidence we already do this:**

| Where                           | What                                                                                      | How it follows the pattern                                           |
|---------------------------------|-------------------------------------------------------------------------------------------|----------------------------------------------------------------------|
| `skills/review/SKILL.md` Step 4 | One subagent per command, all in parallel as background subagents (`is_background: true`) | Each review area is a standalone, well-sized task with a clear scope |
| `skills/review/SKILL.md` Step 5 | Orchestrator only confirms completion and collects the grade                              | The main thread stays clean; agents work asynchronously              |
| Subagent contract               | Each subagent writes its own report file and returns a one-line confirmation              | Hands back only the result, not the working context                  |


## 3. Chain of Small Steps

> *Break complex goals into small, focused, verifiable steps — each verified before building on it.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/chain-of-small-steps/>

**Evidence we already do this:**

| Where                                                   | What                                                                         | How it follows the pattern                                                        |
|---------------------------------------------------------|------------------------------------------------------------------------------|-----------------------------------------------------------------------------------|
| `docs/reference/code/scripts-first-protocol.md`         | Phase A (batch scripts) → Phase B (mechanical assembly) → Phase C (judgment) | Each phase is small and verifiable; B builds on A's cache, C builds on B's report |
| `docs/reference/code/scripts-first-protocol.md` Phase B | "No source file reads in this phase"                                         | Phase B is verifiable precisely because it is mechanical                          |
| Setup guard (`skills/setup/SKILL.md`)                   | Runs before any subcommand if `settings.json` is missing                     | Configuration is a completed step before review begins                            |


## 4. Constrained Tests

> *Design tests so that coverage becomes a reliable quality metric — make it impossible to write tests without assertions.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/constrained-tests/>

**Evidence we already do this:**

| Where                                                   | What                                                                | How it follows the pattern                                             |
|---------------------------------------------------------|---------------------------------------------------------------------|------------------------------------------------------------------------|
| `docs/explanation/code/false-positive-prevention.md` §2 | Coverage cross-check: `pytest --cov`, downgrade if coverage >50%    | Coverage is trusted only as a measured signal, with a stated threshold |
| `docs/reference/code/review-mode.md` line 27-28         | Auto-fixable diagnostics classified by the tool's own fix indicator | The metric comes from the tool, not from judgment                      |
| `skills/patterns/SKILL.md` (test_structure scanner use) | Five structural tables distinguish naming/mirroring from coverage   | Structural checks separated from behavioral checks                     |


## 5. Context Management

> *Treat context as a scarce, degrading resource that requires active management.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/context-management/>

**Evidence we already do this:**

| Where                                                   | What                                                    | How it follows the pattern                                |
|---------------------------------------------------------|---------------------------------------------------------|-----------------------------------------------------------|
| `skills/review/SKILL.md` Step 3.6                       | `cache/_context.md` deduplicates shared context         | Copied once so subagents don't each re-read settings.json |
| `docs/reference/code/scripts-first-protocol.md` line 73 | Judgment-rules digest "~30 lines — only the criteria"   | Full docs never loaded into review context                |
| `skills/patterns/SKILL.md` line 57                      | "MUST consult the relevant sections" — not read in full | Context is appended deliberately, section by section      |
| `skills/review/SKILL.md` Step 2                         | Fresh timestamped run folder per review                 | Reset: every review starts with a clean context           |


## 6. External Context

> *Move a distinct piece of work into its own agent — it runs in a separate context and hands back only the result.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/external-context/>

**Evidence we already do this:**

| Where                           | What                                                              | How it follows the pattern                                   |
|---------------------------------|-------------------------------------------------------------------|--------------------------------------------------------------|
| `skills/review/SKILL.md` Step 4 | Each subagent runs in its own context, writes its own report      | The sub-task's noise never enters the orchestrator's context |
| `skills/review/SKILL.md` Step 5 | Orchestrator collects grades from one-line confirmations          | Like a teammate reporting a summary, not their whole day     |
| Run folder `cache/`             | Script outputs persisted to files instead of held in conversation | Intermediate state lives outside the context window          |


## 7. Feedback Loop

> *Give AI a clear success signal and permission to iterate autonomously until the goal is reached.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/feedback-loop/>

**Evidence we already do this:**

| Where                                    | What                                                        | How it follows the pattern                                      |
|------------------------------------------|-------------------------------------------------------------|-----------------------------------------------------------------|
| `skills/review/SKILL.md` Step 6          | Previous review comparison: ✅ Done / ⚠️ Partial / ❌ Not done | A clear success signal for each carried-forward finding         |
| `skills/review/SKILL.md` Step 7          | "Trend vs previous review" subsection in SUMMARY.md         | The signal is measured across runs                              |
| `skills/review/SKILL.md` Step 5 line 240 | "If a subagent fails or times out, note it and continue"    | Iteration is bounded — failure is recorded, not retried blindly |


## 8. Focused Agent

> *An agent with a narrow scope follows ground rules more reliably than one juggling many responsibilities.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/focused-agent/>

**Evidence we already do this — this is the core architecture:**

| Where                                           | What                                     | How it follows the pattern                                                    |
|-------------------------------------------------|------------------------------------------|-------------------------------------------------------------------------------|
| `SKILL.md` Dispatch section                     | Meta-skill routes to focused subcommands | The meta-skill never does the review itself                                   |
| `skills/review/SKILL.md` Step 4                 | One subagent per review area             | A subagent reviewing code style doesn't also think about docs                 |
| `docs/reference/code/scripts-first-protocol.md` | Per-subcommand script table              | Each subagent runs only the scripts listed for its subcommand                 |
| `skills/patterns/SKILL.md` line 68-75           | "Classes that must be suppressed"        | The agent is told what NOT to report — the scope is narrow in both directions |


## 9. Ground Rules

> *Essential knowledge auto-loaded in every session — stated once, always in context.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/ground-rules/>

**Evidence we already do this:**

| Where                           | What                                                                                                | How it follows the pattern                                      |
|---------------------------------|-----------------------------------------------------------------------------------------------------|-----------------------------------------------------------------|
| `SKILL.md` line 40              | "Sub-skills link back to rules and only narrow behavior — they never override or restate the rules" | Rules are stated once and always in context when the skill runs |
| `skills/review/SKILL.md` Step 2 | Reads `_context.md` which inlines settings and ADR directives                                       | Ground rules are loaded into context, not paraphrased           |
| `settings.json`                 | Project-level configuration auto-read by every subcommand                                           | Project ground truth lives in one place                         |


## 10. Happy to Delete

> *Treat AI-generated code as disposable exploration — revert freely, start fresh with lessons learned.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/happy-to-delete/>

**Evidence we already do this:**

| Where                                    | What                                      | How it follows the pattern                                    |
|------------------------------------------|-------------------------------------------|---------------------------------------------------------------|
| `skills/review/SKILL.md` Step 2          | Each run creates a new timestamped folder | Every review is disposable — no pressure to salvage a bad run |
| Setup Step 2                             | Reports in the global `~/.gitignore`      | Run artifacts are temporary by design                         |
| `skills/review/SKILL.md` Step 5 line 240 | Failed subagent: note it and continue     | Nothing accumulates that needs to be preserved at all costs   |


## 11. Learning Loop

> *Make capture a ritual — every session leaves behind a mechanism the next one runs on.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/learning-loop/>

**Evidence we already do this — in the smallest useful form:**

| Where                                                         | What                                                                               | How it follows the pattern                                               |
|---------------------------------------------------------------|------------------------------------------------------------------------------------|--------------------------------------------------------------------------|
| `docs/reference/code/review-mode.md` line 49                  | Skill-bug rule: an imprecise rule is recorded in the report, not silently absorbed | The learning is captured at the moment it is discovered                  |
| Issue link in the report                                      | `https://github.com/Zolletta/zolletta-metaskill/issues/new`                        | The learning routes to a durable store the next run's maintainers act on |
| "The review surfaces the bug; filing it is the reader's call" | The agent proposes, the human decides                                              | Matches the pattern's "you approve the routing"                          |


## 12. Noise Cancellation

> *AI is verbose by default — explicitly strip filler and compress to essence.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/noise-cancellation/>

**Evidence we already do this:**

| Where                                                      | What                                       | How it follows the pattern                                  |
|------------------------------------------------------------|--------------------------------------------|-------------------------------------------------------------|
| `docs/explanation/code/general-principles.md` line 270-279 | "Do Not Overcomplicate Responses"          | "Report each finding once, with the minimum context needed" |
| `docs/explanation/code/false-positive-prevention.md` §5    | Drift grouped by sub-tree                  | 47 identical findings become 1 actionable one               |
| `docs/reference/code/review-mode.md` line 27-28            | Auto-fixable issues are informational only | Trivial noise never inflates the report or the grade        |
| `docs/reference/code/review-mode.md` line 39-49            | "Never hedge"                              | Filler words are structurally excluded                      |


## 13. Offload Deterministic

> *Don't ask AI to do deterministic work — have it write code that does it, then run the code.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/offload-deterministic/>

**Evidence we already do this — this is the scripts-first protocol:**

| Where                                                     | What                                                                           | How it follows the pattern                                     |
|-----------------------------------------------------------|--------------------------------------------------------------------------------|----------------------------------------------------------------|
| `docs/reference/code/scripts-first-protocol.md` Principle | "Scripts produce deterministic findings. The LLM consumes their cached output" | The LLM is never asked to count, parse, or repeat              |
| Phase B                                                   | Scanner tables copied verbatim from cache into the report                      | Deterministic output is relayed, not regenerated               |
| Anti-patterns section                                     | "Re-deriving a finding the scanner already emits" is forbidden                 | The code does the deterministic work; the LLM never re-does it |
| Two-bucket classification                                 | Auto-fixable vs finding from the tool's own fix indicator                      | Even the classification is mechanical                          |


## 14. Reference Docs

> *On-demand knowledge documents — pulled in only when the current task needs them.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/reference-docs/>

**Evidence we already do this:**

| Where                                         | What                                                             | How it follows the pattern                                 |
|-----------------------------------------------|------------------------------------------------------------------|------------------------------------------------------------|
| `skills/patterns/SKILL.md` Reference Files    | ★ mandatory files consulted section-by-section; others on demand | Knowledge is pulled in when relevant, never front-loaded   |
| `docs/reference/augmented-coding-patterns.md` | Distilled pattern definitions as a local cache                   | Skills cite by name; the doc is loaded only when needed    |
| `docs/reference/code/scripts.md`              | Full script reference consulted per subcommand                   | Same shape: one reference per need, not one for everything |


## 15. Reverse Direction

> *Present the problem, not your solution — let AI's breadth reveal approaches you haven't considered.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/reverse-direction/>

**Evidence we already do this:**

| Where                                           | What                                                             | How it follows the pattern                                           |
|-------------------------------------------------|------------------------------------------------------------------|----------------------------------------------------------------------|
| `skills/help/SKILL.md`                          | Fixed subcommand scopes describe what to check, not what to find | "Review all source code in src/…" — the problem, not a preconception |
| `docs/reference/code/scripts-first-protocol.md` | Scanners scan everything                                         | The user can't inject "check only UserService"                       |
| `skills/patterns/SKILL.md` line 60-66           | Reason-to-change lists ALL reasons, not just the scanner's       | The test is open-ended, not confirmatory                             |


## 16. Shared Canvas

> *Use markdown files as a shared canvas where humans and AI collaborate on specs, docs, and plans.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/shared-canvas/>

**Evidence we already do this:**

| Where                             | What                                                 | How it follows the pattern                                       |
|-----------------------------------|------------------------------------------------------|------------------------------------------------------------------|
| `skills/review/SKILL.md` Step 7-8 | SUMMARY.md + TODO.md designed for team consumption   | An executive overview and an action list both humans and AI read |
| Report structure                  | Each finding links to the detailed specialist report | Linkable, shareable artifacts — point at a specific finding      |
| Report format                     | Standard markdown, readable in any tool              | No platform lock-in; the canvas is the file system               |


## 17. Slice for Review

> *Let the agent deliver large work, then split it into small, coherent, independently reviewable units before human review.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/slice-for-review/>

**Evidence we already do this:**

| Where                           | What                                                     | How it follows the pattern                           |
|---------------------------------|----------------------------------------------------------|------------------------------------------------------|
| `skills/review/SKILL.md` Step 4 | One report per subcommand                                | Each review area is an independently reviewable unit |
| Step 7-8                        | SUMMARY (overview) + TODO (actions) + specialist reports | The large work is split by how it will be consumed   |
| `skills/review/SKILL.md` Step 8 | TODO items link to the relevant specialist report        | Drill-down from the slice to the detail              |


## 18. Text Native

> *Stay in text — editable, version-controlled, shared by human and AI alike.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/text-native/>

**Evidence we already do this:**

| Where            | What                                           | How it follows the pattern                          |
|------------------|------------------------------------------------|-----------------------------------------------------|
| Run folder       | Reports, cache, and settings are all text      | Everything is grep-able, diff-able, and editable    |
| `settings.json`  | Single configuration source as structured text | Project ground truth in a version-controllable file |
| Report templates | Markdown templates with fixed structure        | The output contract is itself text                  |


## 19. Smart Plan, Cheap Execution

> *Use a strong model for the hard planning step and a cheaper one for the mechanical execution.*
>
> Source: <https://lexler.github.io/augmented-coding-patterns/patterns/smart-plan-cheap-execution/>

**Evidence we already do this:**

| Where                           | What                                                                                             | How it follows the pattern                                                                                                                       |
|---------------------------------|--------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------|
| `settings.json`                 | `subcommands` object with one entry per subcommand, each containing a `model` field              | The user names a harness-specific model per subcommand; the skill never hardcodes one — the config channel is the way to "tell the orchestrator" |
| `skills/review/SKILL.md` Step 4 | Orchestrator reads `subcommands.<name>.model` and passes it to each `run_subagent` when non-null | Each review subagent inherits its configured model; the orchestrator itself stays on the harness default                                         |
| Opt-in by design                | `null` means behavior is unchanged                                                               | The pattern is available to users who want it, invisible to those who don't                                                                      |

All six `subcommands` entries are consumed by the review orchestrator — no standalone subagent has an independent model path.

**Scope of adoption.** The per-subcommand model passthrough is implemented; the per-phase split is not. Each subagent interleaves mechanical assembly (Phase B) with judgment (Phase C) in a single pass, so the model choice is per-subagent, not per-phase — splitting phases across different-model subagents would break one-subagent-per-command and double the launch count, and is deliberately not proposed. The user can set a strong model for judgment-heavy subagents (`patterns`, `documentor`) and a cheap one for mechanical ones (`*-code-style`, `*-testing-style`), or leave all at `null`.

## Patterns ruled out

- [Surface Change Attractors](https://lexler.github.io/augmented-coding-patterns/patterns/surface-change-attractors/) — Out of scope: it predicts *maintenance risk* (where debt accumulates over time), not *current code quality* (structural problems right now). The reason-to-change test is hypothetical ("what *could* require editing this class"), not historical — the two signals diverge. A cohesive class that changes often passes the test yet would be flagged; a class with five responsibilities that never changes fails the test yet wouldn't appear.
- [Parallel Implementations](https://lexler.github.io/augmented-coding-patterns/patterns/parallel-implementations/) - Determinism is the product — two reviews of the same code should yield the same results; comparing runs measures noise, not signal ([Sunk Cost](anti-patterns.md#11-sunk-cost))
- [Take All Paths](https://lexler.github.io/augmented-coding-patterns/patterns/take-all-paths/) - Exploring multiple approaches adds non-determinism where the design eliminates it ([Sunk Cost](anti-patterns.md#11-sunk-cost))
- [Playgrounds](https://lexler.github.io/augmented-coding-patterns/patterns/playgrounds/) - Reviews are static analysis by design; runtime verification belongs to tests and CI ([Perfect Recall Fallacy](anti-patterns.md#9-perfect-recall-fallacy))
- [Approved Logs](https://lexler.github.io/augmented-coding-patterns/patterns/approved-logs/) - The suppression log — accepting a risk is the team's decision, not the reviewer's ([AI Isolation](anti-patterns.md#1-ai-isolation))
- [Overnight Batch](https://lexler.github.io/augmented-coding-patterns/patterns/overnight-batch/) - No CI by design — the review runs on demand
- [Habit Hooks](https://lexler.github.io/augmented-coding-patterns/patterns/habit-hooks/) - Review-as-you-write; the review is on demand, not in the authoring loop
- [Orchestrator](https://lexler.github.io/augmented-coding-patterns/patterns/orchestrator/) - Integrates code changes into main — the review orchestrator is read-only report aggregation
- [Poor Person's Skill](https://lexler.github.io/augmented-coding-patterns/patterns/poor-persons-skill/) - The substitute for having no skill file; Zolletta-metaskill has real ones
- [Canary in the Code Mine](https://lexler.github.io/augmented-coding-patterns/patterns/canary-in-the-code-mine/) - A during-authoring signal — the AI struggling as it writes — not a review mechanism

## Subsumed Patterns — delivered by a pattern already in use

- [Chunking](https://lexler.github.io/augmented-coding-patterns/patterns/chunking/) - Chain of Small Steps + Slice for Review already slice the work and the reports
- [Phased Delivery](https://lexler.github.io/augmented-coding-patterns/patterns/phased-delivery/) - The three-phase protocol delivers in verifiable phases
- [Knowledge Document](https://lexler.github.io/augmented-coding-patterns/patterns/knowledge-document/) - The generic base — Ground Rules (always loaded) and Reference Docs (on demand) are its two loading strategies
- [Knowledge Composition](https://lexler.github.io/augmented-coding-patterns/patterns/knowledge-composition/) - The judgment-rules digest composes multiple sources into one ~30-line context
- [Refinement Loop](https://lexler.github.io/augmented-coding-patterns/patterns/refinement-loop/) - Affirmed in the [audit](anti-patterns.md#8-obsess-over-rules): inline FP suppression before emission + previous-review comparison across runs
- [Show the Agent, Let it Repeat/Automate](https://lexler.github.io/augmented-coding-patterns/patterns/show-the-agent-let-it-repeat-automate/) - The skills themselves are the automation of shown processes
- [ROSE Feedback](https://lexler.github.io/augmented-coding-patterns/patterns/rose-feedback/) - The finding structure — severity, file/line evidence, suggested fix — is ROSE-shaped
- [Feedback Flip](https://lexler.github.io/augmented-coding-patterns/patterns/feedback-flip/) - The review orchestrator is the evaluating half of the flip — each subagent finds problems; returning the critique is the author's workflow
- [Decision Guards](https://lexler.github.io/augmented-coding-patterns/patterns/decision-guards/) - ADR directives are the review-side equivalent — decided tradeoffs are respected; inline markers are the authoring-side variant
- [Coerce to Interface](https://lexler.github.io/augmented-coding-patterns/patterns/coerce-to-interface/) - Scanner `--json` output and the tool's own fix indicator — enforcement by mechanism, not instruction
- [Reminders](https://lexler.github.io/augmented-coding-patterns/patterns/reminders/) - Ground Rules auto-load — the durable solution recurring reminders approximate

## Not applicable Patterns

- Authoring-time (patterns for writing code, not reviewing it), like: [Borrow Behaviors](https://lexler.github.io/augmented-coding-patterns/patterns/borrow-behaviors/), [Cast Wide](https://lexler.github.io/augmented-coding-patterns/patterns/cast-wide/), [Softest Prototype](https://lexler.github.io/augmented-coding-patterns/patterns/softest-prototype/), [Knowledge Checkpoint](https://lexler.github.io/augmented-coding-patterns/patterns/knowledge-checkpoint/), [JIT Docs](https://lexler.github.io/augmented-coding-patterns/patterns/jit-docs/), [Approved Scenarios](https://lexler.github.io/augmented-coding-patterns/patterns/approved-scenarios/), [Mind Dump](https://lexler.github.io/augmented-coding-patterns/patterns/mind-dump/), [Extract Knowledge](https://lexler.github.io/augmented-coding-patterns/patterns/extract-knowledge/) (the review's slice runs through the Learning Loop)
- User- or harness-side (not the skill's domain), like: [Advisor Strategy](https://lexler.github.io/augmented-coding-patterns/patterns/advisor-strategy/) (model routing), [Hooks](https://lexler.github.io/augmented-coding-patterns/patterns/hooks/), [Contextual Prompts](https://lexler.github.io/augmented-coding-patterns/patterns/contextual-prompts/), [Context Markers](https://lexler.github.io/augmented-coding-patterns/patterns/context-markers/), [Speak to Me](https://lexler.github.io/augmented-coding-patterns/patterns/speak-to-me/), [Polyglot AI](https://lexler.github.io/augmented-coding-patterns/patterns/polyglot-ai/) (modality choice — Text Native is the deliberate opposite), [Point the Target](https://lexler.github.io/augmented-coding-patterns/patterns/point-the-target/) (prompt-authoring technique)
- Interactive workflows (the review is batch, not conversational), like: [Check Alignment](https://lexler.github.io/augmented-coding-patterns/patterns/check-alignment/)
- Different domain or premise: [AI First Responder](https://lexler.github.io/augmented-coding-patterns/patterns/ai-first-responder/) (incident response), [Memory Grooming](https://lexler.github.io/augmented-coding-patterns/patterns/memory-grooming/) (no persistent memory by design — fresh runs), [Semantic Anchors](https://lexler.github.io/augmented-coding-patterns/patterns/semantic-anchors/), [Semantic Zoom](https://lexler.github.io/augmented-coding-patterns/patterns/semantic-zoom/), [Diagrams as Code](https://lexler.github.io/augmented-coding-patterns/patterns/diagrams-as-code/) (the reviewer reads code; it does not annotate or diagram it), [Yak Shave Delegation](https://lexler.github.io/augmented-coding-patterns/patterns/yak-shave-delegation/) (subagents are scoped, no tangents to delegate), [You Do It](https://lexler.github.io/augmented-coding-patterns/patterns/you-do-it/) (the premise of skills, too generic to claim separately)
