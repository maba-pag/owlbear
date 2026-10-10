# Delivery Next: Architecture (D4)

> **Owning task:** none — M3 D4 of the [liveness-first rebuild](delivery-liveness-first-rebuild.md)
> **Date:** 2026-10-10
> **Question:** What is the smallest set of packages, processes, state files, agent tools and prose
> that delivers the [charter](delivery-next-charter.md) on the Copilot SDK, and how does each part fail?
> **Status:** design draft; `autonomous` until the user approves M3. Revision 2026-10-10 after
> design challenge and the full-set challenge: separate host app until M6, inbox before exclusions,
> host-side termination scan, check environments, bundle and archive preservation, brief endpoint,
> tool count, clone-local state. Revision 2026-10-10 for TD-10 to TD-22: module rules instead of line
> targets, merge gate and pull-back, visual check, thread replies, New Change, consented local files,
> no merge queue. Revision 2026-10-10 aligned with the M4 reshape (phases A–E, `adfb5a77c`): module
> layout, gate order, conversation versions, declared CI, overlap, retry classes, visual check.

## 1. Context and Question

The [charter](delivery-next-charter.md) fixes the route (a thin core beside the old engine, a Python
SDK loop), the touchpoints, the exit contract, the interaction surface (§3.7), agent rules (§3.8),
budgets (§3.9) and proof policy (§3.10). D4 turns that frame into components that keep the tool and
kind limits and the module rules (TD-19). It uses the step kinds, error kinds and state records of the parallel
[status and exit model (D3)](delivery-next-status-and-exits.md); §3.8 lists where the two differ.

## 2. Sources Studied

| ID | Source | Used for |
| --- | --- | --- |
| A01 | [Charter](delivery-next-charter.md) | Binding frame: ownership, route, touchpoints, exits, §3.7–§3.11 |
| A02 | [Platform probe](delivery-next-platform-probe.md) | P1–P12: typed results, permissions, resume, `tasks.list`/`tasks.cancel`, usage, idle pitfall, TLS-proxy runtime |
| A03 | [Route comparison §3.4](delivery-next-route-comparison.md#34-reuse-without-the-old-authority-model) | Modules to copy, their size and coupling |
| A04 | [Ownership map](delivery-next-ownership-map.md) | What Delivery-next owns, its state records and operations |
| A05 | [Journey and failure modes](delivery-next-journey-and-failure-modes.md) | J0–J9, merge gate, pull-back, exit rules (§3.3), rows X1–X10, DR1–DR16 |
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
source path and commit. Modules follow use cases (TD-19). The "Current" column gives raw line counts
(`wc -l`) on the prototype branch `next/m4-slice1` at `adfb5a77c` (2026-10-10), not targets and not
the logic-line measure.

| Module | Responsibility | Origin | Current |
| --- | --- | --- | --- |
| `models.py` | Change, profile, step, exit, pending, question and inbox records, each with `format` | new | 553 |
| `store.py` | State paths, atomic read and write, version gate and forward migration, per-Change lock, merge lock per target, inbox | new, over `storage_io` | 303 |
| `loop.py` | Choose the next step, apply its exit and the inbox, re-entry dispatch | new | 376 |
| `moves.py` | Where a Change goes next, the questions it asks and the tasks it opens | new | 62 |
| `failures.py` | Cause keys, failure classes (environment, Delivery defect, splittable work) and normalised signatures | new | 66 |
| `budgets.py` | Count failures per signature, growing pauses for environment faults, ask once a budget is spent | new | 284 |
| `evidence.py` | When a recorded review, check or visual answer holds, and what a Change must show | new | 119 |
| `briefs.py` | Validate and write a new Change or a new brief version | new | 92 |
| `overlap.py` | Shared paths between Changes as information; behavioural collisions at integration | new | 164 |
| `status.py` | The one status line, the "now" line and next actor (DR8) | new | 217 |
| `mask.py` | The one sanitiser of command text Delivery shows or persists | new | 38 |
| `profile.py` | Detect, confirm and re-read the project profile, including declared CI bound to a workflow digest, merge method, "ask before merge", and model and reasoning effort per role | new | 312 |
| `steps/` `engine`, `worktree`, `review`, `publish`, `follow`, `check`, `merge`, `cleanup` | Engine parts of steps: shared exits, workspace, review, push and PR, CI, declared checks and conversation handling, person-only checks, merge gate and guarded merge, preservation and cleanup | new; the optional "ask before merge" consent keeps the head-bound rule of `merge_approval.py` | 1,640 |
| `steps/conversation.py` | Which PR conversation items are Delivery's, and which item versions are open or handled | new | 199 |
| `steps/visual.py` | Visual check: UI detection, Playwright capture of the brief's states, screenshots to the reviewer, result bound to head and tree | new | 272 |
| `steps/pullback.py` | Fetch and fast-forward the local target after a merge, or record "behind" with its reason; also serves the Pull action | new | 96 |
| `prompts.py` | Bounded context for each agent step | new | 402 |
| `sdk_adapter.py` | Session, agent, model and reasoning effort, result boundary, usage, teardown | new | 417 |
| `session_result.py` | What one worker session produced, mapped to the loop's step result | new | 129 |
| `permissions.py`, `confinement.py` | Allow list and denials per step kind; which paths a command reaches and whether they stay in the worktree | new | 183 |
| `processes.py` | Recorded step processes by PID and start time, signalling, termination verdict | new | 74 |
| `tools.py` | The six tool schemas and their validators | new | 472 |
| `runner.py` | Process entry: one Change, one step | new | 320 |
| `host.py` | Scheduler, runner launcher, startup observation, host lock, check and preview environments, termination scan, New Change launch | new | 388 |
| `api.py` | Status-view HTTP router | new | 337 |
| `mcp_server.py` | Three chat tools; a client of the host, with a read-only status fallback | new | 152 |
| `setup.py`, `cli.py` | Readiness check, setup with consented local files, entry points | new | 556 |
| `git/remote_git.py`, `git/git_executable.py` | Bounded remote Git, write readback | copied as is | 310 |
| `storage_io.py` | `atomic_write`, `locked_roots`, `ControllerLock` | copied, trimmed | 56 |
| `github/provider.py` | PR, check, rule, review-thread and merge contract; direct merge only (TD-22) | `publication_provider.py`, trimmed and adapted | 295 |
| `github/gh.py`, `gh_client.py`, `gh_checks.py`, `gh_conversation.py` | `gh` provider split by use case: client and hosts, PR and rules (HTTP 403 means unknown), checks and logs at a head, conversation items read, replied to and resolved with `gh api graphql`; `sha`-guarded merge | `delivery-github/github.py`, adapted | 632 |
| `github/merge_offer.py` | Merge gate block reasons, attempt readback; proof fields dropped | `merge_offer.py`, adapted | 110 |
| `process_probe.py` | `ProcessTableWorktreeProbe`, `psutil_user_processes`; claim issuer dropped. The probe skips the caller's own descendants, so the host, not the runner, runs it | `worker_stall.py`, adapted | 326 |
| `criteria.py` | Criterion identity and version (P5 input) | not built: no separate module on the branch | — |
| Changes page | List, Change card, detail, New Change, answer, check result, brief approval, Pull, recovery actions | new; `web/changes.html` served by the host app before M6, moved to Cockpit web `src/pages/changes/` at M6, reusing shell, theme, `usePollingFetch`, table and dialog patterns | 275 |

**Module rules (TD-19).** One owner per decision. A module over about 400 lines of logic — not
counting blank lines, comments, docstrings, imports, type-only declarations and interface
definitions — is split by use case, never trimmed of logic. Ruff complexity limits apply per
function. There is no total source budget; the tool limits (≤ 6 agent-facing, ≤ 3 per role), ≤ 10
step kinds, five exits plus pending and ≤ 15 error kinds stay. `tests/test_module_rules.py`
enforces ≤ 400 logic lines per module, ≤ 10 step kinds, ≤ 15 error kinds, exactly five exits plus
pending and the tool limits. About 40 lines are added to Cockpit
`main.py` at M6. Not copied: `effect_launcher.py` (a merge call
guarded by `sha`, then a readback, replaces the frozen-body launch) and the in-memory provider, which
moves to tests as a fake. Agent prose in `agents/` follows the language style (§3.4), not a ceiling.

Measured after the M4 reshape (`adfb5a77c`, 2026-10-10, `wc -l`): 9,956 Python source lines
including copied modules, plus 275 lines of HTML for the Changes page; 4,605 test lines; 123 lines of
agent and skill prose. These are current sizes, not budgets. Four modules exceed 400 raw lines
(`models.py`, `tools.py`, `sdk_adapter.py`, `prompts.py`); the module-rule test passes them on logic
lines.

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
  brief approval, answers, person-only check results, recovery choices, Pull, and merge consent
  where the profile asks before merge. A reconciled
  item makes the Change runnable again. Before skipping a Change that waits on the user, it observes
  the Change's PR terminal state: merged → after confirming termination, preservation and cleanup
  run, and no creative work starts for a paused or held Change; closed → the M4 `ask` (D3). Only
  then does it skip Changes waiting on the user, paused or stopped, and start a runner for the next
  step of the rest. Termination checks still precede
  launching another writer. Pending conditions are re-observed at the profile's poll intervals (D3).
- Launches `python -m owlbear_delivery_next.runner <change>` in its own process group and records the
  PID. The next runner starts only after the previous one has exited and its termination is
  confirmed by the host's worktree scan (§3.5).
- Runs a person-only check's or visual check's environment, for example a local preview server, itself. The
  preparing Builder returns a verified launch recipe (command, directory, readiness URL or probe)
  and is then fully terminated under the normal teardown (§3.2 SDK adapter). The host then launches
  the environment, verifies readiness, records its PIDs and enters pending for the check. It
  relaunches the environment after an interruption and disposes of it before any other writer
  starts on the Change.
- Detects sleep by a jump of more than 60 s between wall-clock and monotonic time, then runs an
  observation pass.
- Starts new Changes for the New Change button: `POST /api/next/new-change` runs
  `code chat -r -m agent "<start prompt for the delivery skill>"` in the project folder, as an
  argument list without a shell and with a fixed prompt. If `code` is not on the path, the endpoint
  returns that exact command and the page shows it (S12).
- Starts through a VS Code folder-open task ("OwlBear Delivery host", `runOn: folderOpen`). Setup
  writes `.vscode/tasks.json` only with consent and only while it is untracked, adds it to the
  clone's `.git/info/exclude` so nothing is committed (TD-11, DR14), and verifies workspace trust and
  `task.allowAutomaticTasks`. `.git/info/exclude` covers only untracked files: a tracked
  `.vscode/tasks.json` is not written, and setup shows the manual alternative. Without the task, the
  disclosed start action is "Run task: OwlBear Delivery host" or the host's start command, and the
  status view and chat say nothing advances until it runs.

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
| Model | Model and reasoning effort per role from the profile; defaults wait for the `maba-pag` seat probe (TD-17, O1). After each step the billed model from usage metrics is compared; a mismatch shows in the status line, and becomes `ask` only if the profile marks the model as required | P6 silent fallback, P11 |
| Result boundary | The step ends when a result tool call is accepted; the handler validates and returns field errors to the same agent (T3, T4). Never wait on `session.idle`. A turn that ends without a result gets one reminder, then `retry`. Each step kind has a deadline | P1, P4 |
| Questions | No `on_user_input_request` handler; the runtime's own question tool is unavailable. `ask_question` ends the step with `ask`; the answer is delivered by resuming the session and sending it as a message | P2b, P2d |
| Permissions | Handler with the step kind's allow list (§3.6); everything else denied and recorded in the activity log | P5 |
| Usage | `usage.get_metrics` per session into the activity log; credits per Change and step on the card, never used to stop or ask (TD-21) | P11 |
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
  changes/<slug>/visual/      visual-check screenshots per reviewed head
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
  archive read-back succeed. No new refs, no push. If the workspace uses Git LFS or has submodules
  with local changes, cleanup does not retire it: the card shows "workspace kept: <reason>" with its
  path (M11, `autonomous`).
- Worktrees live under one user data root (`~/Library/Application Support/OwlBear/worktrees/` or
  `$XDG_DATA_HOME/owlbear/worktrees/`), keyed by repository name and a short hash of the common
  directory, so setup grants folder trust once (P8).

**Project profile.** Detected with `gh repo view --json`, `gh api` for branch rules and protection,
`.github/workflows/`, manifests and lockfiles per package, hook and signing configuration,
`.gitattributes` and `.gitmodules`. Each entry is known, unknown or unsupported with its evidence
(DR1); an HTTP 403 on rules is unknown. The user confirms it in the status view at setup; each
Change records the profile version it started with. Effective rules and required checks are re-read
before publish and before merge; a difference becomes `ask` showing it. Model and reasoning effort
per role, the merge method and "ask before merge" (default off) are part of the profile; a merge
queue in the rules is marked unsupported (TD-22).

**Git and GitHub adapters.** Copied modules (§3.1). The loop pushes with hooks as configured, never
with `--no-verify` or force. A failing pre-push hook becomes a builder fix step (DR3); transport or
authentication failure becomes pending; an unknown write result is read back with
`classify_write_readback` and replayed only on confirmed absence.

- **Merge.** `steps/merge.py` re-reads the rules, evaluates the gate, takes the merge lock for the
  target, re-reads the PR and evaluates the gate again in the order of D3 §3.2; the first unmet
  condition is the exit. Then the REST merge call with `sha` set to the gated head and the profile's
  method, then a readback. Setup recommends GitHub's "require branches to be up to date" and
  "require conversation resolution" where the plan allows, and the profile records whether they are
  on. Without them, a change between re-read and merge is a documented residual risk for personal
  use (TD-9). After the merge the engine watches the target checks at the merge commit: running
  checks keep it pending; a failure drafts one fix Change for the owner's approval while the original
  continues to preservation, cleanup and pull-back. No merge queue (TD-22); a required queue sends
  the merge to GitHub. A required human review is pending ("waiting for review by …").
- **Declared CI.** The profile's declared-CI entry is bound to a digest of the workflow files at the
  PR head. Changed workflows are detected again; check names Delivery cannot resolve are asked once
  per digest; unreadable workflows keep the gate waiting. Unknown CI never counts as "no CI"
  (interpretation of TD-15, `autonomous`).
- **Conversation and review threads.** The gate covers every PR conversation item regardless of
  author or API type: issue comments, review bodies (`gh api graphql`, `pullRequest.comments` and
  `reviews`) and review threads (`pullRequest.reviewThreads`). An item is Delivery's only by a
  recorded reply id, or when it is the viewer's own comment carrying the complete marker. Each other
  item is handled for its exact ID and version digest: answered by a reply, resolved after a fix, or
  recorded "no action needed: <reason>" and shown on the card (interpretation of TD-15,
  `autonomous`). A reopened or edited item is a new version and gets a new task. The Builder writes
  reply text; the engine posts it (`addPullRequestReviewThreadReply` or an issue comment) and
  resolves (`resolveReviewThread`); an acknowledged item is resolved too. Each reply carries the
  hidden marker `<!-- delivery:<change>:<item-id>:<fix-id> -->`; the engine looks for it before
  posting and never posts twice (P12). A deleted reply is reposted at most 3 times, then the owner
  is asked. A fix counts only while its commit is in the PR head. Before resolving it re-reads the
  thread; a newer comment not by Delivery means no resolution and a new feedback item (P13).
- **Pull-back.** `git fetch`, then each worktree from `git worktree list` is inspected. If the target
  is not checked out, `git fetch origin <target>:<target>`, which git refuses unless it
  fast-forwards; if it is checked out clean (no untracked files in paths the update touches) and not
  diverged, `git merge --ff-only --no-autostash --no-overwrite-ignore` there — never `git pull` with
  the user's configuration. Otherwise no stash, reset or merge: "behind" with the reason and Pull.
  Submodules are not updated; a changed gitlink adds "submodules changed" to the notice. Hooks and
  LFS filters run as with the user's own `git merge`. Unsaved editor buffers are invisible to git;
  VS Code shows its "file changed on disk" dialog.

**Visual check.** For UI changes the final review runs in visual mode on the exact head. The brief
records a render recipe: start command, URL or entry, a `ui` flag, and up to six `visual` states to
capture; a person-only check may be marked `visual: true`. A Change is UI when the brief says so or
its diff touches UI suffixes or folders, rename endpoints included; the owner's "Not a UI change"
holds only for that brief version and that UI path set. Captures are 1280×800 and 390×844, at most
6000 px high and 12 MB per review, with same-origin navigation only; the result is bound to head,
tree, states and criterion versions. Residual: JS or TS markup rendered outside UI folders is caught
only by the brief's `ui` flag. Shaping
establishes it before approval; if the project has none, shaping offers to add one as part of the
Change, declare a person-only visual check in the brief (TD-14), or change scope; visual testing is
never skipped (interpretation of TD-14, `autonomous`). The host launches the preview from that
recipe, as verified by the Builder; `steps/visual.py` captures the named UI states with Playwright
for Python, stores the PNGs under
`changes/<slug>/visual/` and passes them to the reviewer, who judges them with `submit_result`; the
reviewer may name further views for one more capture. Playwright, not the OwlBear browser MCP: the
MCP has no screenshot tool, worker sessions run without MCP servers (P8), and Playwright is already a
workspace dependency of `owlbear-browser`. The engine captures, so the reviewer keeps three tools.
A recipe that fails or a missing browser at runtime is B24.

**Changes page.** Served by the host app before M6; a "Changes" page beside Ideas and Memory in
Cockpit after it. Endpoints under `/api/next`:

| Endpoint | Purpose |
| --- | --- |
| `GET /changes` | Every Change card: status line, "now" line (step plus last tool event), step time, quiet warning, credits, overlaps, next actor |
| `GET /changes/{slug}` | Brief and versions, plan, open question, person-only checks, visual-check screenshots, decisions with origin, PR link, pull-back result, activity |
| `POST /new-change` | Run `code chat` with the delivery skill's start prompt; returns the command when `code` is missing |
| `POST /briefs` | Create a Change or revise its brief draft (behind `save_brief`): validates the brief, returns the host-issued handle or field-specific errors |
| `POST /changes/{slug}/brief-approval` | Approve one brief version |
| `POST /changes/{slug}/answers` | Answer one question (also used by the chat tool) |
| `POST /changes/{slug}/check-results` | Pass or fail of one person-only check, with a note |
| `POST /changes/{slug}/merge-consent` | Only with "ask before merge": consent to merge one exact head; void when the head changes |
| `POST /changes/{slug}/pull` | Retry pull-back of the local target |
| `POST /changes/{slug}/intent` | Pause, resume or abandon |
| `POST /changes/{slug}/recovery` | Apply one action offered by the current `stop` (T6), e.g. "end processes 4312, 4318" |

A brief save is validated and written at once, so its errors reach the chat. Every other write lands
in the inbox and wakes the scheduler. Recovery actions are only those the current
`stop` names; agents have no recovery tool (T6).

### 3.3 Agent-facing contract

| Role | Runs in | Receives | Returns | Tools |
| --- | --- | --- | --- | --- |
| Designer | VS Code chat, skill `delivery` | The user's words, the repository | A brief draft | `save_brief`, `show_status`, `answer_question` |
| Planner | SDK, step `plan` | Approved brief, criteria, profile commands, file scopes of other open plans | Ordered tasks with title, goal, scope paths and checks | `submit_result`, `ask_question`, `report_wrong_premise` |
| Builder | SDK, steps `build`, `integrate`, and `check` preparation | One task, its criteria, profile commands, findings to fix | Summary, checks run with exit codes, notes; for `check` preparation, a verified launch recipe (command, directory, readiness URL or probe) | same three |
| Reviewer | SDK, brief and plan challenge inside `shape` and `plan`, and `review`, including visual mode | The brief, plan or diff, criteria; in visual mode the screenshots; read-only | Verdict `pass` or `fix`, findings with place, problem and fix. The engine computes the covered paths deterministically from git (`git diff --name-status -M base...head`, including additions, deletions and renames), never from the reviewer's return, and records them, the judged criterion versions with fingerprints, and the tree each local check and visual capture ran on. Any path changed outside the covered set invalidates the review; a new head needs fresh proof for its changed paths (P5, `autonomous`) | same three |

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

| Artefact | Purpose | Loaded by | Location | Current lines |
| --- | --- | --- | --- | --- |
| Skill `delivery` | Shape or revise a Change with the user and save the brief; status, answers, the start action when the host is down (read-only status then); the New Change start prompt | VS Code harness | User-level (`~/.copilot/skills/`) for consumers, never in the project; `.github/skills/` in this repository (E1) | 36 |
| Agents `planner`, `builder`, `reviewer` | Worker craft, including condensed `h-ac-quality` rules and the visual review | Runner, as SDK custom agents | Package `owlbear_delivery_next/agents/`; nothing in consumer repositories | 83 |

No line ceilings (TD-19): prose follows a language style instead — specialist terms, no fillers or
explanations, not telegraphic. Worker craft lives in agent prose because skill use inside SDK sessions is
untested (P7). The chat MCP server is registered in the clone's `.mcp.json`, written with consent and
listed in `.git/info/exclude`; if `.mcp.json` is already tracked, setup does not write it and shows
how to add the server in the user-level MCP configuration instead. Its
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
| Network loss | Transport errors from git, `gh` or the SDK | pending with growing pauses on the host's network probe (`network`); age and attempts on the card, ask after 24 hours of the same fault (D3 §3.3); an unknown write is read back on return | Observation when the probe succeeds |
| Sign-in expired | Authentication errors, readiness | ask: run the exact login command, then continue (`auth`) | The owner answers "Done, continue" |
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
  the MCP server). New Change starts `code` with a fixed argument list, never a shell or request text.
- **Trust.** Folder-open tasks run only in trusted workspaces. The worktree root is trusted once at
  setup. Repository files, issues and PR comments enter prompts as quoted data, not instructions.

### 3.7 Proof per P8

| Piece | Proof |
| --- | --- |
| Exit transitions, budgets per cause carried across `retry` and `back` | Automated |
| Re-entry decisions with fake git and GitHub observers; replay only on confirmed absence | Automated |
| Lock, inbox folding, atomic write, version gate and migration | Automated |
| Status line derivation, including the "now" line and quiet warning; merge gate re-evaluated on head change | Automated |
| Termination decision with a fake process probe, including the host's scan of the runner's former subtree | Automated |
| Tool schemas (fields described, at most six, example present) and field errors | Automated |
| Budgets: tools, step kinds, error kinds, tests ≤ source; module rules: about 400 logic lines per module, ruff complexity per function; no old-engine import | Automated |
| SDK adapter, permission policy, Changes page and New Change, folder-open task, profile detection, `gh` provider, automatic merge under protection, pull-back, thread reply and resolve, visual check | M4 demonstration |
| Killed runner and host, sleep, network loss, two windows, CI failure, PR comment, target conflict, head change after the gate passed, dirty local target at pull-back, failed visual check | M4, triggered by hand |

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
| O1 | Which models and reasoning efforts per role on `maba-pag`'s business seat (TD-17)? | Probe (R8 repeat) | Profile defaults per role; P6 showed silent fallback |
| O2 | Merge, rule and required-review reads on a protected repository | Probe in a `maba-pag` sandbox | `gh.py` 403 handling, required-check identities, required reviews |
| O3 | Do SDK-created sessions appear in the VS Code Agents window? | Probe | Could replace parts of the status view later (Q9) |
| O5 | Do user-level tasks support `runOn: folderOpen`? | Probe | Would avoid writing a tracked `.vscode/tasks.json` |
| O7 | Do permission requests show a shell's `detach` flag; do pre-tool hooks work in SDK sessions? | Probe | Detached shells outlive the runtime (P4) |
| O8 | How do consumers get a Copilot CLI behind a TLS-intercepting proxy? | Probe, setup | The SDK's runtime download failed (S02) |
| O10 | Can an SDK session take screenshots as image input? | Probe | The visual check hands PNGs to the reviewer |
| O11 | Which stronger model may the retry policy switch to? (`autonomous`) | Profile, after O1 | The prototype has no profile setting for it, so the only alternative before asking is a re-plan |

Settled in revision 2026-10-10: O4, `submit_result` counts as one tool (charter §3.9), so the total
stays 6; O6, clone-local state is a stated limitation (§3.2, §4); O9, Cockpit is not modified
before M6 because the host is its own app until then.

## 4. Recommendation, Confidence, and Limits

**Recommendation (`autonomous`):** build `serve/delivery-next/` as laid out in §3.1: its own host
app until M6 and Cockpit as the host after it, one runner process per step, state in the common git
directory, six agent-facing tools of which
three are SDK-defined per session, and worker craft in package-shipped agent prose. Probe O1, O2,
O5, O8 and O10 before M4 depends on them.

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

**Confidence:** high that the components keep the limits (6 tools, 10 step kinds, 15 error kinds)
and that the state location meets DR11 and DR10.
Medium for the host app and the termination protocol: both follow probe evidence, but
neither has run as a whole. Low for the folder-open start, per-role model selection and the visual
check's image input, which depend on O5, O1 and O10.

**Limits:** the reshaped prototype (`adfb5a77c`) is proven by its package tests with fakes and
disposable repositories, plus one real Playwright capture; the reshaped flow has not yet run live
against GitHub and Copilot, and CI skips draft PRs. Current sizes are raw prototype line counts; the
logic-line measure of TD-19 is enforced by the prototype's module-rule test.
State is clone-local: deleting the clone deletes unfinished Change state; branches and PRs remain on
GitHub. D3 was read as a parallel draft; its later edits may change names (§3.8). The probe evidence comes from one macOS laptop, a
free personal identity, Auto models and an unprotected private repository.
