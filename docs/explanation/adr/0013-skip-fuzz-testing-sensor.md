# ADR-0013: Do not add a fuzz testing sensor

## Status

Accepted

## Context

Fuzz testing feeds random or invalid input to code to find crashes, panics, or security vulnerabilities. Tools like [Atheris](https://github.com/google/atheris) (Python, Google) and python-afl exist for Python. We evaluated whether Zolletta-metaskill should add a fuzz testing sensor.

## Decision

We do **not** add a fuzz testing sensor to Zolletta-metaskill.

Fuzz testing does not fit the "run during review, parse output, report findings" model that Zolletta-metaskill uses for its sensors:

1. **Not zero-config** — fuzzing requires writing fuzz targets (functions that accept fuzzer-generated input), specifying time budgets, and choosing what to fuzz. This is project-specific configuration, not something a review skill can do automatically.
2. **Not a review-time tool** — fuzzers run for minutes to hours, not seconds. They are not suitable for in-session or review-time execution.
3. **Output is crash reports** — unstructured crash logs, not structured findings that can be mapped to source locations and packaged in a review report.
4. **Security-focused, not maintainability-focused** — fuzzing finds crashes and vulnerabilities, not test quality gaps or maintainability issues. Zolletta-metaskill is a maintainability review tool, not a security audit tool.
5. **No PHP equivalent** — there is no widely adopted fuzz testing framework for PHP, making a cross-language integration impossible.

## Consequences

**Positive:**

- No sensor that requires project-specific configuration, runs too slowly for review-time use, and produces unstructured output.
- No false expectation that Zolletta-metaskill is a security audit tool.

**Negative:**

- Crash-prone edge cases that fuzzing would find are not covered. This is accepted — fuzzing is a specialized security activity, not a maintainability review concern.

**Neutral:**

- The mutation testing sensor (#47) covers the related concern of "tests don't catch realistic bugs" computationally, which is the maintainability-relevant subset.
