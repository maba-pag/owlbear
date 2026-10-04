# Delivery N09 — Continuation Entry Cutover and Cockpit Entry Surface

> **Package:** N09 of the [execution plan][n09-section].
> **N09-P1 planned N09-A1 and N09-A2** (§1.1–§1.11, §3.2–§3.3). **N09-P2 plans N09-B and N09-C**
> ([§1.12](#112-entry-cutover-contract-n09-p2), §3.4–§3.5) on `origin/dev` `66dcd5da0` (N03-B #368 and
> N04-P #369 merged; N05-B1 on PR #371 and N08-C on PR #370 read from their branches). N09-P2 works in the
> execution plan's [operating context](delivery-redesign-execution-plan.md#19-operating-context).
> **N09-P1 planned on:** `origin/dev` `ef622c354` (N01-A merged; N01-B and N01-C not merged; Python 3.14.8).
> Live controller observed read-only: three Changes, frontier schema 18, no deferral, no active claim.
> **Status:** N09-P1 approved: plan gate `plan-sound` in round 8 of fresh GPT-6.1 Sol challenges (2026-10-03).
> N09-P2 in review; its PR changes no product code.

## 1. Contract

### 1.1 Result

N09-A makes Cockpit's entry surface truthful for the continuation model that D02/D03 already ship,
and gives Pause/Resume the programme's policy semantics. It is split into two phases ([D9](#19-decisions)):

- **N09-A1 — Truthful entry presentation** (no persisted change):
  - Every executable agent step offers **Copy continuation prompt**, which copies the complete
    engine-authored `/continue-change <change-id> …` prompt and says to run it in Copilot Chat.
    No control labelled *Start* copies text, and no copy reports that an agent launched.
  - Delivery projects one programme §4.3 progress description per Work Item and per Change,
    including **Waiting for chat to resume**. The Change value follows the active or next eligible
    outcome, not the first card. **Working**, **Checking** and **Repairing** need dispatch evidence;
    A1 has none, so a held claim shows neutral custody (*Claimed by Builder*). Cockpit renders the
    projection; it computes none of it.
  - **Pause** and **Resume** replace the *Defer Change* label and are offered for every nonterminal
    Change, not only on the publication card. Semantics stay those of the existing defer intent.
  - #218 is verified as already fixed on `dev` and its closure evidence is prepared ([U1](#u-decisions)).
- **N09-A2 — Pause drains active work** (persisted coordination change; after N02-B):
  - Pause while a step holds custody records a durable pause request at once, through a
    custody-neutral path, instead of being refused or waiting for the step. New work is refused;
    the started owner finishes its own effect, receipts, runtime writes, publication and release;
    an unstarted engine action is cancelled without effect; when custody has drained, the request
    becomes the existing deferral (**Paused**). Resume clears either form.

### 1.2 Requirements

| ID | Requirement | Source |
| --- | --- | --- |
| R1 | **Copy continuation prompt** copies a complete prompt and explicitly says to run it in Copilot Chat | Programme §4.2 (`change-continuation-delivery-redesign.md:859`); execution plan §5 N09 (`:1122`); §14.4 *Copilot host integration* (`:1606`) |
| R2 | Never label clipboard copying **Start** or report that an agent launched | §4.2 (`:859`); V17 presentation half (no fake launch) |
| R3 | Show the §4.3 progress descriptions as projections, not a second editable lifecycle stored in Cockpit | §4.3 (`:880`); execution plan `:1124` |
| R4 | Do not say **Working** without evidence of a current dispatch; with no host running say **Waiting for chat to resume**; a retry time does not imply an agent will start | §4.3 (`:882`); §6 (`:997`); §10.3 (`:1215`) |
| R5 | **Pause/Resume** is policy state, not a request to terminate an unknown live process; Pause prevents new work and drains or cancels existing work according to ownership | §4.2 (`:863`); execution plan `:1122-1123` |
| R6 | Settle Pause semantics versus the existing Defer | Execution plan §5 N09 *P must settle* |
| R7 | Memory curation does not block acquisition (#218) | Execution plan `:416`, `:1125`; issue #218 |
| R8 | J03: Cockpit shows current activity beside the last completed result (A1 adds the activity; task evidence and attempt history keep rendering completed work); J08: the same continuation prompt resumes, the user supplies no request or claim IDs | §4.1 J03, J08 |
| R9 | Mandatory companions: every new readiness field, reason, action or status ships with its `workItems.ts` mirror, rendering with a component test and the parity assertion in `tests/test_cockpit_boundary.py`; every new frontier-writing operation joins the central mutability policy | Execution plan §1.4 |
| R10 | Support baseline: Python 3.14; Chromium-only Cockpit (clipboard via `navigator.clipboard`); macOS and Ubuntu | Execution plan §1.1 |
| R11 | LC gate where persisted formats, loading or startup change (A2: full form); never activate against live state | Execution plan §1.3 |

N09-A owns no V-scenario on its own. It supplies the entry surface that V01 (N10) exercises (V17 was
dropped on 2026-10-04), and keeps the D01–D03 regressions (V02–V10, V13) green.

### 1.3 Invariants

- **I1 One owner for progress.** The progress value is derived once, in Delivery, by a pure
  function over the final readiness (after the retry and worker-stall overlays) plus evidence the
  application supplies. MCP, HTTP and Cockpit pass it through; Cockpit only maps keys to labels.
- **I2 Evidence before activity.** `working`, `checking` and `repairing` require evidence that a
  worker was dispatched and is active. A1 has no such evidence: the issuer record is published
  before claim activation and before the launch package returns (`application_acquisition.py:1920-1921`),
  and the window probe only checks that a process exists (`worker_stall.py:121-135`). Claim
  existence, an `alive` issuer window, `activity.state == "working"` or a portfolio claim count
  therefore never produce an active label; a held claim shows neutral custody (M6, M7).
- **I3 Reads never mutate.** Computing progress (issuer liveness, retry episode, execution
  occupancy) reads only; it creates no ledger, receipt or coordination record.
- **I4 Projection, not state.** No progress value is persisted. `DeliveryReadiness` is not embedded
  in any persisted record (probe P5); adding a field changes response schemas only.
- **I5 Copy is honest.** The continuation copy control copies exactly `readiness.prompt`, only when
  that prompt starts with `/continue-change` and this Change's ID followed by a space. Other prompts
  keep their current owners and rendering (N04 `/design`, N08 `/repair-delivery`, `/inspect-change`).
- **I6 Pause never stops a process.** Pause never kills, cancels or settles a running worker or a
  started engine effect. It only refuses new custody and new effects (A2); a started owner finishes
  its own completion, reconciliation, publication and release (§1.11 K2), and the D03 settlement,
  release and recovery routes stay the only ways existing custody ends.
- **I7 Drain is pre-effect and atomic (A2).** A pause request is checked at every custody acquisition
  and effect start, in the same transaction as that start's own marker (§1.11 K3), not only at the
  frontier write that records it. A refused start leaves no partial effect (for example a target merge in the
  worktree without its receipt); a start that wins is a started owner and drains.
- **I8 One paused state.** After drain, the durable paused state is the existing
  `DeliveryChangeDeferral`. The A2 request is transient custody-side state and never coexists with a
  deferral or an abandonment.

### 1.4 Progress projection

New `DeliveryProgress` literal in `work_items.py` (keys) and Cockpit labels (`workItemPresentation.ts`):

| Key | Cockpit label | Emitted from |
| --- | --- | --- |
| `preparing` | Preparing | Reserved; no owner since N06 and N07 were cut (2026-10-04) |
| `working` | Working | Reserved; needs dispatch evidence (G3) |
| `checking` | Checking | Reserved; needs dispatch evidence (G3) |
| `repairing` | Repairing | Reserved; needs dispatch evidence (G3) |
| `needs-decision` | Needs your decision | A1 |
| `needs-sign-in` | Needs your sign-in | Reserved; no owner since N06 and N07 were cut (2026-10-04) |
| `waiting-for-service` | Waiting for service | A1 |
| `waiting-for-change` | Waiting for another Change | A1 |
| `ready-to-merge` | Ready to merge | A1 (N05 may refine, see G8) |
| `completed` | Completed | A1 |
| `paused` | Paused | A1 (deferral); A2 (drained request) |
| `waiting-for-chat` | Waiting for chat to resume | A1 |

Fields: `DeliveryReadiness.progress: DeliveryProgress | None = None` (every card, therefore also
`get_change().readiness`, which stays card-level), plus `ChangeGroupView.progress` and
`WorkItemDetailView.change_progress` (both `DeliveryProgress | None = None`), carrying the Change
activity to the portfolio group and to `get_change().detail` and the Cockpit detail.

Change activity is not the progress of the card `_selected_change_card` (`application_recovery.py:1324`)
picks. That selector returns the containment card, the repair-proposal card, else the publication
card or `cards[0]` (`:1336`); the round-1 challenge's probe saw it pick completed OUT-001 while
OUT-002 was running. It keeps choosing `get_change`'s detail card, so the last completed result stays
presented beside the activity (J03). A new `_change_activity_card` in `application_readiness.py`
chooses the card whose progress is the Change activity (first matching rule wins):

| # | Rule | Change activity |
| --- | --- | --- |
| C1 | Frontier completion, abandonment or deferral | M1–M3: `completed`, none or `paused` |
| C2 | Containment precedence: the card `_selected_change_card` returns for `builder-transition-contained` or a repair proposal | That card's progress |
| C3 | Current ownership: a card with status `running` or reason `engine-action-pending` or `worker-stall-wait` | That card's progress |
| C4 | Next eligible: among `runtime.claimable_outcome_ids()` (`runtime_reads.py:276`), the card first by `_candidates`' key (`_dependency_depth`, then contract outcome index; `application_acquisition.py:1482-1501`); else the first non-`complete` outcome card in projection order (blocked or waiting) | That card's progress |
| C5 | Otherwise | The publication card's progress |

Derivation (first matching row wins; evaluated per card on the final readiness from
`_read_projector`, `application_readiness.py:806-837`, after the overlays at `:828-831`):

| # | Condition | Progress |
| --- | --- | --- |
| M1 | Frontier `change_completion` present, or card status `complete` (a completed outcome) | `completed` |
| M2 | Frontier `change_abandonment` present | none |
| M3 | Frontier `change_deferral` present (A2: or a drained pause request) | `paused` |
| M4 | Reason `worker-stall-wait` (issuing window gone; Delivery settles on a later acquisition) | `waiting-for-chat` |
| M5 | Reason `engine-action-pending` (acquired, not started) | `waiting-for-chat` |
| M6 | Status `running`, reason `active-custody`, from an outcome Planner/Builder claim (its outcome card, or the publication card while that claim is active) | issuer `alive`: none (neutral custody, *Claimed by Planner/Builder*; I2); issuer record missing, window unidentifiable or `unknown`: `needs-decision` |
| M7 | Status `running`, Finalizer writer (publication card) | issuer `alive`: none (neutral custody, *Finalizer attempt held*); otherwise `needs-decision` |
| M8 | Status `running` from a legacy Integration repair claim | none |
| M9 | Reasons `request-action`, `design-attention`, `retry-exhausted`, `settled-attention-target-drift` | `needs-decision` |
| M10 | Publication phase `awaiting-merge`, or reason `acceptance-wait` | `ready-to-merge` |
| M11 | Reasons `publication-wait`, non-executable `checkpoint-pending`; `retry-backoff` on `sync-target`, `mark-ready` or `observe-acceptance` | `waiting-for-service` |
| M12 | Status `ready`, executable, next actor `agent` | `waiting-for-change` when execution occupancy is at capacity (`_execution_occupancy`, `application_readiness.py:1839`); otherwise `waiting-for-chat` |
| M13 | Reasons `retry-backoff` (other operations), `review-repair`, `target-sync-required` | `waiting-for-chat` |
| M14 | Every other reason (containment and unavailability: `retry-containment`, `*-transition-contained`, `engine-action-interrupted/-blocked/-failed/-incomplete`, `claim-custody-unreconciled`, `claim-activation-failed`, `finalization-failed`, `workspace-*`, `*-unavailable`; plus `dependency-wait`, `task-incomplete`) | none |

`none` means the card keeps the D01 rendering: readiness status label, reason and prompt ([D3](#19-decisions)).
M6 and M7 `needs-decision` is the D03 question "was this exact run stopped?", answered through the
existing **Release stuck worker** control or `/release-stuck-worker`; it is not a new approval.

### 1.5 Pause semantics

Status quo (probe P2): `set_change_intent(kind=defer)` (`portfolio_application.py:1214`) records a
`DeliveryChangeDeferral` through `DeliveryRuntime.defer_change` (`delivery_runtime.py:2441`). It is
refused while any outcome claim exists (`:2456`, `_require_no_active_change_claim` at `:6243`), while
Finalizer custody is held (`prepare_runtime_custody_guard`, `change_workspace.py:2601-2627`) and while
an unfinished continuation action holds custody (`require_continuation_access`, `:2062-2071`). Once
deferred, every frontier mutation except resume and abandon is refused (`_require_change_mutable`,
`delivery_runtime.py:6227`), and a deferral cannot coexist with a claim (`:1310-1311`). Cockpit offers
*Defer Change* only on the publication card (`WorkItemDetail.tsx:236`), which exists only once all
outcomes are complete or a checkpoint, disposition, deferral or abandonment is present
(`work_items.py:755-769`). Defer therefore neither drains nor is reachable for in-progress Changes.

Decided semantics:

| User action | Change state | A1 behavior | A2 behavior |
| --- | --- | --- | --- |
| Pause | No custody | Records the deferral → `paused` | Records the request and converts it in the same call when the acquisition and checkpoint locks are free (§1.11 K1, K5) → `paused`; on contention the next drain point converts |
| Pause | Claim, Finalizer attempt or unfinished continuation action held (Change readiness `running` or `engine-action-pending`) | Control disabled with the reason "Pause is available when the current step returns"; a direct MCP or HTTP call is refused as today | Records a pause request through the one admission path (§1.11 K1) and returns before the step ends; new work is refused; card keeps its activity progress with a **Pause requested** badge |
| — | Pause request, custody drains | — | The first of: the draining owner's conversion point (§1.11 K2), the next acquisition for the Change, or the next intent converts the request into the deferral in one transaction (K5) → `paused`. Until converted, the card shows `paused` because no new custody can be created. If the started owner completes the Change (acceptance), the completion transaction clears the request instead → `completed` |
| Pause | Unstarted engine action (`engine-action-pending`, or acquired and past preflight but not started) | Disabled (custody) | Request recorded; executing that action returns `stale` / `readiness-changed` with no started marker and no effect, and releases its custody (§1.11 K3); a direct entry whose start marker would follow the request is refused the same way |
| Pause | Started engine action, direct entry past its start marker, first-checkpoint snapshot past its intent, or standalone publication holding its lease | Disabled | Request recorded; the started owner finishes its effect, receipts, runtime writes, publication and release (§1.11 K2); nothing is stopped (I6) |
| Pause | Blocked or interrupted engine action, contained claim | Disabled | Request recorded and kept until the D03 owner route resolves custody; an issued recovery journal still completes (§1.11 K4); nothing is stopped (I6) |
| Resume | Deferral | Clears it | Same |
| Resume | Pause request | — | Clears the request; nothing else changes |
| Abandon | Any | Unchanged (requires no active claim) | Unchanged; refused while a request's custody is held; an abandonment after drain clears the request in its transaction (I8) |

Engine and MCP intent kinds keep their names (`defer`, `resume`, `abandon`); the MCP description
already says "pause, resume, or abandon". A reason is still required for Pause (the intent model
requires it, `application_models.py:593-611`); Cockpit asks for it inline.

### 1.6 Interfaces and error cases

| Interface | A1 | A2 |
| --- | --- | --- |
| `DeliveryReadiness` (`work_items.py`) | `progress: DeliveryProgress \| None = None` | Unchanged |
| `ChangeGroupView` (`work_items.py`) | `progress: DeliveryProgress \| None = None` (Change activity, C1–C5) | `pause_requested: bool = False` |
| `WorkItemDetailView` (`work_items.py:516`) | `change_progress: DeliveryProgress \| None = None` (Change activity, set by `_captured_detail`) | Unchanged |
| `DeliveryChangeView` (`application_models.py:517`) | Unchanged (`detail.change_progress` carries the Change activity) | `pause_requested: bool = False` |
| `derive_delivery_progress(...)` (new, `work_items.py`, pure) | Inputs: readiness, card, frontier lifecycle facts, issuer state, occupancy-at-capacity flag | Adds the drained-request input |
| Action label for `start-orchestration` (`application_readiness.py:1542`) | `"Copy continuation prompt"`; kind unchanged (renamed only in N09-B) | — |
| `next_step` copy (`work_items.py:859`, `:862`) | "Claimed by Planner/Builder" and "Run the continuation prompt in Copilot Chat" | — |
| `ChangeCoordination` (`change_workspace.py:1427-1430`, after N01-B `workspace_models`) | — | `pause_request: ChangePauseRequest \| None`, omitted when `None`; schema version 1 → 2 under N02's rules |
| `ChangeDirectOperation` (new; `workspace_models.py`) | — | Body of `started.json` and `finished.json` under `action-receipts/direct-<sha256(kind:operation_id)>/` (§1.11 K2): Change, kind (`sync-target`, `mark-ready`), operation ID, request digest; new family, version 1, no migration (§3.3) |
| `PortfolioCoordinator.start_direct_operation` / `finish_direct_operation` (new; `workspace_coordination.py`) | — | Start: one `RuntimeTransaction` commits `started.json` with the coordination bytes as an exact no-op participant after checking they carry no `pause_request` (K3); runs inside the entry's checkpoint lock (K5) and takes no lock of its own. Finish: writes `finished.json` before the entry returns; no pause check (owner drain) |
| `PortfolioCoordinator.record_pause_request` / `clear_pause_request` (new; `workspace_coordination.py`) | — | Admission per §1.11 K1: one `RuntimeTransaction` with the observed frontier bytes as an exact participant; no Change lock; allowed under any custody, including a recovery fence; no effect access |
| `PortfolioCoordinator.recovery_authority_digest` (new; `workspace_coordination.py`) | — | Recovery authority digest of coordination without `pause_request` (§1.11 K4) |
| `set_change_intent` (`portfolio_application.py:1214`) | Unchanged | Every Pause, and Resume of a request, takes §1.11 K1, then converts at once when no owner holds custody and the acquisition and checkpoint locks are free (`blocking=False`); the old defer path is no Pause entry |
| Custody and effect starts: coordinator `acquire` (`:2250`), `acquire_continuation_action` (`:2128`), `start_continuation_action` (`:2173`), `reserve_publication` (`:2629`), `start_direct_operation`; the Design package snapshot intent commit (`snapshot_design_package`, `workspace_snapshots.py:74`); the acceptance retry reservation (`_reserve_acceptance_observation`, `portfolio_application.py:653`); manager custody and direct effect entries (guarded at `:4111`, `:4431`, `:4493`, `:5012`); application-owned provider and publication entries | — | Refuse with `CoordinationConflictError` "Change pause requested", checked in the start's own transaction (§1.11 K3); the application maps it to continuation `waiting` / `change-paused`, portfolio candidate skip, or an engine `stale` / `readiness-changed` result |
| `_require_change_mutable` (`delivery_runtime.py:6214`) and the custody guard it runs beside | — | Mutation classes and drain-authority tokens per §1.11 K2 and K7 |
| `DeliveryChangeIntentResult.receipt` (`application_models.py:613`) | — | Adds `ChangePauseRequest`; MCP `SetChangeIntentResponse` and Cockpit mirrors follow |
| Cockpit HTTP `/api/changes/{id}/defer`, `/resume` (`routes/target_work.py:686`, `:694`) | Unchanged routes; UI labels Pause/Resume | Responses carry the request receipt |

Error cases: issuer record unreadable or mismatched during the read → progress per M6/M7 "unknown"
(`needs-decision`), never an exception from the read path; retry ledger unreadable → the existing
`retry-ledger-unavailable` readiness (M14) wins; occupancy unreadable → `waiting-for-chat` (never
claim a capacity wait without evidence). A2 admission and conversion errors are defined in §1.11 K1
and K5.

A2 direct operations (§1.11 K2, K3, K5):

- Lost race to Pause: the request is present at start, or a coordination conflict re-read shows one →
  `CoordinationConflictError` "Change pause requested"; no marker, fetch, Git write or provider call; the
  entry returns `stale` / `readiness-changed`. A coordination change without a request re-reads and
  retries, bounded by `_OCC_RETRY_LIMIT`.
- Identical replay (same identity and request digest) with `started.json` and no `finished.json`:
  returns the marker without the pause check and rebuilds the owner token (K2); once the request has
  converted, the deferral refuses the replay until Resume (K5).
- Replay after `finished.json`: the entry's existing replay answers (`_replay_target_sync_receipt`, the
  provider's draft-state operation record); no token is granted.
- Same identity, different request digest: conflict before any token; nothing written, no effect.
- `finish_direct_operation` without its matching `started.json`: integrity error, nothing written; a
  repeated finish is a no-op.
- A crash between start and finish leaves an unfinished marker; with the checkpoint lock free it blocks
  no conversion (K5).
- Snapshot start lost to Pause: no intent and no Git write; the reconciler returns not reconciled and
  records no checkpoint failure. A crashed snapshot owner, unlike a marker, blocks conversion until its
  replay publishes the checkpoint, including after re-anchoring and before the lease (K2 handoff, K5).

### 1.7 Existing owners to reuse

- Issuer evidence: `_read_claim_issuer` and the window probe used by `_issuer_stall`
  (`application_recovery.py:700-742`); `WindowHostIdentity` and `ProcessWindowLivenessProbe`
  (`worker_stall.py:87`, `:121`). Used only to choose neutral custody or the D03 `needs-decision`
  (I2). Tests inject `PortfolioApplicationDependencies.window_liveness_probe`.
- Capacity: `_execution_occupancy` (`application_readiness.py:1839`).
- Selection: `_selected_change_card` (`application_recovery.py:1324`) stays the detail-card and
  containment selector; C2 reuses it, and the new `_change_activity_card` lives beside the overlay
  in `application_readiness.py`.
- Prompts: `_engine_action_prompt` (`application_readiness.py:1560-1566`) already authors the
  complete `/continue-change` prompt for executable actions; D03's worker-stall prompt likewise.
- Cockpit: `useCopyToClipboard` (`CopyCommand.tsx:11-40`), `StatusChip`, the existing
  `deferChange` / `resumeChange` hooks (`hooks/useWorkItems.ts:812-823`) and HTTP routes.
- A2: the existing deferral receipt, `set_change_intent` replay rules, `RuntimeTransaction`,
  `_change_intent_custody_participants` (`delivery_runtime.py:6085`) for the one-transaction
  conversion; the exact frontier participant of `acquire_continuation_action`
  (`workspace_coordination.py:337-349`, N01-C layout) for the request commit; the
  `continuation_execution` ContextVar pattern (`:2102-2111`) for drain-authority tokens;
  `complete_change(additional_participants=...)` (`portfolio_application.py:775-780`) for clearing
  the request on completion; settlement receipts, `DeliveryPendingStatePublication` and recovery
  journals as durable drain-authority sources (§1.11 K2); the `start_continuation_action` marker
  layout (`workspace_coordination.py:309-321`, `:368-377`) for direct markers; the acceptance retry
  reservation transaction (`recovery.py:1234-1250`, `:1913-1958`) for its fence; N02-A's family
  registry (`state_formats.py`) and N02-B's registered migrations and `delivery-lc`.

### 1.8 Exclusions

- N09-B/C scope: retiring `/orchestrate` as the normal entry, the capability inventory, routing of
  `finalize-change`, `resolve-delivery-attention`, `resolve-target-conflict`, `address-pr-feedback`,
  `release-stuck-worker` and `inspect-change`, renaming `start-orchestration` / `queued_for_orchestration`
  / portfolio guidance commands (`WorkPortfolioPage.tsx:652-654`), WIRING and operating docs (P22).
- Controls owned elsewhere: **Change requirements** (N04), **Approve merge** (N05); **Help with this step**
  (dropped 2026-10-04 with V17), the Cockpit **Repair Delivery** control (cut with N08-B; `/repair-delivery`
  remains) and **Open in Copilot** (not planned).
- Prompt-file to agent-skill migration of `/continue-change` (input to N09-P2, probe P8).
- New user copy for containment or unavailable states (D3); Abandon placement and semantics.
- Terminating or cancelling any running worker or started effect (I6).

### 1.9 Decisions

Agent-settled with probe evidence:

- **D1 Progress is an engine projection.** A pure `derive_delivery_progress` in `work_items.py`
  plus evidence supplied by `_ReadinessViewsMixin`; exposed on `DeliveryReadiness`,
  `ChangeGroupView` and `WorkItemDetailView`. Rejected: a Cockpit-side mapping from reason codes (cannot see issuer,
  ledger or capacity evidence; would be a second decision owner, against WP1 and I1).
- **D2 One vocabulary, defined here.** All twelve keys exist from A1 so later packages add mapping
  rows, not vocabulary. Five are reserved (`preparing`, `needs-sign-in`, `working`, `checking`,
  `repairing`) and a test asserts A1 never emits them.
- **D3 Non-ordinary states keep D01 rendering.** §4.3 describes "an ordinary card". Containment and
  unavailability have no §4.3 description; mapping them to one would either fake progress or ask a
  fake approval question, which programme §1.1 forbids. They keep the readiness status, reason,
  owner and prompt. No new user copy is invented.
- **D4 Host evidence.** An `alive` issuer window proves only that the VS Code process that
  acquired the claim still exists (P6); the issuer record precedes activation and the launch
  package, so a claim acquired without dispatch (for example from Cockpit) reads the same. A1
  therefore shows neutral custody for an `alive` issuer and keeps D03's recovery semantics for the
  rest: `gone` yields `worker-stall-wait`; missing or `unknown` evidence yields `needs-decision`
  with the D03 release route. Active labels wait for evidence whose boundary shows dispatch (G3).
  Rejected: a new heartbeat or host signal (unnecessary for truthful A1 copy).
- **D5 "Persist waiting for chat" needs no new record.** Programme §6 asks to persist *waiting for
  chat* and the complete prompt. Both are deterministic projections over durable state
  (`readiness.prompt` is engine-authored from the frontier and coordination), so every fresh read
  after a closed chat shows them. No status record is added.
- **D6 Which prompt gets the continuation label.** Only `readiness.prompt` values that start with
  `/continue-change`, this Change's ID and a space render as **Copy continuation prompt**; the table
  row gets a copy button instead of the navigating `ActionLink` (`WorkPortfolioTable.tsx:60-87`) for
  `start-orchestration`. The helper text reads "Run it in Copilot Chat. Copying does not start an
  agent." and the toast "Copied continuation prompt".
- **D7 Pause is the user-facing name of the defer intent.** One durable paused state, the deferral.
  Cockpit offers Pause/Resume at Change level (group header and Change detail) for every
  nonterminal Change. MCP kinds are unchanged to avoid a schema rename with no user benefit.
- **D8 Drain mechanism (A2).** The request lives in `ChangeCoordination`, the owner of custody,
  because custody is host-local and every custody acquisition already reads coordination (P9).
  State publication copies only branch and head fields from coordination (`delivery_state.py:130-135`),
  so the request never reaches a published snapshot. [§1.11](#111-a2-custody-contract) is the one
  A2 custody contract; this decision records only the choice. Rejected: a frontier field (portable
  but forces a frontier and snapshot version cascade for transient host-local state); allowing a
  deferral to coexist with claims (rewrites the meaning of a stored record and the `:1310`
  validator); the existing intent path for any Pause (waits behind or is refused by the custody it
  should drain, and its custody check races owner starts); recovery authority over full
  coordination bytes (a policy write invalidates an issued journal); rehashing issued journals
  (changes immutable intent and evidence identities).
- **D9 Re-split N09-A.** A1 changes no persisted format and edits only `work_items.py` and
  `application_readiness.py` among Delivery core modules. N02-A's application entry names
  `admit_delivery_change` (`portfolio_application.py:890`) and `repair_delivery_state_snapshot`
  (`application_recovery.py:804`), so A1 carries the `get_change` Change activity on
  `WorkItemDetailView` (built by `_captured_detail`, `application_readiness.py:639`) rather than
  editing `portfolio_application.py`, and can run beside N02-A. A2 changes one persisted family
  (coordination v2) and adds one (direct markers, v1, no migration: no records exist before A2);
  after N02-A any schema change needs a version bump and a registered migration (N02 plan I2, D5),
  so A2 adds the prerequisite N02-B (allowed: a package plan may add prerequisites, execution plan
  §4.2). See [1.10](#110-execution-plan-delta). This re-split amends the execution plan's package
  cut, which §1.1 reserves to the user: merged under the user's overnight authorization of
  2026-10-03; confirmed 2026-10-03 (listed to the user without objection).
- **D10 #218 needs no product change.** PR #308 ("Fixes #218", merged 2026-09-07) made curation
  failures non-blocking in `w-orchestration` Step 5 (`share/skills/w-orchestration/SKILL.md:402-420`)
  and Step 6 (`:422`), with ecosystem assertions (`tests/test_agent_ecosystem_validation.py:763-778`,
  `:1181-1186`). The continuation route (`SKILL.md:53-188`) dispatches no curator at all, so it cannot
  block. Whether periodic curation keeps a cadence once `/orchestrate` retires is a capability-inventory
  row for N09-P2, not N09-A work. The issue is still open; the agent closes it with evidence
  ([U1](#u-decisions) (b)).
- **D11 Portfolio guidance stays, minus false claims.** The `/orchestrate` portfolio command and
  guidance kinds remain until N09-B. A1 only replaces the untruthful "An orchestration session is
  already working" (`PortfolioOperatingSummary.tsx:37`) with "N Work Items hold active custody; each
  Change shows its progress" and removes the activity-only "Working" fallback
  (`workItemPresentation.ts:201`, becomes "Claimed").

#### U decisions

**U1 — Close #218 with evidence** (decided 2026-10-03: (b); required before N10-M's programme
closure; nothing in N09-A depends on it). Status quo: #218 is open although PR #308, which says
"Fixes #218", merged into `dev` on 2026-09-07 and its behavior is on `origin/dev` (P1). Problem:
programme completion requires #218 closed with evidence (execution plan §6), and commenting on or
closing an issue is an external action that needs the user. Options: (a) the N09-A1 PR description
carries a drafted closure comment (PR #308, skill lines, test names, the N09-A1 rerun) and the user
posts it and closes the issue; (b) the user authorizes the agent to post and close; (c) leave it
open until N10-M. **Decision (2026-10-03): (b)**, an engineering decision listed to the user without
objection: the agent posts the evidence comment (PR #308, skill lines, test names, the N09-A1 rerun)
and closes #218.

No other genuine user decision was found. Pause semantics are settled by programme §4.2; D1–D11 are
engineering choices inside that contract.

**U2 — Periodic memory curation after `/orchestrate` retires** (N09-P2; open; must be answered before
N09-B starts). *When it applies:* in every long Delivery run. Today `/orchestrate` dispatches the memory
curator after its third completed cycle and every tenth after that, so long portfolio runs turn pending agent
lessons into curated memory automatically; short runs never do. *Problem:* retiring `/orchestrate` removes
that trigger, and a continuation session carries one Change. Options:

- (a) No automatic trigger. Curation runs when the user starts `memory-curator` (`Curate: Periodic curation`);
  Cockpit's Memory tab already lists pending entries, and the docs say when to curate. Pro: smallest change;
  Delivery's normal entry stays free of housekeeping (the #218 class of coupling); matches the documented
  policy that the cadence is opportunistic and the operator invokes the curator (`h-mcp-memory`, curation
  trigger). Con: pending lessons wait until the user remembers. Risk: low; pending entries are invisible to
  recall, so nothing breaks, value is only delayed.
- (b) Move the same cadence into the continuation loop. Pro: keeps today's automatic curation. Con: puts a
  delegate and its failure rules back into the most important workflow; a one-Change session rarely reaches
  cycle 3, so it seldom fires. Risk: low to medium (more text in the continuation contract).
- (c) Cockpit shows the pending count with a copyable curator prompt. Pro: a visible nudge. Con: a Cockpit
  change for a non-Delivery concern.

**Recommendation: (a).** N09-B's editable paths cover (a) and (b); (c) would add Cockpit paths.

D12–D20 ([1.12](#112-entry-cutover-contract-n09-p2)) are planner choices inside the programme contract.

### 1.10 Execution-plan delta

This P phase re-splits N09-A. Execution plan §4.4 says the P phase's PR updates §4.2, the schedule
and the status rows. The N09-P1 PR applies exactly this delta to the execution plan (re-checked
after Sol round 1 against `origin/dev` `ef622c354`; no row changed, since A1 stays inside
`work_items.py` and `application_readiness.py` and A2's new coordinator owner exists after N01-B,
which precedes N01-C):

| Execution plan location | Current | Change to |
| --- | --- | --- |
| §2.6 (`:416`) | `#218 memory-curation coupling → N09` | `#218 memory-curation coupling: fixed on dev by PR #308; N09-A1 records closure evidence (N09 plan U1)` |
| §4.2 (`:513-514`) | `N09-P1 (plans N09-A)`; `N09-A` → `N09-P1, N01-C` | `N09-P1 (plans N09-A1, N09-A2)`; `N09-A1` → `N09-P1, N01-C`; `N09-A2` → `N09-A1, N02-B` |
| §4.2 (`:515`) | `N09-P2` needs `… N09-A` | `… N09-A2` |
| §4.2 mermaid (`:537`, `:541`) | `N09A[N09-A presentation]` | `N09A[N09-A1/A2 presentation + pause]`, plus edge `N02 --> N09A` |
| §4.3 schedule (`:578`) | Lane B stage 2: `N09-A, N03-P, N08-P` | `N09-A1, N03-P, N08-P` |
| §4.3 schedule stage 3 | Lane B: `N05-B … N05-D, N08-A, N08-B` | append `N09-A2` |
| §4.4 (`:634`) | row `N09-A` | rows `N09-A1`, `N09-A2` |
| §5 N09 (`:1125`, `:1139-1140`) | `#218` as open work; one `N09-A` | #218 verified fixed (D10), closure evidence in N09-A1; N09-P1 plans `N09-A1` and `N09-A2`, listed as two phases |

### 1.11 A2 custody contract

This is the only statement of A2 custody rules; §1.5, §1.6, D8 and §3.3 refer to it. Round-3 and round-4
citations are on `origin/dev` `58c4d928b` (N01 complete, P15); round-5 citations are on lane B `f225ad508`
(N02-A; these owners unchanged, P16); round-6 citations are on lane D `0e126b007` (`origin/dev` after N01
and N03-P; publication owners unchanged by N02-A, P17); round-7 citations are in the lane D tree (P18);
earlier ones come from P13–P14. A pause request is policy, not custody: it refuses new custody and
effects, never ends existing custody (I6), and never changes the authority an issued owner, receipt or
recovery journal relies on (K4).

**Why one short path.** The existing intent path cannot admit Pause under custody, and checking for
custody before entering it races owner starts. `set_change_intent` takes the acquisition and checkpoint
locks (`portfolio_application.py:1214-1218`), which an executing engine owner holds for its whole
operation (`application_acquisition.py:760`); `_runtime(for_mutation=True)` refuses recovery,
continuation and Finalizer custody (`portfolio_application.py:1747-1767`); `publication_lock` is
`recovery_lock` plus a continuation-owner check (`workspace_coordination.py:83-101`), held across remote
work by `sync_with_target` (`workspace_target_sync.py:323-421`) and `ChangeBranchPublisher.publish`
(`change_publication.py:156-186`). An owner can acquire or start between a custody observation and
that path's lock entry, so every A2 Pause takes K1.

Reconciled with N02-C (#355, D7): `sync_with_target` now fetches outside the publication and
target-sync locks into a private ref. The direct marker is still committed under the publication lock
after the replay and start checks and before any fetch or ref write; the merge, CAS and coordination
update retake both locks. The checkpoint lock still spans the direct entry to return (K5), so the
K2 row, F4 and F6 hold; P14's "across fetch" citation predates N02-C.

**K1 Admission.** Every Pause, and every Resume of a request, takes these steps.

| Step | Rule |
| --- | --- |
| Validate | Read the runtime without the mutation guard; take no lock. Refuse a terminal Change. A deferral or recorded request with the same reason returns its receipt (existing replay rule); another reason conflicts. Otherwise `expected_frontier_digest` must equal the current frontier digest |
| Record | `record_pause_request` commits one `RuntimeTransaction` (root lock only, `runtime_transaction.py:147-171`): the coordination replacement adding `pause_request`, plus the observed frontier bytes as an exact no-op participant (the `acquire_continuation_action` pattern, `workspace_coordination.py:337-349`). It takes no acquisition, checkpoint, target-sync, publication or recovery lock, skips `require_no_pending_recovery` and continuation access, and gains no effect access |
| Conflict | On `TransactionConflictError`, re-read and revalidate against the caller's original digest. A coordination-only change retries, bounded by `_OCC_RETRY_LIMIT`; a frontier change fails "Change intent frontier changed" and records nothing. The digest is never refreshed |
| Convert at once | If the committed bytes show no K2 owner (claim, writer, Finalizer attempt, unfinished continuation action, unexpired publication lease, recovery fence), the same call tries the acquisition and checkpoint locks with `blocking=False` (`locked_roots`, `storage_io.py:43`; `acquisition_lock`, `workspace_coordination.py:77`, gains the flag), re-reads and converts (K5). The checkpoint lock covers the owners bytes cannot show: direct entries and standalone publications hold it from before their start marker to return (K5). Contention or a new owner returns the request receipt and leaves conversion to the owner's K2 point or the next acquisition or intent (K5). Admission never waits |
| Resume | Clears a request through the same transaction. A deferral resumes through the existing path; no custody coexists with a deferral |
| Abandon | Unchanged: refused while custody is held; after drain, the abandonment transaction clears the request (I8) |

The request is durable before any lock is tried: an owner that starts later is refused by K3, and one
that started earlier is a K2 owner. The old defer path is no Pause entry.

**K2 Owner kinds and drain authority.** A drain-authority token is process-local (the
`continuation_execution` ContextVar pattern) and names the Change, the owner and the permitted
operations. Each entry rebuilds it at call start, before its first write, from durable evidence, or
creates it in the transaction that commits its own start marker (K3), so a restart loses no drain. A
changed envelope, result or request matches no retained receipt and fails as today (for example
`runtime_settlement.py:289-290`) before any token exists. No entry has a blanket bypass: a token permits
only its row's operations, each bound to that owner's own operation identity.

Direct markers: direct sync and mark-ready write no fenced durable evidence before their effect, so A2
adds `start_direct_operation`. It commits `started.json` under `action-receipts/direct-<sha256(kind:operation_id)>/`
(the `start_continuation_action` layout, `workspace_coordination.py:309-321`, `:368-377`) with the coordination
bytes as an exact no-op participant (K3); `finish_direct_operation` adds `finished.json` before return. The
identity pattern is a new N02-A family without migration. A marker is drain and replay evidence, not custody.

Snapshot intents: `_prepare_checkpoint_head` snapshots the package (`application_publication.py:1416`) and
re-anchors the queue (`:1428`) before `_publish_checkpoint_branch` reserves a lease (`:1278`), and the snapshot
commits and advances the reviewed head (`workspace_snapshots.py:122`, `:132-140`). The existing
`design_package_snapshot_intent` is therefore its pause-fenced start evidence (K3); no marker is added.

Snapshot handoff: re-anchoring (`record_design_package_snapshot`, `delivery_runtime.py:678`, `:704`) leaves
no intent, an anchored receipt, no lease and no checkpoint-lock holder until `_publish_checkpoint_branch`
reserves one (`change_publication.py:350`). A crash there, or the finalization-invalidated return
(`application_publication.py:1433-1441`, `:1263-1269`), keeps that state. A2 adds no record; the handoff is:
(a) the coordination `design_package_snapshot` receipt; (b) a pending `first-promoted-task` checkpoint whose
head equals its `snapshot_head` while `published_head` differs (`None` at `:1413`); (c) the unacknowledged
state-publication intent that the re-anchoring `_replace` writes for a portable frontier
(`delivery_runtime.py:2348-2357`, `:2380-2386`). It ends when `record_checkpoint_branch_publication`
records the snapshot head.

Handoff fast path: `ChangeBranchPublisher._publish` returns the stored receipt, with no reservation, when the
remote already has the head (`change_publication.py:344-349`, before `:350`). A crash after the push and
lease release (`:389-390`) but before recording (`application_publication.py:1280`) replays with no lease
token. So, entered from `_reconcile_change_checkpoint` (`:1203`), the handoff token is retained until that
call returns and covers the rest of the call (snapshot row). The publisher is unchanged; a
fast-path reservation was rejected (a coordination write and release on a path that pushes nothing).

| Owner kind | Durable authority source | Allowed under the token | Converts |
| --- | --- | --- | --- |
| Live Planner or Builder claim | The active claim and attempt named by `submit_result` (`portfolio_application.py:1271`), `transition_delivery` (`application_recovery.py:393`), `settle_worker_invocation` (`:425`), `release_stuck_worker` or `_settle_stalled_workers` | Its result, transition or settlement; owner-drain mutations (K7); `_publish_delivery_state` (`portfolio_application.py:1696`) and the reservation its `_publish_checkpoint_branch` makes for the queued checkpoint | After claim removal and publication, in the same call |
| `submit_result`, replayed | The promoted result and its immutable result-candidate receipt, checked by `require_result_replay` (`runtime_settlement.py:221-235`; written by `transition`, `delivery_runtime.py:1952-1962`). From the receipt the token rebuilds the internal `AdvanceDelivery(outcome_id, claim_id, output=receipt.output)` that `transition` hashed (`portfolio_application.py:1314-1322`; `delivery_runtime.py:1935`) and requires its digest to equal the pending `transition_request_digest`; the outer submission is never hashed | `_record_worker_retry_success` for that claim; the bound publication (below) for operation `submit-result-…` (`portfolio_application.py:1282-1306`) | After acknowledgement |
| Worker transition, replayed (successful Planner advance) | The existing exact pending-transition authority: `transition` returns early when `_pending_transition_matches` (`runtime_reads.py:422-431`; `delivery_runtime.py:1941-1943`) holds for the identical request digest; an advance has no planning-retry receipt. The token binds that request digest | Retry success for that claim; the bound publication for operation `transition-…` (`application_recovery.py:403`, `:413-422`) | After acknowledgement |
| Worker settlement, replayed | Planner `planning-retry-receipts` (`runtime_settlement.py:274-291`), Builder invocation or release receipt equal to the replayed envelope, plus `_apply_worker_settlement`'s existing predicate: pending `frontier_digest` current and `transition_request_digest` equal to the envelope digest (`application_recovery.py:475-478`) | The bound publication for operation `…-settlement-…` (`:479-497`) | After acknowledgement |
| Pending publication, standalone | `DeliveryPendingStatePublication` (`runtime_models.py:315`) with `base_frontier_digest` set and `frontier_digest` equal to the current frontier after `_reconcile_pending_state_publication`; entered from acquisition replay (`application_acquisition.py:209`, `:1012`, `:1293`; `application_publication.py:1451-1513`) | The bound publication for operation `replay-state-<frontier_digest>`; the acquisition then returns `waiting` / `change-paused` | After acknowledgement |
| Engine action | `start_continuation_action` returned `True` (marker committed under K3). Entering `continuation_execution` (`application_acquisition.py:767`) before `started.json` (`:789`) grants nothing | Its effect receipt, owner-drain mutations, reservations for its own operation, `finish_continuation_action` | After finish |
| Direct `sync_change_with_target` (`application_publication.py:116`) | Its direct marker for `sync-target:<operation_id>`, committed inside `sync_with_target`'s locks after the receipt replay and start checks (`workspace_target_sync.py:328-331`), before any write or fetch (`:339-360`). The coordination `target_sync_receipt` is written only after the merge (`:398-421`), so it cannot start the owner; an identical replay rebuilds the token from the marker or that receipt (`_replay_target_sync_receipt`, `:328-330`) | Its fetch, `return-draft-<operation_id>` demotion with `clear_ready_for_head_change` (`application_acquisition.py:1715-1771`), merge and coordination update; `record_target_sync` or `capture_target_sync_conflict` and its attention publication (`application_publication.py:147-170`); the merged head's branch reservation, push and `record_checkpoint_branch_publication` (`:1373-1385`); state publication `target-sync-<receipt_id>`; `acknowledge_checkpoint_publication` of that head | After `finish_direct_operation`, before return |
| Direct `mark_change_ready` (`application_publication.py:743`) | Its direct marker for `mark-ready:<operation_id>`, committed after the authority checks (`:754-769`) and before any provider call (`:776`, `:781`). The provider's draft-state operation record precedes `_mutate_draft_state` (`draft_pull_request.py:678-691`) but is a plain atomic write outside the runtime-root transaction: replay evidence, not a fence. An identical replay rebuilds the token from the marker | Required-check reads; provider `mark_ready` for that request (`application_publication.py:776`, `:794`); `mark_awaiting_merge` (`:777`, `:795`); `capture_publication_attention` for its failed required checks (`:796-797`); state publication `ready-<receipt_id>` | After `finish_direct_operation`, before return |
| Direct `observe_acceptance` (`portfolio_application.py:645`) | Its retry-ledger reservation (`_reserve_acceptance_observation`, `:653`, `:666-688`), already reserved "atomically before dispatch/effect entry" by one `RuntimeTransaction` on the shared root (`recovery.py:1234-1250`, `:1913-1958`); K3 adds the coordination fence to that commit. A completed Change's replay (`:649-652`) only publishes | Provider PR and check reads; `capture_acceptance_attention` (`:735`), `latch_merged_pull_request`, `complete_change` with the request-clearing participant; `record_failure` or `record_accepted_progress` for its attempt (`:656-664`); state publication `acceptance-<completion_id>` or its attention publication | Completion clears the request (I8); otherwise after its ledger outcome, before return |
| Standalone publication: `reconcile_change_checkpoint`, `reconcile_pending_checkpoints`, `supersede_publication` (`application_publication.py:1069`, `:1121`, `:497`) | Its `PublicationLease`, committed by `reserve_publication` as a coordination replacement before any push (`workspace_coordination.py:824-867`; `change_publication.py:267`, `:350`); the publication operation record (`change_publication.py:855-880`) is replay evidence only. The lease is released right after the push (`:350-386`), so the token, created with the lease, lives until the call returns | The rest of that call for the same checkpoint head or supersession operation: its push and release, `record_checkpoint_branch_publication`, draft pull-request and summary operations for that head with `record_publication_identity`, `reconcile_finalization_head` and `record_publication_successor` (`application_publication.py:535-544`), `record_checkpoint_failure`, state publication, `acknowledge_checkpoint_publication` | After the call returns; a crashed owner drains when its lease expires (10 minutes, `change_publication.py:40`) and its stored operation replays after Resume |
| First-checkpoint snapshot: `_prepare_checkpoint_head` (`application_publication.py:1394`) for a pending `first-promoted-task` checkpoint with no published head (`:1413`), from `_reconcile_change_checkpoint` (`:1257`) | Before the commit: the coordination `design_package_snapshot_intent` (`workspace_models.py:1492`) committed under K3 before any Git write (`workspace_snapshots.py:103-122`) for operation `_checkpoint_operation_id("package", change, pending head, package_id)` (`application_publication.py:1425`). After it: that operation's `design_package_snapshot` receipt, whose `snapshot_head` is the reviewed head (`workspace_snapshots.py:132-140`), while the pending checkpoint head equals its `previous_head` and differs from its `snapshot_head` (un-anchored). After re-anchoring: the handoff (a)–(c) above; the token binds the receipt's own `operation_id`, `package_id`, `previous_head` and `snapshot_head`, not the package operation recomputed from the anchored head (`:1425`), which only returns that receipt (`workspace_snapshots.py:89-93`) and skips re-anchoring (`application_publication.py:1427`) | Completing that intent's commit and receipt; `record_design_package_snapshot` (`delivery_runtime.py:678`) for that receipt; `reconcile_finalization_head` of its snapshot head (`application_publication.py:1433-1434`); then that checkpoint's publication only: the reservation, push and release for `_checkpoint_operation_id("branch", change, snapshot head)` (`:1278`, `:1351-1374`) and `record_checkpoint_branch_publication`. In the handoff the token grants that publication step, entered from `_reconcile_change_checkpoint` or the standalone pending-publication replay, which pushes the same branch operation (`portfolio_application.py:1709-1712`). Entered from `_reconcile_change_checkpoint`, it is retained until that call returns, past recording, and also grants the rest of that call for the snapshot head (`application_publication.py:1279-1340`): the draft pull-request and summary operations with `record_publication_identity`, state publication `_checkpoint_operation_id("state", change, snapshot head)` and `acknowledge_checkpoint_publication` of that head. It does so whether `publish` reserved a lease (whose token permits the same) or returned the stored receipt (`change_publication.py:344-349`), which repeats no push. The standalone replay continues under its pending-publication token. No other snapshot, package, head or operation | With the lease row, after the call returns |
| Finalizer attempt | The active attempt, or its identical stored finalization (`finalize_change`, `application_lifecycle.py:279`); the attempt and its report or receipt (`settle_finalizer_invocation`, `:519`) | Finalization, `_promote_finalized_external_head` (`application_acquisition.py:1692`), release | After release |
| D03 recovery | A journal intent read by `recovery_id`, evidence passing `verify_evidence`, and `authority_matches` (`recovery.py:192`) against a K4 re-capture, in `_complete_recovery` (`application_recovery.py:1949`); or the stored receipt in `_verified_recovery_replay` | `_readback_recovery_ready`'s read-only `observe_pull_request` (`:2082`), `complete_recovery`, retry release, `record_verified_exclusion`. `recover_claim` (`:1556`) stays allowed: it ends custody (I6) | After `record_verified_exclusion`, inside its held locks |
| Legacy Integration repair claim | None | Completion class only (`remove_integration_repair_claim`) | Next acquisition or intent |

**Bound publication.** Replay tokens fix the pending intent's `base_frontier_digest` and
`transition_request_digest`, not its frontier digest: `_publish_delivery_state` may first push the pending
checkpoint and record it (`portfolio_application.py:1708-1712`), which rewrites the frontier and re-records
the intent under a new frontier digest with both bound digests carried (`delivery_runtime.py:646-676`). The
token permits exactly that bookkeeping: the branch reservation and push for
`_checkpoint_operation_id("branch", change, head)` of the pending head, then `record_checkpoint_branch_publication`.
The fence then moves to the new digest, and the state publication and `acknowledge_pending_publication` of
that digest follow (`portfolio_application.py:1713-1727`; `delivery_runtime.py:230-249`). Bookkeeping that
changes a bound digest, and every other operation, is refused.

**K3 Start serialization.** Every new custody or effect start checks `pause_request` in the same
transaction as its own start marker: coordinator `acquire`, `acquire_continuation_action`,
`start_continuation_action`, `reserve_publication`, `start_direct_operation`, the Design package snapshot
intent commit and the acceptance retry reservation (K2); manager custody and direct effect entries (P9);
application-owned provider and publication entries; Planner claim activation through the custody guard
its frontier write joins. `start_continuation_action` commits `started.json` with no coordination fence
today (`workspace_coordination.py:368-377`); A2 adds the current coordination bytes as an exact no-op
participant after checking they carry no request. CAS starts check the bytes they replace. A Pause commit
and a start commit therefore conflict and exactly one wins, neither taking the other's lock. If Pause
wins, the executor returns `stale` / `readiness-changed`, writes no marker, calls no provider and
releases custody; if the start wins, it is a K2 engine owner.

`snapshot_design_package` commits its intent through `_update`, an exact replacement of the bytes it
reads (`workspace_coordination.py:612`, `:646-648`). A2 refuses an intent-creating replacement
(`workspace_snapshots.py:116`, `:171`) whose replaced bytes carry a request, in that same commit; the
receipt update completing a started intent (`:140`, `:195`) and an identical existing intent are not
checked (K2 owner). If Pause wins, no intent or commit exists and the reconciler returns not reconciled
without `record_checkpoint_failure`. New snapshot work (admission at `portfolio_application.py:918`, or a
first-task snapshot without its intent) stays refused.

**K4 Recovery authority is orthogonal to pause policy.** Today `prepare_recovery_release` requires
`digest(previous)` to equal the journal's `coordination_digest` (`workspace_coordination.py:149`), and
`_complete_recovery` re-captures that digest over full coordination bytes (`application_recovery.py:1865`),
so any request write or clear would refuse an issued journal. A2 changes only the digest, not the CAS:

- `recovery_authority_digest(coordination)` hashes `_model_content` (`workspace_models.py:2075-2077`,
  sorted keys) of the coordination without `pause_request` and with `schema_version` 1. For a record
  without a request this equals its v1 bytes, so journals and preservation receipts issued before or
  after `coordination-1-to-2` verify unchanged. No journal is rehashed; intent, `recovery_id` and
  evidence identities stay as stored, and `authority_matches` is unchanged.
- It replaces the full-byte digest at `_capture_recovery_intent` (`application_recovery.py:1865`),
  `record_recovery_intent` (`workspace_coordination.py:122`), `prepare_recovery_release` (`:149`) and
  preservation capture and verify (`workspace_preservation.py:555`, `:1108`).
- Both coordinator methods still replace the exact current full bytes and carry `pause_request` forward;
  `recovery_coordination_bytes` (`workspace_coordination.py:104`) still returns the full replacement.
- `_complete_recovery` and its ready-effect read-back are completion owners (K2), and the frontier is
  unchanged by a request, so the journal's `frontier_digest` check (`delivery_runtime.py:1728-1729`) holds.

**K5 Conversion.** Drained means the existing `defer_change` preconditions hold, no recovery fence,
unverified exclusion, unexpired publication lease, snapshot intent, un-anchored snapshot receipt or
anchored-but-unpublished snapshot checkpoint (K2 handoff (a) and (b)) remains, and the converter holds
the Change checkpoint lock. Every converter holds that lock (K1 tries it without blocking). (a) and (b)
alone block, so a handoff without (c) never permits conversion; (c) only selects a replay route. Every
direct entry and standalone publication
holds the checkpoint lock from before its start marker to return, exceptional exits and failure recording included
(`_engine_checkpoint_lock`, `application_acquisition.py:975-980`,
at `application_publication.py:129`, `:753`, `:1075` and `portfolio_application.py:648`; the plain lock at
`application_publication.py:1150`, `:507`), so no live direct or lease owner is converted under. An
unfinished direct marker with that lock free is a crashed owner and blocks nothing; its identical replay
runs under its rebuilt token before conversion, or after Resume once converted. A snapshot intent,
un-anchored receipt or handoff instead blocks conversion even with the lock free: its identical replay (the
checkpoint supervisor, `checkpoint_supervisor.py:68`, or the next reconcile; for a handoff also the
acquisition's standalone pending-publication replay) re-anchors if needed, re-enters
`_publish_checkpoint_branch` under its rebuilt token, reserves, pushes and records, or takes the stored
receipt when the remote has the head (K2 handoff fast path), then converts, so no
deferral holds a reviewed head ahead of its queue or its remote branch. A missing worktree fails that replay
(`workspace_snapshots.py:198-211`) and keeps the request; the route is Resume, `recover_change_worktree`,
then the identical snapshot replay. Conversion is
`defer_change` with the request-clearing coordination participant in one transaction, taking reason and
time from the request so a replay yields the same receipt, then the deferral's state publication.
Converting owners: each K2 owner at its point, K1's immediate conversion, the next acquisition and the
next intent. `complete_change` and an abandonment clear the request instead (I8). A failed conversion
leaves the request, which still refuses new custody.

**K6 Lock order and concurrent fields.** The order stays acquisition → checkpoint → target-sync →
publication/recovery → transaction root; `_complete_recovery` follows it. K1 Record takes only the
transaction root and K1 conversion tries its locks without blocking. Locks are fresh-descriptor `flock`s
(`storage_io.py:43-66`), so owner conversions run inside the owner's held locks and never call
`set_change_intent` or a lock-taking coordinator method. Every coordination replacement built from a
captured model (`_update`, `release`, the `prepare_*` participants, `sync_with_target`'s `update`,
`record_recovery_intent`, `prepare_recovery_release`) copies `pause_request` from the bytes it replaces;
a field-only conflict is re-prepared and retried, so Pause never fails or erases an owner's write.

**K7 Mutation classes.** While a request exists, the completion class of `_NORMAL_CHANGE_MUTATIONS`
(`delivery_runtime.py:2222-2266`) is allowed anywhere: `remove_active_claim`, `publish_output`,
`publish_plan`, `publish_result`, `transition`, `settle_planning_retry`, `settle_builder_invocation`,
`_retry`, `complete_recovery`, `publish_recovery_attention`, `remove_integration_repair_claim`,
`finalize_change`, `record_checkpoint_branch_publication`, `acknowledge_checkpoint_publication`,
`record_checkpoint_failure`, `record_publication_identity`, `defer_change`, `resume_change`,
`abandon_change`. The owner-drain class is allowed only inside a matching K2 token: at least
`record_target_sync` and `capture_target_sync_conflict` (`application_publication.py:167`, `:149`),
`mark_awaiting_merge` (`:795`), `capture_publication_attention` (`:797`), `clear_ready_for_head_change`
(`application_acquisition.py:1759-1770`), `reconcile_finalization_head` and `record_publication_successor`
(`application_publication.py:535-544`), `record_design_package_snapshot` (`delivery_runtime.py:678`, `:685`),
`capture_acceptance_attention`, `latch_merged_pull_request` and `complete_change`
(`portfolio_application.py:735`, `:747`, `:775`). Each direct, lease, snapshot or replay token allows
exactly the completion and owner-drain writes its K2 row names. Every other name, every owner-drain call
outside its token, and every reservation or provider entry for another operation is refused. A test
enumerates the registry; an unclassified name fails.

**K8 Falsifiers.** Each row is an assembled test in `test_change_pause.py` with barriers at the named
points; "before release" means the Pause receipt returns while the owner's barrier still holds.

| ID | Inserted interleaving | Required outcome |
| --- | --- | --- |
| F1 | After Pause's Validate and before its Record, an owner acquires or starts an engine action, takes a Finalizer writer, reserves standalone publication (coordination-only) or commits a direct sync, mark-ready, acceptance or snapshot-intent start (K2), then holds | Pause persists before release, retrying with its original digest when coordination bytes changed; each owner drains; conversion after release → `paused`. A direct or snapshot start whose commit follows Pause's is refused before any effect |
| F2 | Same window: a claim activation, Planner publication or completion (frontier write) | "Change intent frontier changed", nothing recorded; a retry with the fresh digest persists before release |
| F3 | Quiescent Pause while another Change's acquisition holds the acquisition lock | Request receipt returns before release; card `paused`; the next drain point converts; request and deferral never coexist |
| F4 | `ChangeBranchPublisher.publish` and `sync_with_target` held inside the publication lock; an engine owner inside its checkpoint lock | Pause through MCP and Cockpit persists before release; the owner's later coordination write keeps the request |
| F5 | Pause between `_engine_action_preflight` and `start_continuation_action` | No `started.json`, no provider or Git call, `stale` / `readiness-changed`, custody released |
| F6 | Hold, engine and direct form each: `mark-ready` inside the provider's `mark_ready`; `sync-target` after the merge, before `record_target_sync`; `observe-acceptance` that completes the Change. Hold a standalone `reconcile_change_checkpoint` inside its push with the lease held. Hold production first-task checkpoint reconciliation after the snapshot commit (`workspace_snapshots.py:122`), before `record_design_package_snapshot`. Admit Pause, then release. Exceptional unwind: a bulk `reconcile_pending_checkpoints` whose push raises, with a K1 conversion waiting on the checkpoint lock. Repeat the direct sync, direct mark-ready, snapshot and standalone holds with a crash at the hold, restart and identical replay. Snapshot handoff: crash right after `record_design_package_snapshot` (`application_publication.py:1428`), before the lease reservation; restart with Pause present; race K1 conversion and the next intent against the supervisor's reconciliation and the acquisition's pending-publication replay. Handoff fast path: production `reconcile_change_checkpoint` crashed right after the push and lease release (`change_publication.py:389-390`), before `record_checkpoint_branch_publication` (`application_publication.py:1280`); restart with Pause present; replay it; during the replay attempt a target sync, `mark_ready` and another head's reservation | Receipts, runtime writes, branch and state publication, marker finish or lease release complete, then `paused`; acceptance ends `completed` with the request cleared. The snapshot owner re-anchors, reserves, pushes and records its branch, and the call's draft, state publication and acknowledgement finish before conversion; reviewed, pending and published heads agree. The bulk failure is recorded before the checkpoint lock is released and conversion follows it. After a crash the marker, `target_sync_receipt`, snapshot intent or un-anchored receipt rebuilds the token and a replay before conversion records and publishes (a snapshot blocks conversion until then); a crashed lease converts at expiry and replays after Resume. In the handoff every conversion attempt is refused until the replay returns the stored receipt, reserves, pushes and records the snapshot head; then it converts → `paused` with reviewed, pending and published heads equal. On the handoff fast path the replay takes the stored receipt (no reservation, no second push), records the branch, and finishes the draft, summary, state publication and acknowledgement under the retained handoff token; conversion then yields `paused`, and the unrelated operations are refused with no effect. Under the handoff token another snapshot, package, head or branch operation, a target sync or `mark_ready` is refused |
| F7 | Retain a `clean-claim` recovery intent; Pause; complete with the original verified evidence. Repeat for `ready-readback`; repeat with Resume clearing the request before completion; repeat with a preservation receipt verified after Pause | Receipt, release and conversion → `paused`; the read-back succeeds; with Resume the recovery completes and no deferral exists; preservation verifies |
| F8 | Records generated by production calls, then crash, restart, Pause and identical replay: a Planner and a Builder settlement after receipt, before `_publish_delivery_state`; `submit_result` after `transition` promotes the result and queues its checkpoint, before the push; a successful Planner `transition_delivery` advance crashed after `record_checkpoint_branch_publication`, before state publication; standalone acquisition replay | Each replay pushes or reuses the checkpoint, publishes, acknowledges and converts → `paused`; the fence moves only through the bound bookkeeping. A changed envelope, result, claim or advance output fails as today with no publication; a pending intent whose transition digest differs is not this owner's; under each replay token a target sync, `mark_ready` or another operation's reservation is refused |
| F9 | Owner-drain mutations from an unrelated direct call, for another Change, owner or operation, or inside `continuation_execution` before `started.json`; a direct, lease, snapshot or replay token used for another operation identity; a snapshot token used for another snapshot, package or head | Refused with no partial effect |
| F10 | Crash after Record and before conversion; crash after conversion and before publication | Restart shows the request or the deferral, never both (I8); tokens rebuild from K2 sources |

### 1.12 Entry cutover contract (N09-P2)

**Result.**

- `/continue-change <change-id>` is the one normal execution entry. `/ideate` and `/design` keep semantic
  approval, and Design's admission output names the continuation prompt (J02).
- `/orchestrate` is retired: its prompt is deleted, and `w-orchestration` loses the portfolio batch loop, the
  portfolio claim check and the periodic housekeeping ([U2](#u-decisions)). The orchestrator agent keeps only
  what the continuation entry uses. Portfolio monitoring stays in Cockpit and the read tools, and engine
  coordination (readiness, capacity, dependencies, custody) stays in Delivery.
- Every other public prompt and control is normal, exceptional, maintenance or retired as listed in the
  inventory below. A retirement happens only where a tested replacement is named.
- User-facing documentation describes exactly that surface (P22).

| ID | Requirement | Source |
| --- | --- | --- |
| R12 | `/continue-change` is the normal entry; `/orchestrate` is retired as a normal entry; portfolio monitoring and engine coordination are retained | Programme §1.1 R1, §6, WP7 steps 1–2; execution plan §5 N09 |
| R13 | Every public prompt and control is classified, and each retirement has demonstrated replacement proof | WP7 risk; execution plan §5 N09 *P must settle* |
| R14 | No old public alias remains as an alternative path after cutover | WP7 step 2 |
| R15 | Design admission returns the complete continuation prompt | Programme §4.1 J02 |
| R16 | The continuation entry names `/repair-delivery` when Delivery MCP is unavailable | [N08 plan](delivery-n08-plan.md) G9 |
| R17 | WIRING, operating guide, setup guides and READMEs match the shipped entries and labels | P22; programme §6 completion ("Documentation matches shipped behavior") |
| R18 | Periodic memory curation is settled once `/orchestrate` retires | D10; [U2](#u-decisions) |

#### Capability inventory

Prompts (`share/prompts/`) and agents. *Engine-authored* means Delivery or Cockpit writes the command into a
readiness prompt, card action or diagnostic (P20).

| Entry | Normal capabilities | Exceptional capabilities | Disposition | Replacement proof, or why it stays |
| --- | --- | --- | --- | --- |
| `/ideate`, `/design` | Discover, design, approve, admit | `/design` resumes a Design return and, from N04, a requirement change | Normal | Unchanged; admission output adds the continuation prompt (R15) |
| `/continue-change` | One Change: Planner and Builder launches, issued finalization, the engine actions `reconcile-checkpoint`, `sync-target`, `mark-ready` and `observe-acceptance`, worker settlement and transition routing, `resume-design` handoff, merge-offer pointer (N05-C) | Per-Change claim check and stopped-worker release; engine-authored repair proposal → `repairer`; reports engine-authored exceptional prompts unchanged | **Normal**, the only execution entry | D02; `test_continuation_plans_builds_and_finalizes_via_existing_result_routes`, `test_continuation_publishes_syncs_finalizes_and_observes_acceptance`, `test_continuation_reenters_finalization_with_new_exact_attempt_after_invalidation` (P19) |
| `/orchestrate` | Portfolio batch (`acquire_actions`) and dispatch across Changes; settlement and transition routing | Portfolio claim check; repair-proposal routing; `recover_claim` and `recover_integration_repair_claim` on acquisition failures; health hint; periodic memory curation; quiescence report | **Retired** (prompt deleted) | Batch dispatch → one `/continue-change` chat per Change; capacity and dependencies stay engine-enforced across sessions (programme §5.2, `_execution_occupancy`). Monitoring → Cockpit portfolio view, guidance and N09-A1 progress; `list_changes`, `get_change`. Claim check → the continuation check, Cockpit **Release stuck worker**, engine `worker-host-lost`. Settlement, transition and repairer routing → kept in `w-orchestration` for continuation. `recover_claim` → Cockpit **Recover claim**, `/resolve-delivery-attention` (it refuses without host exclusion anyway). `recover_integration_repair_claim` → `/resolve-delivery-attention`. Health hint → `get_change` availability, Cockpit health panel, `/repair-delivery`. Curation → U2. Quiescence → Cockpit portfolio |
| `/finalize-change` | Finalize one exact reviewed head | Fallback that continuation names when its host cannot dispatch Finalizer (`host-capability-unavailable`); `/address-pr-feedback` start-mode handoff | **Exceptional**: kept, removed from normal surfaces (D16) | Normal path → continuation's issued finalization (tests above). Not retired: no full host run of nested Finalizer and `build-reviewer` dispatch under `/continue-change` (G11) |
| `/resolve-target-conflict` | — | Engine-authored for a preserved target-sync conflict and for a PR with merge conflicts | **Exceptional**; handoff becomes `/continue-change <change-id>` (D15) | Continuation then finalizes and publishes (tests above) |
| `/address-pr-feedback` | — | User-initiated after external review: `start` (prepare review repair, one commit per thread), `resume` (publish, reply, resolve); engine-authored on the review-repair card | **Exceptional**, user-initiated (D16) | External review arrives outside Delivery's loop; N05-D owns its continuity (#225) |
| `/resolve-delivery-attention` | — | Engine-authored for typed dispositions and health diagnostics; external-head adoption and promotion, publication-baseline recovery, legacy Integration repair claim recovery | **Exceptional** (kept) | Its own retirement condition (prompt header) is not demonstrated; N09 does not re-audit it |
| `/release-stuck-worker` | — | Release one user-confirmed stopped worker | **Retired** (prompt deleted, D18) | Cockpit **Release stuck worker** (`test_http_release_stuck_worker_*`, `WorkPortfolio.part1.test.tsx`, `e2e/work-portfolio.spec.ts`) and the continuation claim check, both through the same guarded `release_stuck_worker` (`test_registered_release_stuck_worker_*`). No engine-authored text names the prompt (P20) |
| `/inspect-change` | — | Read-only diagnosis; engine-authored for `retry-exhausted`, `settled-attention-target-drift`, a retained Design-return handoff and unavailable readiness | **Exceptional** (kept) | Engine-authored and read-only |
| `/repair-delivery` | — | Offline diagnosis and fenced repair while Delivery is unusable | **Maintenance** (kept) | Programme §11.1; N08-A. N09-B adds the continuation pointer (R16) |
| `/upgrade-delivery` | — | Controller upgrade and state migration | **Maintenance** (kept) | N02-D, N08-C |
| Other prompts (`test-curation`, `kb-*`, `*-audit`, `architecture-review`) | Non-Delivery work | — | Unchanged | Outside N09 |
| Agent `orchestrator` | Continuation controller | — | Kept; persona, tools and delegates trimmed (D14) | — |
| Agents `finalizer`, `memory-curator` (user-invocable) | — | `/finalize-change`; manual curation | Kept | D16; U2 |

Cockpit controls (P21):

| Control | Disposition |
| --- | --- |
| **Copy continuation prompt**, **Pause**/**Resume** (N09-A1, A2); answer request, clear block; **Approve merge** (N05-C), **Change requirements** (N04-C) | Normal |
| Engine-action buttons (publish checkpoint, synchronize target, make PR ready, check merge status) through Cockpit's HTTP routes (`…/continuation/acquire`, `…/execute`, `…/publication/ready`, `…/acceptance/observe`) | Normal: the same engine owners continuation uses |
| **Release stuck worker**, **Recover claim**, **Adopt changed PR head**, attention resolution, abandon, move backward; health panel naming `/resolve-delivery-attention` | Exceptional, kept |
| Card copy command `/finalize-change` on a ready-to-finalize or invalidated publication card | **Removed**: duplicates the continuation prompt the same card already offers (I10) |
| Portfolio guidance `start-orchestration` and `work-underway` copying `/orchestrate` | **Replaced** by text pointing to each Change's **Copy continuation prompt**; no command (D17) |
| **Repair Delivery** (cut with N08-B), **Help with this step** (dropped with V17), **Open in Copilot** (not planned) | Not built |

#### Invariants (N09-B, N09-C)

- **I9 Retire only by replacement.** Every retired capability maps to a row above whose replacement exists and
  is tested. After N09-B no shipped prompt, skill, agent, engine-authored text or Cockpit copy names a retired
  entry (N09-B grep gate).
- **I10 One offered entry per step.** A card offers the continuation prompt or one exceptional command, never
  both for the same step (programme §4.3 item 4).
- **I11 No new routing machinery.** N09-B adds no Delivery operation, readiness reason, action kind, persisted
  record or MCP tool. It edits text, removes command strings and changes Cockpit guidance copy.
- **I12 Engine coordination unchanged.** Readiness, capacity, dependency and custody owners are not edited.

#### Decisions (planner, 2026-10-04)

- **D12 Retire `/orchestrate` entirely.** It is not kept as an exceptional portfolio entry: R1 and WP7 step 2
  ask for no alternative path, and every capability has a replacement above. Several chats, one per Change, are
  the developer's normal concurrency; engine capacity governs them.
- **D13 Keep `acquire_actions` and the guidance wire names.** The MCP tool `acquire_actions` stays registered
  for engine coordination (R1), tests and disposable rehearsals, granted to no shipped agent and behind the same
  engine fences. `start-orchestration` and `queued_for_orchestration` keep their identifiers: the user-visible
  label is already **Copy continuation prompt**, and a rename would touch Python, TypeScript, HTTP models and
  parity tests with no user-visible effect.
- **D14 Keep the agent name `orchestrator`.** Programme §6 permits a rename but does not require it; the name is
  the memory identity and is pinned by WIRING and tests. N09-B rewrites the description, persona and output to
  the continuation controller and keeps only tools and delegates the remaining text uses (expected removals:
  `list_changes`, `acquire_actions`, `recover_claim`, `recover_integration_repair_claim`, and `memory-curator`
  under U2 (a)).
- **D15 `/resolve-target-conflict` stays explicit.** An internal handler would add continuation dispatch for a
  rare step that may need the user's judgment; programme §7.3 allows either. Its handoff becomes
  `/continue-change <change-id>`, because continuation finalizes after a resolved conflict (P19).
- **D16 `/finalize-change` stays exceptional.** Normal surfaces drop it: Cockpit card commands, Cockpit copy
  ("run `/finalize-change` again"), the target-conflict handoff and the docs' normal path.
  `/address-pr-feedback` keeps its finalize-only handoff, because continuation would also publish and mark the
  PR ready before the `resume` replies (`w-address-pr-feedback` Steps 5–6, P23). The N05 plan §1.7 names
  `/address-pr-feedback` retirement as N09-B work; N09-P2 keeps it, since external review is user-initiated.
- **D17 Cockpit portfolio guidance.** `start-orchestration` reads "Copy the continuation prompt of each ready
  Change" with the count; neither it nor `work-underway` offers a command. `resume-design` and
  `create-change` are unchanged.
- **D18 Retire `/release-stuck-worker`.** The Cockpit control and the continuation claim check call the same
  guarded operation and are tested (inventory row).
- **D19 No prompt-file migration of `/continue-change`.** Prompt files work with the Local agent today
  (N09-P1 P8); no replacement host binding has been shown. N10-H exercises the copied prompt in the real host;
  a future host change is an ordinary PR (G2).
- **D20 Phase boundary.** N09-B owns every agent-facing and product surface (prompts, skills, agents, WIRING,
  engine-authored text, Cockpit, tests), so each removal ships with its companions. N09-C owns user-facing
  prose (operating, setup and sharing guides, READMEs) as the P22 audit after N09-B, N05 and N08-C have
  merged. Until N09-C merges, user-facing docs on `dev` may still name `/orchestrate`; consumers receive docs
  only through the manually dispatched `sync-to-main`.

## 2. Feasibility Probes

All probes ran on `ef622c354` in the lane worktree, read-only, plus read-only reads of live state and
GitHub. Scratch: `.owlbear/scratch/n09p1/` (unversioned). The shared VS Code terminal interleaved
other lanes' output, so every result was redirected to a file and read back.

| ID | Executed | Result | Premise settled |
| --- | --- | --- | --- |
| P1 | GitHub read of #218 and PR #308; `git log -S` on the skill; `pytest tests/test_agent_ecosystem_validation.py -k housekeeping` | #218 open, no comments; PR #308 merged 2026-09-07 into `dev`, body "Fixes #218"; commit `f6f51c7f7`; Step 5 says "record a non-blocking housekeeping failure … continue with the next acquisition cycle"; test 1 passed | #218 is already fixed; execution plan `:416`/`:1125` premise is false (D10, U1) |
| P2 | Source read of defer/resume paths; `pytest serve/delivery/tests/test_delivery_runtime.py -k "change_deferral_rejects_active_claims or change_deferral_retains_frontier"` | Both tests passed (`..`); the session teardown was then interrupted by a SIGINT from the shared terminal (exit 130 after results). Defer refuses claims, Finalizer custody and continuation custody; deferral freezes all but resume/abandon | Defer does not drain (R5 gap); A2 needed (1.5) |
| P3 | Source read `WorkItemDetail.tsx:232-330`, `work_items.py:755-769`, `:919-955`; `pytest serve/delivery/tests/test_work_items.py -k deferred_change_projects_paused`; `pytest serve/delivery/tests/test_portfolio_application.py -k test_portfolio_keeps_deferred_change_visible_without_orchestration_queue` | 1 passed, 1 passed. The lifecycle section renders only on the publication card, which an in-progress Change lacks | Pause is unreachable for in-progress Changes today (D7) |
| P4 | Source read of labels and prompts | `"Start Orchestration"` (`application_readiness.py:1542`); `"Ready for Orchestration"` (`work_items.py:862`); "already working" (`PortfolioOperatingSummary.tsx:37`); activity fallback "Working" (`workItemPresentation.ts:201`); readiness prompt shown in a `<pre>` without copy (`WorkItemDetail.tsx:879-906`); `CopyCommand` labels "Copy command …" (`CopyCommand.tsx:42-85`); executable actions already carry a complete `/continue-change` prompt (`application_readiness.py:1560-1566`) | R1/R2/R4 gaps are presentation-only; no new prompt authoring needed |
| P5 | `git grep` of `DeliveryReadiness` and `WorkItemCardView` in the persisted owners (`delivery_state`, `delivery_runtime`, `recovery`, `finalization_reports`, `change_workspace`, `acceptance`, `draft_pull_request`, `change_publication`, `worker_stall`); read `DeliveryEngineActionResult` (`application_models.py:1164-1186`) | 0 hits; engine results embed no readiness. `probe_facts.py`: `DeliveryReadiness` has `extra="forbid"` | A1 changes response schemas only, not persisted formats (I4); LC not applicable to A1 |
| P6 | `probe_facts.py`: `WindowHostIdentity.capture()` and `ProcessWindowLivenessProbe` from a lane terminal | Captured `Code Helper` (VS Code helper process), state `alive` | Issuer evidence is window-level, not chat-level (D4, G1) |
| P7 | `probe_facts.py` read-only over live `runtime/changes/*/frontier.json` | 3 frontiers, schema 18; no deferral, abandonment or completion; no active claim; stages implementation, completed, planning | No live pause or deferral state to migrate; A2's LC full form has no live request case (G7) |
| P8 | VS Code prompt-file documentation (edited 2026-09-30) | Prompt files are deprecated for Agent Host sessions and still work with the Local agent, which "will be removed in a future release"; extra text after a slash command is passed to the model; `${input:…}` relies on model inference | `/continue-change` copy works today; its future host binding is an N09-P2 inventory risk (G2) |
| P9 | Source read of custody acquisition and lock use | Custody is created at `ChangeWorkspaceManager.acquire` (`:2250`), `acquire_continuation_action` (`:2128`, CAS on the frontier digest), `reserve_publication` (`:2629`) and `activate_claim` after writer acquisition (`application_acquisition.py:1786-1840`); direct effects check writers at `change_workspace.py:4111`, `:4431`, `:4493`, `:5012`; 16 frontier-writer call sites already call `_require_no_active_change_claim` (`delivery_runtime.py:2456-5690`); the execute path runs `_engine_action_preflight` before `start_continuation_action` (`application_acquisition.py:779-796`) | Pre-effect gates (I7) and the K7 classification are feasible at existing chokepoints; inventory proof is A2's first step (G4) |
| P10 | Source read of the readiness composition | Overlays run at `application_readiness.py:828-831`; `_with_retry_readiness` returns early for `running` (`:1055-1056`), so running cards carry no attempt data | `repairing` would need an explicit `episode_for_attempt` lookup; moot after round 1 (D4: active labels reserved) |
| P11 | Source read of capacity handling | Capacity waits exist only as continuation results `waiting`/`execution-capacity` (`application_acquisition.py:384-388`, `:542-546`), not as readiness reasons; `_execution_occupancy` lives in `_ReadinessViewsMixin` | M12 can project `waiting-for-change` without a new reason |
| P12 | `git grep` for changed labels in docs and tests | No doc names "Start Orchestration", "Defer Change" or "Copy continuation"; tests and E2E name `Copy command …` (`e2e/work-portfolio.spec.ts:274-498`, `CopyCommand.test.tsx`) and `start-orchestration` (`test_delivery_state.py:1820-1822`, `test_portfolio_application.py:9685-9686`) | Companion list for A1 (3.2); no doc companion needed |
| P13 | Round-1 source re-read of the five Sol findings | Confirmed: owners record after their effect (`application_publication.py:167`, `:795`; `portfolio_application.py:747`, `:775`); `set_change_intent` takes acquisition and checkpoint locks (`:1216-1218`); the executor holds the checkpoint lock (`application_acquisition.py:760`); `_runtime` and `publication_lock` refuse non-owners (`portfolio_application.py:1756-1767`, `change_workspace.py:1893`); `start_continuation_action` has no coordination fence (`:2173-2182`); `_selected_change_card` falls back to `cards[0]` (`application_recovery.py:1336`); issuer published before activation (`application_acquisition.py:1920-1921`); probe checks existence only (`worker_stall.py:127-135`) | D4, D8, C1–C5 |
| P14 | Round-2 source re-read of the four Sol findings on the N01-C layout (lane B, `1ba931191`); round-2 citations in §1.11 and C4 use these lines | Confirmed: `publication_lock` wraps `recovery_lock` (`workspace_coordination.py:83-91`); `sync_with_target` holds it across fetch, merge and `update` (`workspace_target_sync.py:323-421`); `ChangeBranchPublisher.publish` across its push (`change_publication.py:156-186`); `RuntimeTransaction.commit` locks only its root and conflicts on changed bytes (`runtime_transaction.py:147-171`); locks are fresh-descriptor `flock`s (`storage_io.py:43-66`); `acquire_continuation_action` already binds exact frontier bytes (`workspace_coordination.py:337-349`); `continuation_execution` entered (`application_acquisition.py:767`) before `started.json` (`:789`); `submit_result` publishes state after `transition` (`portfolio_application.py:1271-1329`, `:1696-1710`); `finalize_change` promotes after its receipt (`application_lifecycle.py:339-345`); eligibility is `claimable_outcome_ids` ranked by dependency depth then contract index (`runtime_reads.py:276-301`, `application_acquisition.py:1472-1501`) | §1.11 K1–K3, K6; C4 |
| P15 | Round-3 source re-read of the three Sol findings on `origin/dev` `58c4d928b` (N01 complete; `git show` copies, lane B being mid-edit) | Confirmed: `authority_matches` compares encoded intents including `coordination_digest` (`recovery.py:192-205`); `_capture_recovery_intent` digests full fenced bytes (`application_recovery.py:1865`); `record_recovery_intent` and `prepare_recovery_release` require that digest (`workspace_coordination.py:122`, `:149`); preservation also binds full coordination bytes (`workspace_preservation.py:555`, `:1108`); `_model_content` is sorted-key JSON (`workspace_models.py:2075-2077`); `settle_planning_retry` removes the claim and writes its receipt and pending publication in one transaction (`delivery_runtime.py:2013-2075`); an identical replay returns early (`runtime_settlement.py:274-291`) and `_apply_worker_settlement` then replays publication (`application_recovery.py:475-494`); pending publication binds `transition_request_digest` (`runtime_models.py:315-341`); acquisition replays it (`application_acquisition.py:209`, `:1012`, `:1293`); state publication copies only branch and head fields (`delivery_state.py:130-135`) | K1, K2, K4; the v1→v2 rewrite would also break issued journals without K4's projection |
| P16 | Round-5 source re-read of the Sol finding on lane B `f225ad508` (N02-A; the cited files have no local changes) | Confirmed: `_reconcile_change_checkpoint` prepares the head (`application_publication.py:1257`) before `_publish_checkpoint_branch` (`:1278`); for a first-task checkpoint with no published head (`:1413`), `_prepare_checkpoint_head` calls `snapshot_design_package` (`:1416`) then `record_design_package_snapshot` (`:1428`); the snapshot holds `publication_lock` (`workspace_snapshots.py:87`), persists its intent (`:103-119`), commits (`:122`) and records the receipt with `last_reviewed_commit` advanced (`:132-140`), reserving no lease; `_update` replaces exactly the bytes it reads (`workspace_coordination.py:612`, `:646-648`); `record_design_package_snapshot` is a frontier write under `_require_change_mutable` (`delivery_runtime.py:678-685`); `reconcile_pending_checkpoints` releases its non-blocking checkpoint lock (`application_publication.py:1150-1155`) before its handler calls `record_checkpoint_failure` (`:1167-1185`), unlike `reconcile_change_checkpoint` (`:1075`, `:1089-1119`) | K2 snapshot row, K3, K5, K7, F6; §3.3 exceptional-exit inventory check |
| P17 | Round-6 source re-read of the Sol finding on lane D `0e126b007` (`origin/dev` after N01 and N03-P; publication owners unchanged by N02-A) | Confirmed: `_prepare_checkpoint_head` re-anchors (`application_publication.py:1428`) before `_publish_checkpoint_branch` (`:1278`), whose `publish` reserves the lease (`change_publication.py:267`); the finalization-invalidated return (`application_publication.py:1433-1441`, `:1263-1269`) leaves the queue anchored and unpublished without a crash; re-anchoring is a `_replace` (`delivery_runtime.py:704`) that writes a pending state-publication intent for a portable frontier (`:2348-2357`, `:2380-2386`) and returns early once anchored (`:687-688`); a replay returns the stored receipt for the same package whatever the operation ID (`workspace_snapshots.py:89-93`) and requires the worktree (`:198-211`); `_publish_delivery_state` pushes the pending head under the same branch operation (`portfolio_application.py:1709-1712`); the supervisor replays through `reconcile_pending_checkpoints` (`checkpoint_supervisor.py:68`) | K2 snapshot handoff, K5, F6 |
| P18 | Round-7 source re-read of the Sol finding in the lane D tree (head not re-observed: terminal exit 130) | Confirmed: `ChangeBranchPublisher._publish` returns the stored receipt when the remote has the head (`change_publication.py:344-349`) before `_reserve_publication` (`:350`); the push path releases the lease before returning (`:389-391`); `_reconcile_change_checkpoint` (`application_publication.py:1203`) then records the branch (`:1279-1280`), creates the draft (`:1294-1313`), updates the summary (`:1314-1332`), publishes state (`:1333-1337`) and acknowledges (`:1338-1340`). The round-6 handoff cite `change_publication.py:267` is the supersession reservation; corrected to `:350` | K2 handoff fast path, K5, F6, §3.3 |

N09-P2 probes ran read-only on `66dcd5da0` in lane D, plus `git show` reads of the PR #371 and PR #370
branches. Output went to files under `.owlbear/scratch/` (unversioned) because the shared terminal garbles
foreground output.

| ID | Executed | Result | Premise settled |
| --- | --- | --- | --- |
| P19 | Source read of continuation routing: `acquire_change_action` (`application_acquisition.py:356-396`) and `_card_readiness` / `_engine_action_prompt` (`application_readiness.py:1801-1880`, `:1898-1990`); test names in `serve/delivery/tests/test_portfolio_application.py` | Executable `reconcile-checkpoint`, `sync-target`, `mark-ready`, `observe-acceptance` → engine action; executable `finalize` → issued Finalizer launch; otherwise the next worker launch, or `human`/`waiting`/`unsupported`. An executable publication card's readiness prompt is already `/continue-change`. Tests cover plan → build → finalize, sync → finalize → acceptance, and re-finalization after invalidation (`:1608`, `:5603`, `:5988`) | `/continue-change` already routes every normal step; N09-B needs no routing code (I11); D15, D16 |
| P20 | `git grep` of slash commands in `serve/*/src` and `serve/cockpit/web/src` | Engine-authored: `/continue-change`, `/inspect-change`, `/repair-delivery`, `/design` (`application_readiness.py`, `application_models.py:152`); `/finalize-change` card commands (`work_items.py:1107`, `:1116`; `application_readiness.py:1767`); `/address-pr-feedback` (`work_items.py:1099`, `application_support.py:338`); `/resolve-target-conflict` (`work_items.py:1167`, `:1205`, `:1263`); `/resolve-delivery-attention` (`work_items.py:1344`, `state_repair.py`, Cockpit health panel `WorkPortfolioPage.tsx:461`); `/upgrade-delivery` (`state_repair.py:357`). `/orchestrate` only in Cockpit guidance (`WorkPortfolioPage.tsx:688`). `/release-stuck-worker` nowhere in product source. Cockpit copy names `/finalize-change` at `WorkItemDetail.tsx:1188`, `:1955` | Inventory "engine-authored" column; D16–D18 |
| P21 | `WorkItemActionKind` (`work_items.py:85-103`); Cockpit HTTP routes (`routes/target_work.py:492-779`); release-stuck tests | Cockpit has continuation acquire and execute, answer, clear block, recover claim, release stuck, move backward, ready, observe acceptance, attention resolve, defer/resume, abandon. Release is covered by HTTP (`tests/test_cockpit_work_items.py:962-1242`), Vitest (`WorkPortfolio.part1.test.tsx:940-1100`), E2E (`e2e/work-portfolio.spec.ts:1123-1221`) and MCP (`test_target_server.py:2164-2245`) | Cockpit inventory; D18 |
| P22 | `git grep` for retired entries and portfolio steps in `share/`, docs and tests | Skills: `w-orchestration` (session-start, Steps 1, 5, 6, continuation note), `orchestrator.agent.md`, `h-mcp-memory` (curation trigger), `w-mem-curation` (`:9`, `:57`), `w-target-conflict-resolution` (`:75`, `:91`, `:113`), `h-decision-requests:46` (cites Step 3). Tests: `tests/test_agent_ecosystem_validation.py` pins the orchestrate and release prompts and the portfolio route (`:531-540`, `:679`, `:990-1078`, `:1108`, `:1190`); Cockpit Vitest pins `/orchestrate` guidance (`WorkPortfolio.part1.test.tsx:324-326`) and `/finalize-change` card commands (`CockpitShell.test.tsx:103`, `WorkPortfolio.part2.test.tsx:869-934`, fixtures in parts 2–5); `test_work_items.py:559`, `:647`. No E2E names either command. Docs: `README.md:41-43`, `README-consumer.md:20-30`, `:132-142`, `setup/setup-guide.md:201-221`, `setup/operating-owlbear.md` (`/orchestrate`, `/release-stuck-worker`, `/finalize-change` as normal path), `serve/delivery-mcp/README.md:63` (stale `acquire_frontier_work`) | N09-B and N09-C editable paths |
| P23 | Read `w-address-pr-feedback` Steps 5–6 and `w-design-session` Session Output | `start` hands off to `/finalize-change` and `resume` replies before the ready decision; continuation would also publish and mark ready after finalizing (P19). Admission output names no continuation prompt | D16; R15 |
| P24 | `git show` of the N05 plan (PR #371 branch) §1.7, §3.6, §3.7 and the N08 plan (PR #370 branch) §3.4, G9; their diff stats | N05-C edits `continue-change.prompt.md`, `w-orchestration`, `orchestrator.agent.md`, the operating guide and `README.md`; N05-D edits `w-address-pr-feedback`; N08-C edits the operating, setup and sharing guides and the consumer README. N05 §1.7 assigns `/address-pr-feedback` retirement to N09-B; N08 G9 assigns the MCP-down pointer to N09-B | Prerequisite order (N09-B after N05-D or N05-C and N08-C); D16; R16 |
| P25 | Read `h-mcp-memory` curation trigger, `memory-curator.agent.md`, `memory-audit.prompt.md`, Cockpit `MemoryTab.tsx` | The cadence is "opportunistic, not an eventual-processing SLA"; the operator invokes the curator when needed; pending entries are recall-invisible; `memory-curator` is user-invocable; Cockpit lists pending entries (`MemoryTab.tsx:58`) | U2 options |

Not run in N09-P1 (machine load): Vitest, Cockpit build, E2E, any multi-file suite (G6). N09-P2 ran source
reads only; no test or host run was needed to settle its premises.

## 3. Phases

### 3.1 Shared rules

- Plans name symbols; re-resolve files with `grep` after N01-B and N01-C. Expected homes:
  `ChangeCoordination` → `workspace_models.py`; `PortfolioCoordinator` (`acquire`,
  `acquire_continuation_action`, `start_continuation_action`, `reserve_publication`,
  `recovery_lock`, `publication_lock`, `prepare_runtime_custody_guard`) → `workspace_coordination.py`;
  `ChangeWorkspaceManager` entries → `change_workspace.py` facade or a `workspace_*` mixin;
  `sync_with_target` and adoption entries → `workspace_target_sync.py`;
  `_require_change_mutable` → `runtime_support.py`; `defer_change`/`resume_change` stay in the
  `delivery_runtime.py` facade (N01 I6 writers).
- Opus keeps the progress derivation, host-evidence rules, the A2 gate, conversion and migration.
  Luna may take the `workItems.ts` mirror, label maps, component tests, E2E fixtures and the PR
  closure-comment draft, each with an exact contract (execution plan §1.6).
- Assembled claims use the default loader, `Client(assemble_target_server(...))`, the Cockpit HTTP
  test client and the maintained disposable E2E stack. Fakes sit only below the window-liveness and
  process probes (injected `window_liveness_probe`) and the provider.
- No live Delivery record is created or read through the live controller; LC copies only (A2).

### 3.2 N09-A1 — Truthful entry presentation

- **Prerequisites:** N09-P1, N01-C (execution plan §4.2). A1 edits no module that N02-A lists, so it
  may run beside N02-A under the ready rule.
- **Editable paths:**
  - Delivery core: `serve/delivery/src/owlbear_delivery/work_items.py` (`DeliveryProgress`,
    `derive_delivery_progress`, `DeliveryReadiness.progress`, `ChangeGroupView.progress`,
    `WorkItemDetailView.change_progress`, `_outcome_next` copy at `:859`, `:862`);
    `serve/delivery/src/owlbear_delivery/application_readiness.py` (`_read_projector` progress
    overlay after `:831`, evidence helpers, new `_change_activity_card` and the group and detail
    Change activity, `_captured_detail`, `_captured_action` label at `:1542`). No other Delivery
    core module; `_selected_change_card` is called, not edited.
  - Cockpit web: `serve/cockpit/web/src/api/workItems.ts` (`DeliveryProgress` union, three fields),
    `components/workItemPresentation.ts` (progress labels, status precedence, remove the
    activity-only "Working"), `components/WorkItemDetail.tsx` (`ReadinessSection` progress chip and
    continuation copy control; Change-level Pause/Resume replacing *Defer Change* in
    `ChangeDispositionSection`), `components/WorkPortfolioTable.tsx` (copy button for
    `start-orchestration`, progress chip), `components/CopyCommand.tsx` (labelled variant:
    visible label, helper text, toast), `components/PortfolioOperatingSummary.tsx` (D11 copy),
    `pages/WorkPortfolioPage.tsx` (Change group progress and Pause/Resume placement),
    `hooks/useWorkItems.ts` (Change-level pause/resume wiring, reusing `deferChange`/`resumeChange`).
  - Tests: new `serve/delivery/tests/test_delivery_progress.py`; `serve/delivery/tests/test_work_items.py`;
    `serve/delivery/tests/test_portfolio_application.py` (assembled progress cases; label assertions);
    `serve/delivery/tests/test_delivery_state.py` (only if an asserted label changes);
    `serve/delivery-mcp/tests/test_target_server.py` (`get_change` schema includes `progress` and
    `change_progress`);
    `tests/test_cockpit_work_items.py` (HTTP payloads); `tests/test_cockpit_boundary.py` (new
    `DeliveryProgress` parity test beside `test_delivery_readiness_reason_typescript_parity`);
    `serve/cockpit/web/src/__tests__/WorkPortfolio.test.tsx`, `CopyCommand.test.tsx`;
    `serve/cockpit/web/e2e/work-portfolio.spec.ts`, `e2e/support/api-fixtures.ts`,
    `e2e/support/seed-work-portfolio-delivery.py`.
  - Records: this plan's N09-A1 progress row; the execution plan's N09-A1 status row.
- **Required companions:** TS mirror, rendering with component tests and the parity assertion for
  `DeliveryProgress` (R9); MCP and HTTP schema snapshots if the suites pin them. No new frontier
  writer, so the mutability-policy test is untouched.
- **First discriminating check:** an assembled test acquires a Builder claim through
  `acquire_change_action` and dispatches nothing, with the injected probe reporting the issuing
  window `alive`. The card, group and `get_change().detail.change_progress` show neutral custody
  (null progress, *Claimed by Builder*), never `working`, `checking` or `repairing` (I2, D4).
- **Positive scenarios:**
  - Ready Planning outcome, no claim: card and `get_change` show `waiting-for-chat`; action label
    "Copy continuation prompt"; Cockpit copy button copies exactly `readiness.prompt`
    (`/continue-change <id> …`), shows "Run it in Copilot Chat. Copying does not start an agent."
  - Active Builder or Planner claim, or Finalizer attempt, issuer `alive` → null progress with the
    D01 `running` status and *Claimed by Builder/Planner* or *Finalizer attempt held*.
  - Issuer `gone` and not yet quiet → `worker-stall-wait` → `waiting-for-chat`.
  - Pending engine action → `waiting-for-chat` with the existing resume prompt.
  - Capacity 1 and another Change holds the slot; ready outcome → `waiting-for-change`.
  - Open request → `needs-decision`; exhausted retry → `needs-decision`; awaiting merge →
    `ready-to-merge`; publication wait → `waiting-for-service`; deferral → `paused`; completion →
    `completed`.
  - Change activity (C1–C5): two outcomes, OUT-001 completed. With an OUT-002 claim held, the group
    and `detail.change_progress` show OUT-002's custody, not `completed`; after its result, with
    OUT-002 ready, both show `waiting-for-chat`. `get_change().detail` stays the card
    `_selected_change_card` picks, so the completed result keeps rendering. A contained Builder
    transition still wins (C2). Dependency-first declaration: OUT-001 depends on OUT-002 and is
    declared first; with OUT-002 runnable, the group and `detail.change_progress` show OUT-002's
    `waiting-for-chat`, not OUT-001's null progress; with no outcome claimable, the first
    unfinished card is chosen.
  - Cockpit: Pause/Resume present on an in-progress Change (group header and detail); Pause with a
    reason on a quiescent Change → `paused` and Resume restores; portfolio summary shows the D11 copy.
- **Negative scenarios:**
  - Active claim with issuer record missing or probe `unknown` → `needs-decision` with the Release
    stuck worker control; with issuer `alive`, no active-work label.
  - No card or chip anywhere reads "Working" from `activity.state` alone; no copy control or label
    contains "Start"; no toast or text says an agent started.
  - Every `DeliveryReadinessReason` maps per 1.4; M14 reasons yield `null` and keep the D01 status;
    the five reserved keys are never emitted; an unmapped new reason fails the exhaustive test.
  - Prompts starting with `/repair-delivery`, `/inspect-change` or `/design` are never labelled
    continuation prompts; a `/continue-change` prompt for another Change ID is not either.
  - Retry ledger unreadable → existing `retry-ledger-unavailable` (null progress), no exception;
    occupancy unreadable → `waiting-for-chat`, not `waiting-for-change`.
  - Pause on a Change whose readiness is `running` or `engine-action-pending` is disabled with the
    stated reason; a forced HTTP call still returns the existing refusal and changes nothing.
  - The progress read creates no file: record-tree hash of a disposable portfolio is unchanged
    across `list_work_items`, `get_change` and `/api/work-items`.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_delivery_progress.py -q`, then
  `uv run pytest serve/delivery/tests/test_work_items.py tests/test_cockpit_boundary.py -q`, then
  `npm --prefix serve/cockpit/web test -- WorkPortfolio CopyCommand`.
- **Closeout:** `uv run test --changed`; `npm --prefix serve/cockpit/web test`;
  `npm --prefix serve/cockpit/web run build`; `npm --prefix serve/cockpit/web run test:e2e:work`;
  scoped `uv run ruff check` and `uv run ruff format --check` on changed Python; Biome on changed
  frontend files; `uv run pytest tests/test_cockpit_work_items.py serve/delivery-mcp/tests/test_target_server.py -q`.
  Rerun the P1 housekeeping test and put the U1 closure draft in the PR description.
- **LC:** not applicable: no persisted format, record loading or startup change (P5). If N02-A has
  merged first, its schema-fingerprint test proves no registered family changed.
- **Size / risk:** M / medium (many companions; the risk is a misleading label, caught by the
  exhaustive mapping and negative UI tests).

### 3.3 N09-A2 — Pause drains active work

- **Prerequisites:** N09-A1, N02-B (registered migrations, format marker, `delivery-lc` full form;
  it includes N02-A's registry, which the new marker family joins).
- **Editable paths** (N01/N02 homes in brackets; re-resolve):
  - `ChangeCoordination` and new `ChangePauseRequest` [`workspace_models.py`]; schema version 2. New
    `ChangeDirectOperation` marker model [`workspace_models.py`] (§1.6).
  - `PortfolioCoordinator` [`workspace_coordination.py`, N01-B]: new `record_pause_request`,
    `clear_pause_request` (§1.11 K1) and `recovery_authority_digest` with its uses in
    `record_recovery_intent` and `prepare_recovery_release` (K4); new `start_direct_operation` and
    `finish_direct_operation` (K2 direct markers, K3); `acquisition_lock(blocking=)`;
    `pause_request` carry-forward and field-only conflict retry in every replacement K6 lists;
    pause check in the start's own transaction in `acquire`, `acquire_continuation_action`,
    `start_continuation_action` (coordination participant beside `started.json`) and
    `reserve_publication` (K3); the drain-authority token beside `continuation_execution` (K2);
    the request check in `_update` for an intent-creating replacement (K3);
    the request check inside `prepare_runtime_custody_guard`.
  - `workspace_snapshots.py`: `snapshot_design_package` and `_replace_design_package_snapshot` intent commits
    pause-fenced, identical-intent replay and receipt completion as the snapshot owner (K2, K3).
  - `workspace_preservation.py`: preservation capture and verify use `recovery_authority_digest` (K4).
  - `ChangeWorkspaceManager`: delegating `record_pause_request`, `clear_pause_request`; pause
    refusal in its custody entries and pre-effect refusal at the direct effect entries named in P9
    [`change_workspace.py` facade, `workspace_target_sync.py`, and whichever N01-B module holds the
    finalization entry at `change_workspace.py:5012`]; conversion participant.
  - `workspace_target_sync.py`: `sync_with_target` commits the `sync-target` direct marker inside its
    locks after the receipt replay and start checks (`:328-331`), before any write or fetch (K2).
  - `recovery.py`: the acceptance retry reservation commit takes the coordination fence (K3).
  - `_require_change_mutable` classification [`runtime_support.py`]; `DeliveryRuntime.defer_change`
    accepts the request-clearing participant [`delivery_runtime.py` facade].
  - Application: `set_change_intent` one admission path and immediate conversion with non-blocking
    acquisition and checkpoint locks (K1), `submit_result` drain token including its replay branch,
    and post-release conversion, `observe_acceptance` (`:645`) reservation fence and owner token,
    `_observe_acceptance_once` request clearing in its `complete_change` transaction
    [`portfolio_application.py`]; `defer_change`, `resume_change`, `finalize_change` and
    `settle_finalizer_invocation` drain tokens through promotion [`application_lifecycle.py`];
    `_continuation_stop`, portfolio candidate skip, `_engine_action_preflight`,
    `_execute_engine_action` (Pause-won start → `stale`, release), `execute_change_action`
    post-finish conversion, and the acquisition replay sites returning `change-paused` after
    conversion [`application_acquisition.py`]; `sync_change_with_target` (`:116`) and
    `mark_change_ready` (`:743`) direct markers through `start_direct_operation` /
    `finish_direct_operation` and their owner tokens, the publication helpers they call (provider
    entries gated), lease tokens for `reconcile_change_checkpoint` (`:1069`),
    `reconcile_pending_checkpoints` (`:1121`) and `supersede_publication` (`:497`), the first-checkpoint
    snapshot token in `_prepare_checkpoint_head` (`:1394`) and its handoff token through
    `_publish_checkpoint_branch` (`:1278`) and the standalone replay, held by `_reconcile_change_checkpoint`
    (`:1203`) until it returns, across the stored-receipt return of `ChangeBranchPublisher._publish`
    (`change_publication.py:344-349`, not edited), the K5 handoff check (a, b) in
    every conversion, `reconcile_pending_checkpoints`' failure
    recording moved inside its checkpoint lock (`:1150-1155`, `:1167-1185`), and the
    standalone pending-publication replay token (`:1451-1513`) [`application_publication.py`];
    `transition_delivery`, `settle_worker_invocation`, `release_stuck_worker` drain tokens,
    `_apply_worker_settlement`'s settled-replay token, `_capture_recovery_intent` (K4),
    `_complete_recovery` and `_verified_recovery_replay` recovery tokens and conversion, and
    `_settle_stalled_workers`' post-release conversion [`application_recovery.py`];
    drained-request input to progress and `pause_requested`
    [`application_readiness.py`, `work_items.py`]; `DeliveryChangeIntentResult.receipt`,
    `DeliveryChangeView.pause_requested` [`application_models.py`].
  - Format [N02-A `state_formats.py`, lane B `e6ed5bb31`]: `coordination` kind version 1 → 2 with
    the registered `coordination-1-to-2` rewrite [`state_migration.py`, N02-B]; new kind and family
    `direct_operation` for `runtime/changes/<id>/action-receipts/direct-<sha256>/(started|finished).json`,
    owner `ChangeDirectOperation`, mutability `R`, version 1, no migration (new family, no prior
    records). The `action_receipt` pattern matches only `continue-<digest>`, so the two never overlap.
    `serve/tools/src/owlbear_tools/delivery_diagnostics.py` mirrors both versions.
  - Adapters: `serve/delivery-mcp/src/owlbear_delivery_mcp/target_models.py`
    (`SetChangeIntentResponse` receipt union), `target_server.py` description;
    `serve/cockpit/src/owlbear_cockpit/routes/target_work.py`, `target_models.py` (responses).
  - Cockpit web: `api/workItems.ts`, `components/WorkItemDetail.tsx`, `pages/WorkPortfolioPage.tsx`,
    `hooks/useWorkItems.ts` (enable Pause during custody; **Pause requested** badge).
  - Tests: new `serve/delivery/tests/test_change_pause.py`; `test_change_workspace.py`;
    `test_portfolio_application.py`; `test_delivery_state.py` (default-loader restart);
    `tests/test_delivery_worktree_authority.py` (custody-entry inventory);
    `serve/delivery-mcp/tests/test_target_server.py`; `tests/test_cockpit_work_items.py`;
    `tests/test_cockpit_boundary.py`; `serve/tools/tests/test_delivery_diagnostics.py`;
    `serve/delivery/tests/test_state_formats.py`, `fixtures/state_formats.json` (both families'
    fingerprints and versions) and golden records under `fixtures/state_formats/golden/runtime/`
    (a v2 coordination record; `started.json` and `finished.json` under
    `changes/change-a/action-receipts/direct-<digest>/`); Cockpit component and E2E tests.
  - Docs: `setup/operating-owlbear.md` (Pause semantics row); consistency check of
    `share/skills/w-delivery-attention-resolution/SKILL.md:191` (agent-ecosystem tests if edited).
  - Records: this plan's N09-A2 row; the execution plan's status row.
- **Required companions:** `workItems.ts` mirrors of `pause_requested` and the request receipt with
  component tests and the `test_cockpit_boundary.py` parity assertion (R9); the K7 registry test as
  the mutability-policy companion; registry fixtures and goldens for both families (Tests above); MCP
  and HTTP schema snapshots if the suites pin them.
- **Step 1 (before behavior):** an inventory test that enumerates (a) every public
  `PortfolioCoordinator` method that creates custody or an effect-entry marker, including
  `start_direct_operation`, (b) every public `ChangeWorkspaceManager` method that acquires custody
  or starts a worktree, Git or provider effect, including `snapshot_design_package`, (c) every
  application-owned provider and publication
  entry (draft pull-request publisher calls, checkpoint and target-sync branch publication),
  (d) `_NORMAL_CHANGE_MUTATIONS`, (e) every completion and replay entry and (f) every direct entry
  and standalone publication (§1.11 K2 rows). It fails for any name not classified as pause-gated,
  owner-drain or completion (K7), any (e) entry not mapped to one K2 authority source, any (f) entry
  that does not hold the checkpoint lock from before its marker, snapshot intent, lease or reservation to
  return, exceptional exits included (K5), or a direct entry that returns without
  `finish_direct_operation` (G4). The exceptional-exit check covers every `record_checkpoint_failure`
  and attention capture: `reconcile_pending_checkpoints` today leaves its lock (`application_publication.py:1150-1155`)
  before its handler records the failure (`:1167-1185`), so the check fails until A2 moves the handler inside.
- **Positive scenarios:** F1–F8 and F10 of §1.11 K8; F1 and F6 cover the direct sync, mark-ready and
  acceptance owners, standalone publication, the first-checkpoint snapshot and its pre-lease handoff,
  including its stored-receipt replay,
  F8 the owner-specific
  replay bindings. Also: Pause
  with a running Builder claim → request receipt; the Builder's `submit_result` (or
  ended-without-result settlement) succeeds and the same call converts → `paused`; Resume restores
  the prior stage. Same for a Planner claim, a Finalizer attempt ending in `finalize_change` or
  report-plus-settlement, a host-lost settlement and
  a `release_stuck_worker` release. Pause with a pending engine action → executing it returns
  `stale`/`readiness-changed`, custody released, no effect; the next acquisition converts. Pause on a
  quiescent Change converts in the same call. Resume while draining clears the request and work
  continues. Default-loader restart with a request present keeps it and still refuses new custody.
  Replayed identical Pause returns the same receipt. Builder drain with publication: Pause during a
  Builder claim whose result queues a checkpoint branch publication; `submit_result` publishes the
  result, reserves, pushes and records the branch, releases custody and converts → `paused`; inside
  that token a target sync, adoption or another operation's reservation is refused. A recovery
  journal and a preservation receipt issued on coordination v1 complete after `coordination-1-to-2`.
  A direct sync and a direct mark-ready write `started.json` and `finished.json` that the N02-A scan
  classifies `current` at version 1; a default-loader restart with an unfinished marker loads.
- **Negative scenarios:** F9 of §1.11 K8 (owner-drain writes outside their token, tokens used for
  another operation). While a request exists, `acquire_actions`, `acquire_change_action`
  (`waiting`/`change-paused`), Cockpit continuation acquire, and new calls (no matching marker, lease
  or K2 replay token) of `sync_change_with_target`, `mark_change_ready`, `observe_acceptance`,
  `reconcile_change_checkpoint`, a Design package snapshot without its identical intent, external-head adoption,
  target-conflict resolution,
  `administrative_move` and explicit checkpoint
  each refuse before any effect: Git refs, worktree bytes, frontier and receipts unchanged (hash
  comparison). Pause never signals a process (no settlement or release receipt is created by Pause
  itself); a blocked or interrupted engine action keeps the request and its custody unchanged; Pause
  on a completed or abandoned Change → typed refusal; Abandon while custody is held → refused as
  today; an older (N02-B) release refuses a coordination v2 record with a typed version diagnostic;
  a direct start that loses to Pause writes no marker and returns `stale`/`readiness-changed`; a
  replay with another request digest under the same direct identity conflicts with no effect;
  the inventory test fails when a new custody entry is added unclassified.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_change_pause.py -q`, then
  `uv run pytest serve/delivery/tests/test_change_workspace.py -q -k pause`.
- **Closeout:** `uv run test --changed`; `npm --prefix serve/cockpit/web test`, `run build`,
  `run test:e2e:work`; scoped Ruff and Biome; agent-ecosystem tests if `share/` changed.
- **LC:** full form via `delivery-lc` (N02-B): unmigrated copy refused, `coordination-1-to-2`
  applied and verified, migrated copy loads with every Change available, live hashes unchanged. The
  direct-marker family needs no migration; a live copy has none of its records.
- **Size / risk:** M / high (custody gating on every effect path; crash ordering; first coordination
  format change).

### 3.4 N09-B — Entry cutover

- **Prerequisites:** N09-P2; N05-D (N05-C when N05-D is not built); N08-C (execution plan §4.2). Package
  addition: U2 answered.
- **Editable paths** (re-resolve lines; N05-C, N05-D and N08-C edit some of these files first, P24):
  - Delete `share/prompts/orchestrate.prompt.md` and `share/prompts/release-stuck-worker.prompt.md`.
  - `share/skills/w-orchestration/SKILL.md`: remove Step 1, the portfolio half of the session-start check,
    Step 5 (under U2 (a); under (b) it moves into the continuation section), Step 6, the portfolio output
    and the "`/orchestrate` remains the unchanged portfolio entry" sentence. Keep Steps 2–4 under their
    current headings as the shared dispatch, settlement, release and repair rules the continuation section
    cites, so references such as `h-decision-requests:46` stay valid. Continuation Bindings name
    `/repair-delivery` when Delivery MCP is unavailable or refuses to start (R16).
  - `share/agents/orchestrator.agent.md`: description, argument hint, persona, critical rules, `tools`,
    `agents`, `<agents>` table and output for the continuation controller (D14).
  - `share/skills/w-design-session/SKILL.md`: Session Output gains `- Next: /continue-change <change_id>`
    after admission (R15).
  - `share/skills/w-target-conflict-resolution/SKILL.md` and `share/prompts/resolve-target-conflict.prompt.md`:
    handoff `/continue-change <change-id>` (D15).
  - `share/skills/h-mcp-memory/SKILL.md` (curation trigger) and `share/skills/w-mem-curation/SKILL.md`
    (periodic-mode audience) per U2.
  - `share/WIRING.md`: orchestrator runtime row and paragraph, Prompt Entry Map (remove `orchestrate` and
    `release-stuck-worker`; `continue-change` as the normal entry; `finalize-change` as the exceptional
    fallback), delegation rows for `finalizer` and `memory-curator`.
  - Product: `serve/delivery/src/owlbear_delivery/work_items.py` (no `command` on the two `FINALIZE`
    publication actions) and `application_readiness.py` (`_captured_action` `FINALIZE` without `command`);
    `serve/delivery/tests/test_work_items.py` (`:559`, `:647`) and any assembled assertion of that command.
  - Cockpit web: `pages/WorkPortfolioPage.tsx` (`guidanceCommands`), `components/PortfolioOperatingSummary.tsx`
    (D17 text), `components/WorkItemDetail.tsx` (`:1188`, `:1955`: "run the continuation prompt again");
    `src/CockpitShell.test.tsx`, `src/__tests__/WorkPortfolio.part1.test.tsx`–`part5`, only where an
    assertion depends on a removed command.
  - `tests/test_agent_ecosystem_validation.py`: drop the pins on the deleted prompts and the portfolio route,
    and keep every pin on the continuation section unchanged (P22).
  - Records: this plan's N09-B progress row; the execution plan's status row.
- **Required companions:** none of the §1.4 product companions (I11: no new reason, action, status or
  frontier writer); agent, skill and prompt validators; WIRING in the same phase.
- **First discriminating check:** the grep gate, run before any edit (it lists the hits of P22) and after
  (it must be empty): `git grep -n -E '/(orchestrate|release-stuck-worker)([^-a-z]|$)' -- share serve
  .github ':!**/__tests__/**' ':!**/*.test.tsx'`.
- **Positive scenarios:**
  - The validators (`validate_prompts.py`, `validate_agents.py`, `validate_skills.py`) and the ecosystem
    tests pass with the reduced prompt set; WIRING lists exactly the shipped prompts.
  - A ready-to-finalize or invalidated publication card has no `command`; its readiness prompt is the
    `/continue-change` prompt, which Cockpit renders as **Copy continuation prompt** (I10).
  - Portfolio guidance with queued work shows the D17 text and no copy command.
  - The admission output template names the continuation prompt.
  - Every continuation pin in the ecosystem tests passes unchanged: launch, finalization, engine-action,
    settlement, release and repairer routing are intact.
- **Negative scenarios:**
  - The grep gate is empty, and `/finalize-change` appears only in its prompt, the finalizer agent,
    `w-change-finalization`, the `w-address-pr-feedback` handoff and the continuation fallback text (with
    their WIRING rows).
  - No skill or agent still cites Step 1, 5 or 6 of `w-orchestration`, `acquire_actions` or the
    `list_changes` portfolio check.
  - The orchestrator `tools` keep every continuation binding (`get_change`, `acquire_change_action`,
    `execute_change_action`, `transition_delivery`, `settle_worker_invocation`, `release_stuck_worker`).
  - `acquire_actions` stays registered and its MCP tests pass unchanged (D13).
- **Inner loop:** `uv run pytest tests/test_agent_ecosystem_validation.py -q -n0`; the three validators;
  `uv run pytest serve/delivery/tests/test_work_items.py -q -n0`; `npm --prefix serve/cockpit/web test --
  WorkPortfolio CockpitShell`.
- **Closeout:** `uv run test --changed --base origin/dev`; `npm --prefix serve/cockpit/web test` and
  `run build`; Biome on changed frontend files; scoped Ruff; the grep gate. No E2E: no Cockpit interaction or
  HTTP contract changes and no E2E names a removed command (P22).
- **LC:** not applicable (no persisted format, loading or startup change).
- **Size / risk:** M / medium (many small text edits; the risk is deleting a rule continuation still needs,
  caught by the unchanged continuation pins and the implementation gate).

### 3.5 N09-C — Documentation reconciliation (P22)

- **Prerequisites:** N09-B.
- **Editable paths:** `setup/operating-owlbear.md`, `setup/setup-guide.md`, `setup/sharing-guide.md`,
  `README.md`, `README-consumer.md`, `serve/delivery/README.md`, `serve/delivery-mcp/README.md`,
  `serve/cockpit/README.md`, `share/README.md` (each only where it names an entry, a label or the journey);
  `tests/test_agent_ecosystem_validation.py` only to keep an existing doc pin true; this plan's progress row;
  the execution plan's status row.
- **Contract:**
  - The normal journey reads: `/ideate` or `/design` → admission returns `/continue-change <change-id>` → run
    it in Copilot Chat → Cockpit shows progress, requests, **Pause**/**Resume** and **Approve merge** →
    **Completed**. After an interruption, the same prompt resumes (J08). Several Changes: one chat per Change.
  - One "Exceptional entries" table replaces the scattered prose: `/resolve-target-conflict`,
    `/address-pr-feedback`, `/resolve-delivery-attention`, `/inspect-change`, `/finalize-change` (fallback),
    `/repair-delivery`, `/upgrade-delivery`, each with where it is offered (engine-authored prompt or Cockpit
    control).
  - Remove statements that are false on N09-C's base (`/orchestrate`, `/release-stuck-worker`, the portfolio
    claim check, `/finalize-change` as a normal step, stale tool names such as `acquire_frontier_work`). Keep
    the wording other packages shipped (N04-C, N05-C, N08-C) and author no policy (P22).
- **Positive scenarios:** every `/name` in the edited docs has a `share/prompts/<name>.prompt.md`; every bold
  Cockpit label they quote occurs in `serve/cockpit/web/src`; markdownlint passes on the edited files; the
  ecosystem tests pass.
- **Negative scenarios:** `git grep -n -E '/(orchestrate|release-stuck-worker)([^-a-z]|$)'` over the edited
  docs is empty; no doc presents `/finalize-change` as a normal step or promises **Help with this step**, a
  **Repair Delivery** control, **Open in Copilot** or an always-on agent (programme §6).
- **Inner loop:** the two greps; markdownlint on the edited files.
- **Closeout:** `uv run pytest tests/test_agent_ecosystem_validation.py -q -n0`; markdownlint; `uv run test
  --changed --base origin/dev` (record it if the runner falls back to the full suite for `setup/` paths).
- **LC:** not applicable.
- **Size / risk:** S / low.

## 4. Progress

| Phase | PR | Exact head | Proof | Challenges | Status |
| --- | --- | --- | --- | --- | --- |
| N09-P1 | #351 | — | Probes P1–P18 | Sol round 1: revision-required (drain exceptions, custody-neutral pause admission, pause/start atomicity + coordinator inventory, Change progress selection, liveness evidence) → revised; Sol round 2: revision-required (short pause fence, frontier-bound CAS, completion-call drain authority, eligibility-based C4) → revised; Sol round 3: revision-required (recovery authority vs pause policy, settled-owner replay authority, unified admission) → consolidated A2 custody contract; Sol round 4: revision-required (direct/standalone owner rows, owner-specific replay bindings) → revised; consistency pass (§1.6/§3.3/formats aligned with §1.11); Sol round 5: revision-required (pre-lease snapshot drain authority) → revised; Sol round 6: revision-required (anchored pre-lease snapshot handoff) → revised; Sol round 7: revision-required (fast-path handoff lease) → revised; Sol round 8: `plan-sound` | approved (D9 re-split confirmed 2026-10-03; U1 decided (b) 2026-10-03) |
| N09-A1 | #354 | `3573866ac` | First check `test_undispatched_builder_claim_with_live_issuer_shows_neutral_custody` fails on base (`progress` missing), passes after; `test_delivery_progress.py` 66 passed; `test_work_items.py` + MCP progress test 26 passed; HTTP progress/pause 2 passed; Vitest WorkPortfolio + CockpitShell + CopyCommand targeted pass; `npm run build` pass; `test:e2e:work` 26 passed; Ruff and Biome clean on touched files; `test --changed --base origin/dev`: pytest 2552 passed, 1 failed (HTTP wire snapshot lacked `progress`; fixed; `test_cockpit_work_items.py` + `test_cockpit_boundary.py` rerun 122 passed), Vitest 25 files / 345 passed; P1 housekeeping rerun 1 passed. Repair: 26 new Pause cases (12 retained-custody reasons × group/detail, non-custody blocked control, filtered mixed group) — 23 fail on `e3fc1d482` sources, all pass after; WorkPortfolio.test.tsx 165 passed; `npm run build` pass; Biome clean on 3 touched files; `test:e2e:work` 26 passed; `test --changed --base origin/dev --web` Vitest 25 files / 371 passed. Repair 2 (Pause availability derived by Delivery from the defer intent's own refusal predicates, `pause_available`/`pause_unavailable_reason` on group and detail): 10 assembled fixtures assert projection == defer acceptance, read-only (masked Finalizer and every retained claim/engine-action state refused; passive Finalizer attention, reservation-only retry containment and quiescent Change accepted) plus unreadable coordination and unverified recovery; `test_delivery_progress.py` + `test_work_items.py` + `test_cockpit_boundary.py` + `test_cockpit_work_items.py` 226 passed, 1 failed (projector fixture lacked a second binding; fixed, rerun passed); `test_target_server.py` 126 passed; Vitest WorkPortfolio + CopyCommand + AcceptanceReconciliation 166 passed; `npm run build` pass; Biome and Ruff clean on touched files; `test:e2e:work` 26 passed; `test --changed --base origin/dev`: pytest 2566 passed, 1 failed (runtime writer-inventory invariant counted the read-only probe; frontier guards moved to a module-level mirror; invariant + progress rerun 117 passed), rerun EXIT=0, pytest 2567 passed, Vitest 25 files / 360 passed | Sol implementation round 1: repair-required (retained-custody Pause predicate, filtered custody) → repaired; Sol implementation round 2: repair-required (server-derived Pause availability) → repaired; Sol implementation round 3 `implementation-sound` | merged |
| N09-A2 | #357 | `7a2d974b3` (round-2 repair; round-1 product `28a446ff6`, candidate `e0da9da1a`; LC oracle `d512a42e4`) | First check `test_pause_under_builder_drains_result_then_converts_and_resumes` (Pause under a Builder claim → `ChangePauseRequest`, acquisition waits, `submit_result` converts → `paused`, Resume restores). `test_change_pause.py` 21 passed (F1–F6, F9, F10, K4, K6, K7, direct markers, refusals); step-1 inventory + K7 writer-declaration tests in `test_delivery_worktree_authority.py` (64 passed with the pause suite); `test --changed --base origin/dev`: pytest 3087 passed, 2 failed (package-export fixture; LC fixture still seeded coordination v2 and the inspector reported `PENDING_EFFECTS_UNKNOWN` for a v1 coordination record — both fixed; LC + diagnostics + module-structure rerun 282 passed; diagnostics consumers + state migration/formats rerun 276 passed), Vitest 25 files / 361 passed; WorkPortfolio Vitest 155 passed after the Pause-requested updates; `npm run build` pass; Biome and Ruff clean on touched files; `test:e2e:work` 25 passed, 1 failed (`unknown paths render the global Not Found view`, `route.fetch: Test ended` teardown race; isolated rerun `--repeat-each=3` 3 passed). LC full form not run here (lead runs `delivery-lc`). Gap repair: operator new-work entries (both adoptions, promotion, target-conflict abort/resolve, review repair, standalone finalization-head reconciliation, out-of-band and baseline recovery, target-sync publication repair, worktree recovery) start through `_operator_start`, a Pause-fenced coordination commit (`start_pause_fenced`) inside their checkpoint lock, and drain only their own named writes; `_publish_checkpoint_branch` grants a reservation only to owners whose K2 row names the queued checkpoint; standalone reconciliation holds a lease token inert until its own lease commits and a start with no owner under a request returns not reconciled without a failure; snapshot tokens bind the exact snapshot (`_bind_snapshot_owner`) and cover the handoff fast path; a mark-ready replay after `finished.json` gets no token. Direct sync/mark-ready lost to Pause stay the typed `ERR_DELIVERY_CHANGE_PAUSE_REQUESTED` refusal (§1.6; engine form returns `stale`/`readiness-changed`). `test_change_pause.py` 41 passed (adds Finalizer via `finalize_change` and report+settlement, host-lost, `release_stuck_worker`, operator start lost/won ×2, Builder drain with in-token refusals, direct sync won/lost, first-task snapshot after its commit, snapshot handoff via supervisor and acquisition replay, handoff fast path, F9 snapshot, F8 Builder and Planner replays, K4 v1 journal and preservation after `coordination-1-to-2`); default-loader restart, MCP and HTTP refusal tests pass; operator-start inventory in `test_delivery_worktree_authority.py`; `test:e2e:work` stuck-worker group 4 passed incl. **Pause requested**; closeout `test --changed --base origin/dev`: pytest 3111 passed, Vitest 25 files / 361 passed; focused rerun after the last source edit (pause, worktree-authority, checkpoint/snapshot portfolio tests) 122 passed; `npm run build` pass; `test:e2e:work` 27 passed (Chromium); Ruff check and format clean on changed Python (Biome ignores `e2e/`; no other frontend file changed in the repair). Sol round-1 repair (`28a446ff6`): (1) worker replay tokens bind only the replaying owner's own digest — `submit_result` rebuilds `AdvanceDelivery` from its verified result receipt, transition, settlement and release bind their own request or envelope — and a replay token without its own digest permits no publication; (2) a repeated `release_stuck_worker` rebuilds authority from its release receipt, finishes that receipt's pending publication and converts; (3) public `PortfolioApplication.defer_change`/`resume_change` retired (only tests called them; MCP and Cockpit already use `set_change_intent`); Pause admission refuses an unreconciled runtime, matching its projection; (4) a recorded request overlays `blocked`/`change-paused` non-executable readiness on every executable card, retained-owner, containment and recovery readiness unchanged; (5) K8 assembled tests: F1 production owner starts inside Pause's Validate→Record window (engine-action acquisition, Finalizer writer, standalone lease held on a thread, direct mark-ready held inside the provider on a thread), F5 Pause between `_engine_action_preflight` and start, F6 bulk push failure with a waiting Pause (failure recorded before conversion), F6 crash/restart/identical replay of direct mark-ready and direct sync, F7 `ready-readback` under Pause and under Resume, F8 old result replay against a later pending intent, Builder-settlement and Planner-advance replays with changed-envelope refusal and in-token foreign-start refusal, F9 digestless replay token; step-1 inventory adds provider-effect gating (call graph to a Pause gate; quarantined-snapshot repair classified deferral-equivalent), the K2 authority-source map with own-request replay digests, checkpoint-lock lifetime of direct and standalone entries, and direct finish markers. Fail-before (`e0da9da1a` sources, `serve/delivery/src` stashed): 9 failed — `test_f8_old_builder_result_replay_never_publishes_a_later_pending_intent`, `test_f9_replay_token_without_its_own_digest_permits_no_publication`, `test_release_stuck_worker_replay_after_crash_publishes_then_converts`, `test_pause_and_resume_admit_only_through_the_change_intent`, `test_unconverted_request_projects_no_executable_new_work`, `test_request_under_custody_blocks_sibling_new_work_and_keeps_owner_readiness` and the 3 unreconciled-runtime Pause cases in `test_portfolio_application.py`; all pass after. `test_change_pause.py` + `test_delivery_worktree_authority.py` 105 passed; portfolio/state/progress/work-items/worker-stall/recovery/MCP/Cockpit suites 1218 passed; `test --changed --base origin/dev` on `28a446ff6`: pytest 3132 passed, 1 failed (`test_http_loader_contains_unknown_custody_without_repeating_effects[observe-acceptance]`: pytest-timeout >30 s inside a `git show-ref` subprocess while the LC container ran; isolated rerun of all 3 parametrizations 3 passed), Vitest 25 files / 361 passed; Ruff check and format clean on 9 touched files; LC full form (`delivery-lc run --form full --candidate 28a446ff6 --previous ac3bf23f9 --uv-cache-volume n00a-uv-cache`, stage `/private/tmp/n09a2-r1-lc`, 132 live records): unmigrated copy refused (`state-migration-required`, gate also names the 3 coordination v1 records, inspector `COORDINATION_MIGRATION_REQUIRED` + `FORMAT_MIGRATION_REQUIRED`, hashes unchanged); `coordination-1-to-2` ×3 + format marker applied and verified, changed records equal the proposal; migrated copy: gate clean, inspector healthy, all 3 Changes loaded, none unavailable; synthetic newer format refused; previous release `ac3bf23f9` refuses the 3 coordination v2 records with typed `state-newer-than-controller` (gate and load) and unchanged hashes; `compare`: live unchanged (132 records). Tool verdict `passed: false` solely from `previous_release_oracle`, which recognised an unsupported downgrade only at `runtime/format.json` when the previous release supports the target format; D3 and §3.3 require exactly this family-version refusal. Oracle fix `d512a42e4` (engineering decision by the lead; no format bump): with the target format supported, the previous release must refuse with typed `state-newer-than-controller` exactly the records whose candidate family version exceeds every version its registry reads, with unchanged hashes and no load; full load only when no family exceeds it; `test_delivery_lc.py` 93 passed (6 new oracle cases + family-bump full form), `test_change_pause.py` 58 passed, Ruff clean. LC full form rerun (`--candidate d512a42e4 --previous ac3bf23f9` = merge-base with `origin/dev`, `--uv-cache-volume n00a-uv-cache`, stage `/private/tmp/n09a2-r2-lc`, 132 live records): **`passed: true`**, run exit 0, launch validated; unmigrated refused (`state-migration-required`, hashes unchanged); 3 coordination + marker migrated and `verified`; migrated gate clean, inspector healthy, 3 Changes loaded, none unavailable; previous gate refuses exactly the 3 coordination v2 records (`previous_beyond` = those 3; registry reads coordination 1), hashes unchanged, no previous load; synthetic newer format refused; `compare`: live unchanged. Round-2 repair `7a2d974b3`: (1) K3 start-commit interleavings `test_k3_acceptance_reservation_commit_races_pause` (`[pause]`, `[start]`; Pause injected in `RetryLedger._commit_summary` of the reservation, before or after its commit) and `test_k3_snapshot_intent_commit_races_pause` (same pair; Pause injected at the intent-creating `update-change-a` coordination commit, before or after): Pause wins → `ChangePauseRequestedError` / not reconciled with no failure recorded; retry-ledger bytes, intent, snapshot receipt, reviewed head and branch unchanged; no provider read or pull request. Start wins → the owner drains (acceptance completes and clears the request; the snapshot anchors, publishes, then converts). Fence-removal check: with `fence=` dropped from `_reserve_acceptance_observation` and the `_validate_update` intent check removed, both `[pause]` cases fail (`DID NOT RAISE`; `reconciled` true) and both `[start]` cases pass; fences restored (`git diff` empty on both files). (2) `repair_quarantined_delivery_state_snapshot` starts through `_operator_start` inside its acquisition and checkpoint locks (refused before any read or push under a request; a started repair drains, then converts); inventory exemption removed and the entry added to the operator-gated set. Failing before: `test_new_quarantined_snapshot_repair_refuses_under_request_without_push`, `test_quarantined_snapshot_repair_start_races_pause[pause]` (`DID NOT RAISE`) and `[start]` (no conversion), plus inventory `test_every_provider_effect_entry_is_reached_only_through_a_pause_gate` and `test_operator_new_work_entries_start_pause_fenced_inside_their_checkpoint_lock`; all pass after. `test_change_pause.py` + `test_delivery_worktree_authority.py` 112 passed; Ruff clean on 3 touched files; `test --changed --base origin/dev --py` 3147 passed (exit 0); no persisted-format change, LC not rerun | Sol implementation round 1: repair-required (replay token copied a foreign pending digest; crashed release replay skipped publication and conversion; second guarded Pause entry; executable readiness under an unconverted request; missing K8 interleavings and inventory properties) → repaired; Sol implementation round 2: repair-required (start-race evidence, snapshot repair exemption) → repaired | candidate ready for round 3 |
| N09-P2 | #372 | — | Probes P19–P25 (read-only source and branch reads); markdownlint on a temporary copy | Lead runs the Sol plan gate | in review |
| N09-B | — | — | — | — | not started (needs U2) |
| N09-C | — | — | — | — | not started |

## 5. Verification Gaps

| ID | Claim | Why unproven | Evidence available | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | An `alive` issuer window with a held claim may have no running worker | The issuer is the VS Code window process; a stopped chat or an undispatched claim in a live window still reads `alive` (P6, P13) | A1 shows neutral custody, never an active label (I2, D4); D03 user-confirmed release | Accepted D03 limit; N10-H observes it in the host journey | Nothing |
| G2 | The copied `/continue-change <id> …` prompt binds the right Change in Copilot Chat now and after the Local agent's removal | Input binding is model inference; prompt files are deprecated for Agent Host (P8); no host run in P | D02 named-host rehearsal; VS Code docs 2026-09-30 | N09-P2 settled: no migration (D19); N10-H runs the copied prompt in the real host | Nothing |
| G3 | Some evidence boundary establishes current dispatch, so **Working**, **Checking** and **Repairing** can be emitted | Issuer evidence precedes activation and the launch package, and the probe checks process existence only (P13); a new heartbeat was rejected | None today; the keys stay reserved (D2). N09-P2: no remaining package supplies dispatch evidence (N06 and N07 cut; N05 adds none) | Keys stay reserved; any later evidence boundary is new work | Nothing |
| G4 | Every custody acquisition, effect start and provider entry passes a pause-gated entry serialized with its start | P9 and P13 are source reads, not an inventory | Named coordinator, manager and application chokepoints; 16 `_require_no_active_change_claim` call sites | N09-A2 step 1 inventory test | N09-A2 merge |
| G5 | #218 is closed with evidence | The agent has not yet posted the evidence comment (U1 (b)) | PR #308, P1 test run | Agent (U1 (b)) | N10-M programme closure |
| G6 | Frontend, build and E2E behave as planned | Not run in P (machine load); only Python probes ran | Source reads P3, P4, P12 | N09-A1 closeout | N09-A1 merge |
| G7 | A2's migration on live state | Live has no deferral or claim (P7), so LC exercises only the version rewrite; the new direct-marker family has no live records | P7 | N09-A2 LC full form plus disposable custody fixtures | N09-A2 merge |
| G8 | `ready-to-merge` stays correct once exact-head merge approval exists | N05 not planned yet (in progress in another lane) | Programme §4.2, §10.2 | N05-P / the N05 phase that adds **Approve merge** updates M10 | Nothing in N09-A |
| G9 | `needs-decision` for unknown issuer evidence does not lead users to release a live worker | Behavioral, host-level | `release_stuck_worker` 30-second write and process guard | Accepted D03 guard; N10-H | Nothing |
| G10 | K4's projection reproduces the stored digest of every issued recovery journal and preservation receipt across `coordination-1-to-2` | No live journal or receipt was inspected; equality rests on sorted-key encoding (P15) | `_model_content` (`workspace_models.py:2075-2077`); F7 | N09-A2 fixtures with v1 journals and receipts migrated by `delivery-lc` | N09-A2 merge |
| G11 | Under `/continue-change`, a real host dispatches the nested Finalizer and its `build-reviewer` and finalizes | N03-B rehearsed the reviewer only; a full Finalizer chat against a Delivery MCP server was not run (N03 plan G4 limit; programme §6) | Engine tests of the issued finalization (P19); N03-B reviewer rehearsal | N10-H host journey | Nothing: `/finalize-change` stays as the fallback (D16) |

[n09-section]: delivery-redesign-execution-plan.md#n09--continuation-entry-cutover-and-cockpit-entry-surface
