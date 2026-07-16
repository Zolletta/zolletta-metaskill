---
name: python-code-style
license: MIT
description: Python code style, linting, formatting, naming conventions, and documentation standards. Use when writing new code, reviewing style, configuring linters, writing docstrings, or establishing project standards.
---

# Python Code Style & Documentation

Consistent code style and clear documentation make codebases maintainable and collaborative. This skill covers modern Python tooling, naming conventions, and documentation standards.

> **Project-driven configuration**: this skill reads all conventions (line length, target Python version, linting rules, type checking strictness) from the project's `pyproject.toml`. Do not hardcode defaults — always check what the project has configured first. If a setting is absent from `pyproject.toml`, use the fallback defaults noted in each pattern.

> **Tool availability**: before running any tool, read `settings.json` and check the `python` subobject to see which tools are available (`uv`, `ruff`, `pytest`, `ty`, `vulture`, `mypy`). If a tool is `false`, print the corresponding "not installed" message from `../reference/tool-messages.md` and skip that check. **Do NOT install anything.**

> **Running tools**: if `container_name` is set in `settings.json`, run tools inside the container via `docker compose exec <container_name> <command>`. If `container_name` is `null`, run tools directly on the host. If `python.uv` is `true`, prefer `uv run <command>` to ensure the project environment is used.

## When to Use This Skill

- Setting up linting and formatting for a new project
- Writing or reviewing docstrings
- Establishing team coding standards
- Configuring ruff, mypy, or ty
- Reviewing code for style consistency
- As part of a `/zolletta-metaskill review` run (python-code-style subagent)

## Core Concepts

### 1. Automated Formatting

Let tools handle formatting debates. Configure once in `pyproject.toml`, enforce automatically.

### 2. Consistent Naming

Follow PEP 8 conventions with meaningful, descriptive names.

### 3. Documentation as Code

Docstrings should be maintained alongside the code they describe.

### 4. Type Annotations

Modern Python code should include type hints for all public APIs.

### 5. One Class Per File

Each class gets its own file; the filename matches the class name (snake_case → PascalCase).

## Quick Start

Read `pyproject.toml` to understand the project's configuration. All tool invocations should respect the project's settings.

```bash
# If uv is available:
uv run ruff check --fix .   # Lint and auto-fix
uv run ruff format .         # Format code

# If uv is not available, run directly:
ruff check --fix .
ruff format .
```

## Fundamental Patterns

### Pattern 1: Modern Python Tooling

Use `ruff` as an all-in-one linter and formatter. It replaces flake8, isort, and black with a single fast tool.

**Read the project's `pyproject.toml`** to find the ruff configuration. The `[tool.ruff]` section defines line length, target version, selected lint rules, and formatting options. Do not hardcode a rule set — use what the project has configured.

If ruff is not configured in `pyproject.toml` and is available as a tool, suggest the following minimal configuration:

```toml
# pyproject.toml
[tool.ruff]
line-length = 120  # fallback default if not set
target-version = "py312"  # fallback default

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # pyflakes
    "I",    # isort
    "B",    # flake8-bugbear
    "C4",   # flake8-comprehensions
    "UP",   # pyupgrade
    "SIM",  # flake8-simplify
]
ignore = ["E501"]  # Line length handled by formatter

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

Run with (adjust for container/uv as noted above):

```bash
ruff check --fix .  # Lint and auto-fix
ruff format .       # Format code
```

If `ruff` is `false` in `settings.json`, print the ruff "not installed" message and skip linting/formatting checks.

> **Review mode (read-only)**: when this skill is invoked as part of a `/zolletta-metaskill review` (or any read-only review context), do **NOT** apply any fixes. Run `ruff check` (no `--fix`) and `ruff format --check` (no formatting). Classify every issue into two buckets:
> - **Auto-fixable** (ruff reports the rule as fixable, or `ruff format --check` would reformat the file): report as **informational** — list them in a separate "Auto-fixable (informational)" section, do **not** count them toward the grade, and do **not** list them as findings.
> - **Not auto-fixable**: list as actual findings with severity, impact, and suggested fix — these are the only issues that affect the grade.
>
> To distinguish the two buckets, run `ruff check` and inspect the output: ruff marks each diagnostic with a fix indicator (e.g. `[F]` or `[*]` for fixable, `[--fix]` for unsafe-fixable). Alternatively run `ruff check --fix --exit-zero` as a dry-run probe to see what would be fixed, then discard the changes (`git checkout -- .`). For format, `ruff format --check` lists the files it would reformat — those are auto-fixable (informational).

### Pattern 2: Type Checking Configuration

**Read the project's `pyproject.toml`** to find the type checker configuration. The project may use `mypy` (`[tool.mypy]`), `ty` (`[tool.ty]`), or `pyright` (`[tool.pyright]`). Use whichever is configured.

If both `mypy` and `ty` are available, prefer the one configured in `pyproject.toml`. If neither is configured, use whichever tool is available (check `settings.json`).

Do not hardcode strictness settings — read them from `pyproject.toml`. If no type checker is configured and one is available, suggest a minimal config:

```toml
# pyproject.toml — mypy
[tool.mypy]
python_version = "3.12"  # fallback default
strict = true
warn_return_any = true
warn_unused_ignores = true
disallow_untyped_defs = true
disallow_incomplete_defs = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

```toml
# pyproject.toml — ty
[tool.ty]
python-version = "3.12"
```

If neither `mypy` nor `ty` is available (`python.mypy: false` and `python.ty: false` in `settings.json`), print both "not installed" messages and skip type checking.

> **Review mode (read-only)**: when this skill is invoked as part of a `/zolletta-metaskill review` (or any read-only review context), do **NOT** apply any fixes. Run `ty check` (no `--fix`) and `mypy` as-is. Classify `ty` issues into two buckets:
> - **Auto-fixable** (ty reports the diagnostic as fixable): report as **informational** — list them in a separate "Auto-fixable (informational)" section, do **not** count them toward the grade, and do **not** list them as findings.
> - **Not auto-fixable**: list as actual findings with severity, impact, and suggested fix — these are the only type issues that affect the grade.
>
> `mypy` does not have an auto-fix mode, so all mypy findings are listed as actual findings and scored normally.

### Pattern 3: Naming Conventions

Follow PEP 8 with emphasis on clarity over brevity. PEP 8 naming conventions are standard and should not be overridden by `pyproject.toml` — they are language conventions, not project configuration.

**Files and Modules:**

```python
# Good: Descriptive snake_case
user_repository.py
order_processing.py
http_client.py

# Avoid: Abbreviations
usr_repo.py
ord_proc.py
http_cli.py
```

**Classes and Functions:**

```python
# Classes: PascalCase
class UserRepository:
    pass

class HTTPClientFactory:  # Acronyms stay uppercase
    pass

# Functions and variables: snake_case
def get_user_by_email(email: str) -> User | None:
    retry_count = 3
    max_connections = 100
```

**Constants:**

```python
# Module-level constants: SCREAMING_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT_SECONDS = 30
API_BASE_URL = "https://api.example.com"
```

### Pattern 4: Import Organization

Group imports in a consistent order: standard library, third-party, local. If ruff is configured with the `I` (isort) rule, import ordering is enforced automatically — do not restate the rules manually.

```python
# Standard library
import os
from collections.abc import Callable
from typing import Any

# Third-party packages
import httpx
from pydantic import BaseModel
from sqlalchemy import Column

# Local imports
from myproject.models import User
from myproject.services import UserService
```

Use absolute imports exclusively:

```python
# Preferred
from myproject.utils import retry_decorator

# Avoid relative imports
from ..utils import retry_decorator
```

### Pattern 5: One Class Per File

> **Note**: this is a convention, not a PEP standard. PEP 8 does not mandate one class per file. The convention is inspired by Java's "one public class per file" rule and is widely adopted in Python codebases for discoverability and testability.

**Rules:**

- Each public class should live in its own file
- The filename should match the class name: `snake_case.py` → `PascalCase` class (e.g. `user_repository.py` → `UserRepository`)
- Small helper classes or enums closely tied to a main class may share the same file
- Data classes and protocols that are used together may be grouped

**Good:**

```python
# user_repository.py
class UserRepository:
    """Repository for user persistence."""
    ...
```

**Avoid:**

```python
# models.py — 15 classes in one file
class User: ...
class Order: ...
class Product: ...
class Invoice: ...
# ... hard to find, hard to test, hard to import
```

**Detection**: use `scan_one_class_per_file.py` from `../patterns/scripts/python/` to find files with multiple classes. Apply judgment — some groupings are intentional (e.g. a module of closely related enums).

## Advanced Patterns

### Pattern 6: Google-Style Docstrings

Write docstrings for all **public** classes, methods, and functions. Private functions (leading underscore), nested/local functions, and helper closures do **not** need docstrings — they are implementation details, not API.

**When to include `Args:` and `Returns:` sections:**

Type annotations already convey the argument types and return type. Do **not** repeat them in a docstring section. Only include `Args:` or `Returns:` when there is information the type annotation cannot express:

- Constraints on values (e.g. "must not be empty", "must be a positive integer")
- Units or formats (e.g. "seconds, not milliseconds", "ISO 8601 format")
- Side effects or mutation (e.g. "modifies the list in place")
- Default behavior that is non-obvious

If the type annotation fully describes the argument, a one-line summary docstring is sufficient.

**Simple Function (one-line summary — type annotations say the rest):**

```python
def get_user(user_id: str) -> User:
    """Retrieve a user by their unique identifier."""
    ...
```

**Complex Function (Args/Returns only for non-obvious info):**

```python
def process_batch(
    items: list[Item],
    max_workers: int = 4,
    on_progress: Callable[[int, int], None] | None = None,
) -> BatchResult:
    """Process items concurrently using a worker pool.

    Args:
        items: Must not be empty. Items are consumed lazily.
        on_progress: Receives (completed, total) counts. Called from a
            worker thread — ensure the callback is thread-safe.

    Raises:
        ValueError: If items is empty.
        ProcessingError: If the batch cannot be processed.

    Example:
        >>> result = process_batch(items, max_workers=8)
        >>> print(f"Processed {len(result.succeeded)} items")
    """
    ...
```

> Note: `max_workers` and the return type are not in `Args:`/`Returns:` — the type annotations (`int = 4`, `-> BatchResult`) already say everything needed.

**Class Docstring:**

```python
class UserService:
    """Service for managing user operations.

    Provides methods for creating, retrieving, updating, and
    deleting users with proper validation and error handling.

    Attributes:
        repository: The data access layer for user persistence.
        logger: Logger instance for operation tracking.

    Example:
        >>> service = UserService(repository, logger)
        >>> user = service.create_user(CreateUserInput(...))
    """

    def __init__(self, repository: UserRepository, logger: Logger) -> None:
        self.repository = repository
        self.logger = logger
```

> Note: `__init__` does not need a docstring when its parameters are self-explanatory from type annotations. Only add one if the constructor has non-obvious side effects or initialization logic.

**What does NOT need a docstring:**

- Private functions (`_helper`, `_format_output`)
- Nested/local functions and closures
- `__init__` when parameters are obvious from type annotations
- Test functions (the test name is the documentation)
- One-line functions where the name + signature is self-explanatory

### Pattern 7: Line Length and Formatting

**Read the line length from `pyproject.toml`** — check `[tool.ruff]` `line-length` first. If not set, use 120 as the fallback default.

Do not hardcode a line length. The project's configuration is the single source of truth.

```python
# Good: Readable line breaks (respecting the project's line-length setting)
def create_user(
    email: str,
    name: str,
    role: UserRole = UserRole.MEMBER,
    notify: bool = True,
) -> User:
    ...

# Good: Chain method calls clearly
result = (
    db.query(User)
    .filter(User.active == True)
    .order_by(User.created_at.desc())
    .limit(10)
    .all()
)

# Good: Format long strings
error_message = (
    f"Failed to process user {user_id}: "
    f"received status {response.status_code} "
    f"with body {response.text[:100]}"
)
```

If ruff is available, `ruff format` handles line breaking automatically — do not reformat manually unless ruff is not available.

## Dead Code Detection

If `vulture` is available (`python.vulture: true` in `settings.json`), run it to find unused code:

```bash
vulture src/ --min-confidence 80
```

Report findings as low-priority issues — vulture has false positives, especially for dynamically-accessed methods. Review each finding before flagging.

If `vulture` is `false`, skip dead code detection.

## Best Practices Summary

1. **Read pyproject.toml first** — never hardcode what the project has already configured
2. **Use ruff** - Single tool for linting and formatting (if available)
3. **Type checking** - Use mypy or ty, whichever the project configures (if available)
4. **Descriptive names** - Clarity over brevity (PEP 8)
5. **Absolute imports** - More maintainable than relative
6. **Google-style docstrings** - For public API only; skip Args/Returns when type annotations suffice
7. **Document public APIs** - Private functions, nested closures, and obvious `__init__` do not need docstrings
8. **One class per file** - Each class gets its own file; filename matches class name
9. **Automate in CI** - Run linters on every commit
10. **Dead code detection** - Run vulture if available, review findings with judgment

## Attribution

This skill is adapted from [python-code-style](https://github.com/wshobson/agents/tree/main/plugins/python-development/skills/python-code-style) by Seth Hobson ([wshobson/agents](https://github.com/wshobson/agents)), licensed under the MIT License. Copyright (c) 2024 Seth Hobson.
