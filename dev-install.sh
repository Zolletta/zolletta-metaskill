#!/usr/bin/env bash
# Dev install — install the current working tree instead of cloning the
# latest git tag. Identical to install.sh except the source is $PWD.
#
# Usage:
#   ./dev-install.sh            # install from the current directory
#   ./dev-install.sh --force    # replace real dirs with symlinks
#
# All arguments are forwarded to install.sh after --source "$PWD".

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
exec "$SCRIPT_DIR/install.sh" --source "$PWD" "$@"
