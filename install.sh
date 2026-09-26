#!/usr/bin/env bash
# Install zolletta-metaskill into ~/.agents/skills/ and symlink it into
# every detected AI agent tool's skills directory.
#
# Usage:
#   ./install.sh                  # clone the latest git tag and install it
#   ./install.sh --force          # replace real dirs with symlinks
#   ./install.sh --source <dir>   # install from a local directory
#                                 # (dev-install.sh is a shortcut for this)
#
# The list of files copied lives in install-manifest.txt (repo root).
# When the manifest is absent (e.g. an old tag), a built-in default is used.
#
# Safety: this script NEVER uses rm -rf. Destination cleanup uses
# find -delete only.

set -euo pipefail

FORCE=false
SOURCE_DIR=""
CANONICAL_DEST="$HOME/.agents/skills/zolletta-metaskill"
REPO_URL_DEFAULT="https://github.com/Zolletta/zolletta-metaskill.git"
MANIFEST_NAME="install-manifest.txt"

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force) FORCE=true; shift ;;
        --source) SOURCE_DIR="$2"; shift 2 ;;
        *) echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

# ---------------------------------------------------------------------------
# Step 1 — Resolve the source tree
# ---------------------------------------------------------------------------

CLONE_DIR=""
if [[ -n "$SOURCE_DIR" ]]; then
    SOURCE_DIR="$(cd "$SOURCE_DIR" && pwd)"
    echo "Installing from local source: $SOURCE_DIR"
else
    # Prefer the repo's own remote when the script runs from inside a clone
    # (SKILL.md sits at the repo root — if it's absent, e.g. the script was
    # fetched standalone via curl, the cwd may be inside an unrelated repo
    # whose remote must not be picked up).
    SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
    if [[ -f "$SCRIPT_DIR/SKILL.md" ]]; then
        REPO_URL="$(git -C "$SCRIPT_DIR" remote get-url origin 2>/dev/null || echo "$REPO_URL_DEFAULT")"
    else
        REPO_URL="$REPO_URL_DEFAULT"
    fi

    TAG="$(git ls-remote --tags "$REPO_URL" \
        | sed -n 's|.*refs/tags/\(v[0-9][0-9.]*\)$|\1|p' \
        | sort -V | tail -1)"

    CLONE_DIR="$(mktemp -d /tmp/zolletta-metaskill.XXXXXX)"
    trap 'if [[ -n "$CLONE_DIR" && -d "$CLONE_DIR" ]]; then find "$CLONE_DIR" -delete 2>/dev/null || true; fi' EXIT

    if [[ -n "$TAG" ]]; then
        echo "Cloning latest tag $TAG from $REPO_URL ..."
        git clone --quiet --depth 1 --branch "$TAG" "$REPO_URL" "$CLONE_DIR"
    else
        echo "No git tags found — cloning the default branch ..."
        git clone --quiet --depth 1 "$REPO_URL" "$CLONE_DIR"
    fi
    SOURCE_DIR="$CLONE_DIR"
fi

# ---------------------------------------------------------------------------
# Step 2 — Copy the manifest-listed files into ~/.agents/skills/
# ---------------------------------------------------------------------------

mkdir -p "$HOME/.agents/skills"

# If the source IS already at the canonical destination, skip the copy.
if [[ "$SOURCE_DIR" == "$CANONICAL_DEST" ]]; then
    echo "Source is already at $CANONICAL_DEST — skipping copy."
else
    echo "Installing to $CANONICAL_DEST ..."
    mkdir -p "$CANONICAL_DEST"
    # Wipe the destination first so renamed/removed files don't linger stale
    # (e.g. SKILL.md -> SUBSKILL.md inside a subskill folder).
    # Using find -delete — never rm -rf.
    find "$CANONICAL_DEST" -mindepth 1 -delete 2>/dev/null || true

    # Read the copy list from the manifest, with a built-in fallback for
    # sources that predate it.
    ITEMS=()
    if [[ -f "$SOURCE_DIR/$MANIFEST_NAME" ]]; then
        while IFS= read -r line; do
            item="${line%%#*}"
            item="${item//[[:space:]]/}"
            [[ -n "$item" ]] && ITEMS+=("$item")
        done < "$SOURCE_DIR/$MANIFEST_NAME"
    else
        ITEMS=(src skills subskills docs assets pyproject.toml CHANGELOG.md CONTRIBUTING.md LICENSE README.md SKILL.md)
    fi

    copied=0
    for item in "${ITEMS[@]}"; do
        if [[ -e "$SOURCE_DIR/$item" ]]; then
            cp -R "$SOURCE_DIR/$item" "$CANONICAL_DEST/"
            copied=$((copied + 1))
        fi
    done
    echo "Copy complete ($copied items)."
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
