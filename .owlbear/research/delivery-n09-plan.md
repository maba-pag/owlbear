# Delivery N09 — Continuation Entry Cutover and Cockpit Entry Surface

> **Package:** N09 of the [execution plan][n09-section].
> **This plan (N09-P1) plans N09-A only.** N09-B (retirement and routing) and N09-C (documentation
> reconciliation) are planned later by N09-P2, after the N05–N08 plans and N09-A are approved.
> **Planned on:** `origin/dev` `ef622c354` (N01-A merged; N01-B and N01-C not merged; Python 3.14.8).
> Live controller observed read-only: three Changes, frontier schema 18, no deferral, no active claim.
> **Status:** approved: plan gate `plan-sound` in round 8 of fresh GPT-6.1 Sol challenges (2026-10-03). Product code is unchanged by this phase.

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

N09-A owns no V-scenario on its own. It supplies the entry surface that V01 (N10) and V17 (N06)
exercise, and keeps the D01–D03 regressions (V02–V10, V13) green.

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
| `preparing` | Preparing | Reserved; N06/N07 (assistance preparation) |
| `working` | Working | Reserved; needs dispatch evidence (G3) |
| `checking` | Checking | Reserved; needs dispatch evidence (G3) |
| `repairing` | Repairing | Reserved; needs dispatch evidence (G3) |
| `needs-decision` | Needs your decision | A1 |
| `needs-sign-in` | Needs your sign-in | Reserved; N06/N07 |
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
- Controls owned elsewhere: **Help with this step** (N06), **Change requirements** (N04),
  **Approve merge** (N05), **Repair Delivery** (N08); **Open in Copilot** (not planned).
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
  2026-10-03; explicit confirmation pending.
- **D10 #218 needs no product change.** PR #308 ("Fixes #218", merged 2026-09-07) made curation
  failures non-blocking in `w-orchestration` Step 5 (`share/skills/w-orchestration/SKILL.md:402-420`)
  and Step 6 (`:422`), with ecosystem assertions (`tests/test_agent_ecosystem_validation.py:763-778`,
  `:1181-1186`). The continuation route (`SKILL.md:53-188`) dispatches no curator at all, so it cannot
  block. Whether periodic curation keeps a cadence once `/orchestrate` retires is a capability-inventory
  row for N09-P2, not N09-A work. The issue is still open ([U1](#u-decisions)).
- **D11 Portfolio guidance stays, minus false claims.** The `/orchestrate` portfolio command and
  guidance kinds remain until N09-B. A1 only replaces the untruthful "An orchestration session is
  already working" (`PortfolioOperatingSummary.tsx:37`) with "N Work Items hold active custody; each
  Change shows its progress" and removes the activity-only "Working" fallback
  (`workItemPresentation.ts:201`, becomes "Claimed").

#### U decisions

**U1 — Close #218 with evidence** (pending user confirmation; required before N10-M's programme
closure; nothing in N09-A depends on it). Status quo: #218 is open although PR #308, which says
"Fixes #218", merged into `dev` on 2026-09-07 and its behavior is on `origin/dev` (P1). Problem:
programme completion requires #218 closed with evidence (execution plan §6), and commenting on or
closing an issue is an external action that needs the user. Options: (a) the N09-A1 PR description
carries a drafted closure comment (PR #308, skill lines, test names, the N09-A1 rerun) and the user
posts it and closes the issue; (b) the user authorizes the agent to post and close; (c) leave it
open until N10-M. **Recommended: (a).**

No other genuine user decision was found. Pause semantics are settled by programme §4.2; D1–D11 are
engineering choices inside that contract.

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

Not run in P (machine load): Vitest, Cockpit build, E2E, any multi-file suite (G6).

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

## 4. Progress

| Phase | PR | Exact head | Proof | Challenges | Status |
| --- | --- | --- | --- | --- | --- |
| N09-P1 | #351 | — | Probes P1–P18 | Sol round 1: revision-required (drain exceptions, custody-neutral pause admission, pause/start atomicity + coordinator inventory, Change progress selection, liveness evidence) → revised; Sol round 2: revision-required (short pause fence, frontier-bound CAS, completion-call drain authority, eligibility-based C4) → revised; Sol round 3: revision-required (recovery authority vs pause policy, settled-owner replay authority, unified admission) → consolidated A2 custody contract; Sol round 4: revision-required (direct/standalone owner rows, owner-specific replay bindings) → revised; consistency pass (§1.6/§3.3/formats aligned with §1.11); Sol round 5: revision-required (pre-lease snapshot drain authority) → revised; Sol round 6: revision-required (anchored pre-lease snapshot handoff) → revised; Sol round 7: revision-required (fast-path handoff lease) → revised; Sol round 8: `plan-sound` | approved (D9 re-split confirmation pending; U1 before N10-M) |
| N09-A1 | #354 | `3573866ac` | First check `test_undispatched_builder_claim_with_live_issuer_shows_neutral_custody` fails on base (`progress` missing), passes after; `test_delivery_progress.py` 66 passed; `test_work_items.py` + MCP progress test 26 passed; HTTP progress/pause 2 passed; Vitest WorkPortfolio + CockpitShell + CopyCommand targeted pass; `npm run build` pass; `test:e2e:work` 26 passed; Ruff and Biome clean on touched files; `test --changed --base origin/dev`: pytest 2552 passed, 1 failed (HTTP wire snapshot lacked `progress`; fixed; `test_cockpit_work_items.py` + `test_cockpit_boundary.py` rerun 122 passed), Vitest 25 files / 345 passed; P1 housekeeping rerun 1 passed. Repair: 26 new Pause cases (12 retained-custody reasons × group/detail, non-custody blocked control, filtered mixed group) — 23 fail on `e3fc1d482` sources, all pass after; WorkPortfolio.test.tsx 165 passed; `npm run build` pass; Biome clean on 3 touched files; `test:e2e:work` 26 passed; `test --changed --base origin/dev --web` Vitest 25 files / 371 passed. Repair 2 (Pause availability derived by Delivery from the defer intent's own refusal predicates, `pause_available`/`pause_unavailable_reason` on group and detail): 10 assembled fixtures assert projection == defer acceptance, read-only (masked Finalizer and every retained claim/engine-action state refused; passive Finalizer attention, reservation-only retry containment and quiescent Change accepted) plus unreadable coordination and unverified recovery; `test_delivery_progress.py` + `test_work_items.py` + `test_cockpit_boundary.py` + `test_cockpit_work_items.py` 226 passed, 1 failed (projector fixture lacked a second binding; fixed, rerun passed); `test_target_server.py` 126 passed; Vitest WorkPortfolio + CopyCommand + AcceptanceReconciliation 166 passed; `npm run build` pass; Biome and Ruff clean on touched files; `test:e2e:work` 26 passed; `test --changed --base origin/dev`: pytest 2566 passed, 1 failed (runtime writer-inventory invariant counted the read-only probe; frontier guards moved to a module-level mirror; invariant + progress rerun 117 passed), rerun EXIT=0, pytest 2567 passed, Vitest 25 files / 360 passed | Sol implementation round 1: repair-required (retained-custody Pause predicate, filtered custody) → repaired; Sol implementation round 2: repair-required (server-derived Pause availability) → repaired; Sol implementation round 3 `implementation-sound` | merged |
| N09-A2 | — | — | — | — | — |

## 5. Verification Gaps

| ID | Claim | Why unproven | Evidence available | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | An `alive` issuer window with a held claim may have no running worker | The issuer is the VS Code window process; a stopped chat or an undispatched claim in a live window still reads `alive` (P6, P13) | A1 shows neutral custody, never an active label (I2, D4); D03 user-confirmed release | Accepted D03 limit; N10-H observes it in the host journey | Nothing |
| G2 | The copied `/continue-change <id> …` prompt binds the right Change in Copilot Chat now and after the Local agent's removal | Input binding is model inference; prompt files are deprecated for Agent Host (P8); no host run in P | D02 named-host rehearsal; VS Code docs 2026-09-30 | N09-P2 (skill migration in the capability inventory); N10-H | N09-P2 |
| G3 | Some evidence boundary establishes current dispatch, so **Working**, **Checking** and **Repairing** can be emitted | Issuer evidence precedes activation and the launch package, and the probe checks process existence only (P13); a new heartbeat was rejected | None today; the keys stay reserved (D2) | N09-P2 capability inventory records whether any later package supplies such evidence | Nothing in N09-A |
| G4 | Every custody acquisition, effect start and provider entry passes a pause-gated entry serialized with its start | P9 and P13 are source reads, not an inventory | Named coordinator, manager and application chokepoints; 16 `_require_no_active_change_claim` call sites | N09-A2 step 1 inventory test | N09-A2 merge |
| G5 | #218 is closed with evidence | Needs a user-posted comment (U1) | PR #308, P1 test run | User | N10-M programme closure |
| G6 | Frontend, build and E2E behave as planned | Not run in P (machine load); only Python probes ran | Source reads P3, P4, P12 | N09-A1 closeout | N09-A1 merge |
| G7 | A2's migration on live state | Live has no deferral or claim (P7), so LC exercises only the version rewrite; the new direct-marker family has no live records | P7 | N09-A2 LC full form plus disposable custody fixtures | N09-A2 merge |
| G8 | `ready-to-merge` stays correct once exact-head merge approval exists | N05 not planned yet (in progress in another lane) | Programme §4.2, §10.2 | N05-P / the N05 phase that adds **Approve merge** updates M10 | Nothing in N09-A |
| G9 | `needs-decision` for unknown issuer evidence does not lead users to release a live worker | Behavioral, host-level | `release_stuck_worker` 30-second write and process guard | Accepted D03 guard; N10-H | Nothing |
| G10 | K4's projection reproduces the stored digest of every issued recovery journal and preservation receipt across `coordination-1-to-2` | No live journal or receipt was inspected; equality rests on sorted-key encoding (P15) | `_model_content` (`workspace_models.py:2075-2077`); F7 | N09-A2 fixtures with v1 journals and receipts migrated by `delivery-lc` | N09-A2 merge |

[n09-section]: delivery-redesign-execution-plan.md#n09--continuation-entry-cutover-and-cockpit-entry-surface
