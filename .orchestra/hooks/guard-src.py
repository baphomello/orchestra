#!/usr/bin/env python3
"""PreToolUse guard: block direct writes to src/ so ALL production code comes from the
delegated local coder (.orchestra/scripts/code.py). The orchestrator MAY write tests/
(it owns the acceptance oracle) and everything else. Reads the hook JSON on stdin; emits
a deny only for a direct write to src/, otherwise stays silent."""
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

DELEGATE = ('Delegate production code to the local coder: python3 .orchestra/scripts/code.py "<task>". '
            'You may write tests/ yourself — you own the oracle.')

if tool in ("Write", "Edit", "NotebookEdit"):
    if re.search(r'(^|/)src/', ti.get("file_path", "")):
        deny("Orchestra: direct edits to src/ are blocked. " + DELEGATE)
elif tool == "Bash":
    c = ti.get("command", "")
    src = r'(?:\./|["\'])?src/'
    pats = [
        r'(?<![-=<>])>>?\s*' + src,        # real redirect  cat > src/  (not an --> arrow)
        r'\btee\b[^|;&\n]*\bsrc/',
        r'\bsed\b[^|;&\n]*-i[^|;&\n]*\bsrc/',
        r'\b(?:cp|mv|install|rsync)\b[^|;&\n]*\bsrc/',
        r'open\(\s*["\'](?:\./)?src/',
    ]
    if any(re.search(p, c) for p in pats):
        deny("Orchestra: this command writes to src/. " + DELEGATE)

sys.exit(0)
