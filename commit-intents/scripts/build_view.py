"""Builds view/index.html: the written intents (data/written/*.json) with their sessions, times, repos and source
commits, injected as JSON into view/template.html."""
import os, json, sys
from pathlib import Path

ROOT = Path(os.environ.get("INTENTS_WORKSPACE", ".")).resolve()  # the workspace: data/, sessions/, view/
intents = {i["id"]: i for i in json.load(open(ROOT / "data" / "intents.json"))}
commits = {c["sha"]: c for c in json.load(open(ROOT / "data" / "commits.json"))}
out = []
only = set(sys.argv[1:])  # optional: build only these intent ids
for f in sorted((ROOT / "data" / "written").glob("i*.json")):
    w = json.load(open(f))
    if only and w["id"] not in only:
        continue
    i = dict(intents.get(w["id"]) or intents[w["id"].rstrip("b")])
    if w.get("start"):
        i["start"] = w["start"]
    moved = {}
    for m in w.get("moved", []):
        moved.setdefault(m["commit"], []).append({"kind": m["kind"], "from": m["from"], "why": m["why"]})
    groups = []
    for repo, gs in w.get("squash", {}).items():
        for g in gs:
            groups.append({"repo": repo, "message": g.get("message", ""), "reason": g.get("reason", ""),
                           "sources": [{"sha": s[:7], "subject": commits[s]["subject"], "date": commits[s]["authorDate"],
                                        "pr": commits[s].get("pr"), "plan": commits[s].get("planOnly", False),
                                        "moved": moved.get(s, [])}
                                       for s in g["commits"]]})
    own = [s for g in w.get("squash", {}).values() for grp in g for s in grp["commits"]]
    i["end"] = max(commits[s]["authorDate"] for s in own)
    i["repos"] = sorted(w.get("squash", {}))
    i["commits"] = own
    out.append({"id": w["id"], "session": i["session"], "from": i["start"], "to": i["end"], "repos": i["repos"],
                "commit": w.get("conventionalCommit", ""), "intent": w.get("intent", ""),
                "decisions": w.get("keyDecisions", []), "trigger": w.get("trigger", ""), "kind": w.get("kind", ""),
                "confidence": w.get("confidence", ""), "relations": w.get("relations", []), "groups": groups,
                "messages": len(i["messages"]), "sourceCount": len(i["commits"]),
                "misplaced": [{"sha": m["commit"][:7], "belongsTo": m.get("belongsTo", ""), "why": m.get("why", "")}
                              for m in w.get("misplaced", [])]})
html = (Path(__file__).resolve().parent / "template.html").read_text().replace("/*DATA*/[]", json.dumps(out, ensure_ascii=False))
(ROOT / "view").mkdir(exist_ok=True)
(ROOT / "view" / "index.html").write_text(html)
print(len(out), "intents ->", ROOT / "view" / "index.html")
