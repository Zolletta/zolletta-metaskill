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

A **thin coordinator** (often named `Orchestrator`) wires collaborators and owns the high-level flow, delegating every concrete operation to focused helpers. It is SRP + DIP combined: one responsibility (the flow), every dependency injected.

```python
class Orchestrator:
    """Thin coordinator: wires four collaborators, owns only the flow."""

    def __init__(
        self,
        config: Config,
        *,
        scenario_filter: ScenarioFilter,
        group_runner: PipelineGroupRunner,
        finalizer: ExecutionFinalizer,
    ) -> None:
        self._config = config
        self._scenario_filter = scenario_filter
        self._group_runner = group_runner
        self._finalizer = finalizer

    def run(self, spec: Spec) -> Result:
        scenarios = self._scenario_filter.filter(spec)
        outcomes = self._group_runner.run(scenarios)
        return self._finalizer.finalize(outcomes)
```

**Why this matters**: the orchestrator's methods are 1–5 lines each, every line a delegation — the class reads like a table of contents. This is the inverse of a God class: high attribute count is *delegation*, not mixed concerns. See [false-positive-prevention.md](../false-positive-prevention.md).

## `_initialize` Pattern

Constructors store parameters and call `self._initialize()`. The `_initialize` method performs the actual setup. This separates the *contract* (what the class needs) from the *mechanics* (how it builds itself), and makes mocking easy — tests override `_initialize` to skip heavy setup.

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

**Why this matters**: `__init__` reads as a parameter list; `_initialize` reads as a setup procedure. A test subclass can override `_initialize` to install a fake without touching `__init__`.

## Keyword-Only Dependency Injection

Inject collaborators via keyword-only arguments using the `*,` separator. Configuration/scalar parameters stay positional; collaborators go after `*,` and are always keyword-only.

```python
# Good — every collaborator is named at the call site
orchestrator = Orchestrator(
    config,
    scenario_filter=ScenarioFilter(),
    group_runner=PipelineGroupRunner(),
    finalizer=ExecutionFinalizer(),
)

# Flag — positional collaborators: which is which?
orchestrator = Orchestrator(config, ScenarioFilter(), PipelineGroupRunner(), ...)
```

**Why this matters**: forces readable call sites and prevents positional-argument confusion when the dependency list grows. See [PEP 3102](https://peps.python.org/pep-3102/) (keyword-only arguments).

## Lazy Singletons with `get()` / `set()` / `reset()`

For process-wide singletons that need test isolation, expose a static accessor trio instead of a bare module-level instance.

```python
class MetricsClient:
    _instance: MetricsClient | None = None

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

**Why this matters**: `get()` is lazy (no import-time side effects); `set()` injects fakes in tests; `reset()` tears down between cases. A module-level `CLIENT = MetricsClient(...)` built at import time cannot be replaced without `unittest.mock.patch`.

## Module Docstrings as a Design Journal

Every module opens with a docstring stating *what the module is* and *who it collaborates with*. For extracted modules, the docstring records *what it was extracted from* — a design journal entry that survives the refactor.

```python
"""Thin coordinator that wires together four focused collaborators.

Delegates filtering to ScenarioFilter, group execution to
PipelineGroupRunner, and finalisation to ExecutionFinalizer.
"""
```

```python
"""Extracted from Orchestrator._filter_scenarios to isolate the pure
data operation of filtering scenarios by pipeline type."""
```

**Why this matters**: a reader knows the module's role without reading the body; the refactor history is preserved. See [PEP 257](https://peps.python.org/pep-0257/) (docstring conventions).

## Modern Typing Baseline

New Python code uses the modern typing stack consistently. Older `typing` imports are a generational-drift signal — see [false-positive-prevention.md](../false-positive-prevention.md) → Generational drift.

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
```

**Why this matters**: `from __future__ import annotations` defers annotation evaluation (faster imports); PEP 604 `X | None` works on 3.9+; `collections.abc.Callable` is the canonical home. See [PEP 563](https://peps.python.org/pep-0563/) (postponed evaluation), [PEP 604](https://peps.python.org/pep-0604/) (union types).
