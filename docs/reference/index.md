---
audience: human, ai
status: stable
skills:
  [setup, review, patterns, documentor, external-review, python-code-style, python-testing-patterns]
---

# Reference Index

Technical reference material for zolletta-metaskill. For the full documentation index across all quadrants, see [docs/index.md](../index.md).

## Tree

```text
reference/
├── code/
│   ├── python/
│   │   └── python-code-style.md
│   ├── code-exploration.md
│   ├── review-mode.md
│   ├── scripts.md
│   └── tokensave.md
├── documentation/
│   ├── drift-detection-tools.md
│   ├── operational-rules.md
│   ├── scoring-and-categories.md
│   └── workflows-and-tools.md
├── frontmatter.md
├── index.md
├── reports.md
├── settings-schema.md
├── subcommands.md
└── tool-messages.md
```

## Files

| File                                                                               | Description                                                   |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| [code/scripts.md](code/scripts.md)                                                 | All scanning scripts: usage, options, examples                |
| [code/review-mode.md](code/review-mode.md)                                         | Read-only review conventions                                  |
| [code/code-exploration.md](code/code-exploration.md)                               | tokensave decision tree and task templates                    |
| [code/tokensave.md](code/tokensave.md)                                             | tokensave MCP tools reference                                 |
| [code/python/python-code-style.md](code/python/python-code-style.md)               | Python style rules and configurable toggles                   |
| [documentation/drift-detection-tools.md](documentation/drift-detection-tools.md)   | drift_analyzer, staleness scorer, API validator, link checker |
| [documentation/workflows-and-tools.md](documentation/workflows-and-tools.md)       | Quick start, 5 core workflows, CI recipes                     |
| [documentation/scoring-and-categories.md](documentation/scoring-and-categories.md) | Staleness scoring model, drift categories, troubleshooting    |
| [documentation/operational-rules.md](documentation/operational-rules.md)           | Tool invocation conventions and drift report format           |
| [settings-schema.md](settings-schema.md)                                           | Full field-by-field reference for `settings.json`             |
| [subcommands.md](subcommands.md)                                                   | All zolletta-metaskill subcommands                            |
| [frontmatter.md](frontmatter.md)                                                   | SKILL.md frontmatter fields                                   |
| [reports.md](reports.md)                                                           | Report file format and templates                              |
| [tool-messages.md](tool-messages.md)                                               | "Not installed" messages for the tool-failure handler         |
