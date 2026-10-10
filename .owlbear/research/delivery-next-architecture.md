# Delivery Next: Architecture (D4)

> **Owning task:** none — M3 D4 of the [liveness-first rebuild](delivery-liveness-first-rebuild.md)
> **Date:** 2026-10-10
> **Question:** What is the smallest set of packages, processes, state files, agent tools and prose
> that delivers the [charter](delivery-next-charter.md) on the Copilot SDK, and how does each part fail?
> **Status:** design draft; `autonomous` until the user approves M3. Revision 2026-10-10 after
> design challenge and the full-set challenge: separate host app until M6, inbox before exclusions,
> host-side termination scan, check environments, bundle and archive preservation, brief endpoint,
> tool count, clone-local state.

## 1. Context and Question

The [charter](delivery-next-charter.md) fixes the route (a thin core beside the old engine, a Python
SDK loop), the touchpoints, the exit contract, the interaction surface (§3.7), agent rules (§3.8),
budgets (§3.9) and proof policy (§3.10). D4 turns that frame into components small enough to stay
inside the budgets. It uses the step kinds, error kinds and state records of the parallel
[status and exit model (D3)](delivery-next-status-and-exits.md); §3.8 lists where the two differ.

## 2. Sources Studied

| ID | Source | Used for |
| --- | --- | --- |
| A01 | [Charter](delivery-next-charter.md) | Binding frame: ownership, route, touchpoints, exits, §3.7–§3.11 |
| A02 | [Platform probe](delivery-next-platform-probe.md) | P1–P12: typed results, permissions, resume, `tasks.list`/`tasks.cancel`, usage, idle pitfall, TLS-proxy runtime |
| A03 | [Route comparison §3.4](delivery-next-route-comparison.md#34-reuse-without-the-old-authority-model) | Modules to copy, their size and coupling |
| A04 | [Ownership map](delivery-next-ownership-map.md) | What Delivery-next owns, its state records and operations |
| A05 | [Journey and failure modes](delivery-next-journey-and-failure-modes.md) | J0–J9, exit rules (§3.3), rows X1–X8, DR1–DR15 |
| A06 | [Tool-surface audit §4](delivery-tool-surface-audit.md#4-recommendation-confidence-and-limits) | Rules T1–T8 (TD-1, `decided`) |
| A07 | [Distribution research](owlbear-distribution-agent-host.md), [rebuild E1](delivery-liveness-first-rebuild.md#37-roadmap-milestones-documents-and-products) | Harness loads `.github/skills` or plugins, not `chat.*FilesLocations`; repo `.mcp.json` |
| A08 | [Cockpit main.py](../../serve/cockpit/src/owlbear_cockpit/main.py), [target_context.py](../../serve/cockpit/src/owlbear_cockpit/target_context.py) | Loopback on `127.0.0.1`; a background supervisor already runs beside the API; startup requires old Delivery config |
| A09 | [storage_io.py](../../serve/delivery/src/owlbear_delivery/storage_io.py), [remote_git.py](../../serve/delivery/src/owlbear_delivery/remote_git.py) | `fcntl.flock` lock, atomic write; bounded remote Git with write readback, no hook handling |
| A10 | [pyproject.toml](../../pyproject.toml), [setup/init.py](../../setup/init.py) | Workspace members `serve/*`; setup merges `.vscode/mcp.json` today |
| A11 | [Status and exit model (D3)](delivery-next-status-and-exits.md) | Ten step kinds, fifteen error kinds, state records, cause keys and budgets |

## 3. Design

### 3.1 Package layout

New workspace member `serve/delivery-next/`, distribution `owlbear-delivery-next`, import package
`owlbear_delivery_next`. The existing `members = ["serve/*"]` picks it up. It never imports
`owlbear_delivery` or `owlbear_delivery_github`; copied files start with one comment naming their
source path and commit. Line targets are upper limits per module.

| Module | Responsibility | Origin | Lines |
| --- | --- | --- | --- |
| `models.py` | Change, profile, step, exit, pending, question and inbox records, each with `format` | new | 350 |
| `store.py` | State paths, atomic read and write, version gate and forward migration, per-Change lock, inbox | new, over `storage_io` | 250 |
| `loop.py` | Choose the next step, apply its exit, budgets per cause, re-entry dispatch | new | 500 |
| `status.py` | The one status line and next actor (DR8) | new | 120 |
| `profile.py` | Detect, confirm and re-read the project profile | new | 400 |
| `steps/` `worktree`, `publish`, `follow`, `check`, `merge`, `cleanup` | Engine parts of steps: workspace, push and PR, CI and reviews, person-only checks, consented merge, preservation and cleanup | new; `merge` takes the consent rule of `merge_approval.py` | 1,100 |
| `prompts.py` | Bounded context for each agent step | new | 350 |
| `sdk_adapter.py` | Session, agent, model, permission handler, result boundary, usage, teardown | new | 600 |
| `tools.py` | The six tool schemas and their validators | new | 300 |
| `runner.py` | Process entry: one Change, one step | new | 150 |
| `host.py` | Scheduler, runner launcher, startup observation, host lock, check environments, termination scan | new | 350 |
| `api.py` | Status-view HTTP router | new | 300 |
| `mcp_server.py` | Three chat tools; a client of the host, with a read-only status fallback | new | 150 |
| `setup.py`, `cli.py` | Readiness check, setup, entry points | new | 260 |
| `git/remote_git.py`, `git/git_executable.py` | Bounded remote Git, write readback | copied as is | 308 |
| `storage_io.py` | `atomic_write`, `locked_roots`, `ControllerLock` | copied as is | 188 |
| `github/provider.py` | PR, check, rule and merge contract; `merge_request_body` no longer forces `direct_merge`, so a queued submission is expressible | `publication_provider.py`, trimmed and adapted | 350 |
| `github/gh.py` | `gh` provider: HTTP 403 on rules means unknown, not "no rules"; required checks from the profile; queue-aware merge submission, where `enqueued` maps to pending, not refusal; merge-queue observation; GitHub Enterprise hosts | `delivery-github/github.py`, adapted | 1,150 |
| `github/merge_offer.py` | Block reasons, attempt readback; proof fields dropped | `merge_offer.py`, adapted | 420 |
| `process_probe.py` | `ProcessTableWorktreeProbe`, `psutil_user_processes`; claim issuer dropped. The probe skips the caller's own descendants, so the host, not the runner, runs it | `worker_stall.py`, adapted | 330 |
| `criteria.py` | Criterion identity and version (P5 input) only; the old-contract import and legacy derivation dropped | `acceptance_criteria.py`, trimmed | 60 |
| Changes page | List, detail, answer, check result, brief approval, merge dialog, recovery actions | new; the host app's own small web page before M6, moved to Cockpit web `src/pages/changes/` at M6, reusing shell, theme, `usePollingFetch`, table and dialog patterns | 800 |

Totals: new Python 5,180, web view 800, copied 2,806, plus about 40 lines in Cockpit `main.py` at
M6: about 8,800 of 10,500, leaving room for M4 findings. Not copied: `effect_launcher.py` (a merge call
guarded by `sha`, then a readback, replaces the frozen-body launch) and the in-memory provider, which
moves to tests as a fake and counts against the test budget. Agent prose in `agents/` counts against
the prose budget (§3.4), not source.

### 3.2 Components and responsibilities

**Host.** Before M6 the host is its own small app in `serve/delivery-next/`: `host.py`, `api.py` and
the Changes page, with its own launch command and port. Cockpit is not modified before M6, because
fixes for the open Changes are released from `dev` to the pinned controller
([D5 §3.2](delivery-next-cutover.md#32-coexistence-while-m4-and-m5-run)). At M6 the Changes page
and the host routes move into Cockpit, and Cockpit's unconditional old-engine imports and routers
are removed ([D5 §3.4](delivery-next-cutover.md#34-cutover-gates-and-order-m6)). The charter makes
the process that serves the status view the owner of runners in both phases.

- One host per clone: `flock` on `host.lock` in the store. A second start prints the running URL
  and exits 0.
- Serves the status view on `127.0.0.1` at a free port, recorded with a random token in `host.json`
  (mode 0600).
- One scheduler thread wakes on start, wake from sleep, a new inbox item, a runner exit, or a timer.
  For each Change without a runner it first reconciles actionable inbox items under the Change lock:
  brief approval, answers, person-only check results, recovery choices, merge consent. A reconciled
  item makes the Change runnable again. Before skipping a Change that waits on the user, it observes
  the Change's PR terminal state: merged → after confirming termination, preservation and cleanup
  run, and no creative work starts for a paused or held Change; closed → the M4 `ask` (D3). Only
  then does it skip Changes waiting on the user, paused or stopped, and start a runner for the next
  step of the rest. Termination checks still precede
  launching another writer. Pending conditions are re-observed at the profile's poll intervals (D3).
- Launches `python -m owlbear_delivery_next.runner <change>` in its own process group and records the
  PID. The next runner starts only after the previous one has exited and its termination is
  confirmed by the host's worktree scan (§3.5).
- Runs a person-only check's environment, for example a local preview server, itself. The
  preparing Builder returns a verified launch recipe (command, directory, readiness URL or probe)
  and is then fully terminated under the normal teardown (§3.2 SDK adapter). The host then launches
  the environment, verifies readiness, records its PIDs and enters pending for the check. It
  relaunches the environment after an interruption and disposes of it before any other writer
  starts on the Change.
- Detects sleep by a jump of more than 60 s between wall-clock and monotonic time, then runs an
  observation pass.
- Starts through a VS Code folder-open task ("OwlBear Delivery host", `runOn: folderOpen`). Setup
  asks consent to write `.vscode/tasks.json` (a tracked file, DR14) and verifies workspace trust and
  `task.allowAutomaticTasks`. Without them, the disclosed start action is "Run task: OwlBear Delivery
  host", and the status view and chat say nothing advances until it runs.

**Runner.** One Change, one step, then exit. It takes the Change lock without waiting (held → exit;
the host tries again), folds the inbox, observes git and GitHub for the step's effect (DR5), acts,
writes the exit or pending condition atomically, tears down (§3.5), releases the lock and exits.
Agent steps use one SDK client and one session; engine steps use no agent. It records the session
id, runtime PID and task PIDs as they appear. A runner never starts another runner.

**SDK adapter.**

| Concern | Design | Basis |
| --- | --- | --- |
| Runtime | Installed Copilot CLI via `RuntimeConnection.for_stdio(path=…)`; path and version from readiness. Stdio ties the runtime to the runner | P3; runtime download blocked by the proxy (S02) |
| Agent | One custom agent per role from the package's `agents/`, pre-selected; repository instructions and skills load as the platform loads them | P1, P6, P7 |
| Model | Per step kind from the profile. After each step the billed model from usage metrics is compared; a mismatch shows in the status line, and becomes `ask` only if the profile marks the model as required | P6 silent fallback, P11 |
| Result boundary | The step ends when a result tool call is accepted; the handler validates and returns field errors to the same agent (T3, T4). Never wait on `session.idle`. A turn that ends without a result gets one reminder, then `retry`. Each step kind has a deadline | P1, P4 |
| Questions | No `on_user_input_request` handler; the runtime's own question tool is unavailable. `ask_question` ends the step with `ask`; the answer is delivered by resuming the session and sending it as a message | P2b, P2d |
| Permissions | Handler with the step kind's allow list (§3.6); everything else denied and recorded in the activity log | P5 |
| Usage | `usage.get_metrics` per session into the activity log; spend per Change in the status view | P11 |
| Termination | (1) `tasks.list`; (2) `tasks.cancel` each; (3) check listed and recorded PIDs are gone; (4) disconnect; (5) the runtime PID has exited. Then the host, after the runner exits, scans with `process_probe` for processes in the step's worktree, including the runner's former subtree, which the probe skips while it runs inside the runner. Any survivor or unverified item → `stop` naming the PIDs. The rule holds for every worker, `check` preparation included: no worktree process survives, and a check environment is launched only afterwards by the host | P4, P4b, DR10 |

**State store.** Options for the location, all outside the checkout (DR11):

| Option | For | Against |
| --- | --- | --- |
| `<git-common-dir>/owlbear-delivery/` | Same path from every worktree (`git rev-parse --git-common-dir`); no repository key; never in a branch or push; survives `git clean -xdf`; removed with the clone | Unfinished Change state is lost on re-clone; agents with a shell could edit it (denied by policy) |
| User data directory keyed by repository | Survives re-clone | Needs a stable key; two clones of one repository collide or split; orphans after a clone is deleted |
| `.owlbear/` in the checkout | Visible | Inside the checkout; needs `.gitignore` consent; the old self-conflict class (RC3) |

Chosen: the common git directory. It is clone-local: deleting the clone deletes the state of its
unfinished Changes, while their branches and PRs remain on GitHub. Layout:

```text
<git-common-dir>/owlbear-delivery/
  format                      store version
  profile.json                confirmed project profile
  host.json  host.lock        URL, token, PID; one host per clone
  history.jsonl               one line per finished Change
  changes/<slug>/change.json  the Change record (A04 §4)
  changes/<slug>/lock         per-Change writer lock
  changes/<slug>/inbox/       answers, check results, approvals, consent, intents
  changes/<slug>/activity.jsonl   last 200 events: steps, denials, usage, tool-call outcomes
  changes/<slug>/preserved/   bundle and archive files of unfinished work
```

- Writes use `atomic_write`; the previous file is kept as `.prev`. A newer `format` → `stop`
  "upgrade OwlBear"; an older one migrates forward; a failed migration → `stop` "restore previous".
- The lock is `flock`, released by the OS when its holder dies, plus a holder record (PID, host,
  since) for the status line. A free lock is not proof the writer ended; §3.5 checks that.
- The host API writes inbox items without the Change lock; only a holder of the Change lock folds
  them (the scheduler between steps, the runner at step entry), so answers that arrive during active
  work wait for the next step.
- Preservation bundles the named Change branch with `git bundle create` (a bundle needs a named
  ref; a raw commit SHA cannot be bundled) and archives dirty, staged, untracked and conflicted files
  separately: `git diff --binary` for tracked changes, the index state including conflict stages,
  and an archive of untracked files. The workspace stays untouched until `git bundle verify` and an
  archive read-back succeed. No new refs, no push.
- Worktrees live under one user data root (`~/Library/Application Support/OwlBear/worktrees/` or
  `$XDG_DATA_HOME/owlbear/worktrees/`), keyed by repository name and a short hash of the common
  directory, so setup grants folder trust once (P8).

**Project profile.** Detected with `gh repo view --json`, `gh api` for branch rules and protection,
`.github/workflows/`, manifests and lockfiles per package, hook and signing configuration,
`.gitattributes` and `.gitmodules`. Each entry is known, unknown or unsupported with its evidence
(DR1); an HTTP 403 on rules is unknown. The user confirms it in the status view at setup; each
Change records the profile version it started with. Effective rules and required checks are re-read
before publish and before merge; a difference becomes `ask` showing it. Models per step kind and a
spend estimate are part of the profile.

**Git and GitHub adapters.** Copied modules (§3.1). The loop pushes with hooks as configured, never
with `--no-verify` or force. A failing pre-push hook becomes a builder fix step (DR3); transport or
authentication failure becomes pending; an unknown write result is read back with
`classify_write_readback` and replayed only on confirmed absence. Merge is queue-aware. Without a
required merge queue it is the REST merge call with `sha` set to the consented head and the
profile's method, then a readback. When the effective rules require a merge queue, the loop submits
through GitHub's merge API with the consented head SHA and no rule bypass, and maps an `enqueued`
response to pending, not refusal. Both copied sources need that adaptation: the retained
`publication_provider.merge_request_body` forces `direct_merge`, and `serve/delivery-github` maps
`enqueued` to refusal today. The host then observes the queue; on removal it routes the cause (CI →
fix task, conflict → integrate) or asks with the removal reason.

**Changes page.** Served by the host app before M6; a "Changes" page beside Ideas and Memory in
Cockpit after it. Endpoints under `/api/next`:

| Endpoint | Purpose |
| --- | --- |
| `GET /changes` | Every Change with its status line, next actor and last observed activity |
| `GET /changes/{slug}` | Brief and versions, plan, open question, person-only checks, PR link, activity |
| `POST /briefs` | Create a Change or revise its brief draft (behind `save_brief`): validates the brief, returns the host-issued handle or field-specific errors |
| `POST /changes/{slug}/brief-approval` | Approve one brief version |
| `POST /changes/{slug}/answers` | Answer one question (also used by the chat tool) |
| `POST /changes/{slug}/check-results` | Pass or fail of one person-only check, with a note |
| `POST /changes/{slug}/merge-consent` | Consent to merge one exact head; void when the head changes |
| `POST /changes/{slug}/intent` | Pause, resume or abandon |
| `POST /changes/{slug}/recovery` | Apply one action offered by the current `stop` (T6), e.g. "end processes 4312, 4318" |

A brief save is validated and written at once, so its errors reach the chat. Every other write lands
in the inbox and wakes the scheduler. Recovery actions are only those the current
`stop` names; agents have no recovery tool (T6).

### 3.3 Agent-facing contract

| Role | Runs in | Receives | Returns | Tools |
| --- | --- | --- | --- | --- |
| Designer | VS Code chat, skill `delivery-shape` | The user's words, the repository | A brief draft | `save_brief`, `show_status`, `answer_question` |
| Planner | SDK, step `plan` | Approved brief, criteria, profile commands, file scopes of other open plans | Ordered tasks with title, goal, scope paths and checks | `submit_result`, `ask_question`, `report_wrong_premise` |
| Builder | SDK, steps `build`, `integrate`, and `check` preparation | One task, its criteria, profile commands, findings to fix | Summary, checks run with exit codes, notes; for `check` preparation, a verified launch recipe (command, directory, readiness URL or probe) | same three |
| Reviewer | SDK, brief and plan challenge inside `shape` and `plan`, and `review` | The brief, plan or diff, criteria; read-only | Verdict `pass` or `fix`, findings with place, problem and fix; covered paths, including files read outside the diff. The loop records them and the judged criterion versions with fingerprints, and re-requests the review only when one changes (P5) | same three |

| # | Tool | One job (T1) | Fields (T5) | Ends the step with |
| --- | --- | --- | --- | --- |
| 1 | `save_brief` | Create or revise one Change's brief draft | `change` (short handle, empty for new), `title`, `outcome`, `criteria[]`, `scope`, `person_checks[]` of name, steps, expect | — (chat; `POST /briefs` returns the handle or field errors) |
| 2 | `show_status` | Show waiting Changes, open questions with handles, the status-view URL | `change` (optional) | — (chat) |
| 3 | `answer_question` | Answer one open question | `question` (handle), `option`, `text` | — (chat) |
| 4 | `submit_result` | Submit this step's result; one fixed schema per session (plan, work or review) | At most six per schema | `done` after loop checks, else `retry` |
| 5 | `ask_question` | Ask the owner one question | `question`, `why`, `options[]` of label and effect | `ask` |
| 6 | `report_wrong_premise` | Say the brief or plan is wrong | `stage` (brief or plan), `reason`, `evidence[]` | `back` |

Six names in total, three per role. `submit_result` keeps one fixed schema per session, so it counts
once (charter §3.9). Chat tools are served by `mcp_server.py`; worker tools are
SDK-defined per session, so worker sessions need no MCP server and no MCP folder trust (P8).
When the host is down, `show_status` reads the Change files directly (read-only), shows "Delivery is
not running" and offers Start Delivery; the other chat tools need the host. Recovery decisions stay
in the Changes page (T6).

- **Identity (T2).** SDK tools are closures bound by the runner to Change, step, worktree and attempt;
  they have no identity fields. The commit is the worktree head the loop reads after the step. Chat
  tools take only short handles the host issued (`c3`, `q2`).
- **Validation (T3, T4).** The handler validates while the author's session is alive and returns one
  error naming the field, the rule and an example, e.g. `tasks[2].checks: empty — name at least one
  command from the profile, e.g. "npm test"`. Three invalid calls → `retry` with error kind
  `result`. Every field has a description, limits and one example in its schema.
- **Loop checks after `submit_result`.** Build: a new commit exists, the worktree is clean, the
  reported checks cover the task's checks; files outside the planned scope are listed for review.
  Review `fix` → a build step with the findings; after two rounds → `ask` (charter §3.9).
- **T6–T8.** No recovery tool. Budget tests count tools, fields, step kinds and error kinds. The
  activity log records every tool call's outcome for the M4 measurements.

### 3.4 Skills, agents and instructions

| Artefact | Purpose | Loaded by | Location | Lines |
| --- | --- | --- | --- | --- |
| Skill `delivery-shape` | Shape or revise a Change with the user; save the brief; point to approval | VS Code harness | OwlBear agent plugin for consumers; `.github/skills/` in this repository (E1) | 150 |
| Skill `delivery-continue` | Status, answers, the start action when the host is down (read-only status then) | VS Code harness | same | 100 |
| Agents `planner`, `builder`, `reviewer` | Worker craft, including condensed `h-ac-quality` rules | Runner, as SDK custom agents | Package `owlbear_delivery_next/agents/`; nothing in consumer repositories | 450 |

Total 700 of 800 lines. Worker craft lives in agent prose because skill use inside SDK sessions is
untested (P7). The chat MCP server is registered in the repository's `.mcp.json` with consent; its
`cwd` is the session directory, from which it finds the store through the common git directory, so
worktree sessions reach the same store (A07). Old Delivery skills stay in their Local locations until
M6 and are not ported; `/ideate` is unchanged.

### 3.5 Process model and failure handling

Processes: VS Code window → folder-open task → host (its own app before M6, Cockpit after; scheduler)
→ runner per step → Copilot runtime as a stdio child → shells and tasks it starts. Chat → MCP
server per window → host over loopback HTTP with the token.

| Event | Detection | Exit or pending | Re-entry |
| --- | --- | --- | --- |
| Host not running | `host.json` PID gone or lock free | Nothing advances; every status line says "Delivery is not running" with the start action | Host start observes every Change first |
| Two windows (X5) | `host.lock`; Change lock | Second host exits with the URL; both chats use one host | — |
| Laptop sleep (X1) | Clock jump in host and runner | A runner whose SDK or network calls failed tears down → `retry` | Observation pass on wake |
| Host crash | Runner holds the Change lock in its own process group | Runner finishes and records its exit | New host waits for the live runner to finish or its termination to be confirmed, observes, then continues; it never kills it blindly |
| Runner crash | Runner gone, no exit recorded | Termination check (§3.2) and the host's worktree scan. Verified → `retry` (`liveness`); unverified → `stop` with "end processes …" | Observe, then resume the recorded session with a "check and finish" message (P3) |
| Runtime crash | Connection lost inside the runner | Runner ends; the host's worktree scan finds survivors; none → `retry`, else `stop` | As above |
| Network loss | Transport errors from git, `gh` or the SDK | `retry`, then pending on the host's network probe (`network`); an unknown write is read back on return | Observation when the probe succeeds |
| Sign-in expired | Authentication errors, readiness | `ask` with the exact sign-in command (`auth`) | Readiness passes |
| Worker hangs | Step deadline; no tool activity for the step kind's limit | Teardown → `retry` | New or resumed session |
| Repeated denial | Same command denied twice in a step | `ask`: allow it for this step kind in the profile? | Next step uses the updated list |

A session is resumed only after the previous writer's termination is confirmed; otherwise the step
starts a new session with the same prompt plus what observation found. Observation failure is never
treated as absence (A05 §3.3).

### 3.6 Security and permissions

| Step kind | Allowed | Denied explicitly |
| --- | --- | --- |
| Brief challenge in `shape`, `plan`, `review` | Read, search, read-only `git` (`log`, `diff`, `show`, `status`) | Writes, every other shell command, URL fetch |
| `build`, `integrate`, `check` preparation | Read; write inside the worktree; shell for the profile's install and check commands; `git` `add`, `commit`, `merge`, `status`, `diff`, `log`, `restore` | `git push`, `git config`, `gh`, removal outside the worktree, detached shells where the request shows them |
| `publish`, `follow`, `merge`, `cleanup` | No agent | — |

- **Default deny.** Unlisted requests are denied and recorded; allow-all is never used (P5).
- **Secrets.** The profile stores credential references, never values. A question that needs a
  secret becomes the prerequisite action "set it outside chat". Prompts carry no environment values;
  the activity log redacts tokens.
- **Repository policy.** No `--admin`, `--no-verify`, force push or rule edits. Unknown rules make
  merging human-assisted ("merge in GitHub"). Push protection and required checks are never bypassed.
- **Status view.** Bound to `127.0.0.1`. Requests with any other `Host` header are rejected (DNS
  rebinding). Writes need JSON and a same-origin `Origin`, or the bearer token from `host.json` (for
  the MCP server).
- **Trust.** Folder-open tasks run only in trusted workspaces. The worktree root is trusted once at
  setup. Repository files, issues and PR comments enter prompts as quoted data, not instructions.

### 3.7 Proof per P8

| Piece | Proof |
| --- | --- |
| Exit transitions, budgets per cause carried across `retry` and `back` | Automated |
| Re-entry decisions with fake git and GitHub observers; replay only on confirmed absence | Automated |
| Lock, inbox folding, atomic write, version gate and migration | Automated |
| Status line derivation; consent void on head change | Automated |
| Termination decision with a fake process probe, including the host's scan of the runner's former subtree | Automated |
| Tool schemas (fields described, at most six, example present) and field errors | Automated |
| Budgets: tools, step kinds, error kinds, source lines, prose lines, tests ≤ source; no old-engine import | Automated |
| SDK adapter, permission policy, Changes page, folder-open task, profile detection, `gh` provider, protected merge | M4 demonstration |
| Killed runner and host, sleep, network loss, two windows, CI failure, PR comment, target conflict, head change after consent | M4, triggered by hand |

Copied modules keep only tests of silent logic (`classify_write_readback`, `atomic_write`), within
the test budget. Agent prose gets structural checks only.

### 3.8 Alignment with D3

Adopted from D3 unchanged: the ten step kinds (`shape`, `plan`, `build`, `review`, `integrate`,
`publish`, `follow`, `check`, `merge`, `cleanup`), the fifteen error kinds, cause keys, budgets and
the state records. Differences to settle in the M3 challenge:

- **Worker result shape.** D3's `build` result carries a status (done, blocked, infeasible,
  needs-user) and a question. T1 forbids one tool with several outcomes, so D4 splits them:
  `submit_result` (done), `ask_question` (needs-user, or blocked on a missing item, as an action
  question) and `report_wrong_premise` (infeasible → `back`). D3's exits are unchanged.
- **Preserved work.** Settled in revision 2026-10-10: D3 now records the bundle and archive paths
  in the store, so nothing appears in `git branch` and nothing can be pushed by accident.
- **Writer lock.** D3's lock record stays in the Change file for the status line; D4 adds the
  `flock` file that gives the exclusion. A host-assigned short handle (`c3`, `q2`) is added for chat
  tools (T2).

### 3.9 Open questions

| ID | Question | For | Why it matters |
| --- | --- | --- | --- |
| O1 | Which models and what cost on the employer seat? | Probe (R8 repeat) | Profile defaults and spend estimate; P6 showed silent fallback |
| O2 | Merge and rule reads on a protected repository | Probe in a `maba-pag` sandbox | `gh.py` 403 handling, required-check identities, merge queue |
| O3 | Do SDK-created sessions appear in the VS Code Agents window? | Probe | Could replace parts of the status view later (Q9) |
| O5 | Do user-level tasks support `runOn: folderOpen`? | Probe | Would avoid writing a tracked `.vscode/tasks.json` |
| O7 | Do permission requests show a shell's `detach` flag; do pre-tool hooks work in SDK sessions? | Probe | Detached shells outlive the runtime (P4) |
| O8 | How do consumers get a Copilot CLI behind a TLS-intercepting proxy? | Probe, setup | The SDK's runtime download failed (S02) |

Settled in revision 2026-10-10: O4, `submit_result` counts as one tool (charter §3.9), so the total
stays 6; O6, clone-local state is a stated limitation (§3.2, §4); O9, Cockpit is not modified
before M6 because the host is its own app until then.

## 4. Recommendation, Confidence, and Limits

**Recommendation (`autonomous`):** build `serve/delivery-next/` as laid out in §3.1: its own host
app until M6 and Cockpit as the host after it, one runner process per step, state in the common git
directory, six agent-facing tools of which
three are SDK-defined per session, and worker craft in package-shipped agent prose. Probe O1, O2,
O5 and O8 before M4 depends on them.

**First vertical slice (M4).** One pre-approved, one-task sandbox Change runs through ask → answer
→ resumed build, including one preview-environment cycle (launch recipe, Builder teardown, host
launch and readiness, pending check, disposal). It is done when:

- a real SDK worker receives a field-specific `submit_result` rejection, corrects it, asks a
  question and terminates;
- the answer survives the original runner's disappearance and a host restart, and launches exactly
  one successor without another command;
- host-down status, second-window exclusion and an orphan command preventing replacement are
  demonstrated;
- it ends with a checked commit, durable state in the git common directory and nothing in product
  branches;
- versions, tool-call outcomes and touchpoints are recorded.

Publication, CI, protection and merge are later slices. Only TD-3's silent-logic checks are
automated.

**Confidence:** high that the components fit the budgets (about 8,800 of 10,500 lines, 700 of 800
prose lines, 6 tools, 10 step kinds, 15 error kinds) and that the state location meets DR11 and DR10.
Medium for the host app and the termination protocol: both follow probe evidence, but
neither has run as a whole. Low for the folder-open start and per-step model selection, which depend
on O5 and O1.

**Limits:** no code was run. Line targets are estimates; copied sizes come from the route comparison.
State is clone-local: deleting the clone deletes unfinished Change state; branches and PRs remain on
GitHub. D3 was read as a parallel draft; its later edits may change names (§3.8). The probe evidence comes from one macOS laptop, a
free personal identity, Auto models and an unprotected private repository.
