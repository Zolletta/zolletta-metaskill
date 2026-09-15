---
audience: ai
status: stable
skills: [review, patterns, documentor, python-*, php-*]
---

# Augmented Coding Patterns — Distilled Reference

Short description definitions of the patterns and anti-patterns from [Augmented Coding Patterns](https://lexler.github.io/augmented-coding-patterns/) that zolletta-metaskill's architecture follows or avoids. Skills cite these by name; this file is the local cache so skills don't depend on an external URL at review time.

**Source**: <https://github.com/lexler/augmented-coding-patterns> (lexler)


## Patterns (followed)

| Pattern                  | Short description                                                                                                         | Link                                                                                        |
|--------------------------|---------------------------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------------------|
| **Focused Agent**        | An agent with a narrow scope follows ground rules more reliably than one juggling many responsibilities.                  | [source](https://lexler.github.io/augmented-coding-patterns/patterns/focused-agent/)        |
| **Chain of Small Steps** | Break complex goals into small, focused, verifiable steps — each verified before building on it.                          | [source](https://lexler.github.io/augmented-coding-patterns/patterns/chain-of-small-steps/) |
| **Feedback Loop**        | Give AI a clear success signal and permission to iterate autonomously until the goal is reached.                          | [source](https://lexler.github.io/augmented-coding-patterns/patterns/feedback-loop/)        |
| **Slice for Review**     | Let the agent deliver large work, then split it into small, coherent, independently reviewable units before human review. | [source](https://lexler.github.io/augmented-coding-patterns/patterns/slice-for-review/)     |
| **Active Partner**       | Transform the command relationship into two-way dialogue — AI pushes back, flags contradictions, proposes alternatives.   | [source](https://lexler.github.io/augmented-coding-patterns/patterns/active-partner/)       |
| **Reverse Direction**    | Present the problem, not your solution — let AI's breadth reveal approaches you haven't considered.                       | [source](https://lexler.github.io/augmented-coding-patterns/patterns/reverse-direction/)    |
| **Happy to Delete**      | Treat AI-generated code as disposable exploration — revert freely, start fresh with lessons learned.                      | [source](https://lexler.github.io/augmented-coding-patterns/patterns/happy-to-delete/)      |
| **Shared Canvas**        | Use markdown files as a shared canvas where humans and AI collaborate on specs, docs, and plans.                          | [source](https://lexler.github.io/augmented-coding-patterns/patterns/shared-canvas/)        |
| **Constrained Tests**    | Design tests so that coverage becomes a reliable quality metric — make it impossible to write tests without assertions.   | [source](https://lexler.github.io/augmented-coding-patterns/patterns/constrained-tests/)    |

## Anti-patterns (avoided)

| Anti-pattern               | Short description                                                                                                   | Link                                                                                               |
|----------------------------|---------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------|
| **Distracted Agent**       | One agent doing everything stays shallow and misses what matters.                                                   | [source](https://lexler.github.io/augmented-coding-patterns/anti-patterns/distracted-agent/)       |
| **Big Chunk Working**      | AI generates sweeping changes that are hard to review and easy to merge with hidden damage.                         | [source](https://lexler.github.io/augmented-coding-patterns/anti-patterns/big-chunk-working/)      |
| **Cognitive Overload**     | Too many open loops, fragmented attention — the team loses a shared picture of what matters.                        | [source](https://lexler.github.io/augmented-coding-patterns/anti-patterns/cognitive-overload/)     |
| **Obsess Over Rules**      | More rules → more ignored rules; context rot degrades output as the ruleset grows.                                  | [source](https://lexler.github.io/augmented-coding-patterns/anti-patterns/obsess-over-rules/)      |
| **Flying Blind**           | Accepting AI-generated code without review — bugs accumulate silently, nobody understands what was built.           | [source](https://lexler.github.io/augmented-coding-patterns/anti-patterns/flying-blind/)           |
| **Unvalidated Leaps**      | Building on unverified assumptions about the code — each wrong step compounds.                                      | [source](https://lexler.github.io/augmented-coding-patterns/anti-patterns/unvalidated-leaps/)      |
| **Perfect Recall Fallacy** | Expecting AI to remember library details from training — give it tools to discover instead.                         | [source](https://lexler.github.io/augmented-coding-patterns/anti-patterns/perfect-recall-fallacy/) |
| **Tell Me a Lie**          | Forced premises make AI fabricate plausible nonsense to meet an arbitrary requirement.                              | [source](https://lexler.github.io/augmented-coding-patterns/anti-patterns/tell-me-a-lie/)          |
| **Answer Injection**       | Putting solutions in questions limits AI to your preconceived approach instead of leveraging its breadth.           | [source](https://lexler.github.io/augmented-coding-patterns/anti-patterns/answer-injection/)       |
| **Silent Misalignment**    | AI complies instead of flagging contradictions — misalignment grows silently as it builds on wrong interpretations. | [source](https://lexler.github.io/augmented-coding-patterns/anti-patterns/silent-misalignment/)    |
| **Sunk Cost**              | Pushing AI past diminishing returns — code gets messier with each iteration.                                        | [source](https://lexler.github.io/augmented-coding-patterns/anti-patterns/sunk-cost/)              |
| **AI Isolation**           | Retreating into solo AI work — less pairing, less shared knowledge, weaker collective ownership.                    | [source](https://lexler.github.io/augmented-coding-patterns/anti-patterns/ai-isolation/)           |
| **AI Slop**                | Using AI output without adding human judgment — if anyone with your prompt gets the same result, it's slop.         | [source](https://lexler.github.io/augmented-coding-patterns/anti-patterns/ai-slop/)                |

## How zolletta-metaskill maps to these patterns

| Skill / mechanism                                     | Follows                             | Avoids                                    |
|-------------------------------------------------------|-------------------------------------|-------------------------------------------|
| Subcommand dispatch (meta-skill → focused subcommand) | Focused Agent                       | Distracted Agent                          |
| One subagent per review area, parallel                | Focused Agent, Chain of Small Steps | Distracted Agent, Big Chunk Working       |
| Scripts-first protocol (Phase A → B → C)              | Chain of Small Steps, Feedback Loop | Unvalidated Leaps                         |
| Separate SUMMARY.md + TODO.md + specialist reports    | Slice for Review                    | Big Chunk Working, Cognitive Overload     |
| `cache/_context.md` (shared context digest)           | —                                   | Cognitive Overload, Obsess Over Rules     |
| "No borderline — emit or suppress, never hedge"       | Active Partner                      | Tell Me a Lie, AI Slop                    |
| "Reason to change" test before God class verdict      | Active Partner                      | Unvalidated Leaps, Perfect Recall Fallacy |
| Coverage cross-check before "missing tests" finding   | —                                   | Unvalidated Leaps                         |
| Review-mode (read-only, no fixes)                     | —                                   | Sunk Cost                                 |
| Fresh timestamped run folder per review               | Happy to Delete                     | Sunk Cost                                 |
| Previous review comparison (carry-forward)            | Feedback Loop                       | Flying Blind                              |
| Team-facing reports in standard markdown              | Shared Canvas                       | AI Isolation                              |
| Deterministic scanner output in reports               | —                                   | AI Slop                                   |
| External review on modified files only                | Slice for Review                    | Flying Blind                              |

Full analysis with evidence and enhancement suggestions: [Anti-patterns audit](../explanation/anti-patterns.md).
