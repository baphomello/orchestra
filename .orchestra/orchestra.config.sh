# orchestra.config.sh — source before using the harness.
#   set -a; . .orchestra/orchestra.config.sh; set +a

# open = cloud Claude orchestrates + Codex reviews ; private = (desenhar depois)
export ORCHESTRA_MODE="open"

# coder (local, via Ollama). ornith1.5:9b over the faster 7B: honest finish +
# native tool-calls matter more than raw speed in a TDD loop.
export ORCHESTRA_MODEL="ornith1.5:9b"
# Windows host IP changes per boot in WSL NAT → compute live.
export ORCHESTRA_OLLAMA_URL="http://$(ip route show default | awk '{print $3}'):11434"
export ORCHESTRA_REPO="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
export ORCHESTRA_MAX_STEPS="30"

# reviewer (cloud)
export ORCHESTRA_CODEX_MODEL="gpt-5-codex"
