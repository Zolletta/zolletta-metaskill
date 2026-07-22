---
audience: human, ai
status: stable
skills: [patterns, python-code-style, python-testing-patterns]
---

# Python Review Patterns

Python-specific design patterns that go beyond the language-agnostic principles in [general-principles.md](../general-principles.md). Read this when reviewing Python source code for structural quality.

> This file narrows down any eventual general rule about Python, i.e. [python-rules.md](~/.agents/python-rules.md). All files in `~/.agents/` are the single source of truth for their domain.

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

**ISP reminder**: keep protocols and ABCs thin. If an interface has 5+ methods and different implementers only use subsets, split it into smaller, focused interfaces. See [general-principles.md](../general-principles.md) → Interface Segregation for the full rationale.
