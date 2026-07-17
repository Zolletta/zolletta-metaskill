---
name: python-code-style
license: MIT
description: Python code style, linting, formatting, naming conventions, and documentation standards. Use when writing new code, reviewing style, configuring linters, writing docstrings, or establishing project standards.
---

# Python Code Style & Documentation

Consistent code style and clear documentation make codebases maintainable and collaborative. This skill covers modern Python tooling, naming conventions, and documentation standards.

> **Configuration source**: all project-level configuration (line length, target Python version, linting rules, type checking strictness, tool availability) is read from `settings.json` — specifically the `python`, `python_config`, and `python_code_style_rules` objects. These are populated by `setup` from `pyproject.toml`. Do not read `pyproject.toml` directly; do not hardcode fallback defaults. See the parent `SKILL.md` for the setup guard and the shared "Running tools" convention.

> **Review mode**: when this skill is invoked as part of a read-only review (e.g. `/zolletta-metaskill review`), follow the rules in [`../reference/review-mode.md`](../reference/review-mode.md) — do not apply fixes, classify diagnostics into auto-fixable (informational) vs. not auto-fixable (findings).

## When to Use This Skill

- Setting up linting and formatting for a new project
- Writing or reviewing docstrings
- Establishing team coding standards
- Configuring ruff, mypy, or ty
- Reviewing code for style consistency

## Table 1 — Always-on rules (cannot be disabled)

| # | Area | Name |
|---|------|------|
| 1 | Naming | Descriptive snake_case filenames, no abbreviations |
| 2 | Naming | PascalCase class names |
| 4 | Naming | snake_case functions and variables |
| 5 | Naming | SCREAMING_SNAKE_CASE module-level constants |
| 6 | Imports | Grouped import order (stdlib → third-party → local) |
| 13 | Docstrings | Private functions exempt from docstrings |
| 17 | Docstrings | Test functions exempt from docstrings |
| 19 | Types | Type hints required for all public APIs |

## Table 2 — Configurable settings (stored in `settings.json` under `python_code_style_rules`)

| # | Area | Name | Key | Default |
|---|------|------|-----|---------|
| 3 | Naming | Acronyms stay uppercase in class names | `check_acronym_casing` | `true` |
| 7 | Imports | Absolute imports only, no relative imports | `check_no_relative_imports` | `true` |
| 8 | Structure | One class per file | `check_one_class_per_file` | `true` |
| 9 | Structure | Filename matches class name | `check_filename_matches_class` | `true` |
| 12 | Docstrings | Docstrings required on public classes, methods, functions | `check_public_docstrings` | `true` |
| 14 | Docstrings | No type repetition in docstring Args/Returns | `check_docstring_no_type_repeat` | `true` |
| 18 | Docstrings | Skip docstrings for obvious one-line functions | `check_skip_obvious_docstrings` | `true` |
| 20 | Formatting | Line length from project config | `check_line_length` | `true` |
| 22 | Dead code | Vulture minimum confidence | `vulture_min_confidence` | `80` |

## Detailed rule explanations

### Naming

**#1 — Descriptive snake_case filenames, no abbreviations** *(always-on)*

Module filenames use `snake_case` and spell out words: `user_repository.py`, not `usr_repo.py`. Abbreviated filenames are flagged as findings. This is a PEP 8 naming convention, not project configuration.

```python
# Good
user_repository.py
order_processing.py
http_client.py

# Avoid — abbreviations
usr_repo.py
ord_proc.py
http_cli.py
```

**#2 — PascalCase class names** *(always-on)*

Classes use `PascalCase`: `UserRepository`, `OrderProcessor`. This is PEP 8 standard.

**#3 — Acronyms stay uppercase in class names** *(configurable: `check_acronym_casing`)*

Class names keep acronyms fully uppercase: `HTTPClientFactory`, not `HttpClientFactory`. `CITesterEngine`, not `CiTesterEngine`. This is a deliberate convention common in codebases with domain-specific acronyms.

- **Enforcement**: manual review (no ruff rule for this).

**#4 — snake_case functions and variables** *(always-on)*

Functions and variables use `snake_case`: `get_user_by_email`, `retry_count`, `max_connections`. This is PEP 8 standard.

**#5 — SCREAMING_SNAKE_CASE module-level constants** *(always-on)*

Module-level constants use `SCREAMING_SNAKE_CASE`: `MAX_RETRY_ATTEMPTS`, `DEFAULT_TIMEOUT_SECONDS`, `API_BASE_URL`. This is PEP 8 standard.

### Imports

**#6 — Grouped import order** *(always-on)*

Imports are grouped in three sections, in order: standard library, third-party, local. Blank line between groups. If ruff is configured with the `I` (isort) rule, this is enforced automatically — do not restate the rules manually.

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

**#7 — Absolute imports only, no relative imports** *(configurable: `check_no_relative_imports`)*

Use `from myproject.utils import retry_decorator`, not `from ..utils import retry_decorator`. Absolute imports are more maintainable and easier to trace.

- **Enforcement**: ruff `TID25` rule or manual review.

### Structure

**#8 — One class per file** *(configurable: `check_one_class_per_file`)*

Each class lives in its own file. No exceptions for "small helper classes" or "closely related enums" — if they're worth defining, they're worth their own file. This applies to all classes, public or private.

- **Enforcement**: `scan_one_class_per_file.py` from `../scripts/python/`.

**#9 — Filename matches class name** *(configurable: `check_filename_matches_class`)*

The filename is the snake_case form of the class name: `user_repository.py` → `UserRepository`, `ci_tester_engine.py` → `CITesterEngine`. Acronyms stay uppercase in the class name but lowercase in the filename.

- **Enforcement**: `scan_one_class_per_file.py` + manual review.

### Docstrings

**#12 — Docstrings required on public classes, methods, functions** *(configurable: `check_public_docstrings`)*

All public classes, methods, and functions must have docstrings. A one-line summary is the minimum. Google-style docstrings are the convention.

- **Enforcement**: ruff `D100`–`D106` rules or manual review.

**#13 — Private functions exempt from docstrings** *(always-on)*

Functions with a leading underscore (`_helper`, `_format_output`) are implementation details, not API. They do not need docstrings. This is the complement of #12.

**#14 — No type repetition in docstring Args/Returns** *(configurable: `check_docstring_no_type_repeat`)*

Do not repeat information that the type annotation already conveys. Only include `Args:` or `Returns:` sections in a docstring when there is information the type annotation cannot express:

- Constraints on values ("must not be empty", "must be a positive integer")
- Units or formats ("seconds, not milliseconds", "ISO 8601 format")
- Side effects or mutation ("modifies the list in place")
- Non-obvious default behavior

If the type annotation fully describes the argument, a one-line summary docstring is sufficient — no `Args:`/`Returns:` section needed.

```python
# Good — one-line summary, type annotations say the rest
def get_user(user_id: str) -> User:
    """Retrieve a user by their unique identifier."""
    ...

# Good — Args only for non-obvious info
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
    """
    ...
```

> Note: `max_workers` and the return type are not in `Args:`/`Returns:` — the type annotations (`int = 4`, `-> BatchResult`) already say everything needed.

- **Enforcement**: manual review.

**#17 — Test functions exempt from docstrings** *(always-on)*

Test functions do not need docstrings — the test name is the documentation. `test_user_creation_with_valid_email_returns_user` is self-documenting.

**#18 — Skip docstrings for obvious one-line functions** *(configurable: `check_skip_obvious_docstrings`)*

One-line functions where the name and signature are self-explanatory do not need a docstring. `def get_user(user_id: str) -> User:` with a one-line body is self-documenting. This prevents noise docstrings that just restate the function name.

- **Enforcement**: manual review.

### Types

**#19 — Type hints required for all public APIs** *(always-on)*

All public classes, methods, and functions must include type annotations for parameters and return types. Enforcement is via the configured type checker (`python_config.type_checker`) with `disallow_untyped_defs` or equivalent, plus manual review for the public vs. private distinction.

### Formatting

**#20 — Line length from project config** *(configurable: `check_line_length`)*

Line length is read from `python_config.line_length` in `settings.json` (extracted by setup from `[tool.ruff] line-length`, or ruff's built-in default of 88 if unconfigured). The skill does not carry its own fallback. If ruff is available, `ruff format` handles line breaking automatically — do not reformat manually.

```python
# Good: readable line breaks (respecting python_config.line_length)
def create_user(
    email: str,
    name: str,
    role: UserRole = UserRole.MEMBER,
    notify: bool = True,
) -> User:
    ...

# Good: chain method calls clearly
result = (
    db.query(User)
    .filter(User.active == True)
    .order_by(User.created_at.desc())
    .limit(10)
    .all()
)
```

- **Enforcement**: ruff formatter.

### Dead code

**#22 — Vulture minimum confidence** *(configurable: `vulture_min_confidence`)*

If `vulture` is available (`python.vulture: true` in `settings.json`), run it to find unused code:

```bash
vulture src/ --min-confidence <vulture_min_confidence>
```

The confidence threshold is read from `python_code_style_rules.vulture_min_confidence` in `settings.json` (default: `80`). Findings below this confidence are not reported. Vulture has false positives, especially for dynamically-accessed methods — review each finding above the threshold with judgment before flagging. Report findings as low-priority issues.

If `vulture` is `false` in `settings.json`, skip dead-code detection.

## Output

When this skill runs a review, it writes its findings to a markdown file using the [report template](assets/report_template.md):

- **Path**: `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/python-code-style.md` (timestamp = run start time, via `date +%Y-%m-%d-%H-%M`)
- **Compound skills** (e.g. `zolletta-metaskill-review`) may override the folder and filename — follow their instructions instead
- **Directory setup**: the `.zolletta-metaskill/` directory and `.gitignore` entry are created by the [setup guard](../SKILL.md#setup-guard) — no manual setup needed
- **Format**: follow the [report template](assets/report_template.md) — grade at the top, tool results (ruff, type checker, vulture), auto-fixable issues (informational, do not count toward grade), findings grouped by severity with file/symbol/rule ID/issue/fix columns

## Attribution

This skill is adapted from [python-code-style](https://github.com/wshobson/agents/tree/main/plugins/python-development/skills/python-code-style) by Seth Hobson ([wshobson/agents](https://github.com/wshobson/agents)), licensed under the MIT License. Copyright (c) 2024 Seth Hobson.
