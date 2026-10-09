#!/usr/bin/env bash
# install.sh <target-repo> — install the orchestra workflow into a repo.
set -euo pipefail
SRC="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DST="${1:?usage: ./install.sh <target-repo>}"
[ -d "$DST/.git" ] || { echo "not a git repo: $DST"; exit 1; }
cp -r "$SRC/.orchestra" "$DST/.orchestra"
rm -rf "$DST/.orchestra/codex-home"
bash "$DST/.orchestra/setup-codex-home.sh"
mkdir -p "$DST/.claude/commands"
cp "$SRC/.claude/commands/cycle.md" "$DST/.claude/commands/cycle.md"
printf '\n%s\n' "$(cat "$SRC/CLAUDE.orchestra.md")" >> "$DST/CLAUDE.md"
grep -qxF '.orchestra/codex-home/' "$DST/.gitignore" 2>/dev/null || printf '.orchestra/codex-home/\n__pycache__/\n' >> "$DST/.gitignore"
echo "Installed into $DST. Merge settings.orchestra.json into $DST/.claude/settings.json to skip prompts."
