---
name: zolletta-metaskill-version
description: >
  Print the installed zolletta-metaskill version. Reads the version
  from pyproject.toml at the skill root — the directory containing
  SKILL.md (the installed bundle under ~/.agents/skills/, or the
  repository root when running from source). Invoked with
  /zolletta-metaskill version. Purely informational — no setup guard,
  works outside any project.
license: MIT + Commons Clause
---

# Zolletta-metaskill Version

Prints the installed skill version so the user can check which release is installed (e.g. after `./install.sh`).

## Procedure

1. Locate `pyproject.toml` at the skill root — the directory containing `SKILL.md` (the installed bundle `~/.agents/skills/zolletta-metaskill/pyproject.toml`, or the repository root when running from a source checkout).
2. Read the `version` field under `[project]` (a line like `version = "3.6.0"`). Read it as plain text — do not run Python or packaging tooling.
3. Print the version and the path it was read from:

   ```
   zolletta-metaskill v3.6.0 (~/.agents/skills/zolletta-metaskill/pyproject.toml)
   ```

4. If `.zolletta-metaskill/settings.json` exists in the current project root, also print its `setup_version` on a second line so the user can spot a stale setup after upgrading the skill:

   ```
   project settings: v3.4.0 (setup_version)
   ```

5. If `pyproject.toml` is missing or has no `version` field, print `zolletta-metaskill (version unknown)` — never fail.

That's it — no setup guard, no settings.json requirement, no tool execution. This subcommand is purely informational and always available.
