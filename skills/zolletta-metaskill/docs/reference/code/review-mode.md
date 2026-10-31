---
audience: human, ai
status: stable
skills: [review, python-*]
---

# Review mode (read-only)

Shared rules for every subcommand that runs in a **read-only review context** — i.e. when invoked as part of a `/zolletta-metaskill review` or any other read-only review flow. This file is referenced by `python-code-style`, `python-testing-style`, and any future language-specific review skill.

> **Language-agnostic**: the finding classification and anti-hedging rules apply to all review skills regardless of language. Tool-specific notes (ruff, ty, mypy, vulture) are Python-specific and clearly marked.

## Core rule

**Do NOT apply any fixes.** Run tools in their check-only / no-fix modes. The review reports findings; it does not modify source files.

## Finding classification

Every diagnostic a tool reports is a finding — whether or not the tool could fix it automatically. An unfixed issue is an unfixed issue: fixability changes *how* it is resolved, not whether it counts. Reports carry a **Fixable by tools** column on every finding (`yes` — a mechanical fix exists: formatter, `ruff --fix`, one-line rename; `no` — fixing it requires a judgment call), but both values are **counted toward the grade** at the severity they merit.

## No "borderline" category — emit or suppress, never hedge

There is **no third bucket** between "finding" and "not a finding." Every diagnostic must be classified as either a real finding (emit it, score it) or not a finding (suppress it silently). The following patterns are **forbidden** in review reports:

- **"Borderline" / "low severity and may be an intentional choice"**: if the rule has a documented exception that applies, suppress the finding. If no exception applies, emit it as a finding. Do not emit it and then say "no action required."
- **"No action required unless the team wants strict consistency"**: this is a finding that doesn't know what it is. If the rule is worth enforcing, enforce it. If the rule has an exception, document the exception and suppress. Do not leave the decision to the reader.
- **"Acceptable as-is" in a findings table**: if it's acceptable, it's not a finding. Move it to the informational section or remove it entirely.

**Why this matters**: hedged findings consume triage time without driving any action. A reader who sees "borderline, no action required" must still read the finding, understand it, and decide whether to act — only to arrive at the same conclusion the reviewer already reached. That is pure cost with zero value.

**How to suppress correctly**: if a finding is suppressed because a documented exception applies (e.g. "stdlib concurrency primitive, not a DIP violation" or "enum alias, not a constant"), do not list it in the findings table. Mention it in the manual review checks table with a PASS status and a brief note explaining why the exception applies. Suppressed findings do not count toward the grade.

**How to emit correctly**: if a finding is real, emit it with a severity, a concrete file/line reference, and a specific suggested fix. Do not qualify it with "may be" or "could be considered." If you're not sure whether it's real, the rule definition is not precise enough — that's a skill bug to fix, not a reason to hedge in the report. Make the emit-or-suppress call with your best judgment, then record the skill bug in the report — name the imprecise rule and the case that exposed it — with a link to file it: <https://github.com/Zolletta/zolletta-metaskill/issues/new>. The review surfaces the bug; filing it is the reader's call.

## Grading

**Zero findings means 100.** If every check in scope passed clean, the report's grade is 100 — do not deduct points to signal humility or uncertainty. A grade below 100 must be traceable to a specific finding in the report; an unexplained deduction is the same class of defect as a hedged finding: it costs the reader a triage pass and drives no action.

**The grade is computed, not felt.** Start from the deterministic baseline:

```text
grade = 100 − Σ weight(finding)
  critical −40 · high −15 · medium −5 · low −2
  informational / suppressed findings weigh 0
```

The baseline may be adjusted by **at most ±5 points**, and only when the justification names the finding(s) that justify the deviation and why — e.g. a low finding that is systemic across 40 files (adjust up the deduction), or a high finding already mitigated by a compensating control (adjust down). A deviation without a named finding is a report defect. Severity labels themselves are part of the finding and follow the emit-or-suppress discipline above — do not inflate a severity to make a felt score come out.

## Tool-specific notes (Python)

### ruff

- Run `ruff check` (no `--fix`) for linting.
- Run `ruff format --check` (no formatting) for formatting.
- To fill the **Fixable by tools** column: ruff marks each diagnostic with a fix indicator (e.g. `[F]` or `[*]` for fixable, `[--fix]` for unsafe-fixable). Alternatively, run `ruff check --fix --exit-zero` as a dry-run probe to see what would be fixed, then discard the changes (`git checkout -- .`).
- For format: `ruff format --check` lists the files it would reformat — those are fixable by tools.

### ty

- Run `ty check` (no `--fix`).
- ty reports diagnostics as fixable or not — fill the column accordingly.

### mypy

- Run `mypy` as-is (mypy has no auto-fix mode).
- **All** mypy findings are listed as actual findings (`no` in the column — mypy has no auto-fix mode).

### vulture

- Run `vulture src/ --min-confidence <value>` (value from `python.code_style.vulture_min_confidence` in `settings.json`).
- All vulture findings are listed as low-priority findings (vulture has false positives, especially for dynamically-accessed methods — review each with judgment before flagging).
