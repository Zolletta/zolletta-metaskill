---
audience: human, ai
status: stable
skills:
  [setup, review, patterns, documentor, external-review, python-code-style, python-testing-patterns]
---

# Zolletta-MetaSkill Documentation

The documentation follows the [Diátaxis framework](https://diataxis.fr/), organising content into four quadrants: tutorials, how-to guides, reference, and explanation.

## Quadrants

| Quadrant     | Purpose                                          | Audience                     |
|---|---|---|
| **Tutorials**    | Step-by-step lessons to learn the skills        | Newcomers                    |
| **How-to Guides**| Practical steps to achieve a specific goal      | Practitioners                |
| **Reference**    | Accurate technical description of the tools     | Users who need facts         |
| **Explanation**  | Background, principles, and design choices      | Readers who want context     |

## Tutorials

| Document | Description |
|---|---|
| [Getting Started](tutorials/getting-started.md) | Install, set up, and run your first review |

## How-to Guides

### Getting things done

| Document | Description |
|---|---|
| [Install](how-to/install.md) | Install zolletta-metaskill and its dependencies |
| [Set up a project](how-to/setup-project.md) | Configure zolletta-metaskill for a new project |
| [Run a full review](how-to/run-full-review.md) | Execute the complete review pipeline |

### Code review

| Document | Description |
|---|---|
| [Review code style](how-to/code/review-code-style.md) | Check naming, docstrings, formatting (language-agnostic) |
| [Review test code](how-to/code/review-test-code.md) | Check test structure, coverage gaps, naming (language-agnostic) |
| [Detect God classes](how-to/code/detect-god-classes.md) | Find God classes and SOLID violations |
| [Split a God test class](how-to/code/split-god-test-class.md) | Break a test class into per-SUT files |
| [Run an external review](how-to/code/run-external-review.md) | Delegate review to an external model |

### Python-specific

| Document | Description |
|---|---|
| [Review Python style](how-to/code/python/review-python-style.md) | Python-specific style, linting, typing |
| [Review Python tests](how-to/code/python/review-python-tests.md) | Python-specific test patterns and coverage |

### Documentation review

| Document | Description |
|---|---|
| [Review documentation](how-to/documentation/review-documentation.md) | Audit docs for drift, staleness, and structure |

## Reference

### Code review tools

| Document | Description |
|---|---|
| [Scripts reference](reference/code/scripts.md) | All scanning scripts: usage, options, examples |
| [Review mode](reference/code/review-mode.md) | Read-only review conventions |
| [Code exploration](reference/code/code-exploration.md) | tokensave decision tree and task templates |
| [tokensave](reference/code/tokensave.md) | tokensave MCP tools reference |
| [Python code style](reference/code/python/python-code-style.md) | Python style rules and configurable toggles |

### Documentation tools

| Document | Description |
|---|---|
| [Drift detection tools](reference/documentation/drift-detection-tools.md) | drift_analyzer, staleness scorer, API validator, link checker |
| [Workflows & tools](reference/documentation/workflows-and-tools.md) | Quick start, 5 core workflows, CI recipes |
| [Scoring & categories](reference/documentation/scoring-and-categories.md) | Staleness scoring model, drift categories, troubleshooting |
| [Operational rules](reference/documentation/operational-rules.md) | Tool invocation conventions and drift report format |

### Project configuration

| Document | Description |
|---|---|
| [Settings schema](reference/settings-schema.md) | Full field-by-field reference for `settings.json` |
| [Subcommands](reference/subcommands.md) | All zolletta-metaskill subcommands |
| [Frontmatter](reference/frontmatter.md) | SKILL.md frontmatter fields |
| [Reports](reference/reports.md) | Report file format and templates |
| [Tool messages](reference/tool-messages.md) | "Not installed" messages for the tool-failure handler |
| [Reference index](reference/index.md) | Full directory tree of the reference quadrant |

## Explanation

### Code review principles

| Document | Description |
|---|---|
| [General principles](explanation/code/general-principles.md) | SOLID, KISS, composition over inheritance, God class detection |
| [Structural conventions](explanation/code/structural-conventions.md) | One class per file, test mirroring, naming, test splitting |
| [False positive prevention](explanation/code/false-positive-prevention.md) | Suppression rules to avoid noisy reports |

### Language-specific patterns

| Document | Description |
|---|---|
| [Python review patterns](explanation/code/python/python-review-patterns.md) | Strategy autodiscovery, Protocol vs ABC |
| [PHP review patterns](explanation/code/php/php-review-patterns.md) | Strategy autodiscovery, interface vs abstract, traits |

### Documentation principles

| Document | Description |
|---|---|
| [Documentation standards](explanation/documentation/standards.md) | Docs-as-code principles and the four types of documentation |
| [README structure](explanation/documentation/readme.md) | README best practices and anti-patterns |
| [API documentation](explanation/documentation/api.md) | Function, class, and module documentation patterns |
| [Changelog conventions](explanation/documentation/changelog.md) | Keep-a-Changelog format and rules |
| [Architecture Decision Records](explanation/documentation/adr.md) | ADR format and best practices |
| [Drift prevention](explanation/documentation/drift-prevention.md) | Coupling strategies, CI gates, review checklists |
