---
audience: human, ai
status: stable
skills: [setup]
---

# Install Zolletta-MetaSkill

Install the zolletta-metaskill skill family so it is available to the AI agent.

## Prerequisites

- An AI agent that supports skills (Devin, Claude, Cursor, or similar)
- Git

## Installation

### Option 1 — Clone into the skills directory

```bash
git clone https://github.com/Zolletta/zolletta-metaskill.git ~/.agents/skills/zolletta-metaskill
```

### Option 2 — Symlink from a different location

If the repository is already cloned elsewhere:

```bash
ln -s /path/to/zolletta-metaskill ~/.agents/skills/zolletta-metaskill
```

### Verify installation

The skill should appear in the agent's available skills list. Invoke it with:

```
/zolletta-metaskill
```

This should list the available subcommands: `setup`, `documentor`, `patterns`, `external-review`, `review`, `python-code-style`, `python-testing-patterns`.

## Post-installation

After installing, run `/zolletta-metaskill setup` in each project where we want to use the review skills. Setup creates `.zolletta-metaskill/settings.json` with the project's language, tool availability, and configuration. See [Set up a project](setup-project.md) for details.

## See also

- [Set up a project](setup-project.md) — initialize a project for reviews
- [Getting started](../tutorials/getting-started.md) — end-to-end walkthrough
