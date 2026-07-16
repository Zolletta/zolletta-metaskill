# Tool "not installed" messages

Shared messages printed by the `setup` subcommand and the tool-failure handler when tokensave or a Python review skill is not available. Each message explains **why zolletta benefits from the tool/skill** and links to the project homepage (where applicable).

These messages must be printed verbatim (or close to it) by any subcommand that detects a tool is missing — either during setup or via the tool-failure handler when an MCP call returns tool-not-found / server-not-found, or when a skill invoke returns "Skill not found".

---

## tokensave

```text
ℹ tokensave is not installed.

tokensave provides a semantic code-graph index (symbols, call/callee
relationships, impact radius). Zolletta meta-skill uses it to:
  - understand class responsibilities without reading full files (patterns)
  - assess blast radius before proposing God-class splits (patterns)
  - verify documented symbols exist without grep (documentor)
  - find affected tests after a change (review, external-review)

Without tokensave, zolletta falls back to grep + targeted reads (slower,
higher token usage).

Homepage: https://github.com/aovestdipaperino/tokensave
```

---

## python-code-style

```text
ℹ python-code-style skill is not installed.

python-code-style reviews Python source code for style, linting, formatting,
naming, docstrings, and type annotations. Zolletta uses it during /zolletta
review to check all Python source in src/ for:
  - ruff format / ruff check compliance
  - ty / mypy type checking
  - PEP 8 naming conventions
  - Google-style docstring completeness
  - import organization

Without python-code-style, the review skips the code-style area. The design
patterns and documentation reviews still run, but the overall grade will not
include a code-style score.

Install: add the skill to ~/.config/devin/skills/python-code-style/
```

---

## python-testing-patterns

```text
ℹ python-testing-patterns skill is not installed.

python-testing-patterns reviews Python test code for testing best practices.
Zolletta uses it during /zolletta review to check all test code in tests/
for:
  - test isolation and naming conventions
  - coverage gaps
  - mocking patterns and fixture design
  - AAA (Arrange-Act-Assert) structure

Without python-testing-patterns, the review skips the testing area. The
design patterns and documentation reviews still run, but the overall grade
will not include a testing score.

Install: add the skill to ~/.config/devin/skills/python-testing-patterns/
```
