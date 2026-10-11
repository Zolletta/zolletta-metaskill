# ADR-0004: Python stdlib only for scanning scripts

## Status

Accepted

## Context

The project ships scanning scripts that analyze source code: class metrics, SOLID violations, test structure, API doc validation, drift detection, and staleness scoring. These scripts run inside the review pipeline and must be fast, portable, and deterministic.

Using external dependencies (e.g., `rich` for output, `tomli` for TOML parsing, `tree-sitter` for AST) would add install friction, version compatibility issues, and potential supply-chain risk. Some users run the skills in environments with limited network access or strict dependency policies.

## Decision

All scanning scripts use Python 3.12+ standard library only. No external dependencies are required for the core scanning functionality.

This means:

- TOML parsing uses `tomllib` (available since Python 3.11, guaranteed on 3.12+).
- AST analysis uses the `ast` module for Python source.
- Output is plain text or JSON via `json.dumps`.
- File operations use `pathlib` and `os`.
- Subprocess calls use `subprocess` for git and grep.

The one exception is PHP support. Its two dependencies are deliberately of different kinds:

- **`tree-sitter` is a hard runtime dependency.** `php_engine.py` imports `from tree_sitter import Node, Parser, Tree` at module scope, so without it that module fails to import rather than degrading gracefully. It is declared in `dependencies`.
- **`tree-sitter-php` is an optional dependency**, declared as the `[php]` extra (`pip install 'zolletta-metaskill[php]'`) and imported lazily, only when a parser is first built. Without it `PHPEngine` still imports and still satisfies the `LanguageEngine` protocol; `parse_module` raises an `ImportError` carrying the install command, and the PHP scanners report as skipped.

> **Amended.** This section previously described *both* packages as optional. That was wrong: `tree-sitter` was declared in `dependencies` and imported at module scope, and `pyproject.toml` had no `[project.optional-dependencies]` section at all, so the `[php]` extra it referenced did not exist. The tell was a `mypy` override for `tree_sitter.*` with `ignore_missing_imports = true` — configuration for the optional world that packaging had drifted away from. `tree-sitter-php` is genuinely optional and its degradation path is covered by `tests/core/engine/test_php_engine.py`.

## Consequences

**Positive:**

- Zero install friction for Python-only projects — the scripts run with any Python 3.12+ installation. (Amended: `tree-sitter` is a hard dependency, so this now means "one small transitive dependency" rather than "nothing".)
- No version conflicts with the user's project dependencies.
- Deterministic behavior across environments.
- Reduced supply-chain attack surface.

**Negative:**

- Some tasks are harder with stdlib only (e.g., no rich terminal output). We accept the tradeoff.
- PHP AST analysis requires `tree-sitter`, which is a hard dependency rather than an optional one — so a Python-only project pays for it on install even though it never invokes it. We accept this so that PHP review degrades gracefully rather than not at all.
- PHP AST analysis requires the `tree-sitter-php` grammar as well, which is genuinely optional. Users who want PHP review must install it separately.

**Neutral:**

- The stdlib-only constraint applies to scanning scripts, not to the skill infrastructure itself. The project uses `uv`, `ruff`, `pytest`, `mypy`, `ty`, and `vulture` for development — these are dev dependencies, not runtime requirements for the scanning scripts.
