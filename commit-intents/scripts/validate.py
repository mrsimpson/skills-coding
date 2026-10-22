"""Checks the written intents (data/written/*.json): valid JSON with the fields the view needs, every commit in
exactly one squash group across all files, and every group squashable: one repo, and a run of commits each directly
on the one before (first parent), with nothing between. Exit 1 on any finding.

  validate.py [<intent id>...]   only these files; their commits are checked against each other
  validate.py --repo <name>      all files; but only the commits of this repo must each be in an intent"""
import os, json, re, sys
from pathlib import Path

ROOT = Path(os.environ.get("INTENTS_WORKSPACE", ".")).resolve()  # the workspace: data/, sessions/, view/
commits = {c["sha"]: c for c in json.load(open(ROOT / "data" / "commits.json"))}
args = sys.argv[1:]
repo_only = args[args.index("--repo") + 1] if "--repo" in args else None
only = set(a for a in args if a not in ("--repo", repo_only))
order = {c["sha"]: i for i, c in enumerate(json.load(open(ROOT / "data" / "commits.json")))}  # history order
FIELDS = ["id", "conventionalCommit", "intent", "keyDecisions", "trigger", "kind", "relations", "confidence", "squash"]
findings, seen = [], {}
for f in sorted((ROOT / "data" / "written").glob("i*.json")):
    try:
        w = json.load(open(f))
    except ValueError as e:
        findings.append(f"{f.name}: not JSON ({e})")
        continue
    if only and w.get("id") not in only:
        continue
    findings += [f"{f.name}: field {k} missing" for k in FIELDS if k not in w]
    own = {s for gs in w.get("squash", {}).values() for g in gs for s in g["commits"]}
    for m in w.get("moved", []):
        if m.get("commit") not in own or m.get("kind") not in ("moved", "split", "dropped", "plan-rule"):
            findings.append(f"{f.name}: moved entry {str(m.get('commit'))[:7]} is not in this intent or has no valid kind")
    for repo, groups in w.get("squash", {}).items():
        for g in groups:
            if not g.get("message", "").strip():
                findings.append(f"{f.name}: a group in {repo} has no message")
            run = sorted(g["commits"], key=order.__getitem__)
            for s in run:
                if commits[s]["repo"] != repo:
                    findings.append(f"{f.name}: {s[:7]} is in {commits[s]['repo']}, not {repo}")
                if s in seen:
                    findings.append(f"{s[:7]} is in {seen[s]} and in {f.name}")
                seen[s] = f.name
            if re.search(r"\bi\d{3}b?\b", g.get("message", "")):
                findings.append(f"{f.name}: a message in {repo} names an intent id; the history does not know it")
            for before, after in zip(run, run[1:]):
                if commits[after]["parents"][:1] != [before]:
                    findings.append(f"{f.name}: {after[:7]} does not follow {before[:7]} directly "
                                    f"(its parent is {commits[after]['parents'][0][:7]}); split the group")
if not only:
    scope = [c["sha"] for c in commits.values() if c["kind"] == "commit" and (not repo_only or c["repo"] == repo_only)]
    findings += [f"{s[:7]} ({commits[s]['repo']}, {commits[s]['subject'][:50]}) is in no intent" for s in scope if s not in seen]
print("\n".join(findings) or f"ok: {len(seen)} commits")
sys.exit(1 if findings else 0)
