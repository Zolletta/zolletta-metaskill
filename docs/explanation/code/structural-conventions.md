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

**Why this matters**:

- **Navigability**: `MyClass` lives in `my_class.py` (Python) or `MyClass.php` (PHP) — mechanical lookup.
- **Testability**: one class per file means one test file per class.
- **Coupling signal**: multiple classes in one file often indicates tight coupling.

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

**Why this matters**:

- **Coverage visibility**: structural gaps immediately reveal untested source files.
- **Orphan detection**: test dirs with no source dir indicate tests for deleted code.
- **Navigation**: from any source file, the test file is at a predictable path.

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
