# Tool "not installed" messages

Shared messages printed by the `setup` subcommand and the tool-failure handler when a tool is not available. Each message explains **why zolletta-metaskill benefits from the tool** and links to the project homepage (where applicable).

These messages must be printed verbatim (or close to it) by any subcommand that detects a tool is missing — either during setup or via the tool-failure handler.

> **Python skills**: `python-code-style` and `python-testing-patterns` are bundled inside this meta-skill, so they are always available. No "not installed" message is needed for them — the `*_available` flags in `settings.json` only reflect whether the project language is Python.

---

## tokensave

```text
ℹ tokensave is not installed.

tokensave provides a semantic code-graph index (symbols, call/callee
relationships, impact radius). Zolletta-metaskill uses it to:
  - understand class responsibilities without reading full files (patterns)
  - assess blast radius before proposing God-class splits (patterns)
  - verify documented symbols exist without grep (documentor)
  - find affected tests after a change (review, external-review)

Without tokensave, zolletta-metaskill falls back to grep + targeted reads (slower,
higher token usage).

Homepage: https://github.com/aovestdipaperino/tokensave
```

---

## uv

```text
ℹ uv is not installed.

uv is a fast Python package manager and project manager. Zolletta-metaskill uses it
to run Python tools (ruff, mypy, pytest) in the project environment.
Without uv, zolletta-metaskill falls back to calling tools directly.

Homepage: https://github.com/astral-sh/uv
```

---

## ruff

```text
ℹ ruff is not installed.

ruff is an all-in-one Python linter and formatter. It replaces flake8,
isort, and black with a single fast tool. Zolletta-metaskill uses it to check and
format Python source code. Without ruff, the code-style review cannot
run automated linting or formatting checks.

Homepage: https://github.com/astral-sh/ruff
```

---

## pytest

```text
ℹ pytest is not installed.

pytest is the standard Python test runner. Zolletta-metaskill uses it to run tests
and verify coverage. Without pytest, the testing-patterns review cannot
execute tests or report coverage gaps.

Homepage: https://github.com/pytest-dev/pytest
```

---

## ty

```text
ℹ ty is not installed.

ty is a fast Python type checker based on red-knot. Zolletta-metaskill uses it as
an alternative to mypy for type checking. Without ty, type checking falls
back to mypy (if available) or is skipped.

Homepage: https://github.com/astral-sh/ty
```

---

## vulture

```text
ℹ vulture is not installed.

vulture finds dead code (unused classes, functions, variables, imports)
in Python codebases. Zolletta-metaskill uses it to detect unreachable code and
unused symbols during code-style review. Without vulture, dead-code
detection is skipped.

Homepage: https://github.com/jendrikseipp/vulture
```

---

## mypy

```text
ℹ mypy is not installed.

mypy is a static type checker for Python. Zolletta-metaskill uses it to verify
type annotations and catch type errors before runtime. Without mypy
(and without ty), the code-style review cannot run type checking.

Homepage: https://github.com/python/mypy
```
