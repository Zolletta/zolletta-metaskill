# Tool "not installed" messages

Shared messages printed by the `setup` subcommand and the tool-failure handler when tokensave is not available. The message explains **why zolletta benefits from the tool** and links to the project homepage.

These messages must be printed verbatim (or close to it) by any subcommand that detects tokensave is missing — either during setup or via the tool-failure handler when an MCP call returns tool-not-found / server-not-found.

> **Python skills**: `python-code-style` and `python-testing-patterns` are bundled inside this meta-skill, so they are always available. No "not installed" message is needed for them — the `*_available` flags in `settings.json` only reflect whether the project language is Python.

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
