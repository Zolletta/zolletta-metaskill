---
name: python-testing-patterns
version: 1.1.0
license: MIT
description: Implement comprehensive testing strategies with pytest, fixtures, mocking, and test-driven development. Use when writing Python tests, setting up test suites, or implementing testing best practices.
---

# Python Testing Patterns

Review skill for Python test code: test isolation, naming, coverage gaps, mocking patterns, fixture design, and AAA structure.

> **Configuration source**: all project-level configuration (tool availability, effective pytest/coverage config) is read from `settings.json` — specifically the `python` and `python_config` objects. Rule toggles are in `python_testing_patterns_rules`. See the parent `SKILL.md` for the setup guard and the shared "Running tools" convention.

> **Review mode**: when this skill is invoked as part of a read-only review (e.g. `/zolletta-metaskill review`), follow the rules in [`../docs/reference/code/review-mode.md`](../docs/reference/code/review-mode.md) — do not apply fixes, classify diagnostics into auto-fixable (informational) vs. not auto-fixable (findings).

## When to Use This Skill

- Writing unit tests for Python code
- Setting up test suites and test infrastructure
- Implementing test-driven development (TDD)
- Creating integration tests for APIs and services
- Mocking external dependencies and services
- Testing async code and concurrent operations
- Testing database operations
- Debugging failing tests

## Coverage gap detection

> **Scope boundary**: the `/zolletta-metaskill patterns` subcommand runs `scan_tests.py` which produces a "Missing tests" table — a **structural** check (no `test_<module>.py` file exists). That is a structural finding owned by `patterns`. This skill owns **coverage gap analysis** using `pytest --cov` — checking whether code is actually exercised by tests, regardless of file naming. Do not duplicate the structural check. If `scan_tests.py` already flagged a file as structurally missing a test, reference that finding but focus on whether the code is actually covered.

When reviewing test coverage, **never rely on grep alone** to determine if a class is tested. A class with zero direct references in test files may still be well-covered through indirect calls. Follow this procedure:

### Step 1 — Run coverage (mandatory)

You **must** run coverage before flagging any coverage gap. Do not skip this step. Follow the shared "Running tools" convention from the parent `SKILL.md` (container/uv detection) to run `pytest --cov`.

The project's `pyproject.toml` may already configure coverage options under `[tool.coverage.run]` and `[tool.pytest.ini_options]`. If so, a plain `pytest --cov` will use those settings — no need to add extra flags.

Read the coverage output. If a module shows coverage **above `coverage_well_covered_threshold`** (from `python_testing_patterns_rules` in `settings.json`, default `80`), it is well-covered — do not flag it as a coverage gap even if there are no direct test references. The code is exercised through integration tests or indirect calls.

### Step 2 — Check for indirect coverage

If a class has no direct test file but coverage is non-zero, trace the call chain:

1. Use `tokensave_callers` (if tokensave is available) to find who calls the class
2. For each caller, check if it is instantiated **for real** (not mocked) in any test
3. If a caller is real (not `MagicMock()` or `patch()`), the class is indirectly covered

**Key distinction**: `ci_linter=MagicMock()` means the class is NOT covered. `ci_linter=CILinter(mock_gitlab_manager)` means the class IS covered (real instance with mocked dependencies).

### Step 3 — Only flag as a gap if coverage is genuinely low

Only report a coverage gap when:
- Coverage is **below `coverage_gap_threshold`** (from `python_testing_patterns_rules`, default `50`) AND
- There are no direct test references AND
- All callers are mocked in tests (no real instances)

If any of these conditions is false, the class has adequate coverage — do not flag it.

### Step 4 — For genuine gaps, check callers' test style

If you find a genuine gap, check whether the caller's tests mock the class or use a real instance. This determines the fix:
- If callers mock the class → recommend a direct unit test file for the class itself
- If callers use real instances but don't exercise all branches → recommend adding edge-case tests

## Review rules

### Always-on rules (cannot be disabled)

| #   | Area      | Name                                                                                                               |
|---|---|---|
| 1   | Structure | AAA pattern (Arrange, Act, Assert)                                                                                 |
| 2   | Isolation | Tests must be independent — no shared state, each test cleans up after itself                                      |
| 3   | Coverage  | Coverage gap detection is mandatory (run `pytest --cov` before flagging any gap)                                   |
| 4   | Scope     | Do not duplicate the structural "missing test file" check from `patterns` — this skill owns coverage analysis only |

### Configurable settings (stored in `settings.json` under `python_testing_patterns_rules`)

| #   | Area     | Name                                                         | Key                               | Default   |
|---|---|---|---|---|
| 5   | Coverage | Coverage gap threshold (below X% = gap)                      | `coverage_gap_threshold`          | `50`      |
| 6   | Coverage | Well-covered threshold (above X% = don't flag)               | `coverage_well_covered_threshold` | `80`      |
| 7   | Naming   | Test naming convention (`test_<unit>_<scenario>_<expected>`) | `check_test_naming`               | `true`    |

## Detailed rule explanations

### #1 — AAA pattern (always-on)

Each test follows the Arrange-Act-Assert structure:
- **Arrange**: set up test data and preconditions
- **Act**: execute the code under test
- **Assert**: verify the results

### #2 — Test isolation (always-on)

Tests must be independent. No shared mutable state between tests. Each test should clean up after itself. Use fixtures with appropriate scopes (`function`, `module`, `session`) to manage shared resources without coupling tests.

### #3 — Coverage gap detection (always-on)

Run `pytest --cov` before flagging any coverage gap. Never rely on grep alone — a class with zero direct test references may be well-covered through indirect calls. Follow the 4-step procedure above.

### #4 — Scope boundary (always-on)

Do not duplicate the structural "missing test file" check from `scan_tests.py` (owned by `patterns`). This skill owns coverage analysis: whether code is actually exercised by tests, not whether a `test_<module>.py` file exists.

### #5 — Coverage gap threshold (configurable: `coverage_gap_threshold`)

Only report a coverage gap when module coverage is below this percentage. The default is `50` — below this, the code is genuinely under-tested. Above it, the code may be indirectly covered through integration tests.

- **Type**: integer (0–100)
- **Default**: `50`

### #6 — Well-covered threshold (configurable: `coverage_well_covered_threshold`)

If a module shows coverage above this percentage, do not flag it as a coverage gap even if there are no direct test references. The code is exercised through integration tests or indirect calls. The default is `80`.

- **Type**: integer (0–100)
- **Default**: `80`

### #7 — Test naming convention (configurable: `check_test_naming`)

Test functions should follow the pattern `test_<unit>_<scenario>_<expected_outcome>`. The name should be descriptive enough to understand what is being tested without reading the body.

- **Default**: `true`
- **Enforcement**: `scan_test_naming.py` from `../src/zolletta_metaskill/python_testing_patterns/` (deterministic). The scanner counts underscore-separated segments after the `test_` prefix and flags functions with fewer than `--min-segments` (default: 3). This replaces manual review, which was non-deterministic and produced different violation counts on each run.

```bash
python3 ../src/zolletta_metaskill/python_testing_patterns/scan_test_naming.py tests/ --min-segments 3
```

**Good names**: `test_create_user_with_valid_data_returns_user`, `test_login_fails_with_invalid_password`
**Bad names**: `test_1`, `test_user`, `test_function`, `test_init`, `test_to_dict`

> The scanner is the single source of truth for this rule. Do not manually flag test names that the scanner doesn't flag — the segment count is the objective criterion. If the team disagrees with the threshold, change `--min-segments` in the skill invocation, not the scanner output.

## Output

When this skill runs a review, it writes its findings to a markdown file using the [report template](assets/report_template.md):

- **Path**: `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/python-testing-patterns.md` (timestamp = run start time, via `date +%Y-%m-%d-%H-%M`)
- **Compound skills** (e.g. `zolletta-metaskill-review`) may override the folder and filename — follow their instructions instead
- **Directory setup**: the `.zolletta-metaskill/` directory and `.gitignore` entry are created by the [setup guard](../SKILL.md#setup-guard) — no manual setup needed
- **Format**: follow the [report template](assets/report_template.md) — grade at the top, coverage summary, coverage gaps table, findings grouped by severity with file/test-symbol/rule/issue/fix columns

## Attribution

This skill is adapted from [python-testing-patterns](https://github.com/wshobson/agents/tree/main/plugins/python-development/skills/python-testing-patterns) by Seth Hobson ([wshobson/agents](https://github.com/wshobson/agents)), licensed under the MIT License. Copyright (c) 2024 Seth Hobson.
