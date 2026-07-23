#!/usr/bin/env bash
# Install zolletta-metaskill into ~/.agents/skills/ and symlink it into
# every detected AI agent tool's skills directory.
#
# Usage:
#   ./.install           # install/refresh
#   ./.install --force   # replace real dirs with symlinks
#
# Safety: this script NEVER uses rm -rf. It uses cp -R + selective
# find -delete / rm -f for cleanup of excludes in the destination only.

set -euo pipefail

FORCE=false
REPO_ROOT="$(cd "$(dirname "$0")" && pwd)"
CANONICAL_DEST="$HOME/.agents/skills/zolletta-metaskill"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force) FORCE=true; shift ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Step 1 — Ensure ~/.agents/skills/ exists
# ---------------------------------------------------------------------------
mkdir -p "$HOME/.agents/skills"

# ---------------------------------------------------------------------------
# Step 2 — Copy the skill to ~/.agents/skills/zolletta-metaskill
# ---------------------------------------------------------------------------

# If the repo IS already at the canonical destination, skip the copy.
if [[ "$REPO_ROOT" == "$CANONICAL_DEST" ]]; then
    echo "Repo is already at $CANONICAL_DEST — skipping copy."
else
    echo "Copying skill to $CANONICAL_DEST ..."
    mkdir -p "$CANONICAL_DEST"
    cp -R "$REPO_ROOT/" "$CANONICAL_DEST/"

    # Remove excluded dirs/files from the destination (NOT from source).
    # Using find -delete and rm -f — never rm -rf.
    for excl in .venv .git .tokensave .zolletta-metaskill .ruff_cache .mypy_cache .pytest_cache htmlcov dist; do
        if [[ -e "$CANONICAL_DEST/$excl" ]]; then
            find "$CANONICAL_DEST/$excl" -delete 2>/dev/null || true
        fi
    done
    find "$CANONICAL_DEST" -name '__pycache__' -type d -exec find {} -delete \; 2>/dev/null || true
    find "$CANONICAL_DEST" -name '.DS_Store' -delete 2>/dev/null || true
    rm -f "$CANONICAL_DEST/.coverage" "$CANONICAL_DEST/coverage.xml" "$CANONICAL_DEST/junit.xml" "$CANONICAL_DEST/uv.lock" 2>/dev/null || true
    echo "Copy complete."
fi

# ---------------------------------------------------------------------------
# Step 3 — Symlink into every detected tool's skills directory
# ---------------------------------------------------------------------------

# Tool mapping: global_dir|skills_subdir
TOOLS=(
    "Claude Code|$HOME/.claude|skills"
    "Cursor|$HOME/.cursor|skills"
    "Gemini CLI|$HOME/.gemini|skills"
    "Devin|$HOME/.config/devin|skills"
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
            ln -sf "$CANONICAL_DEST" "$link_target"
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
