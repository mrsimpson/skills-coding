# The formats of the workspace

The skill works for sessions of any agent system. Its interface is two things:

1. **One session file per session**, in the format below. Whoever produces it (a script for the agent system, an
   export, a hand conversion) is outside the skill. For Claude Code, `scripts/serialize.py` and the skill
   `claude-code-sessions` produce it.
2. **The session id in each commit message**, so that the inventory can link commits to sessions. By default a
   trailer `Claude-Session: …session_<id>`. For another system, set `INTENTS_SESSION_PATTERN` to a regex whose first
   group is the session id, e.g. `Agent-Session:\s*(\S+)`. The id is exactly what that group captures, prefix
   included (Claude Code: `session_01Abc…`), and the file is `sessions/<that id>.jsonl`.

Check a delivered file before using it: `scripts/check_sessions.py <folder>`. It reports what does not fit and
converts nothing; with `data/commits.json` present it also reports a file that ends before its session's last
commit.

Everything after these two (cut, writing, review, rewrite) is the same for every agent system. All files are UTF-8;
times are ISO 8601 with a time zone (`2026-10-13T15:33:02Z`).

## Input: `sessions/<session id>.jsonl`

One JSON object per line, sorted by time. Required for every line: `time`, `role`, `text`.

```json
{"time": "2026-10-13T15:33:02Z", "role": "user", "text": "This sounds quite math-specific. …"}
{"time": "2026-10-13T15:34:40Z", "role": "assistant", "text": "For biology, …"}
{"time": "2026-10-13T15:40:11Z", "role": "action", "text": "bash: git commit -m \"feat(quiz): …\""}
```

| `role` | What it is | Used for |
|---|---|---|
| `user` | What the person typed. Nothing the system wrote: no tool results, reminders, notifications, summaries. | The cut into intents (each message starts or extends one) and the trigger. Required. |
| `assistant` | The agent's reply text, without thinking or tool output. | Understanding proposals the person only answered with "yes". Optional but strongly advised. |
| `action` | One line per tool call that explains the work: commit, push, pull request, merge, issue, starting another session or messaging it. Free text, short. | Linking a message to the commits it caused. Optional. |

Leave out events of subagents of the session: their work shows up as commits, their prompts are not the person's.

## Input, optional: `data/session-parents.json`

For sessions that another session created; their `user` lines are prompts, not the person.

```json
{"<child session id>": {"parent": "<parent session id>", "time": "…", "title": "…", "prompt": "…"}}
```

## Produced by the scripts

| File | Written by | Content |
|---|---|---|
| `data/commits.json` | `inventory.py` | A list of commits in scope: `repo`, `sha`, `parents`, `author`, `authorEmail`, `authorDate`, `committer`, `committerDate`, `message`, `subject`, `session`, `pr`, `kind` (`commit` or `merge`), `files` (`path`, `added`, `removed`), `planOnly`, `touchesPlan`, `planDiff`; for a merge `brings` (the shas it brings in); for a plan commit `joinsWith`, `joinRule`, `prMerge`. |
| `data/intents.json` | `intents.py` | The first cut: a list of `id`, `session`, `messages` (the `user` lines), `commits` (shas), `repos`, `start`, `end`. An id is the session id's last 8 characters and a number within the session (`MHJp-012`); a split adds `b`. Ids stay the same when session files are added. |
| `data/written/<id>.json` | the agents (`references/brief.md`) | One written intent; the format is `references/schema.md`. |
| `data/slices.json` | by hand or a short script | A list of lists of intent ids, one list per agent. |
| `data/map-<repo>.json` | `rewrite.py` | Old sha → new sha for every commit of `main`. |
| `view/index.html` | `build_view.py` | The review page. |
