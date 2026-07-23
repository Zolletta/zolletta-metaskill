---
audience: human, ai
status: stable
skills: [documentor]
---

# README Structure

A well-structured README is the front door to any project. Follow this ordering for maximum clarity.

## Essential Sections (in order)

1. **Title and Description** — One sentence explaining what the project does. No jargon in the first paragraph.
2. **Badges** — Build status, version, license, coverage. Keep to 4-6 maximum.
3. **Table of Contents** — Required for READMEs longer than 100 lines.
4. **Installation** — Copy-pasteable commands. Cover all supported platforms. Include prerequisites.
5. **Quick Start / Usage** — The shortest path from install to working example. Under 10 lines of code.
6. **API Reference** — Or link to full API docs. Include the most-used functions inline.
7. **Configuration** — Environment variables, config files, CLI flags. Use tables.
8. **Examples** — Real-world use cases beyond the quick start. Link to example directory if extensive.
9. **Architecture** — High-level diagram or description for contributors. Can link to ARCHITECTURE.md.
10. **Contributing** — Or link to CONTRIBUTING.md. Include setup instructions for development.
11. **License** — State the license and link to LICENSE file.
12. **Changelog** — Or link to CHANGELOG.md.

## README Anti-Patterns

- Wall of text with no headings
- Installation instructions that assume specific OS
- Examples that reference files not in the repo
- Badges that point to broken CI pipelines
- "TODO" placeholders left in published README
- Version numbers hardcoded in multiple places
- Screenshots from 3 versions ago
