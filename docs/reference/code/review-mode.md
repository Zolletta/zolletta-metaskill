---
audience: human, ai
status: stable
skills: [review, python-code-style, python-testing-patterns]
---

# Review mode (read-only)

Shared rules for every subcommand that runs in a **read-only review context** — i.e. when invoked as part of a `/zolletta-metaskill review` or any other read-only review flow. This file is referenced by `python-code-style`, `python-testing-patterns`, and any future language-specific review skill.

> **Language-agnostic**: the two-bucket classification and anti-hedging rules apply to all review skills regardless of language. Tool-specific notes (ruff, ty, mypy, vulture) are Python-specific and clearly marked.

## Core rule

**Do NOT apply any fixes.** Run tools in their check-only / no-fix modes. The review reports findings; it does not modify source files.

## Two-bucket classification

Every diagnostic reported by a tool must be classified into one of two buckets:

### Bucket 1 — Auto-fixable (informational)

Issues that the tool could fix automatically (the tool reports the diagnostic as fixable, or a formatter would reformat the file). These are:

- Listed in a separate **"Auto-fixable (informational)"** section of the report.
- **Not** counted toward the grade.
- **Not** listed as findings.

### Bucket 2 — Not auto-fixable (findings)

Issues that require human judgment to fix. These are:

- Listed as actual findings with severity, impact, and a suggested fix.
- **Counted toward the grade.**
- The only issues that affect the review score.

## No "borderline" category — emit or suppress, never hedge

There is **no third bucket** between "finding" and "not a finding." Every diagnostic must be classified as either a real finding (emit it, score it) or not a finding (suppress it silently). The following patterns are **forbidden** in review reports:

- **"Borderline" / "low severity and may be an intentional choice"**: if the rule has a documented exception that applies, suppress the finding. If no exception applies, emit it as a finding. Do not emit it and then say "no action required."
- **"No action required unless the team wants strict consistency"**: this is a finding that doesn't know what it is. If the rule is worth enforcing, enforce it. If the rule has an exception, document the exception and suppress. Do not leave the decision to the reader.
- **"Acceptable as-is" in a findings table**: if it's acceptable, it's not a finding. Move it to the informational section or remove it entirely.

**Why this matters**: hedged findings consume triage time without driving any action. A reader who sees "borderline, no action required" must still read the finding, understand it, and decide whether to act — only to arrive at the same conclusion the reviewer already reached. That is pure cost with zero value.

**How to suppress correctly**: if a finding is suppressed because a documented exception applies (e.g. "stdlib concurrency primitive, not a DIP violation" or "enum alias, not a constant"), do not list it in the findings table. Mention it in the manual review checks table with a PASS status and a brief note explaining why the exception applies. Suppressed findings do not count toward the grade.

**How to emit correctly**: if a finding is real, emit it with a severity, a concrete file/line reference, and a specific suggested fix. Do not qualify it with "may be" or "could be considered." If you're not sure whether it's real, the rule definition is not precise enough — that's a skill bug to fix, not a reason to hedge in the report.

## Tool-specific notes (Python)

### ruff

- Run `ruff check` (no `--fix`) for linting.
- Run `ruff format --check` (no formatting) for formatting.
- To distinguish the two buckets: ruff marks each diagnostic with a fix indicator (e.g. `[F]` or `[*]` for fixable, `[--fix]` for unsafe-fixable). Alternatively, run `ruff check --fix --exit-zero` as a dry-run probe to see what would be fixed, then discard the changes (`git checkout -- .`).
- For format: `ruff format --check` lists the files it would reformat — those are auto-fixable (informational).

### ty

- Run `ty check` (no `--fix`).
- ty reports diagnostics as fixable or not — classify accordingly.
- Auto-fixable ty diagnostics → informational. Not auto-fixable → findings.

### mypy

- Run `mypy` as-is (mypy has no auto-fix mode).
- **All** mypy findings are listed as actual findings and scored normally — there is no "auto-fixable" bucket for mypy.

### vulture

- Run `vulture src/ --min-confidence <value>` (value from `python.code_style.vulture_min_confidence` in `settings.json`).
- All vulture findings are listed as low-priority findings (vulture has false positives, especially for dynamically-accessed methods — review each with judgment before flagging).
