---
audience: human, ai
status: stable
skills: [python-testing-patterns, review]
---

# Review test code

> **Language-agnostic**: this guide covers conventions that apply across all supported languages. Language-specific tooling details (e.g. Python's pytest, coverage) are in the language-specific guides.

Review test suites for isolation, naming, coverage gaps, mocking patterns, fixture design, and AAA structure. This guide covers the general rules that apply to all languages; language-specific guides narrow these for their tooling.

## Prerequisites

- A project that has been set up with `/zolletta-metaskill setup`
- The zolletta-metaskill skill installed and available to the agent

## What the review checks

### Test isolation

Tests must be independent, with no shared mutable state between them. Each test should clean up after itself. We use fixtures with appropriate scopes to manage shared resources without coupling tests to each other.

### Test naming

Test functions should follow a descriptive naming pattern so that the name alone tells us what is being tested. In Python, the convention is `test_<unit>_<scenario>_<expected_outcome>`. Good names look like `test_create_user_with_valid_data_returns_user`; bad names look like `test_1` or `test_init`.

### Coverage gaps

The review runs the test runner with coverage and analyses whether code is actually exercised by tests, regardless of whether a dedicated test file exists. This is a mandatory step: we never flag a coverage gap based on grep alone.

### Mocking patterns

When a class has no direct test file, the review traces the call chain to determine whether callers instantiate the class for real (with mocked dependencies) or replace it entirely with a mock. A real instance means the class is indirectly covered; a full mock means it is not.

### Fixture design

Fixtures should use the narrowest scope that makes sense and avoid coupling tests through shared mutable state. The review checks that fixtures are not leaking state between tests.

### AAA structure

Each test follows the Arrange-Act-Assert pattern: set up preconditions, execute the code under test, then verify the results. Tests that mix arrangement and assertion, or that assert before acting, are flagged.

## Coverage gap detection procedure

Coverage gap detection is the most involved part of the review because a class with zero direct references in test files may still be well-covered through indirect calls. The review follows a strict four-step procedure:

### Step 1 — Run coverage and identify structurally missing files

Run the test runner with coverage, then run the structural test scanner to get the "Missing tests" table. Files that appear in this table are candidates — but structural absence does not mean zero coverage.

### Step 2 — Check indirect coverage for each candidate

For each structurally missing file, search all test files for class name references. If any test file instantiates the class or calls its methods (even indirectly through a caller), the file has indirect coverage. Check whether callers use real instances or full mocks: a full mock means the class is NOT covered, while a real instance with only dependencies mocked means the class IS covered.

### Step 3 — Only flag as a gap if coverage is genuinely low

Report a coverage gap only when all three conditions are true: coverage is below the gap threshold (default `50`), there are no direct test references, and all callers are mocked in tests (no real instances). If any of these conditions is false, the class has adequate coverage and we do not flag it.

### Step 4 — For genuine gaps, check callers' test style

When we do find a genuine gap, check whether the caller's tests mock the class or use a real instance, because that determines the recommended fix. If callers mock the class entirely, recommend creating a direct unit test file for the class itself. If callers use real instances but do not exercise all branches, recommend adding edge-case tests to the existing caller tests.

## Scope boundary with the patterns skill

The `patterns` skill runs the structural test scanner, which produces a "Missing tests" table — a structural check that reports when no test file exists for a given source module. That structural finding is owned by `patterns`. The testing-patterns skill owns coverage analysis only: whether code is actually exercised by tests, not whether a matching test file exists. We do not duplicate the structural check. If the structural scanner already flagged a file as structurally missing a test, we reference that finding but focus on whether the code is covered through indirect calls or integration tests.

## Configurable rule toggles

The review reads its configurable rules from the `settings.json` file. The available settings are:

| Key                               | Type            | Default | Description                                                                 |
| -----------------------------------| -----------------| ---------| ---------------------------------------------------------------------------|
| `coverage_gap_threshold`          | integer (0–100) | `50`    | Module coverage below this percentage is a candidate gap                   |
| `coverage_well_covered_threshold` | integer (0–100) | `80`    | Module coverage above this percentage is never flagged as a gap            |
| `check_test_naming`               | boolean         | `true`  | When `true`, enforce the test naming convention                            |

The remaining rules — AAA pattern, test isolation, mandatory coverage gap detection, and the scope boundary with `patterns` — are always-on and cannot be disabled.

## Review mode (read-only)

When the review runs as part of a read-only review, it follows the shared [review mode](../../reference/code/review-mode.md) convention: it classifies diagnostics into auto-fixable (informational) and not auto-fixable (findings) without applying fixes.

## See also

- [Review Python tests](python/review-python-tests.md) — Python-specific tooling and configuration
- [Review code style](review-code-style.md) — general code style review guide
- [Review mode](../../reference/code/review-mode.md) — shared rules for read-only reviews
- [Settings schema](../../reference/settings-schema.md) — all configuration options
