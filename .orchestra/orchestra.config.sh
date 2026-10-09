# orchestra.config.sh — source before using the harness.
#   set -a; . .orchestra/orchestra.config.sh; set +a

# open = cloud Claude orchestrates + Codex reviews ; private = (desenhar depois)
export ORCHESTRA_MODE="open"

# coder (local, via Ollama). Windows host IP changes per boot in WSL NAT → live.
export ORCHESTRA_MODEL="hf.co/OliviaRossi/Qwen3.5-9B-C3SM-SDM-Agentic-Coder-GGUF:Q5_K_M"
export ORCHESTRA_OLLAMA_URL="http://$(ip route show default | awk '{print $3}'):11434"
export ORCHESTRA_REPO="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
export ORCHESTRA_MAX_STEPS="30"

# reviewer (cloud)
export ORCHESTRA_CODEX_MODEL="gpt-5-codex"
