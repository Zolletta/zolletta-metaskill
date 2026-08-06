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

The one exception is PHP support: `tree-sitter` and `tree-sitter-php` are optional dependencies, installed only when PHP review is needed (`pip install zolletta-metaskill[php]`). The PHP engine degrades gracefully if these are not installed.

## Consequences

**Positive:**

- Zero install friction for Python-only projects — the scripts run with any Python 3.12+ installation.
- No version conflicts with the user's project dependencies.
- Deterministic behavior across environments.
- Reduced supply-chain attack surface.

**Negative:**

- Some tasks are harder with stdlib only (e.g., no rich terminal output). We accept the tradeoff.
- PHP AST analysis requires tree-sitter, which is an optional dependency. Users who want PHP review must install it separately.

**Neutral:**

- The stdlib-only constraint applies to scanning scripts, not to the skill infrastructure itself. The project uses `uv`, `ruff`, `pytest`, `mypy`, `ty`, and `vulture` for development — these are dev dependencies, not runtime requirements for the scanning scripts.
