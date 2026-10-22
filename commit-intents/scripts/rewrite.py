"""Rewrites main of one repository with the written intents (data/written/*.json), in a bare clone, without
touching any tree: every commit keeps its tree, author and committer lines (names, e-mails, times) exactly; only
messages and parents change.

- A squash group becomes one commit: the tree of its last commit, the author line of its first, the committer line of
  its last, the group's message plus the trailers of its commits (Co-Authored-By, Claude-Session, Signed-off-by, and
  the names in INTENTS_TRAILERS).
- Another commit of the inventory keeps its place and gets its group's message.
- A merge commit that brings in commits of the inventory keeps its first line and lists the new subjects it brings.
- Every other commit (bots, people, commits after the inventory) keeps its message.
- Abbreviated or full SHAs of rewritten commits in messages are replaced by the new ones.
- Signatures are dropped; nothing is reordered. A signed commit therefore gets a new SHA even when its message stays,
  and so does every commit after it: expect every SHA of main to change.
- SHAs in messages are remapped only where they name an earlier commit of the same repo; a message cannot name its own
  new SHA, a later commit's or another repo's. Write repo and pull request number instead (references/schema.md).

  rewrite.py <bare repo> <repo name> [<new ref>]   writes refs/heads/main-rewritten (default) and data/map-<repo>.json
"""
import os, json, re, subprocess, sys
from pathlib import Path

ROOT = Path(os.environ.get("INTENTS_WORKSPACE", ".")).resolve()  # the workspace: data/, sessions/, view/
repo_dir, repo = sys.argv[1], sys.argv[2]
new_ref = sys.argv[3] if len(sys.argv) > 3 else "refs/heads/main-rewritten"
# trailers a squashed commit keeps from its commits; INTENTS_TRAILERS adds more names, comma-separated
TRAILER = re.compile(r"^(" + "|".join(["Co-Authored-By", "Co-authored-by", "Claude-Session", "Signed-off-by"] +
                     [t for t in os.environ.get("INTENTS_TRAILERS", "").split(",") if t]) + r"):.*$", re.M)

def git(*args, input=None):
    return subprocess.run(["git", "-C", repo_dir, *args], input=input, capture_output=True, text=True, check=True).stdout

CACHE = {}

def raw(sha):
    if sha not in CACHE:
        CACHE[sha] = _raw(sha)
    return CACHE[sha]

def _raw(sha):
    """tree, parents, author line, committer line, message of a commit (signature and other headers dropped)."""
    head, _, message = git("cat-file", "commit", sha).partition("\n\n")
    fields = {"parent": []}
    for line in head.split("\n"):
        if line.startswith(" "):
            continue  # continuation of a multi-line header (gpgsig)
        key, _, value = line.partition(" ")
        if key == "parent":
            fields["parent"].append(value)
        elif key in ("tree", "author", "committer"):
            fields[key] = value
    return fields["tree"], fields["parent"], fields["author"], fields["committer"], message

def write(tree, parents, author, committer, message):
    body = f"tree {tree}\n" + "".join(f"parent {p}\n" for p in parents) + f"author {author}\ncommitter {committer}\n\n{message}"
    return git("hash-object", "-t", "commit", "-w", "--stdin", input=body).strip()

inventory = {c["sha"]: c for c in json.load(open(ROOT / "data" / "commits.json")) if c["repo"] == repo}
group_of, groups, subject_new = {}, [], {}
for f in sorted((ROOT / "data" / "written").glob("i*.json")):
    for g in json.load(open(f))["squash"].get(repo, []):
        idx = len(groups)
        groups.append(g)
        for s in g["commits"]:
            group_of[s] = idx

order = git("rev-list", "--topo-order", "--reverse", "main").split()
pos = {s: i for i, s in enumerate(order)}
last_of = {i: max(g["commits"], key=pos.__getitem__) for i, g in enumerate(groups)}
first_of = {i: min(g["commits"], key=pos.__getitem__) for i, g in enumerate(groups)}
# an inner commit of a group must have no child outside the group, or the squash would cut a branch off
children = {}
for s in order:
    for p in raw(s)[1]:
        children.setdefault(p, []).append(s)
for i, g in enumerate(groups):
    for s in g["commits"]:
        if s != last_of[i] and any(group_of.get(c) != i for c in children.get(s, [])):
            sys.exit(f"{repo}: {s[:7]} has a child outside its group; split the group")

new = {}

def remap_shas(message):
    def sub(m):
        token = m.group(0)
        hits = [o for o in new if o.startswith(token.lower())] if len(token) >= 7 else []
        return new[hits[0]][:len(token)] if len(hits) == 1 else token
    return re.sub(r"\b[0-9a-f]{7,40}\b", sub, message)

def trailers(shas):
    seen = []
    for s in shas:
        for t in (m.group(0) for m in TRAILER.finditer(raw(s)[4])):
            if t not in seen:
                seen.append(t)
    return seen

def group_message(i):
    g = groups[i]
    text = g["message"].rstrip()
    extra = [t for t in trailers(g["commits"]) if t not in text]
    return text + ("\n\n" + "\n".join(extra) if extra else "") + "\n"

for s in order:
    tree, parents, author, committer, message = raw(s)
    i = group_of.get(s)
    if i is not None and s != last_of[i]:
        continue  # an inner commit of a group: written with the group's last commit
    if i is not None:
        first = first_of[i]
        _, first_parents, first_author, _, _ = raw(first)
        mapped = [new.get(p, p) for p in first_parents]
        sha = write(tree, mapped, first_author, committer, remap_shas(group_message(i)))
        for member in groups[i]["commits"]:
            new[member] = sha
        subject_new[sha] = groups[i]["message"].split("\n", 1)[0]
        continue
    mapped = [new.get(p, p) for p in parents]
    c = inventory.get(s)
    if c and c["kind"] == "merge":
        brought = []
        for b in sorted(c["brings"], key=pos.__getitem__):
            subj = subject_new.get(new.get(b, ""))
            if subj and subj not in brought:
                brought.append(subj)
        first_line = message.split("\n", 1)[0]
        message = first_line + "\n\n" + "\n".join(f"- {b}" for b in brought) + "\n"
    new[s] = write(tree, mapped, author, committer, remap_shas(message))

git("update-ref", new_ref, new[order[-1]])
json.dump(new, open(ROOT / "data" / f"map-{repo}.json", "w"), indent=0)
old_tree, new_tree = git("rev-parse", "main^{tree}").strip(), git("rev-parse", f"{new_ref}^{{tree}}").strip()
kept = [s for s in order if group_of.get(s) is None or s == last_of[group_of[s]]]
same = all(git("rev-parse", f"{s}^{{tree}}").strip() == git("rev-parse", f"{new[s]}^{{tree}}").strip() for s in kept[-50:])
print(f"{repo}: {len(order)} -> {len(set(new.values()))} commits; final tree {'identical' if old_tree == new_tree else 'DIFFERS'};"
      f" last 50 trees {'identical' if same else 'DIFFER'}")
sys.exit(0 if old_tree == new_tree and same else 1)
