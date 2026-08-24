# ADR-0008: skills/ directory grouping

## Status

Accepted

## Context

The project originally stored sub-skills as top-level directories in the repository root: `documentor/`, `external-review/`, `patterns/`, `python-code-style/`, etc. Each contained a `SKILL.md`.

The `.agents/` convention (agentsfolder/spec, .agents Protocol, Agents Standard) groups skills under a `skills/` subfolder. This is the emerging standard for agent skill organization.

Keeping sub-skills at the repo root mixed them with non-skill directories (`docs/`, `src/`, `tests/`, `assets/`), making the repository structure unclear and the skill inventory harder to discover.

## Decision

All subfolders containing a `SKILL.md` are moved from the repo root into a `skills/` directory. The structure becomes:

```
zolletta-metaskill/
├── skills/
│   ├── documentor/SKILL.md
│   ├── external-review/SKILL.md
│   ├── patterns/SKILL.md
│   ├── php-code-style/SKILL.md
│   ├── php-testing-style/SKILL.md
│   ├── python-code-style/SKILL.md
│   ├── python-testing-style/SKILL.md
│   ├── review/SKILL.md
│   └── setup/SKILL.md
├── docs/
├── src/
└── tests/
```

All path references in `SKILL.md`, `README.md`, docs, and sub-skill cross-references are updated to use `../../` relative paths from within `skills/`.

## Consequences

**Positive:**

- Aligns with the `.agents/` convention — other agent tools that scan for skills expect a `skills/` directory.
- The repo root is cleaner — skill directories are grouped, non-skill directories are separate.
- The skill inventory is immediately visible: `ls skills/` shows all available subcommands.

**Negative:**

- All internal path references changed (`../../docs/`, `../../src/` instead of `docs/`, `src/`). This is a one-time cost but touched many files.
- Tools or scripts that hardcoded the old root-level paths needed updating.

**Neutral:**

- The `SKILL.md` at the repo root (the meta-skill) stays at the root — it is the entry point, not a sub-skill. Only sub-skills moved into `skills/`.
