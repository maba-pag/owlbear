# Delivery Next: Status and Exit Model (D3)

> **Owning task:** none — M3 D3 of the [liveness-first rebuild](delivery-liveness-first-rebuild.md)
> **Date:** 2026-10-10
> **Question:** What does Delivery-next record for one Change, which steps can it be in, how does
> each step end, and how is one truthful status line with one next action derived from that?
> **Status:** design draft; `autonomous` until the user approves M3

## 1. Context and Question

The [charter](delivery-next-charter.md) fixes ownership, touchpoints, exits, the host and runners,
and the budgets. The [journey research](delivery-next-journey-and-failure-modes.md) gives stages,
exit rules and the catalogue. This document turns them into a state model, step kinds, an exit
table, one status function, error kinds and budgets, and walks the traces and C rows through them;
architecture is left to D4.

## 2. Sources Studied

| ID | Source | Used for |
| --- | --- | --- |
| D01 | [Charter](delivery-next-charter.md) §3.3–§3.11 | Ownership, touchpoints, exits, host and runners, budgets, proof policy |
| D02 | [Journey and failure modes](delivery-next-journey-and-failure-modes.md) §3.2–§3.6 | J0–J9, exit contract and rules, catalogue rows, DR1–DR15, six connected traces |
| D03 | [Ownership map](delivery-next-ownership-map.md) §4 | Minimal Change and profile records; what is never stored |
| D04 | [Platform probe](delivery-next-platform-probe.md) §3.2, §4 | Loop-owned questions (P2b, P2d); typed-result helper waits on idle, so a result event is the step boundary; termination by `tasks.cancel` plus PID and runtime-exit checks (P4b); default-deny permissions (P5) |
| D05 | [Rebuild research](delivery-liveness-first-rebuild.md) §3.6, §3.8 | Principles P1–P9; decisions TD-1–TD-8 |
| D06 | [Tool-surface audit §4](delivery-tool-surface-audit.md#4-recommendation-confidence-and-limits) | Tool rules T1–T8, especially T2 (no identities from agents) and T6 (recovery is engine or user) |
| D07 | [work_items.py](../../serve/delivery/src/owlbear_delivery/work_items.py) `DeliverySituation`, [status model rethink](delivery-status-model-rethink.md) §3.3 | Vocabulary only: "waiting on", "with an agent" is not proof of running |

## 3. Design

### 3.1 State model

One versioned file per Change and one per project, outside the checkout, written atomically. Kind:
**U** user decision, **L** loop record, **E** evidence input (what a review or check depended on).

| Record | Kind | Fields | Rule |
| --- | --- | --- | --- |
| Format and profile | L | format version; profile path and the profile version seen at step entry | Migrate forward or stop (S6); a newer profile is a premise change |
| Intent | U | the user's words; paused (time, reason); abandoned (time); hold for intent change | Flags are read at every step boundary (D6, X6) |
| Brief | U | draft versions; approved version and time; outcome, scope, non-goals, split; acceptance criteria with id, text, version | Approval is the touchpoint; drafts are L; criterion version is a check input |
| Person-only checks | U | id; criteria refs; steps; what to look for; recorded inputs (criterion version, procedure version, covered paths, environment labels); answer (pass or fail, note, time, input fingerprint at answer) | Valid while the current fingerprint equals the recorded one (P5) |
| Decisions | U or L | text; origin `decided`, `approved` or `autonomous`; time | Origin follows the provenance rule |
| Questions | U | id; step; kind decision or action; text; options, each naming its next step; answer, channel, time; effect check; effect observed time | An answer clears its cause only once its effect is observed |
| Plan | L | version; ordered tasks with id, title, scope paths, checks, origin (plan, review, CI, PR feedback, person-only check, integration) | Fix tasks are appended without a new plan version |
| Reviews | E | per task and final: reviewed commit, fingerprint of the files the Change touches, verdict, round | Valid until that fingerprint changes |
| Current step | L | kind; task id; mode; attempt; started time | Exactly one |
| Outcome | L | exit kind or pending; cause key; reason; next actor; wake trigger or next observation; last permission denial | Exactly one per step attempt; denial shown (B7) |
| Budgets | L | per cause key: count, premise fingerprint, last time; review rounds per task; re-plans per Change | §3.6 |
| Merge consent | U | head SHA; time; channel; delta shown | Void when the PR head is not that SHA |
| Writer lock | L | host id; runner PID and start time; runtime PID; session id; task PIDs with start times; acquired; heartbeat; last tool event | One writer per Change (DR10) |
| Stop record | L | error kind; one action; actor; resume condition; time | Cleared when the resume condition is observed |
| Names and preserved work | L | Change branch, target branch, worktree path; private local branches or paths holding preserved work | Names only; heads come from git; preserved work is never pushed (DR6) |

**Never stored:** heads, push state, PR number or state, checks, GitHub reviews, mergeability,
merge result; each step reads them at entry (DR5). **Project profile:** profile version, confirmed
time, entries known, unknown or unsupported with evidence (DR1), per-step model and allow list,
poll intervals, expected-start window for required checks, step timeouts. **Host record:** host id,
PID, start time, heartbeat; it tells the status function whether the host runs.

### 3.2 Step kinds

Ten kinds. "Prepare" is the start of `build` (engine creates the worktree, the Builder installs);
"await CI/review" is `follow`. Every step first **observes**: intent flags, profile version, PR
merged or closed (→ `cleanup` or the M4 question in `merge`), the writer lock, and whether its own
effect already exists. The step boundary is the runner's typed result event, never runtime idle.
The engine checks each result against git (commit exists, diff in scope and worktree, checks
passed, worktree clean); a claim the facts do not support is B4.

| Step | Stage shown | Entry condition | Agent role | Typed result | Exits; pending |
| --- | --- | --- | --- | --- | --- |
| shape | Shape | Change started, or back from plan, or intent hold released | Designer in chat; brief reviewer as runner | brief draft; reviewer verdict and findings | done, retry, ask, stop; pending on the chat |
| plan | Plan | approved brief, no valid plan | Planner; plan challenger | ordered tasks; challenger verdict | all five |
| build | Build n/m | open task, writer lock held | Builder | status (done, blocked, infeasible, needs-user), checks run with exit codes, question or missing item | all five |
| review | Build n/m | new commit for the task; or all tasks done (final mode) | build reviewer, read-only | verdict, findings, covered files | all five |
| integrate | stage of caller | target moved before publish or merge; I4, I6, M2 | Builder in integration mode | status, conflict paths, checks run | all five |
| publish | Publish | final review valid on an integrated head | none; engine with git and gh | — | all five; pending on network |
| follow | Publish | PR open at the current head | none; observer | — | all five; pending on CI, reviewers, owner action |
| check | Check | a declared person-only check without a valid answer | Builder only to prepare the environment | user's pass or fail and note | all five; pending on the user |
| merge | Merge | follow done; all checks valid | none | — | all five; pending on queue or mergeability |
| cleanup | Done | PR merged, or Change abandoned | none | — | done, retry, stop |

### 3.3 Exit and pending table

Every exit also records its kind, cause key, reason and time. `{S}` is the stage with task position.

| Step | Exit | Next step | Also recorded | Budget | Status text |
| --- | --- | --- | --- | --- | --- |
| shape | done | plan | approved brief version | new brief version resets plan-level causes | "Plan · planning from brief v{v}" |
| shape | retry | shape: Designer revises from findings | findings | review round +1 | "Shape · revising the brief: {finding} (round {r} of 2)" |
| shape | ask | shape; the approve option → done | question: approve, change, split (D1) | none | "Shape · waiting for you: {question}" |
| shape | back | never: first step; scope changes stay in shape | — | — | — |
| shape | stop | shape on the resume condition | stop record | none | "Shape · stopped: {reason} · {action}" |
| shape | pending | shape when the user returns to the chat | draft version | none | "Shape · draft v{v} saved {age} ago · continue in chat" |
| plan | done | build, first open task | plan version | — | "Build 1/{m} · starting: {task}" |
| plan | retry | plan | findings or field errors | review round +1, or cause +1 | "Plan · revising: {finding} (round {r} of 2)" |
| plan | ask | plan after the answer | question (D7, D8, D9) | none | "Plan · waiting for you: {question}" |
| plan | back | shape, which asks for re-approval | reason; kept and dropped work | cause +1 | "Shape · brief needs a change: {reason} · waiting for you" |
| plan | stop | plan on the resume condition | stop record | none | "Plan · stopped: {reason} · {action}" |
| build | done | review, task mode | attempt | — | "{S} · reviewing: {task}" |
| build | retry | build, same task; fresh session after B4 | attempt; diff kept in the worktree | cause +1 | "{S} · retrying: {cause} ({k} of 3)" |
| build | ask | build once the answer's effect is observed | question | none | "{S} · waiting for you: {question}" |
| build | back | plan (B9, D4, exhausted B4, B17 fix-first) or integrate (I6) | reason; preserved diff | cause +1; re-plan +1 if to plan | "Plan · re-planning: {reason}" |
| build | stop | build on the resume condition | stop record | none | "{S} · stopped: {reason} · {action}" |
| review | done | next task; after the last, review final; after final, publish (integrate first if the target moved) | review record | the task's rounds close | "Build {n+1}/{m} · starting: {task}" |
| review | retry | build, same task, with findings | findings | review round +1 | "{S} · fixing review findings (round {r} of 2)" |
| review | ask | build with the decision, or next task if accepted | both positions (B12) | none | "{S} · waiting for you: reviewer and builder disagree on {topic}" |
| review | back | plan | reason | cause +1; re-plan +1 | "Plan · re-planning: review found {reason}" |
| review | stop | review on the resume condition | stop record | none | "{S} · stopped: {reason} · {action}" |
| integrate | done | review final if covered files changed; else the calling step | caller | — | "{S} · updated with {target}" |
| integrate | retry | integrate | conflict paths or failing check | cause +1 | "{S} · updating with {target}: retrying {cause} ({k} of 3)" |
| integrate | ask | integrate or plan, per option | question (I5, conflict choice) | none | "{S} · waiting for you: {question}" |
| integrate | back | plan | reason | cause +1; re-plan +1 | "Plan · re-planning: {target} changed {area}" |
| integrate | stop | integrate on the resume condition | stop record | none | "{S} · stopped: {reason} · {action}" |
| publish | done | follow | nothing; branch and PR stay in GitHub | — | "Publish · waiting for CI on PR #{pr}" |
| publish | retry | publish, after observing push and PR | cause | cause +1 | "Publish · retrying {effect} ({k} of 3)" |
| publish | ask | publish once the effect is observed | question (S1, P5, P6) | none | "Publish · waiting for you: {action}" |
| publish | back | integrate (I4) or build (B15) | reason | cause +1 | "Build · {reason}" |
| publish | stop | publish on the resume condition | stop record | none | "Publish · stopped: {reason} · {action}" |
| publish | pending | publish when the network probe succeeds | outage start | none | "Publish · offline since {time} · continuing when the network is back" |
| follow | done | check if a check lacks a valid answer; else merge | — | — | "Check · waiting for you: {check}" |
| follow | retry | follow, after one rerun | flake per check and head | 1 per check and head | "Publish · re-running {check} once (flaky)" |
| follow | ask | follow or build, per option | question (P3 dispute, P10 owner action) | none | "Publish · waiting for you: {question}" |
| follow | back | build with an appended fix task | fix task with CI log or comment thread | cause +1 per check or thread | "Build · fixing {check}: {summary}" |
| follow | stop | follow on the resume condition | stop record | none | "Publish · stopped: {reason} · {action}" |
| follow | pending | follow when the observed condition changes | condition; next observation | none | "Publish · waiting for {who}: {condition} (checked {age} ago)" |
| check | done | merge | answer with input fingerprint | — | "Merge · waiting for you: approve merging {sha7}" |
| check | retry | check after preparing again | preparation failure | cause +1 | "Check · preparing {check}: retrying ({k} of 3)" |
| check | ask | check after the answer | environment question | none | "Check · waiting for you: {question}" |
| check | back | build with the user's note as a fix task (H2) | fix task | cause +1 per check | "Build · fixing: {check} failed for you" |
| check | stop | check on the resume condition | stop record | none | "Check · stopped: {reason} · {action}" |
| check | pending | check when the answer arrives; no timeout (H1) | steps; what changed if re-asked (H3) | none | "Check · waiting for you: {check}" |
| merge | done | cleanup | — | — | "Done · merged PR #{pr}; cleaning up" |
| merge | retry | merge, after observing whether it merged | cause | cause +1 | "Merge · retrying ({k} of 3): {cause}" |
| merge | ask | merge after consent; abandon → cleanup; reopen → follow | head and delta, or the M4 choice | none | "Merge · waiting for you: approve merging {sha7}" |
| merge | back | integrate (M2) or build (removed from queue by CI) | reason | cause +1 | "Build · updating with {target} before merging" |
| merge | stop | merge on the resume condition | stop record | none | "Merge · stopped: {reason} · {action}" |
| merge | pending | merge when GitHub reports merged or removed | queue or mergeability | none | "Merge · in the merge queue (checked {age} ago)" |
| cleanup | done | none: the Change is Done | preserved work; history line | — | "Done · merged PR #{pr}" |
| cleanup | retry | cleanup | cause | cause +1 | "Done · cleanup retrying ({k} of 3)" |
| cleanup | ask, back | never: unmerged work is preserved and reported; a merge cannot be undone | — | — | — |
| cleanup | stop | cleanup on the resume condition | stop record; workspace untouched | none | "Done · cleanup stopped: could not save {path} · {action}" |

**Global transitions**, applied by the host at a step boundary:

| Trigger | Effect | Status text |
| --- | --- | --- |
| Pause (user) | No new runner; the running step finishes or hits its timeout | "{S} · pausing: finishing {step}", then "{S} · paused by you" |
| Resume (user) | Clears paused; current step re-enters by observation | "{S} · resuming" |
| Intent change (D6) | Hold flag; running step finishes; merge outcome observed first if submitted; then shape | "{S} · holding for your change: finishing {step}" |
| Abandon (user) | Hold; then cleanup in abandon mode (close PR, keep branch) | "Abandoned · PR closed, branch kept" |

**Stop actions.** One action, its actor and the resume condition; the action works without Delivery.

| Cause | Action | Actor | Resume condition |
| --- | --- | --- | --- |
| Delivery's own tools fail to start (S2) | Run setup's repair command | you | Next host start passes readiness |
| Policy or version blocks Copilot (S4, X7) | Ask the administrator to allow {feature}, or update {component} | admin or you | Readiness passes |
| Proxy or TLS breaks installs (S5) | Set the proxy and CA entries named in the profile | you | Next install attempt succeeds |
| Quota exhausted (S9) | Raise the Copilot budget, or wait until {reset} | you | A model call succeeds; host retries at {reset} |
| Worker termination unconfirmed (B6, X5) | End process {pid} ({name}) | you | Host verifies the PID is gone |
| Edits outside the worktree (B11) | Keep or revert the listed files in your checkout; both versions are saved | you | Checkout has no unexplained changes |
| Disk full (B16) | Free space on {volume} | you | Free-space probe passes |
| Preservation unconfirmed (B19, M5) | Copy or delete {path}; Delivery left it untouched | you | {path} clean or gone |
| State cannot migrate (S6) | Finish this Change on OwlBear {version} | you | State loads on that version |
| State file unreadable | Restore the previous state (status-view action) | you | State loads |
| Model unavailable after fallback (B14) | Choose another allowed model for {step} in the profile | you | Profile version changes |

**Pending conditions**, in any step where they arise. None consumes budget.

| Condition | Observer | Wake trigger | Bound |
| --- | --- | --- | --- |
| Draft brief in chat | Designer skill | User continues in chat | none |
| CI running (P2) | host polls checks | completion seen; poll 1 → 10 min | none while running |
| Required check not started (P10) | host | check appears | expected-start window, then follow back (trigger fix) or ask |
| Required reviewer (P7) | host polls reviews | review submitted | none |
| Owner action in GitHub (P10, after ask) | host | the check starts | 3 observations, then stop |
| Person-only check (H1) | host | answer from status view or chat | none |
| Merge queue or mergeability (M3) | host polls PR | merged, or removed with a cause | removal routes its cause |
| Network outage or rate limit (S8, P9, S9) | host probe every 5 min, or the reset time | probe succeeds, or reset time passes | none |

### 3.4 Status line derivation

One function, shared by the status view and the chat skill, which reads the state file directly so
it works when the host is down: `status(stage, step, outcome, activity, now, next_actor) → (line,
action)`. Rules apply in order; the first match wins.

1. Done or abandoned → "Done · …" or "Abandoned · …"; action none.
2. Paused → "{S} · paused by you {age} ago"; action Resume. Runner still alive → "pausing".
3. ask → "{S} · waiting for you: {question}"; action Answer. Host down → append " · Delivery not running".
4. stop → "{S} · stopped: {reason}"; action = the stop action, with its actor if not you.
5. pending → "{S} · waiting for {who}: {condition} (checked {age} ago)"; action none, or the check.
6. Runner alive → "{S} · {verb}: {task} · {role} active {age} ago"; action none. No tool event for
   10 min → "· no activity for {age}"; the step timeout then terminates, confirms and retries.
7. Retry scheduled → "{S} · retrying: {cause} ({k} of 3) at {time}"; action none.
8. No live runner → host up: "{S} · not running: starting {role}", or "waiting for process {pid}
   to end"; host down: "{S} · not running: Delivery is not started"; action Start Delivery.
   Liveness is observed only (lock PIDs and start times, heartbeats, last tool event).

| # | Situation | Line | Action |
| --- | --- | --- | --- |
| 1 | Builder working | "Build 2/5 · implementing: rate limiter · builder active 40 s ago" | none |
| 2 | Not running, host up | "Build 2/5 · not running: starting builder" | none |
| 3 | Host not started | "Build 2/5 · not running: Delivery is not started" | Start Delivery |
| 4 | Checks failing | "Build 3/5 · retrying: checks failed in web (2 of 3)" | none |
| 5 | Question | "Build 3/5 · waiting for you: which variable holds the test API key?" | Answer |
| 6 | Brief approval | "Shape · waiting for you: approve brief v2" | Answer |
| 7 | CI | "Publish · waiting for CI: 2 of 5 checks running (checked 1 min ago)" | none |
| 8 | Person-only check | "Check · waiting for you: log in on staging and see the banner" | Report result |
| 9 | Consent voided | "Merge · waiting for you: approve merging b7e2a91, changed since a1c3f02" | Answer |
| 10 | Stopped | "Build 4/5 · stopped: commit signing key locked" | Unlock the key (you) |
| 11 | Paused | "Plan · paused by you 2 days ago" | Resume |
| 12 | Done with leftovers | "Done · merged PR #14 · 2 unmerged commits kept on owlbear/kept/login-1" | none |

### 3.5 Error kinds

Fifteen kinds, shown to users and agents; each cause key starts with one.

| Kind | Meaning | Rows | Exits |
| --- | --- | --- | --- |
| `auth` | GitHub CLI or Copilot signed out, token expired, SSO not authorized | S1, P5 | ask (exact command) |
| `policy` | Feature, model or command blocked by enterprise policy or the step's allow list | S4, B7, X7 | retry by the agent; ask or stop |
| `tooling` | Delivery's own servers or install broken | S2 | stop |
| `network` | Offline, proxy, GitHub outage | S5, S8, P9 | retry, then pending; stop for proxy |
| `capacity` | Rate limit, quota, model unavailable, disk | S9, B14, B16 | retry or pending, then stop |
| `project-env` | Install or check command wrong, dependencies, LFS, submodules, missing secret | S3, B2, B10, B20 | retry, then ask |
| `checks` | Project checks or CI fail, flaky, failing before the task | B1, B8, B17, I3, P1, P8 | retry or back to build, then ask |
| `commit-policy` | Hook rejects, signer locked, secret blocked | B3, B15, B18 | retry; ask; back |
| `result` | Agent result invalid, empty, early end, context exhausted | B4, B5 | retry, then back to plan |
| `liveness` | Hang, timeout, unconfirmed termination, second writer | B6, X1, X4, X5 | retry after confirmed end; else stop |
| `scope` | Edits outside task scope or worktree, user edits clash | B11, B13 | retry; ask; stop |
| `conflict` | Textual or semantic conflict, foreign pushes, target gone | I2, I4, I5, M2 | integrate; ask |
| `review` | Review rounds exhausted, planner or reviewer disagreement | D9, B12, P3 | retry, then ask |
| `gate` | Rule blocks push or merge, required check missing, PR closed | P5, P6, P10, M3, M4 | pending; back; ask |
| `state` | Format, unreadable state, preservation unconfirmed | S6, B19, M5 | stop |

### 3.6 Budgets

- **Cause key** = error kind + step kind + subject, where the subject is normalized: the check
  command id, the missing item's name, the sorted conflict paths, the hook id, the comment thread
  id. The task id is not part of the key, so a cause survives re-planning and fix tasks (D10).
- **Retries per cause: 3**, counted on `retry` and `back`. The fourth occurrence becomes `ask` with
  a genuine choice (revise requirement, narrow scope, pause), or `stop` when no choice exists.
- **Review rounds: 2** per task, brief and plan; the third set of findings becomes `ask` with both
  positions summarized. **Flakes: 1** rerun per check and head.
- **Re-plans: 3** per Change from any cause; the fourth becomes `ask`: narrow the brief or split.
- **Premise change resets a cause's count:** profile version changes (`project-env`), brief version
  changes (plan-level and review causes), the task's scope changes in a new plan version (that
  task's causes), an answered question whose effect is observed (that cause), observed recovery
  (`network`, `capacity`). An answer whose effect is not observed resets nothing. Target moves,
  new commits and fresh sessions never reset a count.

### 3.7 Walkthroughs

**Connected traces** (journey §3.6):

| Trace | Path through the model | Status text at the hardest point |
| --- | --- | --- |
| Session disconnects while its worker writes; a second window continues | Chat closing does not touch the runner. If the host dies, the next host (the second window's) finds the lock with live PIDs: it cancels and kills the recorded PIDs, verifies them gone, then build retries with the kept diff (`liveness`); an unverifiable PID is a stop | "Build 2/5 · not running: waiting for process 4242 (copilot) to end" |
| User merges an older PR head while newer local commits exist | Any step's entry sees the PR merged; the active runner is ended first; cleanup preserves the 2 unmerged commits on a private branch and reports them | "Done · merged PR #14 · 2 unmerged commits kept on owlbear/kept/login-1" |
| Required workflow never triggers | follow pending until the expected-start window ends; back to build with a fix task (trigger paths); same cause again → ask the owner's exact action; then pending; 3 observations → stop. Gate never downgraded | "Publish · waiting for you: approve the workflow run for PR #14 in GitHub" |
| Same missing prerequisite survives a re-plan and an answer | `project-env:TEST_API_KEY` counts 1 (build ask), 2 (retry after an unobserved answer), 3 (back to plan); next occurrence → ask with scope choice | "Build 3/5 · waiting for you: TEST_API_KEY is still not visible to the task — set it, drop AC-3, or pause?" |
| Intent changes during a task, and again after a merge was submitted | First: hold, task finishes, back to shape with kept and dropped work, ask re-approval. Second: merge outcome observed first; merged → Done and the new intent starts a new Change; queued → ask: let it merge or remove it and revise | "Merge · waiting for you: PR #14 is in the merge queue — let it merge, or remove it and revise?" |
| Consent on head A, integration makes head B, then merge | merge entry compares the PR head with the consent SHA; mismatch voids consent and asks with the delta; the merge call carries the consent SHA as GitHub's head guard | "Merge · waiting for you: approve merging b7e2a91, changed since a1c3f02 (merged main, 1 conflict resolved)" |

**Common catalogue rows:**

| Row | Path | Status text |
| --- | --- | --- |
| S1 | Readiness or push fails `auth` → ask with exact command → effect observed → step re-enters | "Publish · waiting for you: run `gh auth refresh` and authorize SSO for acme" |
| S2 | Host start fails `tooling` → stop | "Not running · stopped: Delivery tools failed to start · run setup repair" |
| S3 | build retries `project-env` 3 times → ask: correct the command (new profile version), re-detect, pause | "Build 1/4 · waiting for you: `npm ci` fails in packages/web — correct the install command?" |
| D1 | shape ask with split options | "Shape · waiting for you: split into 2 Changes as proposed?" |
| D2 | Designer asks in chat, one question at a time; shape pending on chat | "Shape · draft v1 saved 3 min ago · continue in chat" |
| D3 | Reviewer finding → shape retry → criterion rewritten | "Shape · revising the brief: AC-2 is not checkable (round 1 of 2)" |
| D4 | build `result` exhausted → back to plan to split | "Plan · re-planning: task 3 does not fit one session" |
| B1 | build retry ×3 on `checks:web-test` → ask | "Build 2/5 · retrying: checks failed in web (2 of 3)" |
| B2 | Engine creates worktree; Builder runs the profile install; failure is S3 | "Build 1/5 · implementing: parser · builder active 12 s ago" |
| B3 | build retry: stage hook fixes, re-run checks | "Build 2/5 · retrying: pre-commit rejected the commit (1 of 3)" |
| B4 | Engine finds no commit → retry in a fresh session with the diff | "Build 2/5 · retrying: worker ended without a commit (1 of 3)" |
| B6 | Step timeout → cancel, verify PIDs → retry; unverified → stop | "Build 2/5 · stopped: process 911 (vite) would not end · end it" |
| B7 | Unlisted command denied at once; Builder adapts or asks | "Build 2/5 · implementing: parser · last denied: docker compose up" |
| I1 | Before publish: integrate, clean; covered files unchanged → publish | "Publish · updated with main" |
| P1 | follow back → build fix task from CI log | "Build · fixing lint: 3 errors in api.ts" |
| P2 | follow pending | "Publish · waiting for CI: 2 of 5 checks running (checked 1 min ago)" |
| P3 | follow back → fix task per thread; dispute → ask | "Build · fixing review comment: rename `cfg`" |
| H1 | check pending, no timeout | "Check · waiting for you: log in on staging and see the banner" |
| M1 | Entry observes PR merged → cleanup | "Done · merged PR #14" |
| X1 | Host gone; on next start observe, then resume | "Build 2/5 · not running: Delivery is not started" |
| X3 | Next start observes; moved target handled by integrate before publish | "Build 4/5 · starting: export" |

**Rows that did not fit, and the smallest fix:**

| Row | Misfit | Fix |
| --- | --- | --- |
| S3 | "Back to the profile" names no step | ask with a "correct the command" option that writes a new profile version; that version resets the cause |
| S8, P9 | "Then stop offline" needs no user action, so a stop has no real action | Become pending on the host's network probe after 3 retries |
| B7 | "Waiting for you to allow a command" cannot occur: unattended requests are denied at once (P5) | Record and show the last denial; a blocking denial becomes the Builder's ask |
| H3 | "Ask again" is a person action, not a decision | pending again on the check, naming what changed |
| I1 | The journey gives no trigger for integration | integrate before publish, before merge, and on I4, I6, M2 |
| X1 | "Nothing, if the runtime continues in the background" | Runners are host children; whether they survive VS Code quitting is open (D4) |

## 4. Recommendation, Confidence, and Limits

**Recommendation:** adopt the ten step kinds, the exit table, the status function and the fifteen
error kinds as the M3 status contract, with the six row fixes above folded into the journey
catalogue. No new user touchpoint was needed.

**Confidence:** high that every C row and trace reaches a defined step and a status line. Medium for
the budget values and poll intervals, which are first settings. Medium for liveness: it rests on
P4b's cancel-and-verify while the runtime lives and on recorded PIDs after a crash.

**Open questions for D4:** host lifetime when VS Code quits or sleeps (a folder-open task); one
host per project with two windows open; recording task PIDs and start times from SDK events;
shape's reviewer in chat or as a runner; queuing answers that arrive during active work and sending
them as the resumed session's message (P2d); the state location; whether a `sha`-guarded merge with
readback replaces `effect_launcher`; GitHub polling cost across several Changes.

**Limits:** a walkthrough, not a run. M4 must show answer → runner → resume with the original
runner gone, and merging under branch protection.
