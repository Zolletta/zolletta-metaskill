---
audience: human, ai
status: stable
skills: [python-testing-patterns]
---

# How to review Python test code

> **Paths in this document are relative to the Zolletta-MetaSkill project root.**

The `python-testing-patterns` skill reviews Python test suites for isolation, naming, coverage gaps, mocking patterns, fixture design, and AAA structure. This guide walks through what the skill checks, how coverage gap detection works, and how we configure the rules — so we know what to expect when the skill runs as part of a full review or on its own.

## Prerequisites

We need a Python project that has been set up with `/zolletta-metaskill setup`. Setup creates the `.zolletta-metaskill/settings.json` file, which the skill reads to determine tool availability and effective pytest/coverage configuration. Specifically, the skill relies on the `python.tools.*` objects in `settings.json` — each tool has an `available` boolean and, where applicable, its effective configuration extracted from `pyproject.toml` (e.g. `python.tools.pytest` carries `addopts`, `testpaths`, `minversion`). If `settings.json` is missing or the `python` object is `null`, the skill cannot determine whether pytest and coverage are installed and will skip coverage analysis. We recommend running setup first so that the configuration is explicit and the setup guard can detect staleness when `pyproject.toml` changes.

## What the skill checks

The skill evaluates test code across six areas, combining always-on structural rules with configurable thresholds:

- **Test isolation** — tests must be independent, with no shared mutable state between them. Each test should clean up after itself. We use fixtures with appropriate scopes (`function`, `module`, `session`) to manage shared resources without coupling tests to each other.
- **Test naming** — test functions should follow the `test_<unit>_<scenario>_<expected_outcome>` pattern so that the name alone tells us what is being tested. The skill enforces this with the deterministic `src/zolletta_metaskill/python_testing_patterns/scan_test_naming.py` scanner, which counts underscore-separated segments after the `test_` prefix and flags functions with fewer than the minimum (default: 3). Good names look like `test_create_user_with_valid_data_returns_user`; bad names look like `test_1` or `test_init`.
- **Coverage gaps** — the skill runs `pytest --cov` and analyses whether code is actually exercised by tests, regardless of whether a dedicated `test_<module>.py` file exists. This is a mandatory step: we never flag a coverage gap based on grep alone.
- **Mocking patterns** — when a class has no direct test file, the skill traces the call chain to determine whether callers instantiate the class for real (with mocked dependencies) or replace it entirely with a `MagicMock` or `patch`. A real instance means the class is indirectly covered; a full mock means it is not.
- **Fixture design** — fixtures should use the narrowest scope that makes sense and avoid coupling tests through shared mutable state. The skill checks that fixtures are not leaking state between tests.
- **AAA structure** — each test follows the Arrange-Act-Assert pattern: set up preconditions, execute the code under test, then verify the results. Tests that mix arrangement and assertion, or that assert before acting, are flagged.

## Coverage gap detection procedure

Coverage gap detection is the most involved part of the review because a class with zero direct references in test files may still be well-covered through indirect calls. The skill follows a strict four-step procedure:

### Step 1 — Run coverage and identify structurally missing files

The skill runs `pytest --cov` and then runs `src/zolletta_metaskill/shared/scan_tests.py` to get the structural "Missing tests" table. Files that appear in this table are candidates — but structural absence does not mean zero coverage.

### Step 2 — Check indirect coverage for each candidate

For each structurally missing file, the skill searches all test files for class name references. If any test file instantiates the class or calls its methods (even indirectly through a caller), the file has indirect coverage. The skill then checks whether callers use real instances or full mocks: `my_class = MagicMock()` means the class is NOT covered, while `my_class = MyClass(mock_dependency)` means the class IS covered because a real instance is created with only its dependencies mocked.

### Step 3 — Only flag as a gap if coverage is genuinely low

We report a coverage gap only when all three conditions are true: coverage is below `coverage_gap_threshold` (default `50`), there are no direct test references, and all callers are mocked in tests (no real instances). If any of these conditions is false, the class has adequate coverage and we do not flag it.

### Step 4 — For genuine gaps, check callers' test style

When we do find a genuine gap, we check whether the caller's tests mock the class or use a real instance, because that determines the recommended fix. If callers mock the class entirely, we recommend creating a direct unit test file for the class itself. If callers use real instances but do not exercise all branches, we recommend adding edge-case tests to the existing caller tests.

## Scope boundary with the patterns skill

The `patterns` skill runs `src/zolletta_metaskill/shared/scan_tests.py`, which produces a "Missing tests" table — a structural check that reports when no `test_<module>.py` file exists for a given source module. That structural finding is owned by `patterns`. The `python-testing-patterns` skill owns coverage analysis only: whether code is actually exercised by tests, not whether a matching test file exists. We do not duplicate the structural check. If `src/zolletta_metaskill/shared/scan_tests.py` already flagged a file as structurally missing a test, we reference that finding but focus on whether the code is covered through indirect calls or integration tests.

## Configurable rule toggles via settings.json

The skill reads its configurable rules from the `python.testing` object in `settings.json`. Three settings are available:

| Key                               | Type            | Default | Description                                                                                                                                                           |
| --------------------------------- | --------------- | ------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `coverage_gap_threshold`          | integer (0–100) | `50`    | Module coverage below this percentage is a candidate gap (combined with the other two conditions from Step 3)                                                         |
| `coverage_well_covered_threshold` | integer (0–100) | `80`    | Module coverage above this percentage is never flagged as a gap, even with no direct test references                                                                  |
| `check_test_naming`               | boolean         | `true`  | When `true`, the skill runs `src/zolletta_metaskill/python_testing_patterns/scan_test_naming.py` to enforce the `test_<unit>_<scenario>_<expected>` naming convention |

The remaining rules — AAA pattern, test isolation, mandatory coverage gap detection, and the scope boundary with `patterns` — are always-on and cannot be disabled. When the skill runs as part of a read-only review (for example `/zolletta-metaskill review`), it follows the [review mode](../../../reference/code/review-mode.md) convention: it classifies diagnostics into auto-fixable (informational) and not auto-fixable (findings) without applying fixes.

## See also

- [Settings schema](../../../reference/settings-schema.md)
- [Review mode](../../../reference/code/review-mode.md)
- [Scripts reference](../../../reference/code/scripts.md)
- [Review Python style](review-python-style.md)
- [Detect God classes](../detect-god-classes.md)
