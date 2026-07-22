---
audience: human, ai
status: stable
skills: [setup, review, patterns, documentor, external-review, python-code-style, python-testing-patterns]
---

# Documentation Index

The Zolletta-MetaSkill documentation follows the [Diátaxis framework](https://diataxis.fr/), organising content into four quadrants: tutorials, how-to guides, reference, and explanation.

## Full tree

```text
docs/
├── tutorials/
│   └── getting-started.md
├── how-to/
│   ├── code/
│   │   ├── python/
│   │   │   ├── review-python-style.md
│   │   │   └── review-python-tests.md
│   │   ├── detect-god-classes.md
│   │   ├── review-code-style.md
│   │   ├── review-test-code.md
│   │   ├── run-external-review.md
│   │   └── split-god-test-class.md
│   ├── documentation/
│   │   └── review-documentation.md
│   ├── install.md
│   ├── run-full-review.md
│   └── setup-project.md
├── explanation/
│   ├── code/
│   │   ├── php/
│   │   │   └── php-review-patterns.md
│   │   ├── python/
│   │   │   └── python-review-patterns.md
│   │   ├── false-positive-prevention.md
│   │   ├── general-principles.md
│   │   └── structural-conventions.md
│   └── documentation/
│       ├── adr.md
│       ├── api.md
│       ├── changelog.md
│       ├── readme.md
│       └── standards.md
└── reference/
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
    │   └── scoring-and-categories.md
    ├── frontmatter.md
    ├── index.md
    ├── reports.md
    ├── settings-schema.md
    ├── subcommands.md
    └── tool-messages.md
```

## Quadrant guide

| Quadrant | Purpose | Audience |
|----------|---------|----------|
| **Tutorials** | Learning-oriented, step-by-step lessons | Newcomers |
| **How-to Guides** | Task-oriented, practical steps to achieve a goal | Practitioners |
| **Reference** | Information-oriented, accurate technical description | Users who need facts |
| **Explanation** | Understanding-oriented, clarification and background | Readers who want context |
