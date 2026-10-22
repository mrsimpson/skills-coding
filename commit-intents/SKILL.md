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
   about. Without the commits of the other repos, the cut puts hours of messages into one intent. To find them:
   mirror every repo of the owner you can read; if you cannot list them, start with the target repo and add the
   repos that the sessions' `action` lines name (git pushes, pull requests), then run the inventory again. On a
   second run, the earlier data export names the repos.
2. **Inventory:** `inventory.py <mirrors> <repo>...` writes `data/commits.json`: every commit that names its
   session, the merges that bring them in, and for each plan commit (only `.vibe/`) the commit it
   joins. On a second run, leave out the commit of the earlier data export with `--exclude <sha>`.
3. **Sessions:** one file per session of the inventory, in the format of `references/formats.md`. For Claude Code:
   `serialize.py` (skill `claude-code-sessions`: page `list_events`, let large pages land in files, never read
   them) and `session_parents.py` for sessions that another session created (their "user" lines are prompts; the
   person's request is in the parent). Get `claude-code-sessions` from the
   same place as this skill (mrsimpson/skills-coding). For a cloud session without a local transcript, its record
   names its parent (`get_session`: `parent_session_id`). For another system: its own export into the same format.
   Check every delivered file with `check_sessions.py <folder>` before using it; never convert it yourself, ask for
   the right format. A session that is still running: serialize it again before writing and before the dry run.
4. **Cut:** `intents.py` writes `data/intents.json`: per session, the person's messages since the last commit and
   the commits up to the next message. This is only the first proposal.
5. **Probe:** let one agent write about 10 intents by `references/brief.md`; `context.py <id>` gives it the source.
   Build the page (`build_view.py <ids>`), show it privately (a private artifact or the local file), and let the
   person review the texts before going on. The page's labels are German.
6. **Full run:** cut the intents into slices by time (`data/slices.json`), one agent per slice, all with the same
   brief. Then `validate.py` without arguments: every commit in exactly one intent, every squash group possible.
   One more agent resolves what it reports.
7. **Review:** `build_view.py`, show it privately as in step 5. The person checks the cards marked "Zuordnung
   prüfen". Publish the page or the written intents only with the person's yes: they quote the person.
8. **Dry run:** `rewrite.py <bare clone> <repo>` in bare clones made fresh from the remote writes `main-rewritten`.
   It must report the final tree and every kept commit's tree identical. A note about commits that name a session
   but are not in the inventory means main moved on: run the inventory again, or accept that they keep their
   message.
9. **Rewrite:** only with the person's go and branch protection off. Per repo: fetch main, rewrite again, push the
   old main as branch `archive/pre-rewrite` (a proxy may block tags), check it is there, then
   `git push --force-with-lease=main:<old sha> origin main-rewritten:main`. If `archive/pre-rewrite` exists from
   an earlier run, use `archive/pre-rewrite-<date>`. Before: list the open pull requests on the host and merge or
   rebase them. After: from the first changed commit on, every SHA is new (a dropped signature counts as a change);
   old SHAs resolve via the archive.

**One repo only**
- Mirror and inventory all repos as in steps 1–2: the cut needs every commit of the sessions.
- Ask only for the sessions that have commits in the target repo (`data/commits.json`: `session` of its commits).
- The intents to write are those that hold a commit of the target repo after assigning by content. They are the
  probe and the whole run at once: no slices.
- Their commits in other repos stay in `squash`, so the intent stays whole, but need no message: only the target
  repo is rewritten.
- `validate.py <ids>` for those intents, `validate.py --repo <target>` for coverage and messages of the target repo.

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
- **A second run** on a rewritten history: `--exclude` the earlier data export, pick a new archive name. The first
  run's messages are a source like any commit message; the session wins where they differ, and their SHAs of other
  repos are stale.
- **Second run, dates:** a commit squashed in the first run carries the author date of its first member, so the
  cut may put it too early; check the commits at the edges of each intent. The earlier export's SHA map goes stale:
  write a new export.
- **Nobody to review:** an agent that reaches step 5 or 7 without a person to ask stops there and says so; it does
  not rewrite on its own judgement.
- **The request may lie before the window:** when work ran on after the person's next message, `context.py` shows
  the person's last earlier messages too; the trigger can be there.
- **Quotes** in `trigger` stay in the person's language. A session that only refers to another one (not created by
  it) is read on its own; open the other only when the trigger is not found.
