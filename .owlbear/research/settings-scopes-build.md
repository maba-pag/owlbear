# Settings Scopes and Session Limits — Build Design (TD-336, TD-105)

Status: built (part A #496, part B #497); design for build, revision 4 (2026-10-19). Sol challenged revision 1 (gates at session start: missing and
duplicated gates, slots freed before sessions end, a waiter holding the Change lock, the local save path, the
overview's sources), the gate at runner launch (an estimate needs an enforced upper bound, reservations must
survive a host restart, waves must not reuse unconfirmed capacity, the waiting status) and revision 3 (see §7).
Decisions: TD-336 (decided), TD-105 (decided, re-decided by TD-336), TD-243 (scopes, re-decided by TD-336), TD-52,
TD-209, TD-295. Topic C-09 of the decision record.

## 1. What is decided

- Preferences resolve on four levels, built-in → global → machine → project, the project winning. Scope-only
  settings stay in their scope: update channel and registered projects on the machine; test preparations, data
  permissions and the PR marker in the project.
- Two session settings: sessions at once on this machine (machine only, default 4) and sessions at once per
  project (layered, default 2), all projects together within the machine's total. They count agent sessions,
  never per model. Free slots go round-robin across projects, first-ready within one; waiting spends no budget;
  running sessions are never stopped to meet a limit (TD-105).
- Capabilities are checked after resolving and a value is never silently replaced; global and built-in defaults
  stay separate.

## 2. What exists

- `settings/config.py`: `Layer` (project), `GlobalLayer` (shared, `visible` global only, project-only fields
  refused), `resolve(glob, project)` with per-field `sources` (`default`, `global`, `project`, `builder`).
- `state_store/store.py`: `settings()` reads the global layer from the shared repository and the project layer.
- `machine_host/registry.py`: `machine.json` with machine-only `Settings` (channel, update when idle, update while
  paused) and the registered projects.
- Settings page: a layer selector (global or a project), the inherited value per field, its source, an
  "Across projects" overview.
- Capabilities: the page flags an effort or context tier the chosen model does not offer; the SDK adapter omits
  an effort only for a model the runtime says takes none, and journals `effort-omitted`. No other value is
  replaced. This part is built; this design changes nothing there.
- No session limit exists. A project host (only the machine host builds them) launches a runner per ready Change; a
  runner folds the inbox again and runs one step, whose agent sessions run one at a time, except a visual check's
  judges, which run together; their number is known only after the capture batches its screenshots. Pack update
  jobs (updater, challenger, calibration replay judges) run one session at a time in the machine host process.
  Runners outlive a host's stop on purpose.

## 3. Part A: the machine preference layer

- **Storage:** `~/.owlbear/settings.json`, a `MachineLayer`: the `Layer` preferences (`agents`, `runtimes`, `widths`,
  `design_failures`, `final_review`, `pr_labels`, `sessions`). Project-only fields (`preparations`, `data`,
  `pr_marker`) are refused as in `GlobalLayer`; the top-level `visible` switch stays global only, while the
  per-agent `agents.*.visible` is a layered preference like any other. Nullable overrides as in the other layers.
- **Local writer:** a machine save never publishes. It takes the file's own lock, compares the revision it was
  based on inside that lock, validates the layer alone, and validates its combination with the global layer and
  every registered project's layer (TD-209); a combination that fails names the project and changes nothing.
  Every project page of the machine reads and writes the same file, lock and revision.
- **Resolution:** `resolve(glob, project, machine=None)`; every pick gains `("machine", …)` between global and
  project; `Source` gains `"machine"`; the final review's builder fallback stays last. Built-in defaults and the
  stored global layer stay separate, as now.
- **Store:** `Store.settings()` reads the machine layer when the file exists; a file that cannot be read stops the
  run with its reason, as a broken global layer does.
- **API and page:** `GET /config` returns `machine` and `machine_rev`; `PUT /config/machine` saves. The layer
  selector gains "This machine" between Global and the projects; a project's inherited values and sources include
  the machine's. "Across projects" shows the global and the machine baseline separately and takes each value's
  source from the resolver, not from the raw layers.

## 4. Part B: session limits

- **Settings:** machine-only `sessions` in `machine.json` `Settings` (default 4, at least 1) and the layered
  per-project `sessions` (default 2, at least 1). A per-project value above the machine's total is never reached.
- **One arbiter, at launch:** one in-process `Slots` arbiter in the machine host, shared by every project host and
  every pack job (every scheduler runs in that process). Before launching a runner, a project host reserves the
  step's concurrency: 0 only for a step that never starts an agent session (merge, publish, follow, cleanup);
  every other step reserves 1, and a CHECK that may capture and judge reserves up to the project's limit, at
  least 1, whatever the machine grants. No step's session count is predicted beyond that.
- **Enforced in the runner:** the runner gets the grant (`--sessions N`). An agent session started under a grant
  of 0 is a scheduling bug: it is refused before the adapter is entered and stops the Change for the owner with
  that reason. A visual review runs all its planned judge batches, in plan order, in waves of at most N; a wave
  whose session ends without confirmed termination stops the Change as a judge left running does today, and no
  further wave starts, so a partial round never reaches the verdict matrix.
- **Held until gone:** a reservation is held while the runner lives and until the host's liveness checks find its
  processes gone (`_gone`, `_survivors`); unknown liveness counts as running. Each reservation is written beside
  the runner's record (`runner.json` gains `sessions`), so a restarted machine host rebuilds the arbiter from
  every project's live runners before granting anything.
- **Waiting is outside the runner:** a Change waiting for a slot has no runner; the host keeps folding its inbox,
  pause and stop on each pass, so owner input is never stuck behind a wait; the step is judged again before it
  launches. Waiting spends no credits and no time limit.
- **Order:** a waiting entry is (project, Change, a sequence number taken when first seen ready). On each grant the
  arbiter reads the current limits, drops entries no longer ready, and serves the next project after the last
  served in clone-id order that has an entry fitting its limits (round-robin), within it the lowest sequence
  number (first-ready). A freed slot wakes the next waiting project's host.
- **Pack jobs:** each updater, challenger and replay judge session takes one slot of the project that started the
  update in the job's thread and gives it back when the session call returns. An end without confirmed
  termination already fails the update and tells the owner a session may still run (accepted, §7). The pack page
  shows the wait.
- **Visible:** `Activity` gains `waiting_slot` (machine and project counts), and the Changes page and card show a
  waiting Change as "waiting for a session slot (this machine 4 of 4, this project 2 of 2)"; a visual round
  running in waves shows how many judges are left.
- **Never stopped:** a lowered limit affects only the next grant.
- **Not counted:** built-in subagents (they run inside their step's session and its credits), the owner's shaping
  chat in VS Code (not a step).

## 5. Proof

- A: resolution order and sources on four levels; the machine layer refusing project-only fields and top-level
  `visible`; a local save never publishing, a stale revision refused, a combination failing for one registered
  project refused with its name; page selector, inheritance, sources and the overview's two baselines.
- B: the arbiter with fake hosts: machine and project limits; round-robin across three projects; first-ready within
  one; a limit lowered while sessions run; a runner refusing a session under a grant of 0; visual waves under a
  project limit of 1 and 2, and a wave stopping after an unconfirmed end; reservations held while survivors may
  live and rebuilt after a host restart; a pack job's sessions counted for its project; a waiting Change folding
  an answer and a pause without launching; the waiting line.

## 6. Build steps

| Step | Content |
| --- | --- |
| A | Machine preference layer: storage, local writer, resolution, store, API, Settings page |
| B | Session limits: settings, `Slots`, launch reservations and rebuild, runner enforcement and waves, pack jobs, the waiting status |

## 7. Accepted limits (operating context: one owner, one laptop, a few projects)

- A machine host that crashes between spawning a runner and writing its record does not rebuild that runner's
  reservation; at most one session then runs beyond the limit once, until that runner ends. The window exists
  already for liveness; no extra protocol is added for it.
- A pack session that ends without confirmed termination gives its slot back; the update already fails and tells
  the owner a session may still run, so a stray session is reported, not counted.
