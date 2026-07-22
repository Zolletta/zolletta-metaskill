---
audience: human, ai
status: stable
skills: [setup, review, patterns, documentor, external-review, python-*]
---

# Frontmatter Reference

Every documentation file in the `docs/` tree uses YAML frontmatter to declare its audience, stability status, and associated skills. This metadata enables automated tooling (staleness scoring, drift detection, cross-referencing) and helps reviewers understand the purpose of each file at a glance.

## Fields

### `audience`

**Type**: comma-separated list of strings

Declares who the document is written for. Valid values:

- `human` — the document is intended for human readers (developers, contributors, users)
- `ai` — the document is intended for AI agents (skills, subagents, review tools)

Most documents are `audience: human, ai` — they serve both human readers and AI agents that load them as reference material. Some files (e.g. `tool-messages.md`) are `audience: ai` only because they contain verbatim messages printed by the setup subcommand, not prose for human consumption.

### `status`

**Type**: string

Declares the stability of the document. Valid values:

- `stable` — the document is current and authoritative. Changes go through review.
- `draft` — the document is work-in-progress. Content may be incomplete or subject to significant revision.
- `deprecated` — the document is no longer current. A replacement exists or is planned.

### `skills`

**Type**: YAML list of strings

Lists the skills that reference or depend on this document. Valid skill names:

- `setup` — the setup subcommand
- `review` — the review orchestrator
- `patterns` — the design patterns skill
- `documentor` — the documentation review skill
- `external-review` — the external LLM review skill
- `python-code-style` — the Python code style skill
- `python-testing-patterns` — the Python testing patterns skill
- `php-code-style` — the PHP code style skill
- `php-testing-patterns` — the PHP testing patterns skill

**Wildcards**: language-specific skills can be referenced with wildcards instead of listing each one individually:

- `python-*` — matches all Python-specific skills (`python-code-style`, `python-testing-patterns`, and any future Python skills)
- `php-*` — matches all PHP-specific skills (`php-code-style`, `php-testing-patterns`, and any future PHP skills)

Wildcards are **preferred** for language-specific skills; explicit names are still allowed for files that target a single skill only. When a new language-specific skill is added, no docs files need updating if they already use the wildcard.

Use the explicit skill list or wildcards, not `[all]`. This allows tooling to determine which files are affected when a skill changes.

## Example

```yaml
---
audience: human, ai
status: stable
skills: [patterns, documentor, review, external-review]
---
```

## Conventions

- Every `.md` file in `docs/` must have frontmatter.
- The frontmatter is the first block in the file, delimited by `---`.
- Fields are lowercase.
- The `skills` list uses square-bracket YAML list syntax: `[skill1, skill2]`.
- Files that are purely navigational (e.g. `index.md`) list all skills since they serve as the entry point for every skill.
