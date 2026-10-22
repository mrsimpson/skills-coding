"""Serializes Claude Code session transcripts into one JSONL file per session (skill claude-code-sessions in
mrsimpson/skills-coding): what the person typed (user), the reply text (assistant), and the tool calls that explain
the work (action: commits, pushes, pull requests, merges, issues). Subagent events, tool results, thinking and text
the harness writes are left out.

  serialize.py remote <session_id> <page file>...   pages of list_events as saved files (any order; re-runs merge)
  serialize.py local  <session_id> <transcript.jsonl>

Writes sessions/<session_id>.jsonl, sorted by time and without duplicates."""
import os, json, re, sys
from pathlib import Path

OUT = Path(os.environ.get("INTENTS_WORKSPACE", ".")).resolve() / "sessions"
HARNESS = re.compile(r"^\s*(<(system-reminder|task-notification|local-command|command-|bash-|user-prompt-submit-hook|"
                     r"webhook|wake|child-session|scheduled|other-session|agent-message|pasted_content)|"
                     r"This session is being continued|\[Request interrupted|Stop hook feedback|Caveat:|"
                     r"\[SYSTEM NOTIFICATION)")
ACTION_TOOLS = re.compile(r"mcp__github__(create_pull_request|merge_pull_request|issue_write|update_pull_request|"
                          r"add_issue_comment|create_branch|push_files|create_or_update_file)")
ACTION_BASH = re.compile(r"\bgit (commit|push|merge|rebase|tag)\b|\bgh (pr|issue)\b")

def events(path):
    """The events of one saved page: its text (possibly a JSON list of text blocks) holds {"ccr": ...}."""
    text = Path(path).read_text()
    if text.lstrip().startswith("["):
        try:
            text = "".join(b.get("text", "") for b in json.loads(text))
        except ValueError:
            pass
    data, _ = json.JSONDecoder().raw_decode(text[text.index('{"ccr"'):])
    return data["ccr"].get("data", [])

def text_blocks(content):
    if isinstance(content, str):
        return content
    return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")

def action_of(block):
    name, args = block.get("name", ""), block.get("input") or {}
    if name == "Bash" and ACTION_BASH.search(args.get("command", "")):
        return "bash: " + args["command"][:600]
    if name.endswith(("create_session", "send_message")):
        return name.split("__")[-1] + ": " + (args.get("title", "") + " | " if args.get("title") else "") + \
            (args.get("prompt") or args.get("message") or "")[:2000]
    if ACTION_TOOLS.search(name):
        keep = {k: args[k] for k in ("owner", "repo", "title", "pullNumber", "issue_number", "method", "head", "base",
                                     "merge_method", "state", "branch", "message") if k in args}
        return name.removeprefix("mcp__github__") + " " + json.dumps(keep, ensure_ascii=False)
    return None

def rows(time, role, message, meta):
    if meta.get("parent_tool_use_id") or meta.get("isSidechain") or meta.get("isMeta") or \
            meta.get("isCompactSummary") or meta.get("isSynthetic"):
        return
    content = message.get("content", "")
    if role == "user":
        if isinstance(content, list) and any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return
        text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text_blocks(content), flags=re.S).strip()
        if text and not HARNESS.match(text):
            yield {"time": time, "role": "user", "text": text}
    elif role == "assistant":
        text = text_blocks(content).strip()
        if text:
            yield {"time": time, "role": "assistant", "text": text}
        for block in content if isinstance(content, list) else []:
            if isinstance(block, dict) and block.get("type") == "tool_use" and (action := action_of(block)):
                yield {"time": time, "role": "action", "text": action}

def remote(files):
    for f in files:
        for ev in events(f):
            kind = next((k for k in ("user", "assistant") if k in ev), None)
            if kind:
                payload = ev[kind].get("internal_anthropic_catchall", ev[kind])
                yield from rows(payload.get("timestamp") or ev["created_at"], kind, payload.get("message") or {},
                                payload)

def local(path):
    for line in open(path):
        try:
            e = json.loads(line)
        except ValueError:
            continue
        if e.get("type") in ("user", "assistant"):
            yield from rows(e["timestamp"], e["type"], e.get("message") or {}, e)

mode, session, *inputs = sys.argv[1:]
out = OUT / f"{session}.jsonl"
found = list(remote(inputs) if mode == "remote" else local(inputs[0]))
if mode == "remote" and out.exists():
    found += [json.loads(l) for l in open(out)]
norm = lambda t: t.replace("Z", "+00:00")[:19]
seen, unique = set(), []
for r in sorted(found, key=lambda r: norm(r["time"])):
    key = (norm(r["time"]), r["role"], r["text"])
    if key not in seen:
        seen.add(key)
        unique.append(r)
OUT.mkdir(exist_ok=True)
out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in unique))
counts = {role: sum(r["role"] == role for r in unique) for role in ("user", "assistant", "action")}
print(session, counts, unique[0]["time"][:16] if unique else "-", "..", unique[-1]["time"][:16] if unique else "-")
