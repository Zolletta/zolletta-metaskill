---
audience: human, ai
status: stable
skills: [setup]
---

# Install Zolletta-MetaSkill

Install the Zolletta-metaskill skill family so it is available to the AI agent.

## Prerequisites

- An AI agent that supports skills (Devin, Claude, Cursor, or similar)
- Git

## Installation

### Option 1 — One-command installer (recommended)

```bash
curl -fsSL https://raw.githubusercontent.com/Zolletta/zolletta-metaskill/main/install.sh | bash
```

The `install.sh` script:

1. Clones the **latest git tag** into a temp directory
2. Copies only the files listed in `install-manifest.txt` 
3. Symlinks it into every detected AI agent tool's skills directory

Supported tools (auto-detected — only installed tools are linked):

| Tool        | Symlink path                                    |
|-------------|-------------------------------------------------|
| Claude Code | `~/.claude/skills/zolletta-metaskill`           |
| Cursor      | `~/.cursor/skills/zolletta-metaskill`           |
| Gemini CLI  | `~/.gemini/skills/zolletta-metaskill`           |
| Devin       | `~/.config/devin/skills/zolletta-metaskill`     |
| OpenCode    | `~/.config/opencode/skills/zolletta-metaskill`  |
| Windsurf    | `~/.codeium/windsurf/skills/zolletta-metaskill` |
| Cline       | `~/.cline/skills/zolletta-metaskill`            |
| Roo Code    | `~/.roo/skills/zolletta-metaskill`              |
| Continue    | `~/.continue/skills/zolletta-metaskill`         |
| Kiro        | `~/.kiro/skills/zolletta-metaskill`             |
| Goose       | `~/.config/goose/skills/zolletta-metaskill`     |
| Junie       | `~/.junie/skills/zolletta-metaskill`            |
| Augment     | `~/.augment/skills/zolletta-metaskill`          |
| Trae        | `~/.trae/skills/zolletta-metaskill`             |

Native `~/.agents/skills/` readers (Codex, Pi, Kilo Code) need no symlink — they read the canonical copy directly.

To replace an existing real directory with a symlink:

```bash
./install.sh --force
```

### Option 2 — Clone into the skills directory

```bash
git clone https://github.com/Zolletta/zolletta-metaskill.git ~/.agents/skills/zolletta-metaskill
```

### Option 3 — Symlink from a different location

If the repository is already cloned elsewhere:

```bash
ln -s /path/to/zolletta-metaskill ~/.agents/skills/zolletta-metaskill
```

### Verify installation

The skill should appear in the agent's available skills list. Invoke it with:

```
/zolletta-metaskill
```

This should list the available subcommands: `setup`, `documentor`, `patterns`, `review`, `python-code-style`, `python-testing-style`.

## Post-installation

After installing, run `/zolletta-metaskill setup` in each project to use the review skills. Setup creates `.zolletta-metaskill/settings.json` with the project's language, tool availability, and configuration. See [Set up a project](setup-project.md) for details.

## See also

- [Set up a project](setup-project.md) — initialize a project for reviews
- [Getting started](../tutorials/getting-started.md) — end-to-end walkthrough
- [Repository scripts](../reference/code/scripts.md) — `.bump` and `install.sh` reference
