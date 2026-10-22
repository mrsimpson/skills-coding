---
name: commit-intents
description: "Apply this when commits say what changed but not why, and the why is in the agent sessions that made them (Claude Code or any other system whose sessions can be exported as messages): reconstruct each change's intent from those sessions, review it in a page, and rewrite the commit history with the new messages."
---

Reconstruct commit intents from agent sessions and rewrite the history with them.

**Words**
- **Intent:** the why of a change: the problem or the goal. One intent can hold commits in several repos.
- **Key decisions:** the choices made, each with what it was chosen over. They do not refine the intent.
- **Key changes:** the what: how the system behaves differently now. Only in the commit message.

**Workspace**
- One folder holds `data/`, `sessions/` and `view/`. Run the scripts from there, or set `INTENTS_WORKSPACE`.
- Scripts: `scripts/` of this skill. Formats of every file: `references/formats.md`. Rules and the format of a
  written intent: `references/schema.md`. Agent brief: `references/brief.md`.
- **Any agent system:** the skill starts from one file per session (`sessions/<id>.jsonl`: time, role, text) and
  the session id in each commit message (`INTENTS_SESSION_PATTERN`, default the `Claude-Session:` trailer). Produce
  those, and every step from 4 on works unchanged (`references/formats.md`).
- Never put session texts in a public repo; they hold the person's messages. The written intents quote the person in
  `trigger`: ask before publishing them.

**Steps**
1. **Mirror:** a bare clone (`git clone --bare`) of every repo the sessions worked in, not only the one you care
   about. Without the commits of the other repos, the cut puts hours of messages into one intent.
2. **Inventory:** `inventory.py <mirrors> <repo>...` writes `data/commits.json`: every commit that names its
   session, the merges that bring them in, and for each plan commit (only `.vibe/`) the commit it
   joins.
3. **Sessions:** one file per session of the inventory, in the format of `references/formats.md`. For Claude Code:
   `serialize.py` (skill `claude-code-sessions`: page `list_events`, let large pages land in files, never read
   them) and `session_parents.py` for sessions that another session created (their "user" lines are prompts; the
   person's request is in the parent). Get `claude-code-sessions` from the
   same place as this skill (mrsimpson/skills-coding). For a cloud session without a local transcript, its record
   names its parent (`get_session`: `parent_session_id`). For another system: its own export into the same format.
   Check every delivered file against the format before using it; never guess a conversion.
4. **Cut:** `intents.py` writes `data/intents.json`: per session, the person's messages since the last commit and
   the commits up to the next message. This is only the first proposal.
5. **Probe:** let one agent write about 10 intents by `references/brief.md`; `context.py <id>` gives it the source.
   Build the page (`build_view.py <ids>`), show it privately (a private artifact or the local file), and let the
   person review the texts before going on. The page's labels are German.
6. **Full run:** cut the intents into slices by time (`data/slices.json`), one agent per slice, all with the same
   brief. Then `validate.py` without arguments: every commit in exactly one intent, every squash group possible.
   One more agent resolves what it reports.
7. **Review:** `build_view.py`, publish. The person checks the cards marked "Zuordnung prüfen".
8. **Dry run:** `rewrite.py <bare clone> <repo>` in bare clones made fresh from the remote writes `main-rewritten`. It must report the
   final tree identical; every new commit has the tree of an old one.
9. **Rewrite:** only with the person's go and branch protection off. Per repo: fetch main, rewrite again, push the
   old main as branch `archive/pre-rewrite` (a proxy may block tags), check it is there, then
   `git push --force-with-lease=main:<old sha> origin main-rewritten:main`. If `archive/pre-rewrite` exists from
   an earlier run, use `archive/pre-rewrite-<date>`. Before: list the open pull requests on the host and merge or
   rebase them. After: every SHA of main has changed (signatures are dropped); old SHAs resolve via the archive.

**Rules that came from review**
- **Content over time:** a commit belongs to the request it serves, even if it came after the next message
  (subagents still running, usage limits). Record every move in `moved`, so the page can show it.
- **Split** an intent with two unrelated requests; drop one that has no commit left.
- **Squash only** commits that follow each other directly on one branch, no commit or merge between. The intent is
  a logical bracket; nothing is ever reordered.
- **Write the goal**, in active voice. Never narrate who said what ("the owner …"); only `trigger` quotes.
- **Child sessions:** take the trigger from the parent session.
- **Merges** keep their first line and list the new subjects they bring in. Trailers stay.
- **No ids, no foreign SHAs** in messages: no intent ids, no SHAs of other repos or later commits. Name repo and pull
  request ("lernapps/docs#46").
- **A second run** on a rewritten history: leave out the commit of an earlier data export, and pick a new archive
  name.
