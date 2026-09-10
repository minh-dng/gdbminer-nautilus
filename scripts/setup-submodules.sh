#!/usr/bin/env bash
# Initialize pinned submodules and keep evaluation artifacts out of the working tree.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

# Shared by linked worktrees, including worktrees created by Zed.
git config core.hooksPath .githooks

git submodule sync --recursive
git submodule update --init --recursive

# Match gdbminer main content, but do not materialize the evaluation/ tree.
git -C gdbminer sparse-checkout init --no-cone
git -C gdbminer sparse-checkout set '/*' '!/evaluation/'

echo "Submodules ready."
echo "  gdbminer  $(git -C gdbminer rev-parse --short HEAD)  ($(git -C gdbminer branch --show-current 2>/dev/null || echo detached))"
echo "  nautilus  $(git -C nautilus rev-parse --short HEAD)  ($(git -C nautilus branch --show-current 2>/dev/null || echo detached))"
