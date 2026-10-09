#!/usr/bin/env python3
"""Lean coding agent over Ollama's native tool-calling.

The orchestrator feeds it one curated task; it edits the repo directly through a
tiny tool set and verifies with `run`. No skills, no MCP, no framework — the only
context the model sees is this ~1k system prompt, the task, and tool results.

Usage:
  python3 code.py "<task>"
  python3 code.py --task-file path/to/task.md
Env (set by orchestra.config.sh):
  ORCHESTRA_MODEL       Ollama model tag
  ORCHESTRA_OLLAMA_URL  e.g. http://192.168.32.1:11434
  ORCHESTRA_REPO        repo root (default: cwd)
  ORCHESTRA_MAX_STEPS   tool rounds cap (default: 30)
"""
import json, os, subprocess, sys, urllib.request

MODEL   = os.environ.get("ORCHESTRA_MODEL", "qwen2.5-coder:7b")
BASE    = os.environ.get("ORCHESTRA_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
REPO    = os.path.abspath(os.environ.get("ORCHESTRA_REPO", os.getcwd()))
MAXSTEP = int(os.environ.get("ORCHESTRA_MAX_STEPS", "30"))
RUN_TIMEOUT = int(os.environ.get("ORCHESTRA_RUN_TIMEOUT", "300"))

SYSTEM = (
    "You are a focused coding agent working inside a single repository. Make exactly "
    "the change described in the task — nothing more. Do not chat or explain; act "
    "through tools.\n"
    "Rules:\n"
    "- Use tools to read/write files and run commands. NEVER print code as an answer; "
    "write it to the file with write_file.\n"
    "- Paths are relative to the repo root. Stay inside the repo.\n"
    "- Match the existing code style. Keep the change minimal and on-task.\n"
    "- When the task is done AND verified (the requested test/command passes), call "
    "finish with a one-line summary. Do not call finish before verifying.\n"
    "Tools: write_file(path, content), read_file(path), run(command), finish(summary)."
)

TOOLS = [
    {"type": "function", "function": {"name": "write_file",
        "description": "Create or overwrite a file (relative path under repo root).",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"]}}},
    {"type": "function", "function": {"name": "read_file",
        "description": "Read a file's contents (relative path under repo root).",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string"}}, "required": ["path"]}}},
    {"type": "function", "function": {"name": "run",
        "description": "Run a shell command in the repo root and return its output.",
        "parameters": {"type": "object", "properties": {
            "command": {"type": "string"}}, "required": ["command"]}}},
    {"type": "function", "function": {"name": "finish",
        "description": "Signal the task is done and verified.",
        "parameters": {"type": "object", "properties": {
            "summary": {"type": "string"}}, "required": ["summary"]}}},
]

def _safe(path):
    p = os.path.abspath(os.path.join(REPO, path))
    if p != REPO and not p.startswith(REPO + os.sep):
        raise ValueError(f"path escapes repo: {path}")
    return p

def write_file(path, content):
    p = _safe(path); os.makedirs(os.path.dirname(p) or REPO, exist_ok=True)
    with open(p, "w", encoding="utf-8") as f: f.write(content)
    return f"wrote {len(content)} bytes to {path}"

def read_file(path):
    with open(_safe(path), encoding="utf-8", errors="replace") as f:
        return f.read()[:8000]

def run(command):
    r = subprocess.run(command, shell=True, cwd=REPO, capture_output=True,
                       text=True, timeout=RUN_TIMEOUT)
    out = (r.stdout + r.stderr)[-4000:]
    return f"exit={r.returncode}\n{out}"

HANDLERS = {"write_file": write_file, "read_file": read_file, "run": run}

def chat(messages):
    body = json.dumps({"model": MODEL, "messages": messages,
                       "tools": TOOLS, "stream": False}).encode()
    req = urllib.request.Request(BASE + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=RUN_TIMEOUT) as r:
        return json.loads(r.read())["message"]

def main():
    if len(sys.argv) >= 3 and sys.argv[1] == "--task-file":
        task = open(sys.argv[2], encoding="utf-8").read()
    elif len(sys.argv) >= 2:
        task = sys.argv[1]
    else:
        task = sys.stdin.read()
    print(f"[harness] model={MODEL} repo={REPO}\n[task] {task[:300]}\n", flush=True)

    messages = [{"role": "system", "content": SYSTEM},
                {"role": "user", "content": task}]
    for step in range(1, MAXSTEP + 1):
        msg = chat(messages)
        messages.append({k: v for k, v in msg.items() if k in ("role", "content", "tool_calls")})
        calls = msg.get("tool_calls") or []
        if not calls:
            txt = (msg.get("content") or "").strip()
            print(f"[step {step}] no tool call. model said: {txt[:300]}", flush=True)
            messages.append({"role": "user", "content":
                "Act through the tools (write_file/run/finish). Don't describe — do it."})
            continue
        for c in calls:
            fn = c["function"]["name"]; args = c["function"].get("arguments") or {}
            if fn == "finish":
                print(f"\n[FINISH] {args.get('summary','')}", flush=True); return 0
            try:
                result = HANDLERS[fn](**args)
            except Exception as e:
                result = f"ERROR: {e}"
            print(f"[step {step}] {fn}({json.dumps(args)[:120]}) -> {result.splitlines()[0][:160] if result else ''}", flush=True)
            messages.append({"role": "tool", "tool_name": fn, "content": result})
    print("\n[STOP] hit max steps without finish", flush=True); return 1

if __name__ == "__main__":
    sys.exit(main())
