---
audience: human, ai
status: stable
skills: [patterns, review, python-*]
---

# Structural Conventions

Language-agnostic structural conventions for source and test code organisation. These conventions apply across all supported languages. Language-specific enforcement details (e.g. Python's `ast`-based scanners) are noted where relevant.

> **Language-agnostic**: the conventions below use generic file extensions. Where a language has a specific naming pattern (e.g. Python's snake_case → PascalCase mapping), it is noted inline.

## One Class Per File

Each class lives in its own file. The filename should match the class name using the language's conventional mapping.

**Why this matters**: `MyClass` lives in `my_class.py` (Python) or `MyClass.php` (PHP) — mechanical lookup, one test file per class, and multiple classes in one file signal tight coupling. See [PEP 8 — modules](https://peps.python.org/pep-0008/#module-level-dunder-names), [PSR-4 — autoloading](https://www.php-fig.org/psr/psr-4/).

**Acceptable exceptions**:

- Package marker files (e.g. `__init__.py` in Python, `index.ts` in TypeScript) — may re-export
- Closely related tiny helper classes (e.g., an interface and its NoOp implementation — but only if both are < 20 lines)
- Enum/constant classes grouped in one file (but consider a dedicated `enums/` package instead)

**Detection (Python)**: see [scripts.md](../../reference/code/scripts.md) → `scan_one_class_per_file.py`.

## Test Structure Mirrors Source Structure

The test directory tree should mirror the source directory tree. For every source file containing classes, there should be a corresponding test file at the mirrored path.

**Convention**:

```text
src/.../cache.py  ->  tests/.../test_cache*.py
src/.../Cache.php  ->  tests/.../CacheTest.php
```

One source class can have many test files. The check uses prefix matching, not exact filename matching. For example, `cache.py` (class `Cache`) matches any of: `test_cache.py`, `test_cache_operations.py`, `test_cache_getters.py`, `test_cache_init.py`, etc.

```text
src/myproject/engine/config/config_factory.py
-> tests/myproject/engine/config/test_config_factory*.py
```

**Why this matters**: structural gaps immediately reveal untested source files, orphaned test dirs indicate tests for deleted code, and the test file is at a predictable path from any source file. See [pytest — test layout](https://docs.pytest.org/en/stable/explanation/goodpractices.html#choosing-a-test-layout-importing-modes), [PHPUnit — directory structure](https://docs.phpunit.de/en/main/organizing-tests.html).

**Acceptable exceptions**:

- Source directories containing only assets, templates, or dashboards (use `--ignore-dirs` to skip them).
- Source files with no classes (pure functions/constants) — may be tested indirectly through integration tests.
- Test helpers, fixtures, mocks, and mixins live outside the mirrored tree (e.g., `tests/fixtures/`, `tests/mocks/`, `tests/mixins/`).

**Detection (Python)**: see [scripts.md](../../reference/code/scripts.md) → `scan_tests.py`. The script outputs a markdown report with five tables: misnamed tests (rename), misplaced tests (move), orphaned tests (delete or investigate), missing tests (write new tests), and indirect references (informative only).

## Naming Conventions

Two naming rules work together to keep source and test files navigable:

1. **Source file name == class name**: each source file with exactly one class should have a filename matching the class name. In Python, this is snake_case file → PascalCase class (e.g., `my_class.py` → `MyClass`). In PHP, the file name typically matches the class name directly (e.g., `MyClass.php` → `MyClass`).

2. **Test file naming**: every test file must follow the project's test naming convention. In Python: `test_<source_stem><eventual_suffix>.py`. In PHP: `<SourceClass>Test.php`. The `<eventual_suffix>` is an optional `_word` suffix used when tests are split across multiple files.

```text
src/.../cache.py  ->  tests/.../test_cache.py
                   ->  tests/.../test_cache_operations.py
                   ->  tests/.../test_cache_init.py
```

Test files whose name doesn't match any source file or class in the mirrored directory are orphan or misnamed tests — they test code that has been renamed, deleted, or they use a naming pattern inconsistent with the project.

**Detection (Python)**: see [scripts.md](../../reference/code/scripts.md) → `scan_naming_conventions.py` (checks both rules in a single pass).

**Why this matters**: orphan or misnamed tests test code that has been renamed, deleted, or use an inconsistent naming pattern. See [PEP 8 — naming conventions](https://peps.python.org/pep-0008/#naming-conventions), [PHPUnit — test naming](https://docs.phpunit.de/en/main/organizing-tests.html).

## Value-Object Suffixes

Value objects — immutable data carriers with no behaviour — use a conventional suffix that signals their role.

| Suffix    | Purpose                                           | Examples                                       |
|-----------|---------------------------------------------------|------------------------------------------------|
| `*DTO`    | Data Transfer Object — serialisable data carrier  | `GenericDataDTO`, `UserResponseDTO`            |
| `*Spec`   | Specification — describes *what* to build/run     | `EndpointSpec`, `ScenarioSpec`                 |
| `*Params` | Parameter bundle — grouped arguments for one call | `ResizableParams`, `AgencyEstimateCoverParams` |

**Why this matters**: the suffix separates *description* from *thing described* — `EndpointSpec` is a specification, not an endpoint. See [Fowler — Data Transfer Object](https://martinfowler.com/eaaCatalog/dto.html).

**Language notes**:

- **Python**: suffix applies to `@dataclass` / `NamedTuple` / `TypedDict` / frozen dataclasses.
- **PHP**: suffix applies to `readonly class` DTOs and promoted-constructor parameter bundles.

**Acceptable exceptions**:

- Domain entities (`User`, `Order`) are not value objects and do not take a suffix.
- Framework base classes that impose their own naming (`*Controller`, `*Repository`, `*Command`, `*Event`) follow the framework convention.

## Enum Naming

Enums use `PascalCase` for the enum class and `SCREAMING_SNAKE_CASE` for the cases. This separates the *type* (a closed set) from its *members* (individual values) at a glance.

```python
# Good — PascalCase enum, SCREAMING_SNAKE members
class PipelineType(Enum):
    MASTER = "master"
    FEATURE_BRANCH = "feature_branch"
```

```php
<?php

// Good — PascalCase enum, PascalCase cases (PHP convention)
enum CommandRunMode: string {
    case DryRun = 'DRY_RUN';
    case Live = 'LIVE';
}
```

> **PHP note**: PHP enum case names follow [PSR-12](https://www.php-fig.org/per/coding-style/) `PascalCase` by convention, while Python enum members follow `SCREAMING_SNAKE_CASE`. The *class* is `PascalCase` in both. Reviewers should enforce the language-native member casing.

**Why this matters**: the class/member casing split makes enums visually distinct from classes-with-instances. See [PEP 435](https://peps.python.org/pep-0435/) (Python enums), [PHP enums](https://www.php.net/manual/en/language.enumerations.php).

## Acronyms Stay Uppercase in Class Names

Acronyms retain their uppercase form inside PascalCase class names: `HTTPClient`, not `HttpClient`; `CITesterEngine`, not `CiTesterEngine`. This is a cross-language convention.

```python
# Good — acronyms stay uppercase
class CITesterEngine: ...
class JWTDecoder: ...

# Flag — acronym lowercased mid-name
class CiTesterEngine: ...      # should be CITesterEngine
```

```php
<?php

// Good — acronyms stay uppercase
class JWTDecoder { ... }

// Flag
class JwtDecoder { ... }       // should be JWTDecoder
```

**Enforcement**: the acronym list is project-specific. The Python skill ships `scan_acronym_casing.py` with an additive acronym list (shipped base + `settings.json` `acronyms` array + CLI override). A class name is flagged only when a word inside it case-insensitively matches a configured acronym but is not all-uppercase.

> The acronym rule is already enforced by the `python-code-style` skill (rule #3). It is restated here because it is a *cross-language* convention — a reviewer reading PHP code should apply the same rule.

**Why this matters**: `HTTPClient` reads as "HTTP client"; `HttpClient` obscures the acronym. See [PEP 8 — naming conventions](https://peps.python.org/pep-0008/#naming-conventions), [PSR-12 — class names](https://www.php-fig.org/psr/psr-12/).

## Test God Class Splitting

When a test class tests multiple SUTs (Systems Under Test), it should be split into per-SUT test files.

**When to split**:

- The test class tests 2+ different source classes (SUTs)
- Each SUT has its own source file
- The test class has 20+ test methods

**When NOT to split**:

- All test methods target the same SUT (the class is just large, not a God class)
- The SUTs are tiny helper classes that don't warrant separate test files
- The test methods are integration tests that test the interaction of multiple classes together

**Procedure (Python)**: see [scripts.md](../../reference/code/scripts.md) → `test_splitter.py` for the full workflow.

**What the splitter handles automatically**:

- Copies all imports to each split file
- Copies `pytestmark` to each split file
- Copies shared methods (fixtures, helpers) to each split file
- Generates proper class names (`Test<SutName>`)
- Indents methods correctly inside the class
- Reports unmatched methods for mapping review

**What the splitter does NOT do**:

- Remove unused imports from split files (review manually)
- Move the files to the final test directory (human reviews first)
- Delete the original file (human confirms the split is correct)
- Run the tests (human verifies the split files pass)

For the step-by-step procedure, see [split-god-test-class.md](../../how-to/code/split-god-test-class.md).

**Why this matters**: a test class testing multiple SUTs is hard to navigate and maintain — per-SUT files keep tests focused. See [xUnit Test Patterns — One Test Class Per Feature](https://xunitpatterns.com/One%20Test%20Class%20Per%20Feature.html).
