# ADR-0009: Inline shell replaced with testable Python scripts

## Status

Accepted

## Context

The setup skill originally used inline shell commands for detection: `grep` for language markers, `test -f` for config files, `cat` for reading config. These commands were embedded directly in the SKILL.md procedure steps.

Inline shell commands are difficult to test, non-portable (shell syntax varies across platforms), and non-deterministic (different shells, different grep versions). When a detection step failed, debugging required re-running the entire setup procedure.

## Decision

Six detection scripts under `src/zolletta_metaskill/setup/` replace the inline shell commands:

- `ensure_global_gitignore.py` — adds `.zolletta-metaskill/` to the user's global `~/.gitignore`
- `detect_language.py` — detects the project language from marker files
- `detect_pyproject_sections.py` — detects Python tools from `pyproject.toml` sections
- `detect_doc_config.py` — detects the documentation directory (`.backstage/` or `docs/`)
- `detect_php_tools.py` — detects PHP tools from `composer.json`
- `detect_companion_skills.py` — detects companion implementation skills

Each script:
- Is a standalone Python file using stdlib only.
- Has a `detect_*()` function that can be unit-tested directly.
- Has a `main()` CLI entry point that outputs JSON or plain text.
- Is covered by a test suite with 100% coverage.

## Consequences

**Positive:**
- Detection is deterministic — the same input always produces the same output, regardless of shell or platform.
- Each detection step is unit-testable — tests create temp directories with marker files and assert the detection result.
- 100% coverage on the setup package is achievable and maintained in CI.
- The setup SKILL.md is leaner — it calls scripts by name instead of embedding shell logic.

**Negative:**
- Six scripts to maintain instead of inline commands. Each script needs its own test file.
- The scripts add a Python dependency to setup — setup now requires Python 3.8+ to run, not just a shell.

**Neutral:**
- The scripts are part of the `zolletta_metaskill` Python package, installed alongside the skill. They are not standalone tools — they are invoked by the setup skill via `python3 <script>`.
