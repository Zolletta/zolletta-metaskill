---
audience: ai
status: stable
skills: [setup]
---

# Tool "not installed" messages

Shared messages printed by the `setup` subcommand and the tool-failure handler when a tool is not available. Each message explains **why zolletta-metaskill benefits from the tool** and links to the project homepage (where applicable).

These messages must be printed verbatim (or close to it) by any subcommand that detects a tool is missing — either during setup or via the tool-failure handler.

> **Python skills**: `python-code-style` and `python-testing-patterns` are bundled inside this meta-skill, so they are always available. No "not installed" message is needed for them — the `*_available` flags in `settings.json` only reflect whether the project language is Python.

---

# Tool "unconfigured" warnings

Shared warnings printed by the `setup` subcommand when a Python tool is **available** (the command exists) but has **no `[tool.*]` section in `pyproject.toml`**. Each warning states the tool's effective built-in defaults (so the review runs against a known configuration) and links to the full options reference so the user can broaden the review if they choose.

These warnings are **informational only** — setup never modifies `pyproject.toml`. The effective defaults are also written into the `python.*` configuration fields in `settings.json` so review subcommands report against the configuration the tool will actually use, not a skill-invented fallback.

> **Distinguish "absent section" from "present but minimal"**: the warning fires only when the `[tool.*]` section is entirely missing. If the section exists (even with a single key like `line-length = 100`), the tool is considered configured and no warning is printed — the tool merges the user's settings with its own defaults.

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

---

# Tool "unconfigured" warnings — per tool

## ruff (unconfigured)

```text
⚠ ruff is available but has no [tool.ruff] section in pyproject.toml.

ruff will run with its built-in defaults:
  line-length = 88
  target-version = "py310"
  select = ["E4", "E7", "E9", "F"]
  ignore = []
  format.quote-style = "double"

The review will still run, but with a minimal rule set (Pyflakes + a subset of
pycodestyle). Add a [tool.ruff] section to enable broader checks (e.g. isort,
bugbear, pyupgrade, simplify).

See all available options at: https://docs.astral.sh/ruff/settings/
```

## mypy (unconfigured)

```text
⚠ mypy is available but has no [tool.mypy] section in pyproject.toml.

mypy will run with its built-in defaults:
  strict = false
  python_version = (not pinned; uses the running interpreter)
  no per-module overrides

The review will still run, but with lenient type checking. Add a [tool.mypy]
section to enable strict mode, warn_return_any, disallow_untyped_defs, and
per-module overrides (e.g. to relax rules for tests.*).

See all available options at: https://mypy.readthedocs.io/en/stable/config_file.html
```

## ty (unconfigured)

```text
⚠ ty is available but has no [tool.ty] section in pyproject.toml.

ty will run with its built-in defaults:
  rules.all = "warn"
  python-version = (detected from the project environment)
  no overrides

The review will still run, but with default rule severities. Add a [tool.ty]
section to promote rules to errors, ignore specific rules, or configure
per-path overrides.

See all available options at: https://docs.astral.sh/ty/reference/configuration/
```

## pytest (unconfigured)

```text
⚠ pytest is available but has no [tool.pytest.ini_options] section in pyproject.toml.

pytest will run with its built-in defaults:
  no addopts
  testpaths = (current directory, recursively)
  minversion = (not enforced)

The review will still run tests, but with default discovery and no custom
options. Add a [tool.pytest.ini_options] section to set addopts, testpaths,
markers, and filterwarnings.

See all available options at: https://docs.pytest.org/en/stable/reference/reference.html#ini-options-ref
```
