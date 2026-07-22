---
audience: human, ai
status: stable
skills: [documentor]
---

# Documentation Standards

Expert knowledge for writing, maintaining, and evaluating technical documentation across all common formats.

> This file narrows down any eventual general rule about documentation, i.e. [documentation-rules.md](~/.agents/documentation-rules.md). All files in `~/.agents/` are the single source of truth for their domain.

## Documentation-as-Code Principles

### Core Principles

1. **Docs live with code** — Same repository, same branch, same PR
2. **Docs are reviewed** — Documentation changes go through code review
3. **Docs are tested** — Link checking, spell checking, build verification
4. **Docs are versioned** — Tagged with releases, branches for versions
5. **Docs are automated** — Generated where possible, validated in CI

### File Organization

```text
project/
├── README.md              # Entry point
├── CONTRIBUTING.md        # How to contribute
├── CHANGELOG.md           # Version history
├── LICENSE                # License text
├── docs/
│   ├── getting-started.md # Expanded setup guide
│   ├── architecture.md    # System design
│   ├── api/               # API reference
│   ├── guides/            # How-to guides
│   ├── tutorials/         # Step-by-step tutorials
│   └── adr/               # Architecture decisions
└── src/                   # Source with inline docs
```

### The Four Types of Documentation

Following the Diataxis framework:

| Type              | Purpose                | Approach                                 |
| ----------------- | ---------------------- | ---------------------------------------- |
| **Tutorials**     | Learning-oriented      | Step-by-step lessons, hands-on           |
| **How-to Guides** | Task-oriented          | Practical steps to achieve a goal        |
| **Reference**     | Information-oriented   | Accurate, complete technical description |
| **Explanation**   | Understanding-oriented | Clarification, background, reasoning     |

Each type serves a different need. A healthy project has all four.

## Markdown formatting

### Tables

When writing GitHub-flavored markdown tables, use compact separator rows with no inner spaces and no alignment colons, and align columns so pipes line up vertically:

```markdown
| Header A | Header B | Header C |
| -------- | -------- | -------- |
| cell     | cell     | cell     |
| longer   | longer   | longer   |
```

Never use spaced or colon-padded separators like `| --- |`, `|:---|`, or `| ---: |`. Column content must be padded with spaces so that every pipe character in the same column is on the same character position.
