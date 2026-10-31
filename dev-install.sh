#!/usr/bin/env bash
# Dev install — install the current working tree with the same installer end
# users run: `npx skills add` against the local bundle directory.
# For released versions use `npx skills add zolletta/zolletta-metaskill`.
#
# Usage:
#   ./dev-install.sh    # install the working tree
#
# What it does: refreshes the bundle's generated copies via sync-bundle.sh
# (the copy list lives in bundle-files.txt), then `npx skills add` copies
# skills/zolletta-metaskill into ~/.agents/skills/zolletta-metaskill and links
# it into every detected AI agent tool's skills directory. Also activates
# .githooks/pre-commit for this clone so the generated copies stay in sync and
# staged files get their newline/table fixes on every commit.
#
# The local path form installs whatever is on disk — uncommitted changes
# included — which is the whole point of a dev install. Requires Node.js (npx).

set -euo pipefail

if [[ $# -gt 0 ]]; then
    echo "usage: $0" >&2
    exit 1
fi

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

if ! command -v npx >/dev/null 2>&1; then
    echo "error: npx not found — install Node.js, or see docs/how-to/install.md" >&2
    echo "       for the manual clone-and-symlink alternative." >&2
    exit 1
fi

"$SOURCE_DIR/sync-bundle.sh"

# Point git at the tracked hooks so pre-commit bundle sync is active here.
if git -C "$SOURCE_DIR" rev-parse --git-dir >/dev/null 2>&1; then
    git -C "$SOURCE_DIR" config core.hooksPath .githooks
fi

# ---------------------------------------------------------------------------
# Step 1 — Install the bundle globally with the skills CLI
# ---------------------------------------------------------------------------

# --all = --skill '*' --agent '*' -y: every discovered skill into every
# detected agent tool, no prompts. -g installs at user level.
npx --yes skills add "$BUNDLE_DIR" -g --all

echo ""
echo "Done. zolletta-metaskill dev install complete."
