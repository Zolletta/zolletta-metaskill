---
audience: ai, human
status: stable
skills: [review]
description: "Sensor adoption criteria: zero-config, bounded review-time cost, structured-output, maintainability-primary."
---

# ADR-0007: Sensor and tool adoption criteria

## Status

Accepted

## Context

The review pipeline integrates external tools (ruff, mypy, vulture, phpunit, mutmut, …). Not every proposed tool belongs — three evaluation records (former ADR-0011–ADR-0013, originals in git history) rejected a dependency inspector, a property-based testing sensor, and a fuzz sensor, each for the same underlying reason. This ADR states that reason as a standing rule so future proposals are decided by criteria, not re-litigation.

## Decision

A tool joins the review pipeline only if it is zero-config, bounded in review-time cost, structured-output, maintainability-primary.

The criteria:

- **Zero-config.** The tool produces findings on any project with sensible defaults and no authored artifacts. Tools requiring the project to pre-declare architecture (deptrac, dependency-cruiser, Tach) or write project-specific harnesses (fuzz targets) are excluded — if the config exists, CI already enforces it; if not, a review skill cannot invent boundaries.
- **Bounded review-time cost.** Completes within a review session when gated by availability detection, a `check_*` toggle, and scoped targets — the mutation sensor precedent (`mutation_target: "changed"`). Raw speed is not required; unbounded runs are.
- **Structured output.** Emits parseable findings mappable to source locations. Techniques that only run inside the existing test suite with no standalone report (property-based testing) or emit unstructured logs (fuzzer crash output) are excluded — the former belong as inferential guidance in testing-style skills, not sensors.
- **Maintainability-primary scope.** Finds test-quality, structure, and maintainability issues; security-adjacent findings are covered where integrated tools surface them, but the pipeline is not a dedicated security audit.
- **Cross-language.** Has equivalents across supported languages, or the gap is an accepted, documented asymmetry.
- **Conditional integration.** Setup detects availability only (`{available: bool}`); the skill runs the tool gated by a `check_*` toggle and, where results depend on a green suite, a passing coverage run. A stdlib reporter parses output deterministically; judgment is reserved for fix suggestions.

**Positive exemplar:** mutation testing (mutmut/Infection) satisfies all criteria — zero-config, incremental (`mutation_target: "changed"`), structured survived-mutant output, and a `check_mutation_testing` toggle. It was adopted as former ADR-0014 (original in git history).

## Consequences

**Positive:**

- Future tool proposals are evaluated against a written rule instead of re-debated from scratch.
- No dead-weight sensors that duplicate CI output or cannot run.
- The inferential-vs-computational boundary is explicit: LLM judgment covers what tools can't compute; sensors cover what can.

**Negative:**

- Projects with declared-but-unenforced boundaries get no dependency-rule coverage — accepted as vanishingly rare.
- Language-asymmetric techniques (no PHP property-based/fuzz frameworks) stay uncovered rather than integrated half-way.

**Neutral:**

- The criteria apply to *sensors* (tool → parse → report). Inferential review items (coupling judgment, test-quality suggestions) are unaffected.
- The configuration-free DIP scanner and the ADR directives (ADR-0006) cover the architecture-awareness axis that dependency inspectors would address.
