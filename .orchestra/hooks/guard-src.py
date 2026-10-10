#!/usr/bin/env python3
"""PreToolUse guard: block direct writes to src/ or tests/ so ALL code comes from
the delegated local coder (.orchestra/scripts/code.py). Reads the hook JSON on stdin;
emits a deny decision when a write to source is attempted, otherwise stays silent."""
import json, re, sys

try:
    d = json.load(sys.stdin)
except Exception:
    sys.exit(0)

tool = d.get("tool_name", "")
ti = d.get("tool_input", {}) or {}

def deny(reason):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}))
    sys.exit(0)

DELEGATE = 'Delegate code to the local coder instead: python3 .orchestra/scripts/code.py "<task>"'

if tool in ("Write", "Edit", "NotebookEdit"):
    if re.search(r'(^|/)(src|tests)/', ti.get("file_path", "")):
        deny("Orchestra: direct edits to src/ or tests/ are blocked. " + DELEGATE)
elif tool == "Bash":
    c = ti.get("command", "")
    src = r'(?:\./|["\'])?(?:src|tests)/'
    pats = [
        r'(?<![-=<>])>>?\s*' + src,                                        # cat > src/  |  >> tests/
        r'\btee\b[^|;&\n]*\b(?:src|tests)/',                    # tee src/...
        r'\bsed\b[^|;&\n]*-i[^|;&\n]*\b(?:src|tests)/',         # sed -i ... src/
        r'\b(?:cp|mv|install|rsync)\b[^|;&\n]*\b(?:src|tests)/',# cp/mv into src/
        r'open\(\s*["\'](?:\./)?(?:src|tests)/',                # python open("src/..","w")
    ]
    if any(re.search(p, c) for p in pats):
        deny("Orchestra: this command writes to src/ or tests/. " + DELEGATE)

sys.exit(0)
