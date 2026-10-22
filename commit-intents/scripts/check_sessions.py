"""Checks delivered session files against references/formats.md before they are used, and reports every problem in
plain words. It converts nothing.

  check_sessions.py <folder or files>...   e.g. a delivery folder, or sessions/

Checks: the name is <session id>.jsonl, each line is one JSON object with time, role and text, role is user,
assistant or action, time is ISO 8601 with a time zone, lines are sorted by time, and the file has at least one
user line. With data/commits.json in the workspace it also checks that each session of the inventory has a file
and that the file reaches the session's last commit. Exit 1 on any problem."""
import json, os, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(os.environ.get("INTENTS_WORKSPACE", ".")).resolve()
ROLES = {"user", "assistant", "action"}

def when(text):
    t = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if t.tzinfo is None:
        raise ValueError("no time zone")
    return t

files = []
for arg in sys.argv[1:]:
    p = Path(arg)
    files += sorted(p.iterdir()) if p.is_dir() else [p]
problems, found = [], {}
for f in files:
    if f.suffix != ".jsonl":
        problems.append(f"{f.name}: the name must be <session id>.jsonl")
        continue
    last, users, n = None, 0, 0
    for i, line in enumerate(open(f, encoding="utf-8"), 1):
        if not line.strip():
            continue
        n += 1
        try:
            r = json.loads(line)
        except ValueError:
            problems.append(f"{f.name} line {i}: not one JSON object per line")
            break
        missing = [k for k in ("time", "role", "text") if k not in r]
        if not isinstance(r, dict) or missing:
            problems.append(f"{f.name} line {i}: keys must be time, role, text (missing {', '.join(missing)})")
            break
        if r["role"] not in ROLES:
            problems.append(f"{f.name} line {i}: role {r['role']!r} is not user, assistant or action")
            break
        try:
            t = when(r["time"])
        except ValueError as e:
            problems.append(f"{f.name} line {i}: time {r['time']!r} is not ISO 8601 with a time zone ({e})")
            break
        if last and t < last:
            problems.append(f"{f.name} line {i}: not sorted by time")
            break
        last, users = t, users + (r["role"] == "user")
    if n and not users:
        problems.append(f"{f.name}: no user line; the cut needs the person's messages")
    found[f.stem] = last

inventory = ROOT / "data" / "commits.json"
if inventory.exists():
    newest = {}
    for c in json.load(open(inventory)):
        if c.get("session") and c["kind"] == "commit":
            newest[c["session"]] = max(newest.get(c["session"], c["authorDate"]), c["authorDate"])
    for session, at in sorted(newest.items()):
        if session in found and found[session] and found[session] < when(at):
            problems.append(f"{session}.jsonl ends at {found[session]:%Y-%m-%d %H:%M}, before its last commit at {at[:16]}")
    wanted = [s for s in newest if s not in found]
    if wanted and len(wanted) < len(newest):
        print(f"note: {len(wanted)} session(s) of the inventory have no file here (fine if you work on one repo)")
print("\n".join(problems) or f"ok: {len(found)} session file(s)")
sys.exit(1 if problems else 0)
