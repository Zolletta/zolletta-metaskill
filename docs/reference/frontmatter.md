---
audience: human, ai
status: stable
skills: [setup, review, patterns, documentor, python-*]
---

# Frontmatter Reference

Every markdown file in the repository opens with a YAML frontmatter block. A documentation file — anything under `docs/` plus the root documents — declares its audience, stability status and associated skills; a skill manifest (`SKILL.md`, `SUBSKILL.md`) declares the skill's routing metadata instead. This metadata enables automated tooling (staleness scoring, drift detection, cross-referencing) and helps reviewers understand the purpose of each file at a glance.

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
- `help` — the help subcommand
- `adr-distiller` — the ADR distiller skill
- `python-code-style` — the Python code style skill
- `python-testing-style` — the Python testing style skill
- `php-code-style` — the PHP code style skill
- `php-testing-style` — the PHP testing style skill

**Wildcards**: language-specific skills can be referenced with wildcards instead of listing each one individually:

- `python-*` — matches all Python-specific skills (`python-code-style`, `python-testing-style`, and any future Python skills)
- `php-*` — matches all PHP-specific skills (`php-code-style`, `php-testing-style`, and any future PHP skills)

Wildcards are **preferred** for language-specific skills; explicit names are still allowed for files that target a single skill only. When a new language-specific skill is added, no docs files need updating if they already use the wildcard.

**Empty list**: `skills: []` declares that no skill references the document. It is reserved for genuinely skill-independent files and is *not* a default — a navigational file such as an `index.md` serves every skill and must list them all, and a document that a skill reads must name that skill.

Use the explicit skill list or wildcards, not `[all]`. This allows tooling to determine which files are affected when a skill changes.

## Example

```yaml
---
audience: human, ai
status: stable
skills: [patterns, documentor, review]
---
```

## Conventions

- Every `.md` file must have frontmatter — everywhere, not only under `docs/`. A markdownlint custom rule (`md-require-frontmatter.js`) enforces the leading block; the generated `CHANGELOG.md` is the only exemption.
- The frontmatter is the first block in the file, delimited by `---`.
- Fields are lowercase.
- The `skills` list uses square-bracket YAML list syntax: `[skill1, skill2]`.
- Files that are purely navigational (e.g. `index.md`) list all skills since they serve as the entry point for every skill.
- Template assets under `skills/*/assets/` (`*_template.md`) carry frontmatter for the template file itself. A renderer fills the template body and the report starts at its H1 — the frontmatter is source metadata and is not reproduced in the rendered report.
