# Python-Specific Review Guide

Python-specific conventions and patterns that go beyond the language-agnostic principles in `general-principles.md`. Read this file when reviewing Python source code.

> This file narrows down any eventual general rule about Python, i.e. [python-rules.md](~/.agents/rules/python-rules.md). All files in `~/.agents/rules/` are the single source of truth for their domain.

## Strategy Pattern with Autodiscovery

Python's `Protocol` + decorator registration enables the strategy pattern with autodiscovery — new strategies are added by creating a new class and decorating it, without modifying any dispatch logic.

```python
from typing import Protocol
import importlib
import pkgutil

class ScenarioStrategy(Protocol):
    """Protocol for all scenario generation strategies."""
    def generate(self, spec: Spec) -> list[Scenario]: ...
    def get_name(self) -> str: ...

_STRATEGIES: dict[str, type[ScenarioStrategy]] = {}

def register_strategy(name: str):
    """Decorator to register a strategy class."""
    def decorator(cls):
        _STRATEGIES[name] = cls
        return cls
    return decorator

@register_strategy("feature_flag")
class FeatureFlagStrategy:
    def generate(self, spec: Spec) -> list[Scenario]: ...
    def get_name(self) -> str: ...

def autodiscover_strategies(package: str) -> None:
    """Import all modules in a package to trigger @register_strategy decorators."""
    pkg = importlib.import_module(package)
    for _, name, _ in pkgutil.iter_modules(pkg.__path__):
        importlib.import_module(f"{package}.{name}")
```

**Why this matters**: this is the OCP-compliant alternative to if/elif type branching. Adding a new strategy requires zero modification to existing code.

**Common mixin pattern**: shared behavior across strategies goes in a mixin, not in the base class. This keeps the protocol thin (ISP) and allows strategies to opt into shared behavior via composition.

```python
class ScenarioReducerMixin:
    """Shared reduction logic for strategies that need it."""
    def _reduce(self, scenarios: list[Scenario]) -> list[Scenario]: ...

@register_strategy("pipeline_type")
class PipelineTypeStrategy(ScenarioReducerMixin):
    def generate(self, spec: Spec) -> list[Scenario]: ...
```

## One Class Per File

This narrows [rules/python-rules.md](../../rules/python-rules.md) ("1 class 1 file, 1 file one class") for the design-patterns review context. All files in `rules/` are the single source of truth for their domain.

The filename should match the class name (snake_case file -> PascalCase class).

**Why this matters**:

- **Navigability**: `MyClass` lives in `my_class.py` — mechanical lookup.
- **Testability**: one class per file means one test file per class.
- **Coupling signal**: multiple classes in one file often indicates tight coupling.

**Acceptable exceptions**:

- `__init__.py` files (package markers, may re-export)
- Closely related tiny helper classes (e.g., a Protocol and its NoOp implementation — but only if both are < 20 lines)
- Enum/constant classes grouped in one file (but consider a dedicated `enums/` package instead)

**Detection**: see `scripts.md` → `scan_one_class_per_file.py`.

## Test Structure Mirrors Source Structure

The test directory tree should mirror the source directory tree. For every source file containing classes, there should be a corresponding test file at the mirrored path.

**Convention**:

```text
src/.../cache.py  ->  tests/.../test_cache*.py
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

**Detection**: see `scripts.md` → `scan_tests.py`. The script outputs a markdown report with five tables: misnamed tests (rename), misplaced tests (move), orphaned tests (delete or investigate), missing tests (write new tests), and indirect references (informative only — shows which test files provide indirect coverage for source files without a direct test).

## Naming Conventions

Two naming rules work together to keep source and test files navigable:

1. **Source file name == class name**: each source file with exactly one class should have a filename matching the class name (snake_case file → PascalCase class). For example, `my_class.py` should contain `class MyClass`.

2. **Test file naming**: every test file must follow `test_<source_stem><eventual_suffix>.py`, where `<source_stem>` is the stem of the source file being tested, and `<eventual_suffix>` is an optional `_word` suffix used when tests are split across multiple files.

```text
src/.../cache.py  ->  tests/.../test_cache.py
                   ->  tests/.../test_cache_operations.py
                   ->  tests/.../test_cache_init.py
```

Test files whose name doesn't match any source file or class in the mirrored directory are orphan or misnamed tests — they test code that has been renamed, deleted, or they use a naming pattern inconsistent with the project.

**Detection**: see `scripts.md` → `scan_naming_conventions.py` (checks both rules in a single pass).

## Test God Class Splitting

When a test class tests multiple SUTs (detected by `scan_test_god_classes.py --show-methods`), it should be split into per-SUT test files. The `test_splitter.py` script automates this.

**When to split**:

- The test class tests 2+ different source classes (SUTs)
- Each SUT has its own source file
- The test class has 20+ test methods

**When NOT to split**:

- All test methods target the same SUT (the class is just large, not a God class)
- The SUTs are tiny helper classes that don't warrant separate test files
- The test methods are integration tests that test the interaction of multiple classes together

**Procedure**: see `scripts.md` → `test_splitter.py` for the full workflow.

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

## Python Protocol and ABC Patterns

Python offers two mechanisms for defining interfaces:

- **`Protocol`** (PEP 544): structural subtyping — a class is a valid implementation if it has the right methods, no inheritance required.
- **`ABC`** (abstract base class): nominal subtyping — a class must explicitly inherit from the ABC.

**Prefer `Protocol`** for new code: it enables duck typing and doesn't force implementers to import the interface. Use `ABC` when you need `@abstractmethod` enforcement or when the framework requires it.

```python
# Protocol: structural — no import needed by implementer
class VerifierProtocol(Protocol):
    def verify(self, scenario: Scenario) -> VerificationResult: ...

class MyVerifier:  # No inheritance, just matches the shape
    def verify(self, scenario: Scenario) -> VerificationResult: ...

# ABC: nominal — must inherit
class VerifierBase(ABC):
    @abstractmethod
    def verify(self, scenario: Scenario) -> VerificationResult: ...

class MyVerifier(VerifierBase):  # Must inherit
    def verify(self, scenario: Scenario) -> VerificationResult: ...
```

**ISP reminder**: keep protocols and ABCs thin. If an interface has 5+ methods and different implementers only use subsets, split it. See `general-principles.md` → Interface Segregation.
