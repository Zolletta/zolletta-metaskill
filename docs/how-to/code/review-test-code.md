---
audience: human, ai
status: stable
skills: [python-*, review]
---

# Review test code

> **Language-agnostic**: this guide covers conventions that apply across all supported languages. Language-specific tooling details (e.g. Python's pytest, coverage) are in the language-specific guides.

Review test suites for isolation, naming, coverage gaps, mocking patterns, fixture design, and AAA structure. This guide covers the general rules that apply to all languages; language-specific guides narrow these for their tooling.

## Prerequisites

- A project that has been set up with `/zolletta-metaskill setup`

## What the review checks

- **Test isolation** — no shared mutable state; fixtures with appropriate scopes
- **Test naming** — descriptive pattern (`test_<unit>_<scenario>_<expected_outcome>`)
- **Coverage gaps** — runs coverage and checks if code is actually exercised, never flags based on grep alone
- **Mocking patterns** — traces call chains to distinguish real instances from full mocks
- **Fixture design** — narrowest scope, no state leaking between tests
- **AAA structure** — Arrange-Act-Assert; mixed arrangement/assertion flagged

## Coverage gap detection procedure

Coverage gap detection is the most involved part of the review because a class with zero direct references in test files may still be well-covered through indirect calls. The review follows a strict four-step procedure:

### Step 1 — Run coverage and identify structurally missing files

Run the test runner with coverage, then run the structural test scanner to get the "Missing tests" table. Files that appear in this table are candidates — but structural absence does not mean zero coverage.

### Step 2 — Check indirect coverage for each candidate

For each structurally missing file, search all test files for class name references. If any test file instantiates the class or calls its methods (even indirectly through a caller), the file has indirect coverage. Check whether callers use real instances or full mocks: a full mock means the class is NOT covered, while a real instance with only dependencies mocked means the class IS covered.

### Step 3 — Only flag as a gap if coverage is genuinely low

Report a coverage gap only when all three conditions are true: coverage is below the gap threshold (default `50`), there are no direct test references, and all callers are mocked in tests (no real instances). If any of these conditions is false, the class has adequate coverage and is not flagged.

### Step 4 — For genuine gaps, check callers' test style

When a genuine gap is found, check whether the caller's tests mock the class or use a real instance, because that determines the recommended fix. If callers mock the class entirely, recommend creating a direct unit test file for the class itself. If callers use real instances but do not exercise all branches, recommend adding edge-case tests to the existing caller tests.

## Scope boundary with the patterns skill

The `patterns` skill runs the structural test scanner, which produces a "Missing tests" table — a structural check that reports when no test file exists for a given source module. That structural finding is owned by `patterns`. The testing-style skill owns coverage analysis only: whether code is actually exercised by tests, not whether a matching test file exists. The structural check is not duplicated. If the structural scanner already flagged a file as structurally missing a test, reference that finding but focus on whether the code is covered through indirect calls or integration tests.

## Configurable rule toggles

The review reads its configurable rules from the `settings.json` file. The available settings are:

| Key                               | Type            | Default | Description                                                     |
|-----------------------------------|-----------------|---------|-----------------------------------------------------------------|
| `coverage_gap_threshold`          | integer (0–100) | `50`    | Module coverage below this percentage is a candidate gap        |
| `coverage_well_covered_threshold` | integer (0–100) | `80`    | Module coverage above this percentage is never flagged as a gap |
| `check_test_naming`               | boolean         | `true`  | When `true`, enforce the test naming convention                 |

The remaining rules — AAA pattern, test isolation, mandatory coverage gap detection, and the scope boundary with `patterns` — are always-on and cannot be disabled.

## Review mode (read-only)

Follows [review mode](../../reference/code/review-mode.md) — read-only, two-bucket classification, no fixes applied.

## See also

- [Review Python tests](python/review-python-tests.md) — Python-specific tooling and configuration
- [Review code style](review-code-style.md) — general code style review guide
- [Review mode](../../reference/code/review-mode.md) — shared rules for read-only reviews
- [Settings schema](../../reference/settings-schema.md) — all configuration options
