#!/usr/bin/env bash
# Dev install — install the current working tree into ~/.agents/skills/
# and symlink it into every detected AI agent tool's skills directory.
# For released versions use `npx skills add zolletta/zolletta-metaskill`.
#
# Usage:
#   ./dev-install.sh            # install from the current directory
#   ./dev-install.sh --force    # replace real dirs with symlinks
#
# What it installs: the bundle directory skills/zolletta-metaskill/, after
# refreshing its generated copies via sync-bundle.sh (the copy list lives in
# bundle-files.txt). Also activates .githooks/pre-commit for this clone so
# the generated copies stay in sync on every commit.
#
# Safety: this script NEVER uses rm -rf. Destination cleanup uses
# find -delete only.

set -euo pipefail

FORCE=false
CANONICAL_DEST="$HOME/.agents/skills/zolletta-metaskill"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force) FORCE=true; shift ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Step 0 — Resolve the source tree and refresh the generated bundle copies
# ---------------------------------------------------------------------------

SOURCE_DIR="$(cd "$PWD" && pwd)"
echo "Installing from local source: $SOURCE_DIR"

BUNDLE_DIR="$SOURCE_DIR/skills/zolletta-metaskill"
if [[ ! -f "$BUNDLE_DIR/SKILL.md" ]]; then
    echo "error: $BUNDLE_DIR/SKILL.md not found — run from the repository root." >&2
    exit 1
fi

"$SOURCE_DIR/sync-bundle.sh"

# Point git at the tracked hooks so pre-commit bundle sync is active here.
if git -C "$SOURCE_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    git -C "$SOURCE_DIR" config core.hooksPath .githooks
fi

# ---------------------------------------------------------------------------
# Step 1 — Copy the bundle into ~/.agents/skills/
# ---------------------------------------------------------------------------

mkdir -p "$HOME/.agents/skills"

# If the source IS already at the canonical destination, skip the copy.
if [[ "$SOURCE_DIR" == "$CANONICAL_DEST" ]]; then
    echo "Source is already at $CANONICAL_DEST — skipping copy."
else
    echo "Installing to $CANONICAL_DEST ..."
    mkdir -p "$CANONICAL_DEST"
    # Wipe the destination first so renamed/removed files don't linger stale
    # (e.g. SKILL.md -> SUBCOMMAND.md inside a subcommand folder).
    # Using find -delete — never rm -rf.
    find "$CANONICAL_DEST" -mindepth 1 -delete 2>/dev/null || true

    # cp -R src/. copies the directory's contents, dotfiles included.
    cp -R "$BUNDLE_DIR/." "$CANONICAL_DEST/"
    echo "Copy complete (bundle directory)."
fi

# ---------------------------------------------------------------------------
# Step 2 — Symlink into every detected tool's skills directory
# ---------------------------------------------------------------------------

# Tool mapping: global_dir|skills_subdir
TOOLS=(
    "Claude Code|$HOME/.claude|skills"
    "Cursor|$HOME/.cursor|skills"
    "Gemini CLI|$HOME/.gemini|skills"
    "Devin|$HOME/.config/devin|skills"
    "OpenCode|$HOME/.config/opencode|skills"
    "Windsurf|$HOME/.codeium/windsurf|skills"
    "Cline|$HOME/.cline|skills"
    "Roo Code|$HOME/.roo|skills"
    "Continue|$HOME/.continue|skills"
    "Kiro|$HOME/.kiro|skills"
    "Goose|$HOME/.config/goose|skills"
    "Junie|$HOME/.junie|skills"
    "Augment|$HOME/.augment|skills"
    "Trae|$HOME/.trae|skills"
)

# Native ~/.agents/skills/ readers (no symlink needed): Codex, Pi, Kilo Code

printf "\n%-15s %-20s %s\n" "Tool" "Status" "Path"
printf "%-15s %-20s %s\n" "----" "------" "----"

for entry in "${TOOLS[@]}"; do
    IFS='|' read -r name global_dir skills_subdir <<< "$entry"
    link_target="$global_dir/$skills_subdir/zolletta-metaskill"

    # Check if tool is installed
    if [[ ! -d "$global_dir" ]]; then
        printf "%-15s %-20s %s\n" "$name" "not installed" "-"
        continue
    fi

    # Check if the tool's skills dir is already a symlink to ~/.agents/skills
    skills_dir="$global_dir/$skills_subdir"
    if [[ -L "$skills_dir" && "$(readlink "$skills_dir")" == "$HOME/.agents/skills" ]]; then
        printf "%-15s %-20s %s\n" "$name" "already linked" "$skills_dir"
        continue
    fi

    mkdir -p "$skills_dir"

    # Handle existing entry
    if [[ -e "$link_target" || -L "$link_target" ]]; then
        if [[ -L "$link_target" ]]; then
            if [[ "$(readlink "$link_target")" == "$CANONICAL_DEST" ]]; then
                printf "%-15s %-20s %s\n" "$name" "already linked" "$link_target"
                continue
            fi
            # rm first — ln -sf would follow a symlink-to-dir and create the
            # link inside it (self-referential link in the destination).
            rm -f "$link_target"
            ln -s "$CANONICAL_DEST" "$link_target"
            printf "%-15s %-20s %s\n" "$name" "updated" "$link_target"
            continue
        elif [[ -d "$link_target" ]]; then
            if [[ "$FORCE" == "true" ]]; then
                find "$link_target" -delete 2>/dev/null || true
                ln -sf "$CANONICAL_DEST" "$link_target"
                printf "%-15s %-20s %s\n" "$name" "replaced" "$link_target"
            else
                printf "%-15s %-20s %s\n" "$name" "skipped (real dir)" "$link_target"
                continue
            fi
        else
            # Regular file — back it up + symlink
            mv "$link_target" "${link_target}.bak" 2>/dev/null || true
            ln -sf "$CANONICAL_DEST" "$link_target"
            printf "%-15s %-20s %s\n" "$name" "backed up + linked" "$link_target"
            continue
        fi
    fi

    # No existing entry — create symlink
    ln -sf "$CANONICAL_DEST" "$link_target"
    printf "%-15s %-20s %s\n" "$name" "symlinked" "$link_target"
done

echo ""
echo "Done. zolletta-metaskill is installed at $CANONICAL_DEST"
echo "Native ~/.agents/skills/ readers (Codex, Pi, Kilo Code) need no symlink."
