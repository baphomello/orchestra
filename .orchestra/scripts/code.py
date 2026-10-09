#!/usr/bin/env python3
"""Lean coding agent over Ollama's native tool-calling, with a text fallback.

The orchestrator feeds it one curated task; it edits the repo directly through a
tiny tool set and verifies with `run`. No skills, no MCP, no framework.

Many local models emit tool calls as text (```json {...}``` or <tool_call>{...}</tool_call>)
instead of native tool_calls, so we parse those too.

Usage:  python3 code.py "<task>"   |   python3 code.py --task-file path
Env (orchestra.config.sh): ORCHESTRA_MODEL, ORCHESTRA_OLLAMA_URL, ORCHESTRA_REPO,
     ORCHESTRA_MAX_STEPS, ORCHESTRA_CHAT_TIMEOUT, ORCHESTRA_RUN_TIMEOUT
"""
import json, os, re, subprocess, sys, urllib.request

MODEL   = os.environ.get("ORCHESTRA_MODEL", "qwen2.5-coder:7b")
BASE    = os.environ.get("ORCHESTRA_OLLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
REPO    = os.path.abspath(os.environ.get("ORCHESTRA_REPO", os.getcwd()))
MAXSTEP = int(os.environ.get("ORCHESTRA_MAX_STEPS", "30"))
RUN_TIMEOUT  = int(os.environ.get("ORCHESTRA_RUN_TIMEOUT", "300"))
CHAT_TIMEOUT = int(os.environ.get("ORCHESTRA_CHAT_TIMEOUT", "900"))

SYSTEM = (
    "You are a focused coding agent working inside a single repository. Make exactly "
    "the change described in the task — nothing more. Do not chat or explain; act "
    "through tools.\n"
    "Rules:\n"
    "- Use tools to read/write files and run commands. NEVER print code as an answer; "
    "write it to the file with write_file.\n"
    "- Emit tool calls using the native function-call mechanism, one at a time.\n"
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
    return f"exit={r.returncode}\n{(r.stdout + r.stderr)[-4000:]}"

HANDLERS = {"write_file": write_file, "read_file": read_file, "run": run}

def extract_text_calls(text):
    """Parse tool calls a model emitted as text instead of native tool_calls."""
    if not text:
        return []
    regions = re.findall(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    regions += re.findall(r"<tool_call>\s*(.*?)\s*</tool_call>", text, re.DOTALL)
    if not regions:
        regions = [text]
    out, dec = [], json.JSONDecoder()
    for region in regions:
        s, i = region.strip(), 0
        while True:
            j = s.find("{", i)
            if j < 0:
                break
            try:
                obj, end = dec.raw_decode(s, j)
                i = end
                if isinstance(obj, dict) and "name" in obj:
                    out.append({"function": {"name": obj["name"],
                                             "arguments": obj.get("arguments", {})}})
            except Exception:
                i = j + 1
    return out

def chat(messages):
    body = json.dumps({"model": MODEL, "messages": messages,
                       "tools": TOOLS, "stream": False}).encode()
    req = urllib.request.Request(BASE + "/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=CHAT_TIMEOUT) as r:
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
    nudged = 0
    last_sig, repeat = None, 0
    for step in range(1, MAXSTEP + 1):
        try:
            msg = chat(messages)
        except Exception as e:
            print(f"\n[ERROR] chat failed at step {step}: {e}", flush=True)
            print("[STOP] model unreachable or too slow; partial work left on disk.", flush=True)
            return 2
        calls = msg.get("tool_calls") or []
        source = "native"
        if not calls:
            calls = extract_text_calls(msg.get("content") or "")
            source = "text"
        if not calls:
            messages.append({"role": "assistant", "content": msg.get("content") or ""})
            txt = (msg.get("content") or "").strip()
            print(f"[step {step}] no tool call. model said: {txt[:200]}", flush=True)
            nudged += 1
            if nudged > 3:
                print("[STOP] model will not call tools; giving up.", flush=True)
                return 1
            messages.append({"role": "user", "content":
                "Call the tools directly (write_file/run/finish). Do not print JSON or code."})
            continue
        nudged = 0
        # coherent history: always record as native tool_calls, whatever the source
        messages.append({"role": "assistant", "content": "", "tool_calls": calls})
        sig = json.dumps([(c["function"]["name"], c["function"].get("arguments")) for c in calls], sort_keys=True)
        repeat = repeat + 1 if sig == last_sig else 0
        last_sig = sig
        if repeat >= 2:
            print(f"[STOP] model repeated identical actions {repeat+1}x without progress; not converging.", flush=True)
            return 1
        for c in calls:
            fn = c["function"]["name"]; args = c["function"].get("arguments") or {}
            if fn == "finish":
                print(f"\n[FINISH] {args.get('summary','')}", flush=True); return 0
            try:
                result = HANDLERS[fn](**args)
            except Exception as e:
                result = f"ERROR: {e}"
            line = result.splitlines()[0][:160] if result else ""
            print(f"[step {step}] ({source}) {fn}({json.dumps(args)[:100]}) -> {line}", flush=True)
            messages.append({"role": "tool", "tool_name": fn, "content": result})
    print("\n[STOP] hit max steps without finish", flush=True); return 1

if __name__ == "__main__":
    sys.exit(main())
