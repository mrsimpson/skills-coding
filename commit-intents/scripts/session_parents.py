"""Finds the sessions another session created (create_session), with the time, title and prompt, so that an intent
of a child session can be traced to the request in its parent. Reads local transcripts; writes
data/session-parents.json: {child: {parent, time, title, prompt}}.

  session_parents.py <parent session id> <transcript.jsonl>

INTENTS_SESSION_ID is the regex of a session id in a tool result (default: Claude Code's session_<id>). For cloud
sessions without a local transcript, the session record names its parent (get_session: parent_session_id); write
those entries into data/session-parents.json by hand or with a short script."""
import os, json, re, sys
from pathlib import Path

ROOT = Path(os.environ.get("INTENTS_WORKSPACE", ".")).resolve()  # the workspace: data/, sessions/, view/
parent, path = sys.argv[1:]
out_file = ROOT / "data" / "session-parents.json"
found = json.load(open(out_file)) if out_file.exists() else {}
pending = {}
for line in open(path):
    try:
        e = json.loads(line)
    except ValueError:
        continue
    content = (e.get("message") or {}).get("content")
    for b in content if isinstance(content, list) else []:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "tool_use" and b.get("name", "").endswith("create_session"):
            args = b.get("input") or {}
            pending[b["id"]] = {"parent": parent, "time": e["timestamp"], "title": args.get("title", ""),
                                "prompt": args.get("prompt", "")}
        elif b.get("type") == "tool_result" and b.get("tool_use_id") in pending:
            m = re.search(os.environ.get("INTENTS_SESSION_ID", r"session_[A-Za-z0-9]{20,}"), json.dumps(b.get("content")))
            if m:
                found[m.group(0)] = pending[b["tool_use_id"]]
json.dump(found, open(out_file, "w"), ensure_ascii=False, indent=1)
print(len(found), "child sessions ->", out_file)
