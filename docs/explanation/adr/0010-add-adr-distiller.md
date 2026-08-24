# ADR-0010: Add ADR distiller for architectural governance

## Status

Accepted

## Context

GenAI has dramatically increased the pace at which code can be produced, making it difficult for traditional oversight patterns to keep pace. Waiting for human oversight puts organizations at a competitive disadvantage and slows innovation. When it is trivial for everyone to deliver code, maintaining architectural cohesion requires combining centralized decision-making with automated, decentralized governance.

Zolletta-metaskill reviews code for style, testing patterns, design patterns, and documentation quality — but it has no awareness of the project's architectural decisions. A team may have written ADRs documenting that they use PostgreSQL, adopt microservices, or require async event communication, but the review subagents never read these decisions. This means code that violates an accepted architectural decision passes review without comment.

The article [Architectural Governance at AI Speed](https://www.infoq.com/articles/architectural-governance-ai-speed/) (InfoQ, 2026) proposes distilling ADRs into machine-enforceable declarations of intent — an `architecture.md` file where each ADR becomes a brief directive that both humans and agents can internalize and apply to code. The conformant path becomes the path of least resistance.

## Decision

We add an ADR distiller to Zolletta-metaskill that:

1. **Detects the ADR folder during setup** — the setup skill scans the project's documentation folder for files matching the Nygard ADR format, using a fast grep presence check followed by a heading-pattern scan. The detected path is stored as a new `documentation.adrs` field in `settings.json` (relative path or `null` if no ADRs found).

2. **Distills Accepted ADRs into `adr-distilled.md`** — during review, the distiller extracts the Decision section from each Accepted ADR and produces a one-line directive with a markdown link to the source ADR. Only Accepted ADRs are included. Proposed, Deprecated, and Superseded ADRs are excluded — the distilled file represents the rules in force.

3. **Keeps the file in sync via an mtime cache** — on every review run, the distiller compares ADR file modification times against a local cache. New, stale (modified), and removed ADRs are detected and the distilled file is updated incrementally. Up-to-date directives (including agent refinements) are preserved.

4. **Informs review subagents as architectural context** — subagents read the distilled directives and use judgment to check whether code aligns with each directive. Binary directives (e.g., "use PostgreSQL") produce findings when violated. Nuanced directives (e.g., "adopt microservices") produce observations. The LLM determines which is which from the directive's content — no crude severity tag system.

5. **No severity tags** — the ADR Status field is used only as a filter (Accepted = in, everything else = out). The directive is just the ADR reference (as a markdown link) and the distilled decision text. No `[Block]`/`[Warn]` mapping is applied.

## Consequences

**Positive:**

- Review subagents gain awareness of the project's architectural decisions, producing more relevant findings.
- The distilled file serves as a quick-reference index of active decisions, useful beyond review — when writing code, onboarding, or auditing.
- The mtime cache makes refreshes incremental and fast — only changed ADRs are re-distilled.
- Agent refinements (concise one-liners) are preserved across refreshes until the source ADR changes.
- The approach is inspired by a well-reasoned article (InfoQ, 2026) with attribution, not invented in isolation.

**Negative:**

- Adds a new `documentation.adrs` field to `settings.json` and a new settings schema entry to maintain.
- Adds new scripts and their test suites to maintain.
- The binary-vs-nuanced judgment is non-deterministic across reviews — the same directive may produce a finding in one review and an observation in another. This is a deliberate tradeoff: the alternative (a severity tag system mapped from Status) conflates acceptance with criticality and produces worse signal.
- Only the Nygard ADR format is detected. Projects using other non-standard formats won't be detected — documented as a known limitation.

**Neutral:**

- The distilled file is committed to the repo (auto-generated but deterministic — no noisy diffs if content hasn't changed).
- The mtime cache is machine-local and gitignored — fresh clones re-distill from scratch, producing identical output.
