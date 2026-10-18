# One Host per Machine, One UI and Settings Scopes: Build Design (TD-242, TD-241, TD-243, TD-264, TD-265)

> **Owning decisions:** TD-242 (one Delivery host per machine), TD-241 (one UI by kind of work, no project
> mode), TD-243 (machine, global and project settings), TD-264 (lit-html, with TD-241), TD-265 (SQLite stores,
> with TD-242), TD-257/TD-272 (the `owlbear` command, argparse with shtab), TD-258/TD-260 (login item and
> command link, each asked at install), TD-259 (paused until Resume after any start), TD-261 (these come with
> the machine host), TD-262 (Mac first), TD-250 (order), TD-281 (projects are added only in the UI), TD-282
> (a running step finishes after a stop), TD-283/TD-284 (input before Resume), TD-285 (shaping never expires)
> **Date:** 2026-10-17 (revision 3.1, Sol 95%: revision 1 at 55% with sixteen findings, revision 2 at 77% with
> eleven, revision 3 at 86% with five, all taken; three were owner decisions, TD-281..TD-284)
> **Question:** How does one host process serve every project of the machine, with one UI across them, the
> Change stores in SQLite and settings in three scopes, built in reviewable steps?

## 1. Context

Today every clone runs its own host: `owlbear-next --repo R host` takes `R`'s `host.lock`, binds a port, writes
`host.json` and serves pages and API for that clone alone. The VS Code folder-open task starts it as a
background task, so it ends with the window, and it schedules work as soon as it starts. TD-242 replaces this
with one host for the machine, started by the `owlbear` command or the login item and paused until Resume;
TD-241 makes every page show all projects; TD-243 adds the machine scope; TD-264 and TD-265 ride along.

## 2. Sources Studied

| Source | Fact used |
| --- | --- |
| `commands/serve.py` | One host per clone: non-blocking `host.lock`, a free port, a 32-byte token, `host.json` (0600), readiness and scheduler threads, uvicorn; on exit it sets `stopped` without joining and removes `host.json` |
| `project_host/host.py` | `Host(store, repo)` holds all per-project scheduler state; `run()` schedules at once; `_spawn` passes all of `os.environ` (plus `OWLBEAR_DATA`) to runners; `_unloadable` stats `change.json`; `running(store)` reads `host.json` only while `host.lock` is held |
| `project_host/api.py` | `create_app(store, token, host)`: pages, PDS assets, `/api/next/*` behind a bearer token and a Host-header check; `link()` returns `{url}#token=…`; the pack router builds its own `pack_job.Job(store)` |
| `commands/mcp_server.py` | `Chat.call` uses `running(store)` and `{url}api/next{path}`; `show_status` returns `link()` to the browser |
| `commands/setup.py` | Folder-open task `… --repo ${workspaceFolder} host` (`isBackground`); per-project `.mcp.json` chat server with `--repo`, each written only with consent |
| `state_store/store.py` | Store root `<git-common-dir>/owlbear-delivery/` with `changes/<slug>/{change.json, .prev, lock, now.json, activity.jsonl, inbox/, runner.json, runner.log, env.log, visual/, before/}`, `handles.json`, the `format` marker; `Store.open` refuses a marker newer than its `FORMAT` (5); `put_inbox` writes without the Change lock; `fold` calls a `leave` barrier that reads and dequeues PRs (`workflow_steps/queue.py`) |
| `local_system/storage_io.py` | Every record write fsyncs the file and its directory |
| `local_system/data_repo.py`, `settings/config.py` | The shared data repository holds the global layer and one folder per project name; clones of one repository share that folder; `resolve` records each value's source |
| `state_store/backlog.py`, `project_host/backlog_routes.py` | `Entry.project` is one string, `Entry.change` an unqualified slug; every project's listing returns the whole shared issue set with that project's launch overlay |
| `project_host/memory_routes.py`, `workflow_steps/sessions.py`, `serve/memory-mcp/.../server.py` | Memory is one folder per project name; sessions give agents that folder; the memory server opens one engine |
| `project_host/config_routes.py` | A shared-folder rename checks only its own store's runners and takes only its host's launch mutex |
| `pack_runs/pack_job.py`, `design_packs/pack_git.py` | The pack job's mutex is per instance; activation writes the runtime's package files |
| `web/*.html` | Five pages, 3,640 lines; every poll rebuilds the DOM, guarded by fingerprints, focus checks and reopened `<details>`; API calls are root-relative |
| `tests/test_module_rules.py` | Source modules fail at 500 raw lines |
| [lit-html](https://lit.dev/docs/libraries/standalone-templates/) | `render(template, container)` updates only changed parts; standalone ES modules without a build step |
| [SQLite WAL](https://www.sqlite.org/wal.html) | Concurrent readers with one writer across processes on one host; not on network file systems; `synchronous=FULL` keeps commits across power loss |

## 3. Shape

Five steps, each its own PR series with Sol review, each leaving Delivery working:

1. **lit-html pages** (TD-264): the five pages render through lit-html against today's API; no behavior change.
2. **Machine host** (TD-242, TD-257..261, TD-272, TD-281..285): one paused-at-start process serves every
   registered project behind the `owlbear` command and an optional login item; the pages gain
   project-qualified routes and links; the cross-project locks (pack, shared-folder rename) come with it.
3. **One UI across projects** (TD-241): filters, shared resources served once, backlog entries naming several
   projects, Global memory read by agents.
4. **SQLite stores** (TD-265): each project's Change records, inboxes and logs move into one database file.
5. **Settings scopes** (TD-243): the Settings page shows global defaults with each project's differences.

## 4. Step 1: lit-html Pages (TD-264)

- `web/vendor/lit-html/` holds the unmodified ES modules of one lit-html release (`lit-html.js` and the
  directives the pages use), its license and `VERSION`, served under `/assets/lit-html/<release>/` with fixed types.
- A test pins the release: `VERSION` matches each file's header and a committed SHA-256 list matches the files.
- Each page becomes `render(view(state), root)` on every poll, with page-local UI state (open sections,
  drafts) bound through `live()`. Fingerprints, focus checks and reopen code go. Shared helpers (token fetch,
  `ask`, time formatting) move to `web/ui.mjs`.
- **Proof:** existing page and browser tests keep their meaning; new browser tests show typing, an open
  `<details>` and focus surviving two polls with changed data.

## 5. Step 2: The Machine Host

### 5.1 Registry and identity

- `~/.owlbear/machine.json` (format 1, atomic writes under `~/.owlbear/machine.lock`) is the machine scope:
  registered projects `{id, path, added_at}` and the Resume state.
- A project is a clone. Add project canonicalizes the work tree and its git common directory (real paths) and
  refuses a path not owned by the current user, not a git work tree, or whose store marker is unreadable or
  newer than the host's format. Under `machine.lock` it creates the store directory (0700) if absent and
  `<store>/clone-id` with `O_EXCL` (a random id, 0600) if absent, reusing an existing one; only then does
  `Store.open` adopt the shared folder. The registry keeps the id; loading checks the store's `clone-id`
  matches, so a re-clone at the same path shows as replaced (Remove or Adopt) and never inherits the old
  registration. These two files are the only things registration writes into a project.
- A project's name is its shared-folder name, else its directory name; same-named clones show their paths.
- Projects are added only in the UI (TD-281); opening a VS Code window never touches Delivery, so setup
  writes no folder-open task and offers to remove an earlier one. A project without the consented chat
  server shows "setup required" with its `owlbear setup` command.

### 5.2 Process, pause and stop

- `owlbear start` (and the login item) launches the machine host detached (`start_new_session`, stdin from
  `/dev/null`, log `~/.owlbear/host.log`). It takes `~/.owlbear/host.lock`, binds a free loopback port, and
  writes `~/.owlbear/host.json` (url, token, pid, code, started_at; 0600).
- The `owlbear` command normalizes its own environment before anything else (so registration probes and the
  host it starts see the same): it drops credential and repository selectors (`GH_TOKEN`, `GITHUB_TOKEN`,
  `GH_ENTERPRISE_TOKEN`, `GITHUB_ENTERPRISE_TOKEN`, `GH_HOST`, `GH_REPO`, `GH_CONFIG_DIR`, `GIT_DIR`,
  `GIT_WORK_TREE`, `GIT_COMMON_DIR`, `GIT_INDEX_FILE`, `GIT_OBJECT_DIRECTORY`,
  `GIT_ALTERNATE_OBJECT_DIRECTORIES`, `GIT_CONFIG*`), each dropped name logged once. Transport settings
  (`SSH_AUTH_SOCK`, `GIT_SSH`, `GIT_SSH_COMMAND`) stay: they are the owner's, not a project's; a project that
  needs its own SSH identity sets `core.sshCommand` in its Git config, which takes effect only when the
  owner's environment sets no `GIT_SSH_COMMAND` (that variable wins in Git). `owlbear doctor` and each
  project's readiness check report a push or `gh` login that fails from the host's environment, with the fix.
- Every start is paused (TD-259). While paused a project's scheduler applies the owner's input at once
  (TD-283): it folds inboxes with no PR observation, and it records runner exits and confirmed-gone runners.
  It launches no runner, disposes or launches no check environment and runs no Pull. The one GitHub call is
  TD-284's, through the same queue barrier as when running: when a Change with a queued PR leaves its merge
  step (a Pause, an Abandon or an answer), the barrier takes the PR out at once and reads the queue back; the
  item waits only until that read confirms the removal (TD-226), so a merge never lands behind an applied
  Abandon. (Revision 3.2: the build kept the one barrier instead of a paused barrier that never withholds.)
  Chat tools that need a step (the brief challenge) record the request and answer "paused: press Resume" at
  once. The pause holds Delivery's own work, not the owner's explicit actions: New Change opens its shaping
  chat, and Settings, Memory and folder-rename writes are applied and published at once (TD-283); a design
  pack update neither starts nor goes on from an answer until Resume, since its sessions are Delivery's work.
  The UI shows Resume with the number of Changes
  that would continue; Resume (UI only) unpauses the machine and is recorded in `machine.json`.
- A step whose runner outlived a stop or restart keeps running until it ends (TD-282); its result is
  recorded, its Change shows "finishing (started before the restart)", and nothing else starts for it until
  Resume. A runner found gone without a result counts as one failure, as today, and its retry waits for Resume.
- Per project the host keeps a `Project`: its `Store`, `Host` scheduler thread, readiness thread, API sub-app
  and a gate. It takes the project's own `host.lock` and writes the project's `host.json` with the machine
  url, token and the project id, so `running(store)` and the CLI work and a per-clone host can never run beside
  it. A project that fails to load is listed with its reason and retried every 60 s; its failure never
  touches another project.
- Stopping a project (Remove, `owlbear stop`, SIGTERM) closes its gate first: new writes answer 503 and no
  launch starts. The gate counts admitted operations (requests in flight, chat-launch threads, a pack job)
  and the stop waits up to 30 s for them, then wakes and joins the project's threads, removes its
  `host.json` and releases its lock. Remove is refused, naming them, while the project has a live runner, a
  check environment or admitted operations still running after that wait. Machine stop leaves live runners to
  finish (TD-282).
- Cross-project locks come with the host, since it is the first place two projects run at once: one
  machine lock lets one design pack update run at a time, whichever project's page started it; another
  project's start names the project whose update runs (revision 3.2: each project keeps its own run
  record), and a shared-folder rename is refused while any registered clone using that folder has a live
  runner (its `runner.json` process alive, including one that outlived a restart), holding every such
  project's launch mutex while it runs.

### 5.3 HTTP surface and links

- Pages and assets at `/`. Machine routes under `/api/next/`: `projects` (list, register, remove, adopt),
  `resume`, `stop`. Each project's existing routes move unchanged under `/p/{id}/api/next/…`, chosen by a
  small ASGI dispatcher; an unknown or unloaded id answers 404 with the project's state. One token and the
  Host-header check guard everything; the token is not a project boundary (one owner, loopback).
- `link()` becomes `{url}?project={id}#token=…`, so a link opens the machine page on its project; the
  Changes page keeps its `?change={slug}`. The chat server calls `{url}p/{id}/api/next{path}`. (Revision 3.2:
  the project is a query value like `change`, not a hash value; only the token stays out of the address bar.)
- Until step 3 the pages show one project at a time (staging, not TD-241's finished UI): the `project` and
  `change` values survive token extraction, the tab links, reload and Back; a bar under the tabs selects the
  project, adds a folder, removes or adopts a project, and shows Resume with the count of waiting Changes.

### 5.4 The `owlbear` command (TD-257, TD-272)

- One argparse command whose subcommands import their modules only when run: with no arguments it starts
  OwlBear if stopped, else shows status; `start`, `stop`, `restart`, `status`, `logs`, `doctor`,
  `autostart on|off`; today's `owlbear-next` commands move under it unchanged (`setup`, `profile`, `seed`,
  `answer`, `show`, `data`, `home`, `design-pack`, `backlog`, `status --repo`).
- `owlbear install` (run from `~/.owlbear/runtime`) writes the shtab zsh completion into `~/.owlbear/`
  (never `~/.zshrc`, which it only names), then asks separately for the `~/.local/bin/owlbear` link and for the
  login item `~/Library/LaunchAgents/…owlbear.plist` (TD-258, TD-260); `owlbear uninstall` removes both. A
  Mac that refuses the login item is reported by the installer and `owlbear status`; on-demand start keeps
  working. Linux and Windows are refused with a clear message (TD-262).

### 5.5 Proof

- Unit: registry and clone-id round trip (reused, never rewritten), replacement detection, ownership and
  format refusal; paused start: answers folded, no PR observation, no launch, dequeue on Pause only, chat
  challenge answers "paused"; Resume; finishing runners; environment scrub; a failing project beside a
  working one; gate, drain and stop ordering (no launch after close; join; discovery removed last);
  dispatcher 404; link and chat paths; pack jobs of two projects serialized; rename refused while another
  clone's runner lives; the command's dispatch and lazy imports; completion written without touching
  `~/.zshrc`.
- Live on both sandboxes: one machine host serves both, paused at start until Resume; each chat server finds
  its project; a Change runs in each; removing one is refused while its runner lives.

## 6. Step 3: One UI Across Projects (TD-241)

- **Filters:** every page offers each project, Global and All (default All), kept in the URL query (`?project=`,
  revision 3.2); every item
  shows its project; every action calls its project's route and every link carries its project id.
- **Changes:** one list across projects; New Change asks which project unless the filter names one.
- **Shared resources once:** backlog and memory belong to the shared repository, not a clone. Machine routes
  serve them once per shared repository (backlog) and once per shared folder (memory), deduplicated, with
  the projects that use each folder; per-clone overlays (launch state) join by project id. The selected
  project of an action is explicit and separate from the resource's owner.
  (Revision 3.2: the backlog is read through each clone's own route and shown once per repository by the
  page, the first answering clone's read standing for it; launch overlays join from every clone.)
- **Backlog:** an entry names the shared folders (repositories) it concerns and keeps its legacy attribution
  apart: `projects: list[str] | None` (`[]` = Global, `None` = not yet triaged) and `origin: str`. Migration
  takes only what the old scope states: `project` becomes `[project]`, `global` becomes `[]`,
  `cross-project` and `unassigned` become `None`, and the old `project` value becomes `origin`, shown as
  legacy attribution. Untriaged entries show under All and under their origin's filter, marked for triage.
  `Entry.change` becomes `{clone id}/{slug}`; an old unqualified slug resolves only when exactly one
  registered clone of that folder has it, else it shows as unresolved. Triage sets `projects`; starting a
  Change from a Global, untriaged or multi-project entry asks which registered clone.
- **Memory:** each shared folder's memory plus Global (`<shared>/memory/`). Agents read Global with their
  project's memory: sessions pass both folders and the memory server reads both, writing only to the project
  folder. Make global (owner action, same locks and publish) moves an entry once agents read Global.
  (Revision 3.2: like the backlog, the page reads each shown clone's `/memory` and `/memory?where=global`
  and shows each shared folder and each repository's Global once; an action goes through the clone that read
  the entry. The memory server gets Global as `OWLBEAR_MEMORY_GLOBAL_DIR`; a project entry wins an id clash.)
- **Proof:** browser tests with two projects holding the same Change slug (list, detail, answer, screenshot,
  reload, back); a backlog entry naming two projects and none, and the migration of each old scope; memory
  read and Make global.

## 7. Step 4: SQLite Stores (TD-265)

- Each project's `<git-common-dir>/owlbear-delivery/delivery.db`: WAL, `synchronous=FULL`, `busy_timeout`
  10 s, one connection per thread. Tables: `changes(slug PRIMARY KEY, rev, record, prev)`, `inbox(id INTEGER
  PRIMARY KEY, slug, name, item)`, `activity(id INTEGER PRIMARY KEY, slug, at, event)`, `now(slug PRIMARY
  KEY, data)`, `meta(key PRIMARY KEY, value)`. Records stay JSON validated by the same models and migrations.
- The directory must be on a local file system (checked with `df -l`); otherwise the store is refused with
  the reason.
- Run locks stay files: the Change writer lock, `host.lock`, the merge lock. Artifacts stay files:
  `runner.json`, logs, screenshots, worktrees.
- `fold` keeps the Change flock throughout but holds no database transaction across network work: it reads
  the inbox rows (their ids), computes, runs the barrier, then commits the Change and deletes exactly those
  rows in one short transaction. `_unloadable` uses the row's `rev` instead of a file's mtime.
  (Revision 3.2: a store with no file-format state starts its database at once, through the same marker,
  temporary file and rename; one with such state refuses every operation until the machine host imports it.
  `handles.json` becomes the `meta` row `issued`; `history.jsonl` stays a file. The import skips inbox files
  a Change already acknowledged; after it `inbox_acked` stays empty, and an inbox row that no longer
  validates is removed with the fold and kept as an `inbox-rejected` activity event.)
- **Import, fenced and resumable:** the format marker is the old-code fence. Every new-code store operation
  (host, runner, CLI, chat server) holds `<store>/migrate.lock` shared for that one operation only, so an
  idle long-lived client never blocks an import. The machine host imports while it holds the project's
  `host.lock` (so no per-clone host runs), before the project's routes or scheduler start, once no runner is
  alive, with every Change lock held and `migrate.lock` exclusive (waiting for running operations to end):
  (1) the marker becomes `6`, so every older runtime refuses the store on open; (2) the files are read into
  `delivery.db.tmp` in rollback-journal mode together with an `imported(slug, name)` ledger of every inbox
  file and record taken, committed and closed, the file fsynced and renamed to `delivery.db`, the directory
  fsynced, and only then WAL is enabled; (3) files named in the ledger are renamed to `*.imported`. A crash
  before (2) completes leaves the files authoritative and the import runs again; after it, step (3) repeats
  on the next open for ledger names only. An old process already open before (1) can still drop an inbox
  file; every later fold ingests inbox files whose names are not in the ledger, adding them to it in the
  same transaction (`inbox` and `imported` are unique by `(slug, name)`), so none is lost or applied twice.
- **Proof:** the store tests on the database; crashes injected at each import boundary; an older `Store.open`
  refusing a marker-6 store; an inbox file dropped by an already-open old process after import is applied
  once, including across a crash between publication and retirement; a chat server open across the import; a
  runner and the host writing concurrently; a fold whose barrier blocks does not block another Change's write.

## 8. Step 5: Settings Scopes (TD-243)

- Machine: `machine.json` (registry, Resume state, login item status); the update channel joins with TD-239,
  session limits when such a setting exists; no empty fields in advance.
- Global and project layers stay in the shared repository (clone-local without one); `resolve` reports sources.
- The Settings page lists each setting with the global value and its source and each project's differing
  value; an edit asks its scope (Global or which project) and keeps today's revision-conflict refusal;
  machine values are edited only on the machine section.
- **Proof:** page tests for source display, scope choice and conflicts.

## 9. Outside This Design

Runtime self-update and stable tags (TD-239, TD-240); a machine-wide chat server registration replacing the
per-project `.mcp.json`; the doubled agent time limits as role settings (TD-286), a small change of its own.
