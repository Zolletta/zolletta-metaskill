# ADR-0012: Do not add a property-based testing sensor

## Status

Accepted

## Context

Property-based testing (e.g., [Hypothesis](https://hypothesis.readthedocs.io/) for Python) generates hundreds of test cases automatically from declared properties (e.g., `add(x, y) == add(y, x)` for all integers) rather than requiring specific examples. It is a powerful testing technique that can find edge cases example-based tests miss.

We evaluated whether Zolletta-metaskill should add a property-based testing sensor, similar to the mutation testing sensor (#47).

## Decision

We do **not** add a property-based testing sensor to Zolletta-metaskill.

The fundamental issue is that property-based testing is a **testing style**, not a tool you run separately. Unlike mutation testing — where you run `mutmut run` or `infection run` and parse structured output (survived mutants) — property-based testing frameworks like Hypothesis run as part of the existing pytest suite. There is no standalone command that produces structured findings to parse and package in a report.

The potential value-add would be inferential: "this function has clear algebraic invariants (roundtrip, commutativity, idempotency) but only has example-based tests — recommend property-based tests." This is an LLM judgment call about test code quality, not a computational tool output. It belongs in the testing-style skills as guidance, not as a sensor integration with setup detection, tool running, and output parsing.

Additionally, there is no widely adopted property-based testing framework for PHP, making a cross-language integration asymmetric.

## Consequences

**Positive:**

- No sensor that produces no structured output or that only works for one language.
- The testing-style skills remain focused on computational sensors (coverage, mutation testing) with clear tool-output-to-report pipelines.

**Negative:**

- Functions with clear invariants that would benefit from property-based tests are not flagged. This is accepted — the inferential judgment is already within the scope of the testing-style skills' manual review pass, and can be added as guidance without a sensor integration.

**Neutral:**

- The mutation testing sensor (#47) covers the related concern of "tests don't catch realistic bugs" computationally, which is the higher-value signal.
