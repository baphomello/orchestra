#!/usr/bin/env bash
# Minimal CODEX_HOME for the reviewer: auth from ~/.codex, tiny config, no global AGENTS/skills.
set -euo pipefail
CH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/codex-home"
mkdir -p "$CH"
ln -sf "$HOME/.codex/auth.json" "$CH/auth.json"
printf 'model = "gpt-5.5"\nmodel_reasoning_effort = "medium"\nproject_doc_max_bytes = 0\n' > "$CH/config.toml"
: > "$CH/AGENTS.md"
echo "codex-home ready at $CH"
