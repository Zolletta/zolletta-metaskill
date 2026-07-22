# TODO — Installation Script

A bash script to add to the **project root** (next to the existing `.bump`), so it is easy to find and run.

---

## `.install`

An installer script that copies the skill to `~/.agents/skills/` and symlinks it into every detected agent tool's skills directory.

**Status:** Not yet created. The first attempt caused data loss (see "Critical safety note" below).

### Location

Project root, as a sibling of `.bump`:

```
zolletta-metaskill/
├── .bump        # existing version bump script
└── .install     # this script
```

### Usage

```bash
./.install           # install/refresh
./.install --force   # replace real dirs with symlinks
```

### What it does

#### Step 1 — Ensure `~/.agents/skills/` exists

```bash
mkdir -p ~/.agents/skills
```

#### Step 2 — Copy the skill to `~/.agents/skills/zolletta-metaskill`

**IMPORTANT: use `cp -R` with explicit exclude deletion, NOT `rm -rf` + tar/rsync.**

The copy must exclude heavy/regenerable directories:

- `.venv/` (128 MB)
- `.git/`
- `.tokensave/`
- `.zolletta-metaskill/` (generated reports)
- `.ruff_cache/`, `.mypy_cache/`, `.pytest_cache/`
- `htmlcov/`, `dist/`
- `__pycache__/` (all levels)
- `.DS_Store`, `.coverage`, `coverage.xml`, `junit.xml`
- `uv.lock` (regenerable)

**Approach (safe, no `rm -rf` on source):**

```bash
# Copy everything
cp -R "$REPO_ROOT/" "$CANONICAL_DEST/"
# Then delete the excluded dirs from the destination
for excl in .venv .git .tokensave .zolletta-metaskill .ruff_cache .mypy_cache .pytest_cache htmlcov dist; do
  rm -rf "$CANONICAL_DEST/$excl"
done
find "$CANONICAL_DEST" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null
find "$CANONICAL_DEST" -name '.DS_Store' -delete 2>/dev/null
rm -f "$CANONICAL_DEST/.coverage" "$CANONICAL_DEST/coverage.xml" "$CANONICAL_DEST/junit.xml" "$CANONICAL_DEST/uv.lock"
```

#### Step 3 — Symlink into every detected tool's skills directory

Hardcoded mapping (confirmed from each tool's official docs):

| Tool | Global dir check | Skills subdir | Symlink target |
| --- | --- | --- | --- |
| Claude Code | `~/.claude` | `skills` | `~/.claude/skills/zolletta-metaskill` |
| Cursor | `~/.cursor` | `skills` | `~/.cursor/skills/zolletta-metaskill` |
| Gemini CLI | `~/.gemini` | `skills` | `~/.gemini/skills/zolletta-metaskill` |
| Devin | `~/.config/devin` | `skills` | `~/.config/devin/skills/zolletta-metaskill` |
| Windsurf | `~/.codeium/windsurf` | `skills` | `~/.codeium/windsurf/skills/zolletta-metaskill` |
| Cline | `~/.cline` | `skills` | `~/.cline/skills/zolletta-metaskill` |
| Roo Code | `~/.roo` | `skills` | `~/.roo/skills/zolletta-metaskill` |
| Continue | `~/.continue` | `skills` | `~/.continue/skills/zolletta-metaskill` |
| Kiro | `~/.kiro` | `skills` | `~/.kiro/skills/zolletta-metaskill` |
| Goose | `~/.config/goose` | `skills` | `~/.config/goose/skills/zolletta-metaskill` |
| Junie | `~/.junie` | `skills` | `~/.junie/skills/zolletta-metaskill` |
| Augment | `~/.augment` | `skills` | `~/.augment/skills/zolletta-metaskill` |
| Trae | `~/.trae` | `skills` | `~/.trae/skills/zolletta-metaskill` |

**Native `~/.agents/skills/` readers (no symlink needed):** Codex, Pi, Kilo Code — they read the canonical copy from step 2 directly.

For each tool:

1. Check if global dir exists (`[[ -d "$global_dir" ]]`). If not → skip (tool not installed).
2. Check if the tool's skills dir is **already a symlink to `~/.agents/skills`** — if so, skip (the whole dir is already linked).
3. `mkdir -p` the skills subdir.
4. If a `zolletta-metaskill` entry already exists:
   - If it's a symlink → `ln -sf` to update it.
   - If it's a real dir → warn and skip (unless `--force`, then `rm -rf` + symlink).
   - If it's a regular file → back it up + symlink.
5. Create symlink: `ln -sf ~/.agents/skills/zolletta-metaskill <tool_skills_dir>/zolletta-metaskill`

### Output

Print a summary table: tool name, status (symlinked / skipped / not installed / already linked), and the symlink path.

---

## Documentation updates

After `.install` is written, update the relevant docs so users discover the script. Files to touch:

| File | Action | What changes |
| --- | --- | --- |
| `docs/how-to/install.md` | Update | Add `.install` as the recommended install method (above the manual clone/symlink options). Document `./.install` and `./.install --force`, the symlink model, and the list of supported tools. Keep the manual options as fallback. |
| `docs/reference/code/scripts.md` | Update | Add a "Repository scripts" section (separate from the scanning scripts) documenting `.bump` (version bump) and `.install` (skill installer): usage, options, what each touches, safety notes. |
| `README.md` | Update | Add an "Installation" section (currently absent) pointing to `./.install` as the one-command install and to `docs/how-to/install.md` for details. Mention `.bump` for contributors. |
| `docs/index.md` | Update | Refresh the Install row description to mention the `.install` script ("Install Zolletta-metaskill via `.install` or manual clone/symlink"). |
| `CHANGELOG.md` | Update | Add an entry under `[Unreleased]` (or a new version section) for the `.install` script and the documentation updates. |

### Notes

- `docs/how-to/install.md` currently only documents manual `git clone` and `ln -s`. The `.install` script automates both the canonical copy and the per-tool symlinks, so it should become the primary path.
- `docs/reference/code/scripts.md` is scoped to scanning scripts under `src/`. The repo-root `.bump` and `.install` are project-management scripts, not scanning scripts — add them as a distinct section rather than mixing them in.
- The README has no Installation section at all today; this is a gap regardless of `.install`.
- Cross-link: `install.md` → `scripts.md` (reference), and `README.md` → `install.md` (how-to).

---

## Critical safety note

The first implementation of `.install` used `rm -rf "$CANONICAL_DEST"` before copying, to get "clean destination" semantics. Because the repo lives directly at `~/.agents/skills/zolletta-metaskill`, `CANONICAL_DEST` resolved to the same path as the repo root. The `rm -rf` deleted the entire repository including `.git/`, destroying unpushed work.

**Rules for the reimplementation:**

1. **NEVER use `rm -rf` on a path that could be the source.** Always check `REPO_ROOT != CANONICAL_DEST` before any destructive operation.
2. **Prefer `cp -R` + selective delete of excludes** over `rm -rf` + full copy. This is safe even if source and destination overlap (cp into a different dir first, then clean).
3. **If the source IS `~/.agents/skills/zolletta-metaskill`**, the copy step is a no-op (the canonical copy already exists). The script should detect this and skip straight to symlinking.
4. **Ask for confirmation** before any `rm -rf` on a path the script didn't create.

---

## Tool skills paths — sources

Confirmed from official documentation:

- **Claude Code**: `~/.claude/skills/<name>/SKILL.md` — https://code.claude.com/docs/en/skills
- **Cursor**: `~/.cursor/skills/` and `~/.agents/skills/` — https://cursor.com/docs/context/skills
- **Gemini CLI**: `~/.gemini/skills/` or `~/.agents/skills/` alias — https://geminicli.com/docs/cli/skills/
- **Codex**: `$HOME/.agents/skills` (native, no symlink needed) — https://developers.openai.com/codex/skills/
- **Devin**: `~/.config/devin/skills/` (symlinked to `~/.agents/skills/` on this machine)
- **Agent Skills spec**: https://agentskills.io/specification.md
- **Agents Standard (config map)**: https://agentsstandard.com/agent-config-map/

Other tools (Cline, Roo, Continue, Kiro, Goose, Junie, Augment, Trae) use a best-guess `<global_dir>/skills/` pattern based on the Agents Standard config map. The mapping is data-driven and easy to correct.
