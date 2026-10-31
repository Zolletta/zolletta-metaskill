---
audience: human, ai
status: stable
skills: [review, patterns, documentor, python-*, php-*]
---

# Determinism boundary

The design goal of zolletta-metaskill: **two reviews of the same code should yield the same results, more or less.** This page records exactly where that reproducibility holds and where judgment is applied, so readers of a report know what to treat as measurement and what to read as judgment.

The [AI Slop](https://lexler.github.io/augmented-coding-patterns/anti-patterns/ai-slop/) slop test — "could anyone with your prompt get the same result?" — inverts for a review tool. For creative output, reproducibility suggests the output lacks your specific context. For a code review, reproducibility is the product: a review that gives different answers each run is not trustworthy.

## What is deterministic

| Part                            | Mechanism                                                                                              |
|---------------------------------|--------------------------------------------------------------------------------------------------------|
| Scanner findings (Phase A)      | Scripts produce the same output for the same code, every run                                           |
| Cached script output (`cache/`) | The audit-able artifact of what the scripts actually produced                                          |
| Report assembly (Phase B)       | Scanner tables copied verbatim from cache — no LLM rewriting                                           |
| Two-bucket classification       | Auto-fixable vs findings derived from the tool's own fix indicator (ruff `[F]`/`[*]`, ty fixable flag) |
| Drift grouping                  | Generational drift grouped by sub-tree — rule-based, not per-run judgment                              |
| Run structure                   | Timestamped `reports/` + `cache/` layout, always the same shape                                        |

## What is not deterministic

| Part                     | Why                                                                                       |
|--------------------------|-------------------------------------------------------------------------------------------|
| Findings (Phase C)       | LLM judgment on items the scripts explicitly defer — emit/suppress decisions              |
| FP suppression reasoning | "cohesive — not a God class" is a judgment call, constrained by the reason-to-change test |
| Severity assignment      | Judgment by design                                                                        |
| Grade (0-100)            | Judgment by design — two runs may differ by a few points                                  |
| Suggested fixes          | LLM-generated per finding; the developer chooses whether to act                           |

The judgment space is deliberately narrow: the [scripts-first protocol](../../reference/code/scripts-first-protocol.md) marks every judgment item explicitly, and the no-hedge rule, FP suppression, reason-to-change test, and coverage cross-check constrain each one. Judgment is not eliminated — it is bounded.

## Reading a report

- **Scanner tables**: reproducible measurements — identical across runs on the same code. If you want to verify a finding, start here.
- **Findings and grades**: LLM judgment grounded in cached scanner output — expect "more or less" the same results across runs, not byte-identical output.

The boundary is the point: deterministic where measurement is possible, explicit judgment where it is not.
