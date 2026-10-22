"""Prints what a subagent needs to write one intent: the session's entries (person, replies, actions) from the end
of the session's previous intent up to this intent's last commit, and the intent's commits with message and files.

  context.py <intent id>"""
import os, json, sys
from pathlib import Path

ROOT = Path(os.environ.get("INTENTS_WORKSPACE", ".")).resolve()  # the workspace: data/, sessions/, view/
intents = json.load(open(ROOT / "data" / "intents.json"))
commits = {c["sha"]: c for c in json.load(open(ROOT / "data" / "commits.json"))}
intent = next(i for i in intents if i["id"] == sys.argv[1])
same = [i for i in intents if i["session"] == intent["session"]]
before = [i for i in same if i["end"] < intent["start"]]
since = max((i["end"] for i in before), default="")
norm = lambda t: t.replace("Z", "+00:00")[:19]
print(f"# Intent {intent['id']} in {intent['session']}, {intent['start']} .. {intent['end']}\n")
print("## Session entries since the previous intent's last commit\n")
for line in open(ROOT / "sessions" / f"{intent['session']}.jsonl"):
    r = json.loads(line)
    if norm(since) < norm(r["time"]) <= norm(intent["end"]):
        text = r["text"] if r["role"] != "assistant" else r["text"][:3000]
        print(f"[{r['time'][:16]}] {r['role'].upper()}: {text}\n")
parents = json.load(open(ROOT / "data" / "session-parents.json")) if (ROOT / "data" / "session-parents.json").exists() else {}
if intent["session"] in parents:
    p = parents[intent["session"]]
    print(f"## This session was created by {p['parent']} at {p['time'][:16]} ({p['title']})")
    print("Its USER entries are that session's prompts, not the person's own words. The person's request is in the")
    print("parent session; here are the person's messages there in the 3 hours before, and the prompt it sent.\n")
    from datetime import datetime, timedelta
    at = datetime.fromisoformat(p["time"].replace("Z", "+00:00"))
    for line in open(ROOT / "sessions" / f"{p['parent']}.jsonl"):
        r = json.loads(line)
        when = datetime.fromisoformat(r["time"].replace("Z", "+00:00"))
        if r["role"] == "user" and at - timedelta(hours=3) <= when <= at:
            print(f"[{r['time'][:16]}] PERSON IN PARENT: {r['text']}\n")
    print(f"PROMPT TO THIS SESSION: {p['prompt'][:4000]}\n")
print("## Commits of this intent\n")
for sha in intent["commits"]:
    c = commits[sha]
    print(f"### {c['repo']} {sha[:7]} {c['authorDate']}  PR #{c.get('pr') or '?'}"
          + (f"  (plan commit; joins {(c['joinsWith'] or 'nothing')[:7]} by rule {c['joinRule']})" if c.get("planOnly") else ""))
    print(c["message"])
    print("Files: " + ", ".join(f"{f['path']} +{f['added']}/-{f['removed']}" for f in c["files"][:40]))
    print()
