---
name: php-testing-patterns
version: 2.0.0
license: MIT + Commons Clause
description: >
  PHP test code review: PHPUnit test naming, directory mirroring, coverage gap
  detection, mocking with Mockery or PHPUnit mocks, data providers, test doubles,
  and AAA structure. Use when reviewing PHP test code or setting up PHPUnit test suites.
allowed-tools:
  - read
  - grep
  - glob
  - exec
  - edit
  - write
  - mcp_call_tool
  - mcp_list_tools
  - skill
permissions:
  allow:
    - Read
    - Write(.zolletta-metaskill/**)
---

# PHP Testing Patterns

Review skill for PHP test code: test isolation, naming, coverage gaps, mocking patterns, data providers, test doubles, and AAA structure.

> **Configuration source**: all project-level configuration (tool availability, effective PHPUnit config) is read from `settings.json` — specifically the `php.tools.*` objects (availability + effective config for `phpunit`). Rule toggles are in `php.testing`. See the parent `SKILL.md` for the setup guard and the shared "Running tools" convention.

> **Review mode**: when this skill is invoked as part of a read-only review (e.g. `/zolletta-metaskill review`), follow the rules in [`../docs/reference/code/review-mode.md`](../docs/reference/code/review-mode.md) — do not apply fixes, classify diagnostics into auto-fixable (informational) vs. not auto-fixable (findings).

## When to Use This Skill

- Writing unit tests for PHP code with PHPUnit
- Setting up PHPUnit test suites and test infrastructure
- Implementing test-driven development (TDD) in PHP
- Creating integration tests for PHP APIs and services
- Mocking external dependencies with Mockery or PHPUnit mocks
- Testing database operations with PHPUnit
- Debugging failing PHPUnit tests
- Reviewing data providers and test doubles

## Coverage gap detection

> **Scope boundary**: the `/zolletta-metaskill patterns` subcommand runs `scan_tests.py` which produces a "Missing tests" table — a **structural** check (no `*Test.php` file exists). That is a structural finding owned by `patterns`. This skill owns **coverage gap analysis** using PHPUnit's coverage report — checking whether code is actually exercised by tests, regardless of file naming. Do not duplicate the structural check. If `scan_tests.py` already flagged a file as structurally missing a test, reference that finding but focus on whether the code is actually covered.

When reviewing test coverage, **never rely on grep alone** to determine if a class is tested. A class with zero direct references in test files may still be well-covered through indirect calls. Follow this procedure:

### Step 1 — Run coverage (mandatory)

You **must** run coverage before flagging any coverage gap. Do not skip this step. Follow the shared "Running tools" convention from the parent `SKILL.md` (container detection) to run PHPUnit with coverage.

The project's `phpunit.xml` (or `phpunit.xml.dist`) may already configure coverage options. If so, a plain `phpunit --coverage-text` (or `--coverage-html` / `--coverage-clover`) will use those settings — no need to add extra flags.

Read the coverage output. If a class shows coverage **above `coverage_well_covered_threshold`** (from `php.testing` in `settings.json`, default `80`), it is well-covered — do not flag it as a coverage gap even if there are no direct test references. The code is exercised through integration tests or indirect calls.

### Step 2 — Check for indirect coverage

If a class has no direct test file but coverage is non-zero, trace the call chain:

1. Use `tokensave_callers` (if tokensave is available) to find who calls the class
2. For each caller, check if it is instantiated **for real** (not mocked) in any test
3. If a caller is real (not a mock or stub), the class is indirectly covered

**Key distinction**: `$service = $this->createMock(Service::class)` means the class is NOT covered. `$service = new Service($this->createMock(Dependency::class))` means the class IS covered (real instance with mocked dependencies).

### Step 3 — Only flag as a gap if coverage is genuinely low

Only report a coverage gap when:
- Coverage is **below `coverage_gap_threshold`** (from `php.testing`, default `50`) AND
- There are no direct test references AND
- All callers are mocked in tests (no real instances)

If any of these conditions is false, the class has adequate coverage — do not flag it.

### Step 4 — For genuine gaps, check callers' test style

If you find a genuine gap, check whether the caller's tests mock the class or use a real instance. This determines the fix:
- If callers mock the class → recommend a direct unit test class for the class itself
- If callers use real instances but don't exercise all branches → recommend adding edge-case tests

## Review rules

### Always-on rules (cannot be disabled)

| #   | Area      | Name                                                                                                               |
| --- | --------- | ------------------------------------------------------------------------------------------------------------------ |
| 1   | Structure | AAA pattern (Arrange, Act, Assert)                                                                                 |
| 2   | Isolation | Tests must be independent — no shared state, each test cleans up after itself                                      |
| 3   | Coverage  | Coverage gap detection is mandatory (run PHPUnit with coverage before flagging any gap)                            |
| 4   | Scope     | Do not duplicate the structural "missing test file" check from `patterns` — this skill owns coverage analysis only |
| 5   | Naming    | Test classes named `*Test.php` (e.g. `UserServiceTest.php`)                                                        |
| 6   | Naming    | Test methods start with `test_` (e.g. `test_create_user_with_valid_data_returns_user`)                             |
| 7   | Structure | Test directory mirrors `src/` per PSR-4 (e.g. `src/Domain/User.php` → `tests/Domain/UserTest.php`)                |
| 8   | Structure | One test class per system under test (SUT)                                                                         |
| 9   | Scope     | Do not test framework internals (PHPUnit, Mockery) — test your own code only                                       |

### Configurable settings (stored in `settings.json` under `php.testing`)

| #   | Area     | Name                                                         | Key                               | Default |
| --- | -------- | ------------------------------------------------------------ | --------------------------------- | ------- |
| 10  | Coverage | Coverage gap threshold (below X% = gap)                      | `coverage_gap_threshold`          | `50`    |
| 11  | Coverage | Well-covered threshold (above X% = don't flag)               | `coverage_well_covered_threshold` | `80`    |
| 12  | Naming   | Test naming convention (`test_<unit>_<scenario>_<expected>`) | `check_test_naming`               | `true`  |
| 13  | Mocking  | Prefer Mockery over PHPUnit mocks when Mockery is available  | `prefer_mockery`                  | `true`  |

## Detailed rule explanations

### #1 — AAA pattern (always-on)

Each test follows the Arrange-Act-Assert structure:
- **Arrange**: set up test data and preconditions (fixtures, mocks, factories)
- **Act**: execute the code under test
- **Assert**: verify the results with PHPUnit assertions (`assertSame`, `assertTrue`, `assertCount`, etc.)

### #2 — Test isolation (always-on)

Tests must be independent. No shared mutable state between tests. Each test should clean up after itself. Use PHPUnit's lifecycle hooks (`setUp()`, `tearDown()`) to manage per-test state, and `setUpBeforeClass()` / `tearDownAfterClass()` for class-level fixtures. Avoid static properties that persist across test methods.

### #3 — Coverage gap detection (always-on)

Run PHPUnit with coverage before flagging any coverage gap. Never rely on grep alone — a class with zero direct test references may be well-covered through indirect calls. Follow the 4-step procedure above.

### #4 — Scope boundary (always-on)

Do not duplicate the structural "missing test file" check from `scan_tests.py` (owned by `patterns`). This skill owns coverage analysis: whether code is actually exercised by tests, not whether a `*Test.php` file exists.

### #5 — Test class naming (always-on)

Test classes must be named `<SutName>Test` and live in a file named `<SutName>Test.php`. For example, `UserService` is tested by `UserServiceTest` in `tests/Service/UserServiceTest.php`. PHPUnit auto-discovers classes ending in `Test` (or methods starting with `test_`).

### #6 — Test method naming (always-on)

Test methods must start with the `test_` prefix and follow the pattern `test_<unit>_<scenario>_<expected_outcome>`. The name should be descriptive enough to understand what is being tested without reading the body. PHPUnit also supports `@test` annotation as an alternative to the `test_` prefix, but the prefix is preferred for consistency.

**Good names**: `test_create_user_with_valid_data_returns_user`, `test_login_fails_with_invalid_password`
**Bad names**: `test_1`, `test_user`, `test_function`, `test_init`, `test_to_dict`

### #7 — Test directory mirroring (always-on)

The `tests/` directory must mirror the `src/` directory structure per PSR-4 autoloading. For example, `src/Domain/User.php` (namespace `App\Domain\User`) is tested by `tests/Domain/UserTest.php` (namespace `Tests\Domain\UserTest`). This makes it trivial to locate the test for any source class and ensures the test autoloader works correctly.

### #8 — One test class per SUT (always-on)

Each test class should test exactly one system under test (SUT). If a test class tests multiple unrelated classes, split it. This keeps tests focused, makes failures easier to diagnose, and mirrors the one-class-per-file convention from the source tree.

### #9 — Do not test framework internals (always-on)

Do not write tests that verify PHPUnit, Mockery, or any framework's own behavior. Test your application code only. For example, do not test that `createMock()` returns a mock object — that is PHPUnit's responsibility. Test that your code behaves correctly when its dependencies are mocked.

### #10 — Coverage gap threshold (configurable: `coverage_gap_threshold`)

Only report a coverage gap when class coverage is below this percentage. The default is `50` — below this, the code is genuinely under-tested. Above it, the code may be indirectly covered through integration tests.

- **Type**: integer (0–100)
- **Default**: `50`

### #11 — Well-covered threshold (configurable: `coverage_well_covered_threshold`)

If a class shows coverage above this percentage, do not flag it as a coverage gap even if there are no direct test references. The code is exercised through integration tests or indirect calls. The default is `80`.

- **Type**: integer (0–100)
- **Default**: `80`

### #12 — Test naming convention (configurable: `check_test_naming`)

Test methods should follow the pattern `test_<unit>_<scenario>_<expected_outcome>`. The name should be descriptive enough to understand what is being tested without reading the body.

- **Default**: `true`

**Good names**: `test_create_user_with_valid_data_returns_user`, `test_login_fails_with_invalid_password`
**Bad names**: `test_1`, `test_user`, `test_function`, `test_init`, `test_to_dict`

### #13 — Prefer Mockery (configurable: `prefer_mockery`)

When Mockery is available (`php.tools.phpunit.available` and Mockery is installed), prefer Mockery over PHPUnit's built-in `createMock()` for complex mocking scenarios. Mockery provides a more expressive DSL (`Mockery::mock()`, `shouldReceive()`, `andReturn()`, `once()`) and is easier to read for multi-step expectations. For simple stubs, PHPUnit's `createMock()` is fine.

- **Default**: `true`

## Mocking patterns

### PHPUnit built-in mocks

Use `$this->createMock(ClassName::class)` for simple stubs and mocks. Configure return values with `$mock->method('methodName')->willReturn($value)`. For expectations, use `$mock->expects($this->once())->method('methodName')`.

### Mockery

When Mockery is available, use `Mockery::mock(ClassName::class)` for more expressive mocking:

```php
$mock = Mockery::mock(UserRepository::class);
$mock->shouldReceive('findById')
    ->with(1)
    ->once()
    ->andReturn($expectedUser);
```

Always call `Mockery::close()` in `tearDown()` (or use `MockeryPHPUnitIntegration` trait) to verify expectations and free resources.

### Test doubles

- **Stub** — returns canned answers (`$stub->method()->willReturn()`)
- **Mock** — verifies interactions (`$mock->expects($this->once())->method()`)
- **Spy** — records interactions for later assertion (`$spy = Mockery::spy(ClassName::class)`, then `$spy->shouldHaveReceived('method')`)

## Data providers

Use `@dataProvider` annotation (or `#[DataProvider]` attribute on PHP 8.0+) to run a test with multiple datasets:

```php
#[DataProvider('validUserDataProvider')]
public function test_create_user_with_valid_data_returns_user(array $data, User $expected): void
{
    // Arrange + Act + Assert
}

public static function validUserDataProvider(): array
{
    return [
        'minimal user' => [['name' => 'Alice'], new User('Alice')],
        'user with email' => [['name' => 'Bob', 'email' => 'bob@example.com'], new User('Bob', 'bob@example.com')],
    ];
}
```

Name each dataset with a descriptive key so failures are easy to identify in PHPUnit output.

## Procedure

### Step 1 — Read configuration

Read `settings.json`:
- `php.testing` — configurable rule toggles (Table above)
- `php.tools.phpunit` — PHPUnit availability and effective config

### Step 2 — Run PHPUnit with coverage

If `php.tools.phpunit.available` is `true`, run PHPUnit with coverage:

```bash
phpunit --coverage-text
```

Follow the shared "Running tools" convention (container detection) from the parent `SKILL.md`.

Classify output:
- **Auto-fixable** (formatting, style) → informational, not graded
- **Not auto-fixable** (missing tests, low coverage, broken isolation) → findings with severity

### Step 3 — Apply always-on rules (Table 1)

For each `*Test.php` file in the `tests/` directory, check the 9 always-on rules.

### Step 4 — Apply configurable rules (Table 2)

For each configurable rule that is `true` in `php.testing`, check it.

### Step 5 — Write report

Write the report to `.zolletta-metaskill/reports/<timestamp>/php-testing-patterns.md` using the [report template](assets/report_template.md).

## Output

When this skill runs a review, it writes its findings to a markdown file using the [report template](assets/report_template.md):

- **Path**: `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/php-testing-patterns.md` (timestamp = run start time, via `date +%Y-%m-%d-%H-%M`)
- **Compound skills** (e.g. `zolletta-metaskill-review`) may override the folder and filename — follow their instructions instead
- **Directory setup**: the `.zolletta-metaskill/` directory and `.gitignore` entry are created by the [setup guard](../SKILL.md#setup-guard) — no manual setup needed
- **Format**: follow the [report template](assets/report_template.md) — grade at the top, coverage summary, coverage gaps table, findings grouped by severity with file/test-symbol/rule/issue/fix columns

## Shared resources

- [`../docs/reference/code/review-mode.md`](../docs/reference/code/review-mode.md) — read-only review conventions
- [`../docs/explanation/code/general-principles.md`](../docs/explanation/code/general-principles.md) — language-agnostic SOLID/KISS principles
- [`../docs/explanation/code/php/php-review-patterns.md`](../docs/explanation/code/php/php-review-patterns.md) — PHP-specific review patterns

## Attribution

This skill is adapted from [python-testing-patterns](https://github.com/wshobson/agents/tree/main/plugins/python-development/skills/python-testing-patterns) by Seth Hobson ([wshobson/agents](https://github.com/wshobson/agents)), licensed under the MIT License. Copyright (c) 2024 Seth Hobson. Adapted for PHP and PHPUnit with permission under the MIT License.
