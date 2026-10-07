# Delivery Status Model Rethink

> **Owning task:** none yet — design input for a future Delivery and Cockpit status redesign
> **Date:** 2026-10-07 (revision 3: two independent GPT-6.1 Sol plan challenges; decisions R1–R6 taken
> under the user's explicit delegation)
> **Question:** Which status concepts does Delivery expose for a Change, which are wrong, missing,
> overlapping or instructions in disguise, and what single model should Delivery project so Cockpit
> can show one truthful answer to "where is this Change and who or what is it waiting on"?

## 1. Context and Question

After approving a merge in Cockpit, the user saw, at the same time:

- action feedback: "GitHub accepted the merge request and is merging; Delivery records the result shortly."
- readiness header: "Needs your decision" · "Blocked" · "Checks: Passed" · "Next: You"
- publication section: "Awaiting merge in GitHub" · "Needs your decision" · "GitHub has not confirmed
  this merge. It may still run. Check the PR in GitHub: merge it there, Check again, or Pause or Abandon
  the Change." · button "Check again"
- an always-present "Change maintenance" block offering "Merge latest target into Change"

None of these is a status the user can act on with confidence. The request is to step back and
analyse the status model top-down (lifecycle) and bottom-up (fields and labels), not to re-word labels.

## 2. Sources Studied

| Source | Fact used |
| --- | --- |
| `serve/delivery/src/owlbear_delivery/work_items.py` | Enums `WorkItemNeed`, `WorkItemAttention`, `WorkItemNextActor`, `WorkItemActivityState`, `WorkItemStage`, `WorkItemPublicationPhase`, `WorkItemChangeLifecycle`, `DeliveryProgress`; `DeliveryReadiness` (L376–410); `_MERGE_PROGRESS` (L642–651); `derive_delivery_progress` (L675–740); readiness overlay and fallback copy (L790–890); `_awaiting_merge_state` (L1330–1353) |
| `serve/delivery/src/owlbear_delivery/application_readiness.py` | `_merge_attempt_readiness` (L2423–2461): unsettled merge is "unknown" when the observe-acceptance retry episode has `stop_code = acceptance-wait`; `_with_merge_attempt_readiness` (L2463–2486): unknown → `status=blocked`, `next_actor=YOU`; target-sync reasons (L1525–1540); `_card_readiness` (L1946–2010) |
| `serve/delivery/src/owlbear_delivery/portfolio_application.py` | Background acceptance reconciliation (L428–500) uses `explicit=False`; episode key (L716–722) is finalization head + target head + finalization id |
| `serve/delivery/src/owlbear_delivery/recovery.py` | `acceptance_observations = 3` (L756); automatic reservation refused once the episode stops (L1391–1398) |
| `serve/delivery/src/owlbear_delivery/application_merge.py` | Merge attempt settled from the request response (L146) and again inside acceptance reads (L157–205) |
| `serve/delivery/src/owlbear_delivery/merge_offer.py` | Sync is required only when the proof target is missing; a moved target stays offerable (L192–194, U3 amended 2026-10-07) |
| `serve/delivery/src/owlbear_delivery/checkpoint_supervisor.py` | Existing background loop in the MCP server; reconciles pending checkpoints only |
| `serve/cockpit/web/src/hooks/useWorkItems.ts` | Acceptance reconciliation runs from the Work view every 30 s while visible (L94–106) |
| `.owlbear/research/delivery-n05-plan.md` §1.13, U3 | Recorded contract: unsettled merge is unknown once the acceptance episode stops; target freshness policy |
| `.owlbear/research/delivery-interface-usage-audit-2026-09-11.md` L426–440, L528 | Recorded decision: acceptance batch runs through Cockpit's 30 s loop |
| `serve/cockpit/web/src/components/workItemPresentation.ts` | Status, progress, reason, actor label tables; `workItemStatus` precedence (L387–427) |
| `serve/cockpit/web/src/components/WorkItemDetail.tsx` | `ReadinessSection` renders progress chip, status chip, checks and next actor side by side (L1169–1205); `TargetSyncSection` visibility and copy (L1791–1815) |
| `serve/cockpit/web/src/hooks/useWorkItems.ts` | Merge approval feedback copy, `pending` (L878) |
| `.owlbear/research/delivery-n09-plan.md` §1.3–1.6 | Invariants I1 (progress has one owner, in Delivery) and I4 (projection, never persisted); "Run prompt in Copilot Chat" rationale |
| Live state `.owlbear/delivery/runtime/changes/cockpit-abandon-without-publication/` | Observe-acceptance episode stopped (3 observations, last 18:06:24Z); merge released 18:56:27Z; attempt `merged` and completion recorded 19:17:05Z after the merge moved `dev` and a new episode started |

## 3. Analysis

### 3.1 What Delivery exposes today

A single Change card carries at least eleven status-like dimensions, most of which Cockpit renders:

| Dimension | Values | Rendered as |
| --- | --- | --- |
| `stage` | design, planning, implementation, completed | stage/progress bar |
| `publication_phase` | finalization-invalidated, review-repair, ready-for-finalization, checkpoint-pending, pull-request-draft, awaiting-merge, acceptance-observed, deferred, abandoned | publication heading ("Awaiting merge in GitHub") |
| change `lifecycle` | in-delivery, finalization, publication, awaiting-merge, acceptance, deferred, abandoned | portfolio grouping |
| `needs` | you, dependency, none | "Needs you" / "Blocked" |
| `attention` (compat) | user, agent, waiting, none | derived from `needs` |
| `next_actor` | you, agent, dependency, none | "Next: You / Agent / Dependency / Nobody" |
| `activity.state` | idle, ready, working | "Claimed" / "Ready" / "Idle" |
| `readiness.status` | ready, running, waiting, blocked, unavailable, complete | second chip ("Blocked") |
| `readiness.reason_code` | 44 values | sentence under the chips |
| `readiness.progress` | 12 values (5 reserved, unused) | first chip ("Needs your decision", "Run prompt in Copilot Chat") |
| `readiness.checks_state` | not-run, failed, passed, unknown | "Checks: Passed" |
| merge attempt / offer / block | intent, released, pending, …; 11 block reasons | merge sentences, approval dialog |

The detail header renders `progress`, `status`, `checks_state` and `next_actor` side by side, and the
publication section repeats the phase and the reason sentence. Each is derived by a different rule,
so nothing guarantees they agree.

### 3.2 Confirmed defects

**D1 — A new merge is classified "unknown" as soon as it is sent (bug, not wording).**
`_merge_attempt_readiness` calls an unsettled merge attempt `merge-response-unknown` when the
observe-acceptance retry episode has stopped. That episode is keyed by finalization and target head,
not by merge attempt. Background acceptance reconciliation polls an awaiting-merge Change and stops
after three "not merged yet" reads, normally long before the user approves. Live evidence: the
episode for `cockpit-abandon-without-publication` stopped at 18:06:24Z; the merge was released at
18:56:27Z and stayed "unknown" for about 20 minutes. The result is `status=blocked`, `next_actor=you` and
`progress=needs-decision` one second after GitHub accepted the request, contradicting the feedback
message rendered next to it. This follows the recorded N05 §1.13 contract, which assumed the episode
starts with the approval; see re-decision R1.

**D2 — Recording the merge depends on coincidence and on Cockpit being open.** The request response
and acceptance reads settle the attempt, but once the episode has stopped, automatic reads are refused
for the same key. The live merge was recorded at 19:17:05Z only because the merge itself moved `dev`,
which changed the episode key. Automatic reads also run only while Cockpit's Work view is open and
visible (recorded in the 2026-09-11 interface audit); see re-decision R2.

**D3 — The headline has no single owner.** The header shows up to four chips built from
`readiness.progress`, `readiness.status`, `checks_state` and `next_actor`, and the publication section
shows `publication_phase` and the reason sentence. The awaiting-merge card defaults to
`needs=you, next_step="Merge pull request in GitHub"`; an ownership correction drops it only when
readiness names another owner. Reason copy also exists twice, in Delivery fallbacks and in Cockpit's
`READINESS_REASON_LABELS`. The N09 invariant I1 ("one owner
for progress") holds for `progress` alone; the screen still shows five other derived opinions.

**D4 — "Blocked" means four different things.** `readiness.status = blocked` is used for an unknown
merge outcome, a contained engine action, unreconciled claim custody and `merge-blocked`. The
frontend fallback also labels `needs = dependency` as "Blocked". Users read "blocked" as "something
is in the way", which is false for a merge that GitHub is still running.

**D5 — "Needs your decision" is used where no decision exists.** `merge-response-unknown`,
`merge-blocked`, an unknown issuer and retry exhaustion all map to `needs-decision`. Only answering a
request and approving a merge are genuine choices. The merge-unknown copy lists five verbs ("merge
it there, Check again, Pause, Abandon") instead of saying what happened and what usually resolves it.

**D6 — "Run prompt in Copilot Chat" is an instruction used as a status, for eight different situations.**
It is emitted for: a ready agent step, `retry-backoff` (which actually means "wait until time T"),
`review-repair`, `target-sync-required`, `worker-stall-wait` (which actually means "wait for cleanup"),
`engine-action-pending` and a gone claim issuer. The label tells the user what to do, not where the
Change is, and in several of these cases running the prompt changes nothing yet.

**D7 — "Next" mixes who acts with what to do.** "Next: Agent, after you run the prompt" really means
"you, then the agent". "Next: Nobody" is shown while GitHub is merging, although GitHub is the actor.
GitHub, CI and Delivery itself (scheduled retries, background checks) are not actors in the model.

**D8 — "Change maintenance" is unconditional and unexplained.** `TargetSyncSection` renders whenever a
publication exists and the Change is not paused, abandoned or accepted. It does not know whether the
target moved, by how much, whether the PR is behind or conflicting, or whether Delivery will sync anyway.
Delivery already requires a sync before finalization (`target-sync-required` when the last sync receipt
does not match the target head), but presents that as "Run prompt in Copilot Chat", not as maintenance.
So the one case where sync is needed is hidden, and the case where it is optional is permanent.

**D9 — Mechanism names leak into the UI.** Labels such as "Checkpoint pending", "Delivery ready state
not recorded", "Publication needs reconciliation", "Automatic attempts", "Stop reason" and the
readiness basis rows describe engine bookkeeping. They are useful diagnostics but not status.

### 3.3 The Change journey as a user experiences it

Top-down, a Change goes through these phases. Each phase has a clear "done" event:

| Phase | Ends when | Who usually acts |
| --- | --- | --- |
| Design | Design approved and admitted | You + Designer agent |
| Planning | Task chain published | Planner agent |
| Building | All tasks reviewed | Builder agents |
| Finalizing | Exact head finalized, PR published and ready | Finalizer agent + Delivery |
| Review and merge | PR merged into target | You (approve) + GitHub (checks, merge) |
| Done | Acceptance recorded, worktree cleaned | Delivery |

Side states that can apply in any phase: Paused, Abandoned.

At any moment, inside a phase, the Change is in exactly one *situation*. The user needs to know which
one and, if it is their turn, what the one useful action is:

| Situation | Meaning | Waiting on | Typical primary action |
| --- | --- | --- | --- |
| With an agent | An agent holds the step (custody); this is not proof the agent is running | Agent | none (show role and since when) |
| Ready for next step | Nothing blocks; the next step needs you to start it in Copilot Chat | You (start) | Copy prompt |
| Your decision | A genuine choice: answer a request, approve design, approve merge | You (choose) | the choice itself |
| Waiting on GitHub | Checks running, mergeability computing, merge running, GitHub unreachable | GitHub | none (show the next automatic check only when one is scheduled) |
| Waiting on Delivery | Delivery owns the next effect and a running host will perform it (e.g. recording a merge) | Delivery | none |
| Waiting on another Outcome or Change | Dependency or capacity | That Outcome or Change | link to it |
| Retrying automatically | An engine-owned retry with a running executor will run at a known time | Delivery | none (show time) |
| Needs attention | Something failed or is unknown and Delivery cannot continue on its own | You (investigate) | the one recovery action, with what happened |
| Pausing / Paused / Abandoned / Done | Draining, user-held or terminal | — | Resume / — |

"Ready for next step" replaces "Run prompt in Copilot Chat". The prompt is the *action* for that
situation; when prompts run automatically later, only the action disappears, the status stays.

### 3.4 Mapping today's reasons to situations

| Current reason or progress | Proposed situation | Change |
| --- | --- | --- |
| `ready` + agent operation, `review-repair`, `target-sync-required` | Ready for next step | split from "Run prompt" bucket; sync is a step, not maintenance |
| `retry-backoff` on an agent step | Ready for next step, eligible at T | split; nothing runs it automatically |
| `retry-backoff` on an engine operation with a running executor | Retrying automatically (time) | split |
| `engine-action-pending` | Ready for next step (resume the exact retained operation) | its `/continue-change` resume prompt stays the action |
| `worker-stall-wait` | Ready for next step, eligible at T when known | settlement happens on the next acquisition; no claim that cleanup is running |
| issuer gone | Ready for next step (resume) | keep |
| `active-custody` | With an agent | name it (today `progress=None`) |
| `design-attention`, decision requests, `merge-approval-required` | Your decision | keep; only real choices |
| action requests | Needs attention (do X) | split from decisions |
| `checks-running`, `merge-checking`, `merge-in-progress`, `provider-unavailable` | Waiting on GitHub | merge `waiting-for-service` here and name the system |
| `publication-wait`, non-executable `checkpoint-pending` | Waiting on GitHub only when a provider read or write is the pending effect; Waiting on Delivery when a running host retries it; otherwise Needs attention | owner from journal and executor evidence, never from the reason alone |
| `merge-response-unknown` | Waiting on GitHub until the merge deadline, then Needs attention ("unconfirmed") | R1 |
| `merge-blocked` (conflicts, behind) | Ready for next step (sync) | not a decision |
| `merge-blocked` (queue, stack, capability, method) | Your decision: merge in GitHub | manual GitHub hand-off stays |
| `merge-blocked` (protection, checks failed, closed, draft, wrong base) | Needs attention, fix in GitHub | not a decision |
| `retry-exhausted`, `retry-containment`, `engine-action-failed/interrupted/blocked/incomplete`, `claim-custody-unreconciled`, `finalization-failed`, contained transitions | Needs attention | single bucket with specific "what happened" |
| `dependency-wait`, capacity | Waiting on another Outcome or Change | name which one |
| deferral / pause drained | Paused | keep; a pause request still draining stays visible as "Pausing" |
| completion | Done | from completion authority, not worktree cleanup |

The mapping applies per scope: Outcome cards, the Change publication card and the Change group each
get a situation. The Change group reuses the existing Change activity selector
(`application_readiness.py` ~L1045), which deliberately lets a runnable sibling Outcome decide the
Change's situation while a completed Outcome stays selected in detail.

### 3.5 Split, merge, remove, create

| Decision | Item | Reason |
| --- | --- | --- |
| Evolve | `readiness.progress` (already the single engine-owned field, N09 I1) into the `situation` vocabulary, always set | single headline owner (D3) without a parallel model |
| Create | `waiting_on`: you, agent, delivery, github, outcome:{id}, change:{id}, none | replaces `next_actor` in the UI and covers GitHub and Delivery (D7) |
| Create | `since` and the existing `next_eligible_at`, set only when known | "waiting" is only honest with a time; never invented |
| Create | `headline` (one plain sentence, owned by Delivery) and one `primary_action` | replaces the reason sentence, `next_step` and duplicated Cockpit copy |
| Create | sync availability: required, optional, unavailable, unnecessary (phase-aware, §3.6) | maintenance follows U3, the pre-finalization prerequisite and owner guards (D8) |
| Create | merge sub-state: requested → merging → merged → recorded, plus refused, unconfirmed-after-deadline | merge is the most visible flow and needs its own clear path |
| Split | `needs-decision` into Your decision and Needs attention | D5 |
| Split | `waiting-for-chat` into Ready for next step, Retrying automatically and With an agent | D6 |
| Merge | `needs`, `next_actor`, `activity.state`, `readiness.status` and `progress` into `situation` + `waiting_on` for display only | D3, D4; acquisition, MCP and orchestration keep reading readiness |
| Merge | `publication_phase` and change `lifecycle` into one phase list (§3.3) | two names for the same axis |
| Remove from status | "Blocked" as a user-facing label | D4; keep as an internal readiness gate if needed |
| Remove from status | checks, attempts, stop reason, basis rows | move to a collapsed "Details" area (D9) |
| Remove | reserved, never-emitted progress keys (`preparing`, `working`, `checking`, `repairing`, `needs-sign-in`) | dead vocabulary |

`readiness` stays the engine's internal eligibility model; the user-facing projection is derived from it
once, in Delivery, which honours N09 I1 and I4.

### 3.6 End-to-end UX consequences

**Portfolio row:** phase (grouping or small label) plus one situation chip, the headline and, only when
it is the user's turn, the primary action. No second chip.

**Detail view, top to bottom:**

1. Headline block: phase · situation chip · `headline` sentence · "waiting on X since T" · next
   automatic check, only when one is scheduled.
2. Primary action, if any, with one sentence on its effect (e.g. "Merges the PR into dev at head abc123;
   cannot be undone").
3. A merge panel during review and merge only: offer, approval, then progress through
   requested → merging → merged → recorded.
4. Maintenance follows sync availability, derived from phase, final readiness, proof target, merge
   block and owner guards:
   - **Required:** before finalization when no sync receipt matches the observed target, or when the
     PR conflicts with or is behind its target. It is the primary next step, not a side panel.
   - **Optional:** after finalization when the target moved past the proof target (U3). "dev has moved
     since this Change was verified. You can merge now, or update it first; updating returns the PR to
     draft and requires finalizing again, and may raise conflicts."
   - **Unavailable:** while a merge is unsettled or custody, repair or attention holds the Change.
   - **Unnecessary:** hidden.
5. Secondary actions (Pause, Abandon, move back) grouped and quiet.
6. Collapsed "Details": readiness reason code, attempts, basis heads, checks, publication identities.

**Merge flow after D1/D2 are fixed:**

| Moment | Situation | Headline |
| --- | --- | --- |
| Offer available | Your decision | "Ready to merge into dev. Approve here or merge in GitHub." |
| Approved, sent | Waiting on GitHub | "GitHub is merging." plus the next automatic check |
| Merge confirmed | Waiting on Delivery | "Merged. Delivery is recording the result." |
| Recorded | Done | "Merged into dev on {date}." |
| Refused | Needs attention | "GitHub refused the merge: {reason}. {one fix}." |
| No confirmation after deadline | Needs attention | "GitHub has not confirmed the merge for 10 min. Open the PR to check." |

### 3.7 Changed decisions

These recorded decisions change under this plan. The user reviewed the options and delegated the
choice on 2026-10-07 ("no strong opinion … pick the best one for the project"); the chosen option is
marked **Decided**. Each remains open to a later explicit re-decision.

| # | Recorded decision (where) | What it decided and why | What changed | Options | Decided |
| --- | --- | --- | --- | --- | --- |
| R1 | Unknown merge (`delivery-n05-plan.md` §1.13) | An unsettled merge is "in progress" until the observe-acceptance episode stops, then "unknown" with actor you; bounds automatic reads. The record does not discuss an episode that stopped before the approval | The episode is keyed by finalization and target, not by approval, and usually stops before it, so a fresh merge is "unknown" at once (D1) | (a) keep; (b) approval-scoped observation through completion recording, "unconfirmed" after a deadline; (c) never "unknown" | **(b)**; the deadline never refuses, cancels or resends a merge |
| R2 | Acceptance batch driven by Cockpit's Work view (`delivery-interface-usage-audit-2026-09-11.md` L426–440, L528) | A frontend 30 s loop with backoff to 5 min calls the batch route; no further rationale recorded | Recording a merge depends on a visible Cockpit tab (D2). The existing `DeliveryCheckpointSupervisor` already runs every 5 s in both the Cockpit and the MCP host | (a) keep; (b) run the batch from the shared supervisor in both hosts with acceptance-specific due, backoff and budget, and remove the frontend schedule; (c) Cockpit host only | **(b)**; Check again stays |
| R3 | Progress vocabulary, incl. "Run prompt in Copilot Chat" (`delivery-n09-plan.md` §1.4, N09-A1) | Twelve keys; the prompt label names the user's action because auto-dispatch was cut | One key covers eight situations and reads as an instruction (D6) | (a) keep; (b) rename labels; (c) situation vocabulary, prompt as the action | **(c)** |
| R4 | Optional progress with D01 fallback (`delivery-n09-plan.md` §1.9 D3, D4) | Non-ordinary states (containment, unavailability) keep readiness status, reason, owner and prompt so Cockpit neither fakes progress nor asks a fake approval question | The fallback and side-by-side chips produce contradictory headers (D3, D4) | (a) keep; (b) always set a situation; those states become Needs attention with their specific reason, no activity claim, no invented question | **(b)** |
| R5 | Merge block mapping (`_MERGE_PROGRESS`, N05-B1) | `merge-blocked` reads "needs decision", except queue, stack, capability and method blocks, which read "ready to merge" (manual GitHub hand-off) | The remaining blocks are fixes or syncs, not choices (D5) | (a) keep; (b) map each remaining block (sync, fix in GitHub, or choose) | **(b)** |
| R6 | Orthogonal visible axes (`cockpit-work-items-redesign-2026-08-08.md` L98–101) | Needs, Activity and Action stay independently visible so one axis does not hide another | Independent visible axes are the contradictory header the user reported (D3) | (a) keep visible axes; (b) one composed situation, headline and action, axes retained in data and shown under Details; (c) headline plus a secondary activity indicator | **(b)** |

Other choices made under the same delegation:

- **Situation names:** With an agent, Ready for next step, Your decision, Waiting on GitHub, Waiting on
  Delivery, Waiting on another Outcome or Change, Retrying automatically, Needs attention, Pausing,
  Paused, Abandoned, Done.
- **Merge deadline:** 10 minutes after `released_at`, then "unconfirmed" (Needs attention) while
  automatic checks continue.
- **Acceptance cadence and budget:** an approval read is due 30 s after the last read, including after
  a provider failure (one PR read per 30 s needs no further backoff); an approval keeps its allowance
  until completion is recorded or 24 h pass from release, after which only Check again reads. Changes
  without an approval keep today's three-read episode, which restarts whenever the target moves.
- **"Retry now" for automatic retries:** not offered; Check again already covers merges.

Kept, not re-opened: U3 amended 2026-10-07 (a moved target stays offerable after finalization);
N09 I1, I2 and I4; N05 Q3 (Pause and Abandon stay available during an unsettled merge; no cancel);
the 2026-09-11 audit's separation of `observe_acceptance` and the batch operation.

## 4. Recommendation, Confidence, and Limits

The route evolves the existing engine-owned progress field instead of adding a parallel projection and
keeps operational readiness untouched. It is not a small change: headline, action, timing, sync
availability and transport still need substantive work.

1. **Merge fix, small PR (R1, R2).** Approval-scoped observation through completion recording; the
   10-minute deadline from `released_at`; the shared supervisor runs the acceptance batch in both
   hosts with the cadence and budget above. The retry ledger's due time dedups reads across the
   supervisor and any remaining frontend calls, so Cockpit's frontend schedule (which also drives the
   provider-outage banner) is removed in step 2 together with "Waiting on GitHub". Proof gates:
   approval after the pre-approval reads are used up still records the merge without Check again;
   failure after the merged attempt is persisted but before completion is recorded, and a host
   restart, still converge; Check again does not reset the allowance; Cockpit-only, MCP-only and both
   hosts with a frozen clock show the intended provider read count; Pause, race detection and one
   request per approval are unchanged.
2. **Status and Cockpit cutover, one change (R3–R6).** Situation for all 44 reasons per scope; the
   Change selector transports the whole bundle (situation, headline, waiting on, action, timing), so
   Cockpit reconstructs nothing; `since` and `next_eligible_at` only when known; sync availability;
   Cockpit rows, detail header, filters, mobile, maintenance and collapsed Details; parity tests, E2E
   label assertions and `setup/operating-owlbear.md`. Proof gates: one synthetic portfolio (completed
   Outcome, runnable sibling, blocked dependent, same-situation siblings with different actions and
   times, action request, draining pause, pending engine action resume, local checkpoint wait, the
   sync matrix and merge states) asserted through HTTP and MCP transport and actions, desktop and
   mobile; reads stay pure; acquisition decisions unchanged; Done follows completion authority.
3. **Remove** only display fields whose consumers are gone: compatibility `attention`, reserved
   progress keys, and Cockpit's duplicated reason copy.

Constraints: derived once in Delivery (N09 I1, I4); local chats under the execution plan; Delivery is
not used to implement Delivery.

Limits: source reading, one live Change and two independent challenges (focused existing tests passed:
16, 7 and 24); no screenshots compared and no implementation proof yet. The shared supervisor adds
background GitHub reads for awaiting-merge Changes while either host runs.
