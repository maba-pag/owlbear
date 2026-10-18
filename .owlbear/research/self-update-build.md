# Self-Update, Stable Versions and Pause Controls: Build Design (TD-239, TD-240, TD-287..TD-301)

> **Owning decisions:** TD-239 (one runtime per machine in `~/.owlbear`, updating itself when idle, never
> backwards), TD-240 (a stable tag needs evidence; the owner approves it), TD-259 (paused until Resume after a
> start), TD-282 (a running step finishes after a stop), TD-283/TD-284 (input before Resume; a queued PR's
> Pause or Abandon dequeues at once), TD-101/TD-125 (design pack updates commit and push), TD-278 (repository
> maintenance reaches `main` through a pull request), TD-287 (what runs while paused), TD-288 (updates and
> the pause; Pause, Pause and stop when idle; two machine settings), TD-289 (manual deploys until this is
> built), TD-290 (one design pack update at a time), TD-296 (install beside, switch on answer), TD-297
> (`v0.1`), TD-298 (green CI and one finished Change), TD-299 (back as it was), TD-300 (no machine follows
> `main`; minor or major channel), TD-301 (idle), TD-302 (every merge is a minor version), TD-303 (cleanup
> while paused), TD-304 (Run updates now while paused), TD-305 (forward repair after the switch), TD-306
> (versions only by label), TD-307 (no label checks; pack updates labelled as any pull request), TD-308 (pull
> request labels and marker settings)
> **Date:** 2026-10-18 (revision 6: release labels TD-306..TD-308 in §8; revision 5: the owner's answers
> TD-302..TD-305; revision 1 at Sol 30% with
> seventeen findings, revision 2 at 55% with seven, revision 4 at 65% with six, revision 5 at 80% with
> three in §8, all taken)
> **Question:** How does the machine host pause and stop on the owner's word, update itself to the newest
> stable version of its channel without moving backwards or losing work, and propose the next version?

## 1. Context

The runtime `~/.owlbear/runtime` is a clone of `github.com/maba-pag/owlbear` with its `.venv` inside, moved by
hand after each accepted merge (TD-289). Every start is paused (TD-259); there is no Pause button, and a
design pack update is refused while paused, against TD-287. A design pack update commits into the runtime's
own checkout and pushes its branch, which a protected `main` refuses and a tagged checkout cannot do. `v0.1`
marks `8ebc00afe`; the runtime runs a later `main` commit.

## 2. Sources Studied

| Source | Fact used |
| --- | --- |
| `machine_host/serve.py` | Holds `~/.owlbear/host.lock` and its listening socket until the process ends; its cleanup deletes `host.json` |
| `machine_host/control.py`, `install.py`, `commands/setup.py` | The login item, the `owlbear` link and each project's `.mcp.json` are written from `sys.executable`; `doctor` opens project stores |
| `machine_host/machine.py`, `project.py` | `paused` starts true; `closing()` closes gates and sets `stopping` for good; `Project.load` runs `Store.open` (which may move settings) and the database import, both one-way |
| `project_host/host.py` | A paused pass returns before disposing a check environment; runners are separate processes with descendants |
| `design_packs/pack_git.py` | Activation commits the manifest and skills' notice in the package's checkout and pushes its branch; refuses a detached head |
| `local_system/codebase.py`, `commands/runner.py` | `CURRENT` hashes shipped files; a runner refuses to start beside a host of other code, but nothing fences one already running, nor a chat server |
| `web/ui.mjs` | The bar polls every 5 s and skips a poll while focus is in it; no page reports use |
| uv, git | An environment records absolute paths, so a version folder never moves; `git clone --local` makes the source folder its origin |

## 3. Layout and Stable Paths

- `~/.owlbear/repo.git`: a bare clone whose `origin` is the GitHub URL; every fetch, tag and push goes through
  it. Versions are its detached worktrees `~/.owlbear/versions/<tag>/`, each with its own `uv sync --locked`
  environment, never moved.
- `~/.owlbear/runtime` is the **stable alias**: a symlink to the active version. Everything outside OwlBear
  (login item, `~/.local/bin/owlbear`, each project's `.mcp.json`, the shaper agent and skill links) uses the
  alias; setup, install and autostart write the alias, never `sys.executable`. Runners and the new host use
  their version's own physical interpreter.
- **First migration** is the first update itself: the new version is built and started from its own
  folder (§5), never from the legacy one. At activation a new link `runtime.new` to the version is
  swapped with the legacy folder in one atomic rename (`renamex_np` with `RENAME_SWAP`, APFS; TD-262 Mac
  first), so `runtime` is never missing; the legacy folder, now named `runtime.new`, is then renamed to
  `~/.owlbear/versions/legacy-<sha>/`, which every start completes if a crash came between. The legacy
  environment is never run again, so its broken absolute paths do not matter; its old chat servers are told
  to reload (§5.6).
- **Leases and disk:** every OwlBear process (host, runner, chat server, command) holds a lease
  `~/.owlbear/versions/<tag>/leases/<pid>-<start time>` while it runs; a version is removed only once two
  newer ones were active and it has no live lease. The legacy folder has no leases, so it stays until the
  owner removes it with a button in Settings → This machine. An update needs 2 GB free, else it waits and
  says so; a failed install is removed at once.

## 4. Versions, Channel and Never Backwards (TD-297, TD-300)

- A version is an annotated tag `vMAJOR.MINOR` or `vMAJOR`; `vN` and `vN.0` must name the same commit, else
  neither is taken and the owner is told.
- Machine setting `channel`: `minor` (default) takes the newest tag of either form; `major` the newest `vN`.
- **Never backwards:** a target is taken only when it is numerically above the highest version ever active
  and its commit descends from the active commit. The mark is the alias's target (§5.3) joined with
  `machine.json`'s record of it, which every start reconciles before any store opens. A legacy runtime ahead
  of the newest tag waits for a later one.

## 5. Update: Install Beside, One Activation Point, Handover (TD-296, TD-299)

One update at a time (`~/.owlbear/update.lock`); a stop intent (§6) wins over it.

1. **Prepare** (no fence): fetch tags into `repo.git` (non-interactive, 120 s, failures reported), add the
   worktree, `uv sync --locked`, run `python -m owlbear_delivery_next selfcheck` there: imports, page assets,
   and each registered project's store opened read-only for its format markers and settings format, with no
   migration. A failure removes the worktree, keeps the old host running and is shown; three bounded retries
   per version.
2. **Standby:** the new version's host starts from its physical path in standby: it takes no lock, binds a
   private loopback port, serves its own pages and answers `GET /health` with its version and selfcheck. No
   answer in 60 s: it is stopped and the old host continues (TD-296).
3. **Fence and activate:** a machine-wide `updating` state refuses new runner launches, new background work
   (pack update, brief challenge, chat launch) and project admissions with "OwlBear is updating; try again in
   a minute"; idle (§7) is checked again under it, including admitted background work and process groups
   left by ended runners; anything running lifts the fence, stops the standby and the update waits.
   Otherwise the **alias rename is the one activation point**: on the first update the atomic swap of §3;
   on later ones a new link renamed over the alias. Every start completes a half-done first migration and
   raises `machine.json`'s mark to the alias's version before any store opens.
4. **Hand over:** the old host closes every gate, joins every scheduler, releases every project's
   `host.lock`, closes its listener and releases `~/.owlbear/host.lock`, writing `~/.owlbear/handover.json`
   (0600: port, token, paused, resumed or stopping state). The standby takes the machine lock first, then each
   project's, binds the old port with the old token (open pages keep working) and loads projects as before
   (TD-299); `host.json` is written and removed only by its owner. A start without a handover file is an
   ordinary start and pauses (TD-259).
5. **Watch:** the old process waits 60 s for `/api/next/projects` with every previously loaded project
   loaded. Without it the old process starts the new version once more from the alias and tells the owner;
   it never starts the older version after activation, because the loads in step 4 may migrate one way
   (TD-305). A project the new version cannot load shows as failed with its reason.
6. Pages show once "OwlBear now runs v0.N"; a chat server whose code differs from the host's answers every
   tool with "OwlBear updated to v0.N: reload this VS Code window" and reads no state.
7. **Crash points:** before the alias rename the old version stays and a leftover standby or worktree is
   removed at the next start; after it every start, the login item's included, runs the new version.
8. **Run updates now** takes the same path without waiting for 15 minutes without use: pending maintenance
   runs first and ends, then prepare, standby, fence (still refusing while a step, environment or pack
   update runs) and activation.

## 6. Pause Controls (TD-287, TD-288)

- **Pause** (machine route `POST /pause`): no automatic agent step starts; the banner at the top of every page
  shows the pause with Resume, Run updates now, and Pause and stop when idle. The Pause tooltip says OwlBear
  may still update itself while Update while paused is on.
- **Pause and stop when idle** (`POST /pause-stop`): records a stop intent in `machine.json`; from then no
  launch of any kind starts (update, maintenance, New Change's chat, a brief challenge, a pack update), each
  refused with "OwlBear stops once the running steps end; press Resume to cancel", while input that launches
  nothing is still taken; check environments are disposed (the paused pass does that now); OwlBear stops once
  no step, environment or pack update runs; the banner names what it waits for. Resume clears exactly that
  intent; a handover carries it. Hidden while Update while paused is off.
- **Run updates now:** enabled once no step from before the pause runs, else disabled with the reason;
  §5.8. With Update while paused off it still updates; only automatic updates stop while paused (TD-304).
- **Owner actions while paused** run at once: settings, memory, folder rename, a design pack update and its
  answers, New Change with its shaping chat and the brief challenge the owner's chat asks for (a launch
  marked owner-triggered passes the pause; planning and building stay held), cleanups he starts. TD-284's
  immediate dequeue stays.
- **Maintenance OwlBear starts itself** runs while paused (TD-287): a Change's cleanup runs in full, its
  GitHub effects included (deleting branches, closing pull requests, pulling back); publishing a pull
  request and merging wait for Resume (TD-303).

## 7. Idle, Use and Announcement (TD-301)

- **Idle:** no runner and none of its process group alive, no check environment in any project, no design
  pack update, no admitted background work, and no use for 15 minutes.
- **Use:** a page's `POST /seen`, sent at most once a minute on keys, pointer, wheel, scroll or focus while
  the page is visible; any request other than a GET; and any chat tool call (the chat server marks its
  requests). Polls are GETs and never count.
- **Announcement:** when an update is due, every open page shows "OwlBear updates to v0.N in 1:45 ·
  Postpone" for 2 minutes; the bar's poll for it is not skipped by focus. Postpone is use; any use cancels.
  A clock jump (sleep) of more than 30 s restarts the announcement.
- **Machine settings** (Settings → This machine; `machine.json` format 2): `channel`, `update_when_idle`,
  `update_while_paused`, both on at first. With Update when idle off, only Run updates now updates.

## 8. Versions from Merges (TD-302, TD-306..TD-308)

- `ci.yml` gains a `push` trigger for `main`, so each merge commit gets its own `CI` check. Push runs get a
  concurrency group per commit and are never cancelled, in `ci.yml` and in every reusable suite; pull
  request runs keep cancelling their predecessors. On a push the scope compares the merge with its first
  parent.
- A `release` workflow runs on `workflow_run` of `CI` completed with success, for a `push` to `main` of
  this repository, in one release concurrency group that never cancels a running release. Every run drains
  the whole of `main` as it is when the run starts, never only up to its own `workflow_run.head_sha`: it walks
  `main`'s first-parent history from the frontier to its tip in merge order, and for each merge commit
  without a version tag (tags compared by the commit they peel to) whose pull request carries a release
  label and whose own `CI` passed, allocates the next version; it stops at the first labelled merge whose
  `CI` has not passed yet, which a later run continues. Merges without a release label are passed over
  without waiting for their `CI`. Because every run drains all of `main`, a run GitHub replaced or
  coalesced loses nothing. The **frontier** is the
  newest version tag's commit, but never earlier than the first merge whose `CI` ran on its push (`v0.1`'s
  successors #470 and #471 had none; the step that adds the push trigger records that first merge in the
  workflow, so the walk starts after them). Each merge's pull request is found by
  `GET /repos/{owner}/{repo}/commits/{sha}/pulls`, checked to be merged into `main` with exactly that merge
  commit; a merge without such a pull request makes no version. Labels are read when the run reaches the
  merge, so a label set after the merge counts until a later version passes it; no check asks for or
  guards a label (TD-306, TD-307).
- **Allocation:** inside the release group, each tag is decided against freshly read tags: versions are
  compared numerically, `vN` as `(N, 0)`; `release:minor` makes `vX.Y+1` after the highest,
  `release:major` makes `vX+1` (with both labels, `release:major`); no label makes no tag (TD-306). A
  machine on the major channel takes only the `vN` tags (TD-300). A tag is an annotated tag object plus a
  non-forced ref
  (`contents: write` on the job alone); a commit that already peels from a version tag is skipped, so a
  rerun or a second run makes no second version of it.
- **Design pack updates** (TD-101, TD-125, TD-256 as amended): the candidate is the running version's
  files plus the updated pack, built in a worktree of `repo.git` at the running version's commit, where the
  checks run; the running worktree is never touched. Once the challenger passes, or the owner accepts an
  unreviewed repair (TD-256), it commits there on a branch `pack/<id>`, pushes it and opens a pull request
  with the labels OwlBear adds to every pull request it opens (TD-307, TD-308); the branch and pull request
  are kept in the update's state, so a retry reuses them. Its merge, brought up to date with `main` as any
  pull request and checked by CI, becomes a version as its labels say; machines take it at their next idle
  time.
- **Pull request labels and marker** (TD-308): a global setting `pr_labels` lists the labels OwlBear adds
  to every pull request it opens, Delivery's and the design pack update's; a project's value replaces the
  list whole (TD-243); empty at first. OwlBear's own project sets `release:minor`. A project setting
  `pr_marker` (on at first) leaves out the line "Opened by OwlBear Delivery for …" when off. A failure to
  add labels, a label the repository lacks included, is reported on the Change and does not undo the pull
  request.
- No evidence is recorded per commit and no tag is proposed (TD-240's evidence and proposal and TD-298 are
  superseded).

## 9. Small Items Riding Along

- **TD-290:** every project's pack page shows the update running on the machine and the project that started
  it; a second start is refused naming it.

## 10. Answered Questions

The owner answered revision 3's five questions on 2026-10-18: versions from merges (TD-302, replacing the
candidate-proof question and the design pack question), cleanup while paused (TD-303), Run updates now
while paused (TD-304) and forward repair after the switch (TD-305). Release labels followed the same day:
versions only by label (TD-306), no label checks and pack updates labelled as any pull request (TD-307), and
the pull request labels and marker settings (TD-308).

## 11. Build Steps

| Step | Content | Proof |
| --- | --- | --- |
| 1 | Machine settings, `machine.json` format 2, stable alias in setup and install (§3, §7) | migration and Settings page tests; written paths use the alias |
| 2 | Pause, Pause and stop when idle with intent, owner actions and cleanup while paused, TD-290 (§6, §9) | route and page tests: a live runner and a check environment while stopping; a pack update, a brief challenge and a cleanup while paused, publishing held |
| 3 | `ci.yml` on pushes to `main`, the `release` workflow and its labels; the `pr_labels` and `pr_marker` settings in Delivery's publish; design pack updates through a pull request (§8) | workflow tests on a disposable repository; publish tests with labels and without the marker; one real minor tag from a labelled merge |
| 4 | `repo.git`, versions, leases, never backwards, selfcheck, standby, fence, alias activation with first migration, handover, watch, Run updates now (§3–§5) | disposable macOS processes with two local tags: success, selfcheck and standby failure, a crash injected at each ownership step and around the alias rename, an open page and a chat server across it, a second update, disk refusal |
| 5 | Idle, use, announcement, automatic updates (§7) | clock-driven tests: polls never count, Postpone, cancel, sleep |
