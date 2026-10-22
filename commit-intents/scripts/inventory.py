"""Inventory of the commits in scope: every commit whose message names its session (by default a Claude-Session
trailer; set INTENTS_SESSION_PATTERN to a regex whose first group is the session id, e.g. for another agent system)
on main of the given repos, and every merge commit that brings at least one of them in. Plan commits (only .vibe/ changed) get the commit they join.

  inventory.py <folder of bare clones> <repo>...   each repo is a bare clone <folder>/<repo>; writes data/commits.json"""
import os, json, re, subprocess, sys
from pathlib import Path

MIRROR = Path(sys.argv[1])
OUT = Path(os.environ.get("INTENTS_WORKSPACE", ".")).resolve() / "data" / "commits.json"
REPOS = sys.argv[2:]
# the session id must equal the name of the session file: sessions/<id>.jsonl
SESSION = os.environ.get("INTENTS_SESSION_PATTERN", r"Claude-Session:\s*\S*?(session_[A-Za-z0-9]+)")
SEP = "\x1e"

def git(repo, *args):
    return subprocess.run(["git", "-C", str(MIRROR / repo), *args], capture_output=True, text=True, check=True).stdout

def commits(repo):
    fmt = SEP.join(["%H", "%P", "%an", "%ae", "%aI", "%cn", "%cI", "%B"]) + "\x1d"
    for raw in git(repo, "log", "main", "--topo-order", "--reverse", f"--format={fmt}").split("\x1d"):
        raw = raw.strip("\n")
        if not raw:
            continue
        sha, parents, an, ae, ad, cn, cd, body = raw.split(SEP)
        yield dict(sha=sha, parents=parents.split(), author=an, authorEmail=ae, authorDate=ad, committer=cn,
                   committerDate=cd, message=body.strip())

def files(repo, sha):
    out = git(repo, "show", "--numstat", "--format=", sha)
    rows = []
    for line in out.splitlines():
        if line.strip():
            add, rem, path = line.split("\t", 2)
            rows.append(dict(path=path, added=None if add == "-" else int(add), removed=None if rem == "-" else int(rem)))
    return rows

result = []
for repo in REPOS:
    all_commits = list(commits(repo))
    in_scope = set()
    for c in all_commits:
        m = re.search(SESSION, c["message"])
        c["session"] = m.group(1) if m else None
        if c["session"] and len(c["parents"]) < 2:
            in_scope.add(c["sha"])
    for c in all_commits:
        c["repo"] = repo
        c["subject"] = c["message"].splitlines()[0] if c["message"] else ""
        pr = re.search(r"Merge pull request #(\d+)", c["subject"]) or re.search(r"\(#(\d+)\)\s*$", c["subject"])
        c["pr"] = int(pr.group(1)) if pr else None
        if len(c["parents"]) == 2:
            brought = git(repo, "rev-list", f"{c['parents'][0]}..{c['parents'][1]}").split()
            c["brings"] = [s for s in brought if s in in_scope]
            if not c["brings"]:
                continue
            c["kind"] = "merge"
        elif c["sha"] in in_scope:
            c["kind"] = "commit"
        else:
            continue
        c["files"] = files(repo, c["sha"]) if c["kind"] == "commit" else []
        paths = [f["path"] for f in c["files"]]
        c["planOnly"] = bool(paths) and all(p.startswith(".vibe/") for p in paths)
        c["touchesPlan"] = any(p.startswith(".vibe/") for p in paths)
        if c["touchesPlan"]:
            c["planDiff"] = git(repo, "show", "--format=", c["sha"], "--", ".vibe/")
        result.append(c)

# A commit of only the plan file joins another commit, by these rules in this order:
#   parent      its parent is a commit of the same session (same branch): it joins the parent, as the plan written
#               after the change it records;
#   next        it starts its pull request (the parent is on main): it joins the next commit of the same pull request
#               that changes more than the plan, as the plan written before the change it prepares;
#   plan-pr     its pull request holds only plan commits: they become one commit, joined to the first of them;
#   none        neither applies: it stays its own commit, part of the intent.
# A chain of plan commits joins the same commit as its first one.
by_sha = {c["sha"]: c for c in result}
pr_of = {}
for m in result:
    if m["kind"] == "merge":
        for sha in m["brings"]:
            pr_of.setdefault(sha, m)
for repo in REPOS:
    order = [c for c in result if c["repo"] == repo and c["kind"] == "commit"]
    pos = {c["sha"]: i for i, c in enumerate(order)}
    for c in order:
        if not c["planOnly"]:
            continue
        parent = by_sha.get(c["parents"][0]) if c["parents"] else None
        while parent and parent["kind"] == "commit" and parent["session"] == c["session"] and parent["planOnly"]:
            parent = by_sha.get(parent["parents"][0]) if parent["parents"] else None
        target, rule = None, "none"
        if parent and parent["kind"] == "commit" and parent["session"] == c["session"]:
            target, rule = parent, "parent"
        elif c["sha"] in pr_of:
            same_pr = sorted((by_sha[s] for s in pr_of[c["sha"]]["brings"]), key=lambda o: pos[o["sha"]])
            later = [o for o in same_pr if pos[o["sha"]] > pos[c["sha"]] and not o["planOnly"]]
            if later:
                target, rule = later[0], "next"
            else:
                first = same_pr[0]
                target, rule = (None, "plan-pr") if first is c else (first, "plan-pr")
        c["joinsWith"] = target["sha"] if target else None
        c["joinRule"] = rule
        if c["sha"] in pr_of:
            c["prMerge"] = pr_of[c["sha"]]["sha"]

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(result, ensure_ascii=False, indent=1))
by = {}
for c in result:
    k = by.setdefault(c["repo"], {"commit": 0, "merge": 0, "planOnly": 0})
    k[c["kind"]] += 1
    k["planOnly"] += c["planOnly"]
print(json.dumps(by, indent=1))
joins = [c for c in result if c.get("planOnly")]
for c in joins:
    t = by_sha.get(c["joinsWith"]) if c["joinsWith"] else None
    print(f'{c["repo"]:<19} {c["sha"][:7]} {c["authorDate"][:16]} {c["joinRule"]:<12} -> '
          f'{t["sha"][:7] + " " + t["authorDate"][:16] + " " + t["subject"][:50] if t else "-"}')
print("sessions:", len({c["session"] for c in result if c["session"]}))
