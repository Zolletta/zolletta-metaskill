---
name: python-code-style
version: 1.1.0
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

| #   | Area       | Name                                                |
|---|---|---|
| 1   | Naming     | Descriptive snake_case filenames, no abbreviations  |
| 2   | Naming     | PascalCase class names                              |
| 4   | Naming     | snake_case functions and variables                  |
| 5   | Naming     | SCREAMING_SNAKE_CASE module-level constants         |
| 6   | Imports    | Grouped import order (stdlib → third-party → local) |
| 13  | Docstrings | Private functions exempt from docstrings            |
| 17  | Docstrings | Test functions exempt from docstrings               |
| 19  | Types      | Type hints required for all public APIs             |

## Table 2 — Configurable settings (stored in `settings.json` under `python_code_style_rules`)

| #   | Area       | Name                                                      | Key                              | Default   |
|---|---|---|---|---|
| 3   | Naming     | Acronyms stay uppercase in class names                    | `check_acronym_casing`           | `true`    |
| 7   | Imports    | Absolute imports only, no relative imports                | `check_no_relative_imports`      | `true`    |
| 8   | Structure  | One class per file                                        | `check_one_class_per_file`       | `true`    |
| 9   | Structure  | Filename matches class name                               | `check_filename_matches_class`   | `true`    |
| 12  | Docstrings | Docstrings required on public classes, methods, functions | `check_public_docstrings`        | `true`    |
| 14  | Docstrings | No type repetition in docstring Args/Returns              | `check_docstring_no_type_repeat` | `true`    |
| 18  | Docstrings | Skip docstrings for obvious one-line functions            | `check_skip_obvious_docstrings`  | `true`    |
| 20  | Formatting | Line length from project config                           | `check_line_length`              | `true`    |
| 22  | Dead code  | Vulture minimum confidence + unused `__all__` exports     | `vulture_min_confidence`         | `80`      |

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

Class names keep acronyms fully uppercase: `HTTPClientFactory`, not `HttpClientFactory`. `APIGateway`, not `ApiGateway`. This is a deliberate convention common in codebases with domain-specific acronyms.

- **Enforcement**: `scan_acronym_casing.py` from `../src/zolletta_metaskill/scanners/` (deterministic). The scanner splits each PascalCase class name into words, checks each word against the configured acronym list, and flags any word that case-insensitively matches an acronym but isn't all-uppercase.

```bash
python3 ../src/zolletta_metaskill/scanners/scan_acronym_casing.py src/ --acronyms CI,MR,AST,DI
```

The acronym list is built additively:
1. **Shipped base**: `src/zolletta_metaskill/scanners/assets/acronyms.json` (common SE acronyms: CI, CD, CICD, HTTP, HTTPS, JSON, SQL, URL, etc.) — always loaded
2. **Project-specific**: `python_code_style_rules.acronyms` in `settings.json` — merged with the shipped list (additive, not replacing). Use this for domain-specific acronyms not in the shipped list (e.g. `XML`, `SVG`)
3. **`--acronyms` CLI flag**: fully replaces both (for testing/debugging only)

To configure project-specific acronyms, add them to `settings.json`:
```json
"python_code_style_rules": {
    "acronyms": ["CI", "MR", "AST", "DI"]
}
```

> The scanner is the single source of truth for this rule. Do not manually flag class names that the scanner doesn't flag — the word-splitting + acronym matching is the objective criterion.

**#4 — snake_case functions and variables** *(always-on)*

Functions and variables use `snake_case`: `get_user_by_email`, `retry_count`, `max_connections`. This is PEP 8 standard.

**#5 — SCREAMING_SNAKE_CASE module-level constants** *(always-on)*

Module-level **value constants** (strings, numbers, tuples, etc.) use `SCREAMING_SNAKE_CASE`: `MAX_RETRY_ATTEMPTS`, `DEFAULT_TIMEOUT_SECONDS`, `API_BASE_URL`. This is PEP 8 standard.

**Exception — enum/class aliases:** module-level names that re-export an enum member or a class-like constant may use `PascalCase`, following the "**PascalCase for the class, SCREAMING for the constant**" convention. The enum member on the right-hand side is already in `SCREAMING_SNAKE_CASE`; the alias name follows the class/container convention.

```python
# Good — PascalCase alias of a SCREAMING enum member
AppScope = Scope.APP
RuntimeScope = Scope.REQUEST

# Good — SCREAMING_SNAKE_CASE for plain value constants
MAX_RETRY_ATTEMPTS = 3
DEFAULT_TIMEOUT_SECONDS = 30
API_BASE_URL = "https://api.example.com"

# Flag — PascalCase used for a plain value constant (no enum/class on RHS)
MaxRetries = 3  # should be MAX_RETRIES
```

**Decision rule for reviewers:**
- If the right-hand side is an enum member access (`Enum.MEMBER`), a class, or another PascalCase alias → `PascalCase` is valid. **Do not flag.**
- If the right-hand side is a plain value (string, int, float, tuple, list, dict, `True`/`False`/`None`) → `SCREAMING_SNAKE_CASE` is required. **Flag PascalCase as a finding.**
- Dead-code detection (unused aliases) is **vulture's responsibility**, not this rule's. Do not flag an alias as unused under rule #5 — flag it under rule #22 (vulture) if vulture detects it.

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

- **Enforcement**: `scan_one_class_per_file.py` from `../src/zolletta_metaskill/scanners/`.

**#9 — Filename matches class name** *(configurable: `check_filename_matches_class`)*

The filename is the snake_case form of the class name: `user_repository.py` → `UserRepository`, `api_gateway.py` → `APIGateway`. Acronyms stay uppercase in the class name but lowercase in the filename.

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

**#22 — Vulture minimum confidence + unused `__all__` exports** *(configurable: `vulture_min_confidence`)*

If `vulture` is available (`python.vulture: true` in `settings.json`), run it to find unused code:

```bash
vulture src/ --min-confidence <vulture_min_confidence>
```

The confidence threshold is read from `python_code_style_rules.vulture_min_confidence` in `settings.json` (default: `80`). Findings below this confidence are not reported. Vulture has false positives, especially for dynamically-accessed methods — review each finding above the threshold with judgment before flagging. Report findings as low-priority issues.

If `vulture` is `false` in `settings.json`, skip dead-code detection.

**Supplementary check — unused `__all__` exports:** vulture treats every name in `__all__` as "used" (public API export), so it never flags `__all__` entries that are never imported anywhere. This is a known gap. After running vulture, also run:

```bash
python3 ../src/zolletta_metaskill/scanners/scan_unused_all_exports.py src/
```

This scanner cross-references every `__all__` entry against actual import statements across the source tree. Names listed in `__all__` but never imported by any other module are reported as unused exports. Report these as low-priority findings (same severity as vulture findings).

**Do not duplicate**: if vulture already flags a symbol as unused, do not also report it via the `__all__` scanner — report it once under vulture. The `__all__` scanner only catches what vulture misses.

## Output

When this skill runs a review, it writes its findings to a markdown file using the [report template](assets/report_template.md):

- **Path**: `.zolletta-metaskill/reports/<YYYY-MM-DD-HH-MM>/python-code-style.md` (timestamp = run start time, via `date +%Y-%m-%d-%H-%M`)
- **Compound skills** (e.g. `zolletta-metaskill-review`) may override the folder and filename — follow their instructions instead
- **Directory setup**: the `.zolletta-metaskill/` directory and `.gitignore` entry are created by the [setup guard](../SKILL.md#setup-guard) — no manual setup needed
- **Format**: follow the [report template](assets/report_template.md) — grade at the top, tool results (ruff, type checker, vulture), auto-fixable issues (informational, do not count toward grade), findings grouped by severity with file/symbol/rule ID/issue/fix columns

## Attribution

This skill is adapted from [python-code-style](https://github.com/wshobson/agents/tree/main/plugins/python-development/skills/python-code-style) by Seth Hobson ([wshobson/agents](https://github.com/wshobson/agents)), licensed under the MIT License. Copyright (c) 2024 Seth Hobson.
