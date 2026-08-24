---
audience: human, ai
status: stable
skills: []
---

# How-to Guides

Practical steps to achieve a specific goal. Aimed at practitioners.

## Getting things done

Installation, project setup, and running the full review pipeline.

| Document                                | Description                                                         |
|-----------------------------------------|---------------------------------------------------------------------|
| [Install](install.md)                   | Install Zolletta-metaskill via `install.sh` or manual clone/symlink |
| [Set up a project](setup-project.md)    | Configure Zolletta-metaskill for a new project                      |
| [Run a full review](run-full-review.md) | Execute the complete review pipeline                                |

## Code review

Language-agnostic checks for style, test quality, and structural issues.

| Document                                               | Description                                                     |
|--------------------------------------------------------|-----------------------------------------------------------------|
| [Review code style](code/review-code-style.md)         | Check naming, docstrings, formatting (language-agnostic)        |
| [Review test code](code/review-test-code.md)           | Check test structure, coverage gaps, naming (language-agnostic) |
| [Detect God classes](code/detect-god-classes.md)       | Find God classes and SOLID violations                           |
| [Split a God test class](code/split-god-test-class.md) | Break a test class into per-SUT files                           |
| [Run an external review](code/run-external-review.md)  | Delegate review to an external model                            |

## Python-specific

Python-focused style and test reviews with ruff, mypy, and pytest.

| Document                                                  | Description                                |
|-----------------------------------------------------------|--------------------------------------------|
| [Review Python style](code/python/review-python-style.md) | Python-specific style, linting, typing     |
| [Review Python tests](code/python/review-python-tests.md) | Python-specific test patterns and coverage |

## Documentation review

Audit documentation for drift, staleness, and Diátaxis structure compliance.

| Document                                                              | Description                                    |
|-----------------------------------------------------------------------|------------------------------------------------|
| [Review documentation](code/../documentation/review-documentation.md) | Audit docs for drift, staleness, and structure |
