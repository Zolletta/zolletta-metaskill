---
audience: human, ai
status: stable
skills: [setup]
---

# Install Zolletta-MetaSkill

Install the Zolletta-metaskill skill family so it is available to the AI agent.

## Prerequisites

- An AI agent that supports skills (Devin, Claude, Cursor, or similar)
- Node.js (for the `npx` installer) or Git (for manual installation)

## Installation

### Option 1 — `npx skills add` (recommended)

```bash
npx skills add zolletta/zolletta-metaskill
```

The [skills CLI](https://github.com/vercel-labs/skills) clones the repository, copies the bundle discovered under `` to `~/.agents/skills/zolletta-metaskill`, and links it into every detected AI agent tool's skills directory (Claude Code, Cursor, Gemini CLI, Devin, OpenCode, Windsurf, and others — it detects what is installed and asks which to link).

Useful flags and lifecycle commands:

```bash
npx skills add zolletta/zolletta-metaskill -g -y   # global scope, no prompts
npx skills add zolletta/zolletta-metaskill#v3.7.0  # pin a specific tag
npx skills update zolletta-metaskill               # update to the latest commit
npx skills remove zolletta-metaskill               # uninstall
npx skills list                                   # show installed skills
```

The CLI does not track semantic versions — to see which release is installed, run `/zolletta-metaskill version`.

### Option 2 — `gh skill install` (GitHub CLI)

```bash
gh skill install zolletta/zolletta-metaskill
```

The `gh skill` extension discovers the bundle through the `skills/*/SKILL.md` convention and resolves the latest tag by default.

### Option 3 — Clone and symlink manually

The installable bundle lives in the `` subdirectory, not at the repository root — clone anywhere, then link that subdirectory:

```bash
git clone https://github.com/Zolletta/zolletta-metaskill.git ~/src/zolletta-metaskill
ln -s ~/src/zolletta-metaskill/skills/zolletta-metaskill ~/.agents/skills/zolletta-metaskill
```

Symlinking (rather than copying) keeps the installation in sync with the working tree — useful for development checkouts where edits should be picked up immediately. `dev-install.sh` is the scripted alternative: it installs the local bundle through `npx skills add`, which copies rather than links, so it reflects the tree at install time rather than tracking it live.

### Verify installation

The skill should appear in the agent's available skills list. Invoke it with:

```text
/zolletta-metaskill
```

This should list the available subcommands: `help`, `version`, `setup`, `documentor`, `grice`, `patterns`, `review`, `adr-distiller`, `python-code-style`, `python-testing-style`, `php-code-style`, `php-testing-style`.

## Post-installation

After installing, run `/zolletta-metaskill setup` in each project to use the review skills. Setup creates `.zolletta-metaskill/settings.json` with the project's language, tool availability, and configuration. See [Set up a project](setup-project.md) for details.

## See also

- [Set up a project](setup-project.md) — initialize a project for reviews
- [Getting started](../tutorials/getting-started.md) — end-to-end walkthrough
- [Repository scripts](../reference/code/scripts.md) — `dev-install.sh` and `sync-bundle.sh` reference
