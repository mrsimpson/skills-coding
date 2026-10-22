"""Cuts each session into intents: the messages a person wrote since the session's previous commit, and the commits
(in any repo) that follow them up to the person's next message. The commits' author date places them in time; a
plan commit goes with the commit it joins. Writes data/intents.json."""
import os, json, sys
from pathlib import Path
from datetime import datetime

ROOT = Path(os.environ.get("INTENTS_WORKSPACE", ".")).resolve()  # the workspace: data/, sessions/, view/
commits = json.load(open(ROOT / "data" / "commits.json"))
by_sha = {c["sha"]: c for c in commits}
t = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))

def anchor(c):
    while c.get("joinsWith"):
        c = by_sha[c["joinsWith"]]
    return c

intents = []
for path in sorted((ROOT / "sessions").glob("*.jsonl")):
    session = path.stem
    messages = [r for r in map(json.loads, open(path)) if r["role"] == "user"]
    own = sorted((c for c in commits if c["kind"] == "commit" and c["session"] == session),
                 key=lambda c: t(anchor(c)["authorDate"]))
    events = [(t(m["time"]), "m", m) for m in messages] + [(t(anchor(c)["authorDate"]), "c", c) for c in own]
    events.sort(key=lambda e: (e[0], e[1] == "c"))
    pending, current = [], None
    for _, kind, item in events:
        if kind == "m":
            if current:
                current = None
            pending.append(item)
        else:
            if current is None:
                current = {"session": session, "messages": pending, "commits": []}
                intents.append(current)
                pending = []
            current["commits"].append(item["sha"])
    for i in intents:
        if i["session"] == session:
            cs = [by_sha[s] for s in i["commits"]]
            i["repos"] = sorted({c["repo"] for c in cs})
            i["start"] = i["messages"][0]["time"] if i["messages"] else min(c["authorDate"] for c in cs)
            i["end"] = max(c["authorDate"] for c in cs)

for n, i in enumerate(intents, 1):
    i["id"] = f"i{n:03}"
json.dump(intents, open(ROOT / "data" / "intents.json", "w"), ensure_ascii=False, indent=1)

import collections
sizes = collections.Counter(min(len(i["commits"]), 10) for i in intents)
print("intents:", len(intents), "| commits per intent (10 = 10+):", dict(sorted(sizes.items())))
print("multi-repo intents:", sum(len(i["repos"]) > 1 for i in intents),
      "| without messages:", sum(not i["messages"] for i in intents),
      "| messages per intent max:", max(len(i["messages"]) for i in intents))
