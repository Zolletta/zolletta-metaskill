---
audience: human, ai
status: stable
skills: [patterns, python-*]
---

# Python Review Patterns

Python-specific design patterns that go beyond the language-agnostic principles in [general-principles.md](../general-principles.md). Read this when reviewing Python source code for structural quality.

> This file narrows down any eventual general rule about Python, i.e. [python-rules.md](~/.agents/python-rules.md). If you have rules in `~/.agents/`, those are the single source of truth for their domain.

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

## Python Protocol and ABC Patterns

Python offers two mechanisms for defining interfaces:

- **`Protocol`** ([PEP 544](https://peps.python.org/pep-0544/)): structural subtyping — a class is a valid implementation if it has the right methods, no inheritance required.
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

**ISP reminder**: keep protocols and ABCs thin. If an interface has 5+ methods and different implementers only use subsets, split it into smaller, focused interfaces. See [general-principles.md](../general-principles.md) → Interface Segregation for the full rationale.

## Thin Coordinator / Orchestrator Pattern

A **thin coordinator** (often named `Orchestrator`) is a small class that *wires* collaborators and owns the high-level flow, delegating every concrete operation to focused helpers. It is the practical embodiment of SRP + DIP together: the orchestrator has one responsibility (the flow), and every dependency is injected.

```python
class Orchestrator:
    """Thin coordinator that wires together four focused collaborators.

    Delegates filtering to ScenarioFilter, tag cleaning to TagCleaner,
    group execution to PipelineGroupRunner, and finalisation to
    ExecutionFinalizer. Owns no business logic — only the flow.
    """

    def __init__(
        self,
        config: Config,
        *,
        presenter: Presenter,
        scenario_filter: ScenarioFilter,
        group_runner: PipelineGroupRunner,
        finalizer: ExecutionFinalizer,
    ) -> None:
        self._config = config
        self._presenter = presenter
        self._scenario_filter = scenario_filter
        self._group_runner = group_runner
        self._finalizer = finalizer

    def run(self, spec: Spec) -> Result:
        scenarios = self._scenario_filter.filter(spec)
        cleaned = self._tag_cleaner.clean(scenarios)
        outcomes = self._group_runner.run(cleaned)
        return self._finalizer.finalize(outcomes)
```

**Review signals**:

- **Good**: the orchestrator's methods are 1–5 lines each, every line is a delegation. The class reads like a table of contents.
- **Flag**: an orchestrator that starts inlining logic (`if spec.type == ...: scenarios = [s for s in scenarios if ...]`) — the logic belongs in a collaborator, not the coordinator.
- **Flag**: an orchestrator with `new`/`SomeClass(...)` calls inside `run()` — it is creating dependencies instead of receiving them (DIP violation).

> This pattern is the inverse of a God class: high attribute count is *delegation*, not mixed concerns. See [false-positive-prevention.md](../false-positive-prevention.md) → "An orchestrator that delegates to injected dependencies" is explicitly **not** a God class.

## `_initialize` Pattern: Separating "What I Need" from "How I Build It"

Constructors stay thin: they store parameters and call `self._initialize()`. The `_initialize` method performs the actual setup (building internal structures, parsing config, registering handlers). This separates the *contract* (what the class needs) from the *mechanics* (how it builds itself), and makes mocking easy — tests can override `_initialize` to skip heavy setup.

```python
class GitLabClient:
    def __init__(self, url: str, token: str, *, timeout: int = 30) -> None:
        self._url = url
        self._token = token
        self._timeout = timeout
        self._session: httpx.Client | None = None
        self._initialize()

    def _initialize(self) -> None:
        """Build the HTTP session and auth headers from the stored params."""
        self._session = httpx.Client(
            base_url=self._url,
            headers={"Authorization": f"Bearer {self._token}"},
            timeout=self._timeout,
        )
```

**Why this matters**:

- **Testability**: a test subclass can override `_initialize` to install a fake session without touching `__init__`.
- **Readability**: `__init__` reads as a parameter list; `_initialize` reads as a setup procedure. Each has one job.
- **Re-initialisation**: calling `_initialize()` again (e.g. after a config change) is safe and explicit, unlike re-calling `__init__`.

**Flag**: a constructor that mixes parameter storage with multi-line setup logic (building clients, parsing files, registering callbacks) — extract the setup into `_initialize`.

## Keyword-Only Dependency Injection

Inject collaborators via keyword-only arguments using the `*,` separator. This forces call sites to name every dependency, making wiring readable and preventing positional-argument confusion when the dependency list grows.

```python
# Good — every collaborator is named at the call site
orchestrator = Orchestrator(
    config,
    presenter=ConsolePresenter(),
    scenario_filter=ScenarioFilter(),
    group_runner=PipelineGroupRunner(),
    finalizer=ExecutionFinalizer(),
)

# Flag — positional collaborators: which is which?
orchestrator = Orchestrator(config, ConsolePresenter(), ScenarioFilter(), ...)
```

**Convention**: configuration/scalar parameters stay positional (they are the "what"); collaborators (services, helpers, ports) go after `*,` and are always keyword-only (they are the "who"). This mirrors the Orchestrator pattern above: the first arg is the input, the rest are the delegates.

## Lazy Singletons with `get()` / `set()` / `reset()`

For process-wide singletons that need test isolation (metrics clients, feature-flag managers, connection pools), expose a static accessor trio instead of a bare module-level instance:

```python
class MetricsClient:
    _instance: MetricsClient | None = None

    def __init__(self, endpoint: str) -> None:
        self._endpoint = endpoint

    @classmethod
    def get(cls) -> MetricsClient:
        if cls._instance is None:
            cls._instance = cls(endpoint=os.environ["METRICS_ENDPOINT"])
        return cls._instance

    @classmethod
    def set(cls, instance: MetricsClient) -> None:
        cls._instance = instance

    @classmethod
    def reset(cls) -> None:
        cls._instance = None
```

**Why this matters**:

- `get()` — lazy: the singleton is built on first use, not at import time. Importing the module has no side effects.
- `set(instance)` — tests inject a fake (`MetricsClient.set(NullStatsClient())`) without monkey-patching globals.
- `reset()` — tests tear down between cases, preventing cross-test leakage.

**Flag**: a module-level `CLIENT = MetricsClient(...)` built at import time — it runs even when the module is imported for an unrelated reason, and tests cannot replace it without `unittest.mock.patch`.

## Module Docstrings as a Design Journal

Every module opens with a docstring that states *what the module is* and *who it collaborates with*. Beyond documentation, the docstring records *why the class was extracted* and what it replaces — a design journal entry that survives the refactor.

```python
"""Thin coordinator that wires together four focused collaborators.

Delegates filtering to ScenarioFilter, tag cleaning to TagCleaner,
group execution to PipelineGroupRunner, and finalisation to
ExecutionFinalizer. Owns no business logic — only the flow.
"""
```

```python
"""Extracted from Orchestrator._filter_scenarios to isolate the pure
data operation of filtering scenarios by pipeline type. Replaces the
inline list comprehension that was growing conditional branches.
"""
```

**Review signals**:

- **Good**: the docstring names the collaborators and the responsibility. A reader knows the module's role without reading the body.
- **Good**: an extracted module's docstring records *what it was extracted from* — this is senior behaviour: the refactor history is preserved.
- **Flag**: a module with no docstring, or a docstring that restates the class name (`"""User service."""`) without naming collaborators or responsibility.

## Modern Typing Baseline

New Python code uses the modern typing stack consistently. Older `typing` imports (`List`, `Optional`, `Tuple`, `Dict`, `Callable`) are a generational-drift signal — see [false-positive-prevention.md](../false-positive-prevention.md) → Generational drift.

| Construct           | Modern (use)                             | Legacy (flag in new code)                |
|---------------------|------------------------------------------|------------------------------------------|
| Optional            | `X \| None`                              | `Optional[X]`                            |
| Generic collections | `list[T]`, `dict[K, V]`, `tuple[T, ...]` | `List[T]`, `Dict[K, V]`, `Tuple[T, ...]` |
| Callable            | `collections.abc.Callable`               | `typing.Callable`                        |
| Future annotations  | `from __future__ import annotations`     | (none — required in new modules)         |

```python
# Good — modern baseline
from __future__ import annotations

from collections.abc import Callable

def filter_scenarios(
    scenarios: list[Scenario],
    predicate: Callable[[Scenario], bool] | None = None,
) -> list[Scenario]: ...

# Flag — legacy typing in new code
from typing import Callable, List, Optional

def filter_scenarios(
    scenarios: List[Scenario],
    predicate: Optional[Callable[[Scenario], bool]] = None,
) -> List[Scenario]: ...
```

**Why this matters**: `from __future__ import annotations` makes all annotations strings at parse time, enabling [PEP 604](https://peps.python.org/pep-0604/) `X | None` syntax on Python 3.9+ and deferring evaluation (faster imports, no runtime cost for annotations). `collections.abc.Callable` is preferred over `typing.Callable` because it is the canonical home and supports `isinstance` checks.
