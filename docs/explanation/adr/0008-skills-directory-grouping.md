# ADR-0008: skills/ directory grouping

## Status

Accepted

## Context

The project originally stored sub-skills as top-level directories in the repository root: `documentor/`, `patterns/`, `python-code-style/`, etc. Each contained a `SKILL.md`.

Keeping sub-skills at the repo root mixed them with non-skill directories (`docs/`, `src/`, `tests/`, `assets/`), making the repository structure unclear and the skill inventory harder to discover.

Two further issues appeared when the grouped directory was named `skills/`:

- **Discovery clutter.** Skill discovery in agent tools (e.g. OpenCode's `{*.md, **/SKILL.md}` glob) matches any nested `SKILL.md`, so every sub-skill appeared as a top-level skill — 11 entries instead of 1. Permission deny rules were tried but only gate invocation, not listing.
- **Naming inconsistency.** Folder names did not match frontmatter `name` values, violating the convention that `name` equals the containing directory.

An intermediate step renamed the directory to `subskills/`; it did not stop recursive discovery because the glob matches on the filename, not the parent directory.

## Decision

All subfolders containing a sub-skill are grouped under a `skills/` directory. Each folder is named after its skill `name`, and the skill file inside is named `SUBSKILL.md` — not `SKILL.md` — so `**/SKILL.md` discovery finds only the root meta-skill:

```
zolletta-metaskill/
├── skills/
│   ├── zolletta-metaskill-adr-distiller/SUBSKILL.md
│   ├── zolletta-metaskill-documentor/SUBSKILL.md
│   ├── zolletta-metaskill-help/SUBSKILL.md
│   ├── zolletta-metaskill-patterns/SUBSKILL.md
│   ├── zolletta-metaskill-php-code-style/SUBSKILL.md
│   ├── zolletta-metaskill-php-testing-style/SUBSKILL.md
│   ├── zolletta-metaskill-python-code-style/SUBSKILL.md
│   ├── zolletta-metaskill-python-testing-style/SUBSKILL.md
│   ├── zolletta-metaskill-review/SUBSKILL.md
│   └── zolletta-metaskill-setup/SUBSKILL.md
├── docs/
├── src/
└── tests/
```

Subcommand names stay short (`help`, `setup`, ...); dispatch maps `/zolletta-metaskill <subcommand>` to `skills/zolletta-metaskill-<subcommand>/SUBSKILL.md`. All path references use `../../` relative paths from within `skills/`.

## Consequences

**Positive:**

- Folder name == skill `name` — one identifier everywhere, and `zolletta-metaskill-*` patterns cover every sub-skill.
- `SUBSKILL.md` hides sub-skills from `**/SKILL.md` discovery in every agent tool — no per-user configuration needed.
- The repo root is cleaner — skill directories are grouped, non-skill directories are separate.
- The skill inventory is immediately visible: `ls skills/` shows all available subcommands.

**Negative:**

- All internal path references changed (`../../docs/`, `../../src/` from `skills/`). This is a one-time cost but touched many files.
- `SUBSKILL.md` is a project-specific filename — tools that conventionally look for `SKILL.md` won't see the sub-skills even if that were ever wanted; dispatch must always read them explicitly.

**Neutral:**

- The `SKILL.md` at the repo root (the meta-skill) stays at the root — it is the entry point, not a sub-skill. Only sub-skills live in `skills/`.
