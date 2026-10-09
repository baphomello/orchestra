# orchestra

Multi-agent dev workflow for Claude Code: you talk only to **cloud Claude** (architect +
orchestrator); it delegates **coding** to a local model (Ollama, via a lean harness) and
**review** to **Codex** (cross-model, no architect bias). No copy-paste between tools.

See [`.orchestra/ORCHESTRA.md`](.orchestra/ORCHESTRA.md).

## Install into a repo
```bash
./install.sh /path/to/your-repo
```
Requirements: Ollama reachable (coder), `codex` CLI logged in (reviewer), Python 3.

## Config
Edit `.orchestra/orchestra.config.sh` (coder model, Ollama URL). Run `/cycle <feature>` in Claude Code.
