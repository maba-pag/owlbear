# Delivery N04 — Same-Change Revision Activation and Evidence Applicability

> **Package:** N04 of the
> [execution plan](delivery-redesign-execution-plan.md#n04--same-change-revision-activation-and-evidence-applicability).
> **Planned on:** `origin/dev` `ac3bf23f9` (N00, N01, N02-A, N02-B and N09-A1 merged; N03-P, N05-P, N08-P and
> N09-P1 approved; N02-C, N02-D, N03-A…C, N05-A…D and N09-A2 not merged; Python 3.14.8). Live state read only:
> main checkout on `delivery-live` (D03). Rebased on `origin/dev` `634a77be7`: it adds only N05-A
> (`delivery-github`, `publication_provider.py`, forbidden-effect gates), so no locator here moved; P3–P8 rerun
> there with identical outcomes. Round 3 merged `origin/dev` `141795676` (N09-A2, PR #357, merged); the N09-A2
> start-site inventory and K3 fences named here are now on `dev`.
> **Status:** draft for the plan gate; revised after Sol plan gate rounds 1–3 ([§6](#6-round-dispositions)).
> Product code is unchanged by this phase. U1–U3 are recorded engineering decisions of 2026-10-03
> ([1.13](#113-decisions)).
> Dependencies (re-pinned in round 3): **N03 (as amended by #360)**: the [N03 plan](delivery-n03-plan.md) with
> PR #360 (lane C `f4d09d774`, under review; it adds N05 D14's single-use consent generation `merge_consent` and
> N03 D13 *Single use*, which treats the expected frontier digest as the generation of a scoped request and
> states that a decline, a cancel or an unapplied accepted answer consumes nothing): evidence model;
> user-only confirmation through MCP elicitation (N03 D13, R14,
> I6) declared once as a server-injected `Resolve` parameter with a legacy route (`elicitation/create`) and a
> modern route (`InputRequiredResult`) behind the SDK's default `RequestStateBoundary`; the Change-wide
> append-only ledger `DeliveryFrontier.confirmations` read only through `resolve_confirmation` /
> `confirmation_applies` (N03 §1.5, I10, §1.9 N04 contract); schema-2 request-resolution receipts that bind a
> ledger append for restart replay (N03 §1.7 L row). Its U1 was answered (b) on 2026-10-03; its U2 (does a
> Cockpit click count) is open before N03-C ([G17](#5-verification-gaps)). The [N02 plan](delivery-n02-plan.md)
> (registry, gate, migration core; its U1 and U2 were answered (a): pinned live controller,
> `/upgrade-delivery`). The [N09 plan](delivery-n09-plan.md) §1.11 (A2 custody contract, which N04 extends),
> checked against PR #357 (lane A `9a7fff990`: K3 fences, drain tokens and the start-site inventory in
> `tests/test_delivery_worktree_authority.py`; `repair_quarantined_delivery_state_snapshot` is now an
> operator start fenced by `_operator_start(change, "quarantine-repair:<op>")` and no entry is Pause-exempt).

## 1. Contract

### 1.1 Result

- The user changes a nonterminal Change's requirements through Cockpit **Change requirements** or
  `/design <change-id>`. The Designer loads the active proposal, prior decisions, task and evidence history and
  the current block, explains the delta and asks the user to approve behavior and risk changes, never hashes,
  stages or invalidation IDs.
- An admitted Change keeps its active approved package untouched while a candidate revision is drafted in a
  separate, host-local candidate slot. The candidate is never execution authority.
- While a candidate exists, a **revision hold** stops new work on the Change ([U2](#u2--scope-of-the-revision-hold));
  current custody drains through its owner (N09 §1.11 K2) or the D03 settlement routes. No revision activates
  while worktree custody remains, except the Design-return handoff, which activation resolves per
  [U3](#u3--retained-builder-work-at-design-return-readmission).
- Activation is one replayable engine operation: intent → ready-PR demotion (ready only) → verified Design-return
  preservation (U3 (b) only) → deterministic managed-branch child commit → one local transaction (package,
  contract, frontier, admission, generation history, coordination, pending publication, journal) → publication →
  release. Acquisition is blocked from intent to release, except the activation's own identity-bound steps. A
  crash at any boundary restarts to the old approved state (before the intent) or rolls forward to the exact new
  state, with no duplicate child commit; a fresh host restores either state or a visible pending state that
  preserves an unpublished remote child without adopting or overwriting it until a fully fenced replacement
  or a user-approved, fenced resolution of that exact child.
- An applicability report classifies every obligation affected by the revision as reusable, partial,
  invalidated or unknown, with an independent reviewer's justification. Its records are portable frontier
  authority that the N03 evaluator consumes. It replaces the blanket request of
  `_carry_forward_unresolved_binding`: the Planner plans only uncovered, partial or invalidated criteria and the
  user is asked for at most the minimum human step.
- D03's retained-handoff Design return can be readmitted.
- Pre-N04 revisions whose managed-branch package snapshot is older than the active package (live B1) are
  detected and completed by an engine reconcile action.
- Completed and abandoned Changes stay immutable: every revision path refuses them and points to a successor.
- A crash inside any Design package transaction no longer prevents the controller from starting.

### 1.2 Requirements

| ID | Requirement | Source |
| --- | --- | --- |
| R1 | Candidate separate from active authority; the prior approved version is never lost | Programme §8.1; WP4 step 1; P12 |
| R2 | Concrete user route: **Change requirements** or `/design <change-id>`; Designer loads proposal, decisions, task/evidence history and current block; no user-selected stage | §8.2 steps 1–2, 5; §4.2; WP4 step 5; P14 |
| R3 | Engine stops new incompatible work; current custody finishes or settles; no activation while writable custody remains | §8.2 step 3; §5 N04 result |
| R4 | One durable replayable operation across package, admission, contract, frontier remap, branch snapshot and publication; acquisition blocked during activation | §8.3; WP4 step 2 and risk; P12 |
| R5 | Crash at every durable boundary restarts to the old approved state or the exact new state; no duplicate child commit; no lost block | V21; §8.3 step 2 |
| R6 | Applicability per affected obligation (reusable, partial, invalidated, unknown) with reviewer justification; original receipts never relabeled or rewritten | §8.4; WP4 step 3; P13; N03 I1, I3 |
| R7 | Replace the blanket carry-forward with agent reassessment and planning; at most the minimum human step | §5 N04; WP4 step 4; S06; U3, U6 |
| R8 | Evidence reused by covered criterion and version; no new human exercise because a request ID changed | V15; U6 |
| R9 | A revised target not covered by old evidence shows the exact missing criterion; no silent waiver | V16; U7; N03 R10 |
| R10 | Prior authority retained; candidate delta reviewed; activation coherent; only affected work invalidated | V14 |
| R11 | D03's retained-handoff Design return can be readmitted | §2.2 of the execution plan; #213 |
| R12 | Completed Changes immutable; further work is a successor Change | §8.2; §5 N04 |
| R13 | Resolve the S01 contradiction (workflow forbids admitted revision; source allows it) explicitly | Programme S01; §8.2 last paragraph |
| R14 | Interrupted activation remains a visible Change with an actionable reason, never unavailable | V18 (WP4 proof list) |
| R15 | Every new or changed persisted family registers a version owner; registered migrations; LC full form | Execution plan §1.3; N02 I2, I3, D3 |
| R16 | §1.4 companions: each new readiness reason, action or status ships with its TypeScript mirror, rendering, component test and parity assertion; each new frontier writer joins the central mutability policy | Execution plan §1.4 |
| R17 | Support baseline (Python 3.14; macOS and Ubuntu; Chromium Cockpit) | Execution plan §1.1 |

### 1.3 Invariants

- **I1 One execution authority.** Acquisition, planning, building, finalization and publication read only the
  active package and the runtime contract. Nothing reads the candidate except Design operations and the impact
  view.
- **I2 Prior version retained.** After activation the base package bytes stay recoverable from the package
  checkpoint ref, the generation record `revisions/generations/<operation_id>/` (one per activation, never
  overwritten, §1.6) and the managed branch history.
- **I3 Roll forward only.** Before the activation intent the Change is in its old approved state and the user may
  discard the candidate. After the intent the operation only rolls forward; it never silently falls back
  (programme §8.3 step 5). Sole exception: A1b observes the bound pull request merged before any Git effect of
  the activation; the journal then ends `superseded-by-merge` and the acceptance owner completes the Change.
- **I4 One deterministic child commit.** An activation or snapshot creates at most one managed-branch commit:
  the direct child of the intent's expected head, touching only `.owlbear/delivery/packages/<change>/`, with an
  operation-bound message and fixed author, committer and dates. Its SHA, tree and dates live in one durable
  carrier, `ChangeDesignPackageSnapshotIntent` schema 2, written with the child object pinned by a ref before any
  branch, index or worktree write; replay uses that object and never recomputes or re-signs (§1.6, D28, D32).
- **I5 Acquisition fence.** From the hold, no new custody or effect start except draining owners and the exact
  identity-bound exceptions of §1.5; from the intent to the release, only the activation owner's own steps.
- **I6 Immutable history.** No stored observation, review, result, finalization, snapshot or receipt changes
  bytes or identity (N03 I1). Applicability records embed the receipts they cite unchanged.
- **I7 No fabricated provenance.** Applicability records are reviewer statements. They never create
  `user-confirmed` provenance, resolve a request or satisfy a `human-confirmed` requirement on their own (V20).
- **I8 Terminal immutability.** Candidate creation, activation and admission refuse a completed or abandoned
  Change before any write.
- **I9 Gate first.** N02 I1 and I5 unchanged; every N04 family and version joins the registry with a format step.
- **I10 Policy, not custody.** The hold never stops a running worker or a started effect (N09 I6).
- **I11 Confirmation authority only from the ledger.** A reused `waived` or `human-confirmed` record counts only
  through N03 (as amended by #360) `resolve_confirmation` and `confirmation_applies`. Activation, reassessment
  and applicability records never append, alter or reorder `DeliveryFrontier.confirmations` (N03 I10) and never
  derive authority from requests, request history or caller provenance. The only N04 ledger writer is
  `confirm_revision_criterion` through N03's D13 boundary (§1.7, D27); it appends, never alters.
- **I12 Complete preservation before cleanup.** Retained Design-return work is captured as three verified
  components (HEAD commits, the real index, the filesystem state from a bounded walk including full file and
  directory modes, symlinks, untracked files and empty directories; ignored entries inventoried and left in
  place) and re-verified against the live worktree before any cleanup byte changes. Cleanup deletes only
  captured entries, never by `git clean`. No ignored entry may collide with a path the cleanup writes or stop
  being ignored under the reviewed head's ignore rules; either refuses before the intent (D25, D34).
- **I13 One answer per question.** Every N04 user question (candidate-scoped confirmation, foreign-head
  authorization) is bound to a server-owned single-use consent generation that its first answer consumes,
  whether accepted, declined, cancelled or refused at the re-check (§1.7 Consent generation, D36).

### 1.4 Authority layout

| Artifact | Location (under `.owlbear/delivery/`) | Owner | Class | Portable |
| --- | --- | --- | --- | --- |
| Active package | `packages/<change>/` (layout unchanged) | `DesignPackageStore` (active root) | T, R | via branch snapshot |
| Active package history | `refs/owlbear/packages/<change>` | `DesignPackageStore.checkpoint` | Git | no |
| Candidate package (admitted Changes only) | `runtime/package-candidates/<change>/{authority.json,design.md,intent.md,manifest.json}`; `authority.json` always empty | second `DesignPackageStore` instance | M | no (host-local, like unadmitted drafts) |
| Candidate history | `refs/owlbear/package-candidates/<change>` | `DesignPackageStore.checkpoint` with a ref namespace | Git | no |
| Revision hold | `ChangeCoordination.revision_hold` (A1); bound activation operation and `purpose` added at A1 of the operation (A2b) | `PortfolioCoordinator` | M | no |
| Activation journal | `runtime/changes/<change>/revision-activations/<operation_id>/{intent,demotion,local,result}.json` | activation owner (A2b) | R | no |
| Design-return preservation | `runtime/changes/<change>/revision-activations/<operation_id>/preservation/{manifest.json,blobs/<sha256>}` (owner-private, D03 store rules); refs `refs/owlbear/preserved/<change>/<operation_id>/{head,index}` | activation owner (A2b) | R | no |
| Generation history | `runtime/changes/<change>/revisions/generations/<operation_id>/{contract,frontier,admission}.json` (the replaced authority, H) and `generation.json` (R) | activation owner (A2b) via `DeliveryAuthorityRegistry` participants | H, R | no |
| Legacy history | `runtime/changes/<change>/revisions/<64-hex>/` (existing; contract- or frontier-digest named) | none (read only) | H | no |
| Remote activation pin (fresh host) | `refs/owlbear/remote-activations/<change>/<operation_id>`; `ChangeCoordination.remote_activation_pending` | loader restore (A2b) | Git, M | no |
| Fresh-host replacement | `runtime/changes/<change>/remote-activations/<operation_id>/{replacement,replacement-snapshot,replaced}.json` | loader replacement owner (A2b, D38) | R | no |
| Foreign-head records and pin | `revision-activations/<operation_id>/foreign-heads/<F>.json`, `foreign-head.json`; `refs/owlbear/preserved/<change>/<operation_id>/foreign-<F>` | activation owner (A2b, D35) | R, Git | no |
| Consent generations | `runtime/changes/<change>/revision-consents/<sequence>.json` | activation owner store (A2b, D36) | M | no |
| Snapshot child pin | `refs/owlbear/snapshot-children/<change>/<operation_id>` (pre-intent; deleted after the receipt) | snapshot owner (A2a) | Git | no |
| Revision confirmation receipts | `runtime/changes/<change>/revision-confirmations/<confirmation_id>.json` | `confirm_revision_criterion` (B) | R | no (the ledger entry is portable) |
| Applicability records | frontier binding `applicability` (B) | runtime | M (nested) | yes (snapshot) |

- **Unadmitted Changes** keep today's in-place `create_design_session` / `revise_design_session` / `put_design`.
- **Candidate identity.** The candidate's authored package ID is the manifest digest with empty authority
  (`_approved_package_id` pattern). The activated package adds the compiled contract as `authority.json`.
- **Operation identity.** `operation_id = "revision-" + sha256(canonical JSON {kind, change_id,
  base_package_id, candidate_package_id, contract_digest, predecessor: {reviewed_head, frontier_digest},
  history_ref, adopt_child})[:40]`, valid under the existing operation-ID pattern. `kind` is `revision`,
  `snapshot-reconcile`, `reassess` or `remote-child` (§1.6 per-kind contract); the predecessor generation is the
  exact authority being replaced, named by the request's `expected_head` and `expected_frontier_digest` (both
  portable, both fixed from intent to release); `history_ref` is `null` except for `reassess` (§1.7) and
  `adopt_child` is `null` except for `remote-child`. An identical request therefore recomputes the same ID at
  every replay; snapshot-reconcile and reassess of the same package never collide, and returning to an earlier
  package (A → B → A → C) never reuses an earlier operation (D19).
- **Approval record.** The intent stores `approval {approved_package_id, contract_digest, impact_digest,
  review_id, approved_at}` from the Designer's call after explicit user approval: the same trust as today's
  `admit_change` (an engine cannot prove what the user said; it binds what was approved).

### 1.5 Revision hold and quiescence

The hold reuses N09-A2's start serialization: every K3 start site checks `revision_hold` in the same transaction
as its start marker and refuses `CoordinationConflictError` "Change revision hold" unless one of the exact
identity-bound exceptions below applies. Opening a hold is a K1-style admission (one transaction: candidate
files plus the coordination replacement, observed frontier bytes as an exact no-op participant), never waits and
never takes custody. Rows below follow U2 (a).

| State when the hold opens or the intent is attempted | Under the hold | At the activation intent |
| --- | --- | --- |
| Live Planner or Builder claim (live or unknown issuer) | No new claim; the claim returns and settles, or the user releases it (D03) | Refused `revision-custody-active` |
| Started engine action, direct operation, standalone publication, snapshot intent, pending publication or checkpoint | Owner drains (N09 K2 rows) | Refused `revision-drain-pending` |
| Active Finalizer attempt | Drains | Refused `revision-custody-active` |
| Report-backed Finalizer attention (passive) | — | Consumed in the local transaction: report retired, passive custody released (engine-owned, exact) |
| Same-task Builder handoff (passive, Implementation) | Its same-task successor claim may run (draining retained work); no other start | Refused `revision-custody-retained` |
| Planning-route or Design-route Builder handoff (returned work) | No successor | Resolved per [U3](#u3--retained-builder-work-at-design-return-readmission) |
| Unanswered request, block, retry backoff or exhaustion | Unaffected | Allowed; B rules decide what survives |
| Pause request or deferral | Hold may open | Refused `change-paused` (Resume first; K3 already refuses the intent start) |
| Finalized or ready (awaiting merge) | — | Allowed for `revision` and `snapshot-reconcile` (both move the head): A1b demotes the ready PR after the intent inside the activation's held locks; A4 clears `ready` and `finalization` and records `head-drift` (D22). Refused for `reassess` (`reassess-requires-unfinalized`; it moves no head, so `head-drift` cannot hold) |
| Review repair open (`review-repair` invalidation) | — | Refused `review-repair-open` (abort or finalize the repair first; head movement is forbidden while it owns the boundary) |
| Change attention (publication or acceptance disposition) | — | Refused `change-attention` (existing resolution route first) |
| Completed or abandoned | Candidate creation refused | Refused `change-terminal` with successor guidance |
| Branch not at the reviewed head, or dirty worktree without custody | — | Refused `revision-workspace-unclean` (D03 containment routes) |
| Pre-N04 stale branch snapshot (§1.6 legacy reconcile) | — | Refused `revision-snapshot-stale` until reconciled |

K4 (N09): `recovery_authority_digest` also excludes `revision_hold` and `remote_activation_pending`, so opening
or clearing a hold never invalidates an issued recovery journal or preservation receipt. K6 field rule: every
coordination replacement built from a captured model copies both fields from the bytes it replaces.

**Hold exceptions (D21).** The hold check is not a copy of the Pause check: N09-A2 refuses every start below
while any policy is present, which would also refuse the hold's own required starts (activation's snapshot
intent, its reconciliation actions, the retained same-task successor and the ready demotion). N04-A1 replaces
each `pause_request is not None` start check with one coordinator predicate `require_start_permitted(change_id,
kind, identity, coordination)`: no policy → allowed; a K2 drain token for that exact identity → allowed (both
policies); Pause present → refused "Change pause requested"; hold present → allowed only for a matching
exception below, else refused `CoordinationConflictError` "Change revision hold". Exceptions bind exact
identities from durable state; none is a blanket bypass, and none applies while a Pause request exists unless
its K2 token does (a Pause after the intent makes the activation a K2 owner, N09 K2 extension row).

| ID | Exception | Exact identity check (in the start's own transaction) | Phase |
| --- | --- | --- | --- |
| E1 | Activation intent | The replacement adds `design_package_snapshot_intent` (schema 2, D28) whose `operation_id` equals `revision_hold.activation_operation_id` (for `remote-child`, the marker's `resolution_operation_id`; "bound operation" below means either) written by the same A1 transaction, whose `expected_head` equals the journal intent's expected head and whose `package_id` equals the intent's activated package ID (origin `built` for `revision` and `snapshot-reconcile`, `adopted` = T for `remote-child`); a `reassess` A1 adds no snapshot intent and does not use E1 (D31) | A2b |
| E2 | Activation owner steps | Process-local `revision-activation` drain token rebuilt at call start from the journal `intent.json` (operation ID, intent digest) whose ID equals the bound operation (E1); permits only that operation's A1b draft operation `revision-draft-<operation_id>-<observed head>`, A3 ref update, A4 participants, A5 reservation for `_checkpoint_operation_id("branch", change, expected child)`, state publication `revision-<operation_id>`, and A6 | A2b |
| E3 | Reconciliation actions | `acquire_continuation_action` / `start_continuation_action` with kind `reconcile-revision-activation` and `revision_operation_id` equal to the hold's bound operation, or kind `reconcile-revision-snapshot` whose recomputed `snapshot-reconcile` operation ID equals `revision_operation_id` while no other activation is bound; every other kind refused | A2b |
| E4 | Retained same-task successor | Coordinator `acquire` and `prepare_builder_handoff_acquisition` for a Builder writer whose outcome, task and attempt lineage equal the passive `builder_handoff` (route `same-task`); a new task, a Planner claim, a Finalizer attempt or a different task refused | A1 |
| E5 | Hold policy writes | `open_revision_hold` (purpose `revision` with a candidate, or `reassess` bound to one `history_ref` without one, B), `clear_revision_hold`, candidate revise and discard, and the `confirm_revision_criterion` consent-generation writes and ledger append for purposes `revision` and `reassess` (§1.7, B); each a K1-style admission or a declared frontier write, no start | A1, B |
| E6 | Remote-child resolution | `activate_revision` kind `remote-child` whose `adopt_child` equals `remote_activation_pending.child` while the marker is `pending`; its A1 sets the marker `resolving` with this operation's ID; afterwards only E2 for that ID. Also the candidate write and discard of route (ii) (bytes equal to T's package) | A2b |
| E7 | Divergence containment under the marker | The D03 dirty-worktree containment route named for `revision-workspace-unclean`, for this Change only while the marker records a worktree or index divergence (§1.6 Fresh-host restore); it preserves before it cleans | A2b |
| E8 | Quarantined snapshot repair | `repair_quarantined_delivery_state_snapshot` while no activation is bound (it republishes validated local authority and starts no custody); with a bound activation only once `local.json` exists and the republished bytes equal its digests | A1, A2b |
| E9 | Remote-child confirmation capture | `confirm_revision_criterion` purpose `remote-child` while the marker is `pending` and the candidate slot holds exactly T's package (`expected_candidate_package_id` = T's package ID); its transaction also advances the marker's `restored` frontier digest and records the receipt (§1.7) | B |
| E10 | Foreign-head authorization | `resolve_revision_foreign_head` whose operation equals the bound operation and whose foreign head equals the journal's latest `foreign-heads/<F>.json` observation while no `foreign-head.json` authorizes F (§1.6 Foreign Change head) | A2b |

Every other N09-A2 start site stays refused under the hold and under `remote_activation_pending`. The
inventory, from PR #357 (`9a7fff990`), is classified in `tests/test_delivery_worktree_authority.py` by a new
`_HOLD_CLASSES` map beside `_COORDINATOR_PAUSE_CLASSES`, `_MANAGER_PAUSE_CLASSES` and
`_APPLICATION_PAUSE_GATED_ENTRIES`; an entry that is pause-gated but has no hold class fails the test. The
marker admits only E6–E9; the test classifies each site for both policies:

| N09-A2 start site | Hold class |
| --- | --- |
| Coordinator `acquire`, manager `acquire`, `prepare_builder_handoff_acquisition` | refused, except E4 |
| `acquire_continuation_action`, `start_continuation_action` | refused, except E3 |
| `update` (intent-creating snapshot replacement, `_validate_update`), manager `snapshot_design_package` | refused, except E1 (and E2 for the receipt completion) |
| `reserve_publication` | refused, except E2 and existing K2 tokens |
| `start_direct_operation` (`sync-target`, `mark-ready`), manager `sync_with_target` | refused |
| `start_pause_fenced` operator starts: `adopt_external_head`, `adopt_external_head_after_acceptance_attention`, `promote_external_head`, `abort_target_sync_conflict`, `resolve_target_sync_conflict`, `prepare_review_repair`, `reconcile_finalization_head`, `recover_out_of_band_head`, `repair_target_sync_publication`, `recover_publication_baseline`, `recover_change_worktree` | refused (`recover_change_worktree` and `recover_out_of_band_head` stay D03 containment routes: they run after Discard, or after the activation releases; E7 under the marker; a foreign head after the intent uses E10, never `recover_out_of_band_head`) |
| `repair_quarantined_delivery_state_snapshot` (operator start `quarantine-repair:<op>`, Pause-gated since `9a7fff990`) | refused, except E8 |
| `prepare_pause_fence` (`observe-acceptance` provider fence; `complete_change`) | refused before A1; after A1 only the A1b merged-PR path (I3) reaches completion |
| `prepare_runtime_custody_guard` pause-gated class (K7) | refused, except E2 participants; completion class unchanged |
| Finalization repair release (`delivery_runtime.py` request check) and checkpoint publication refusal (`application_publication.py`) | refused, except E2 |

### 1.6 Activation operation

| Step | Durable effect | Crash after this step → restart |
| --- | --- | --- |
| A0 Validate | No authority, branch, index or worktree write. Under the acquisition and checkpoint locks: the per-kind preconditions (table below); §1.5 preconditions; candidate verified and compiles to `contract_digest`; base package equals active; frontier digest equals expected; branch head equals `last_reviewed_commit`, worktree clean (except a U3 (b) handoff, whose bounded walk, collision check and bounds must pass, D25, D30); approval and (from B) applicability review and selected confirmations bound (§1.7); the remote Change branch (`ls-remote`) equals the expected head (T for `remote-child`; else `revision-remote-head-moved`). Git work by kind (D31): `revision` and `snapshot-reconcile` build and pin the child object (§ Deterministic child commit; D32); `remote-child` verifies T at its remote-activation pin and calls no `commit-tree`; `reassess` creates and pins no object | Old approved state; a pin without an intent is reused or replaced by the next A0 (D32); nothing else to replay |
| A1 Intent | One transaction: journal `intent.json` (kind, all §1.4 identities, predecessor generation, expected frontier, branch head, approval, review ID, selected confirmations, handoff disposition, ready-demotion binding: finalization ID, finalized head, PR identity and the permitted observed heads; except for `reassess`, the schema-2 snapshot intent ID, which carries child SHA, tree, dates and pin (D28)) and coordination with `revision_hold.activation_operation_id` and, except for `reassess`, that `design_package_snapshot_intent` (origin `built`, parent = reviewed head; or origin `adopted`, child = T, parent = restored `change_head`) (E1) | Old authority plus intent: readiness `revision-activation-pending`; acquisition refused; replay continues |
| A1b Demote (ready only) | Provider observation of the bound PR. Open, unmerged, not draft, head in the permitted set (the finalized head; for `remote-child` also T; a foreign head F once `foreign-head.json` authorizes it): `return_to_draft` with `exact_head` = the observed head and operation `revision-draft-<operation_id>-<observed head>` under the E2 token, inside the held checkpoint lock (no lock re-entry, no frontier write, no state publication). Already draft at a permitted head: no provider write. Then journal `demotion.json` (observed head, draft receipt ID or `already-draft`) in its own write, before A3 (D26). A head outside the set → § Foreign Change head | Before `demotion.json`: replay observes again; the provider returns the stored receipt for the same operation, or a new observed head gets its own operation. After it: replay never calls the provider (the PR head may already be the child). PR merged before any Git effect → journal `result.json` `superseded-by-merge`, hold cleared, acceptance owner completes (I3); for `remote-child` a merged PR refuses at A0 (`change-attention`) |
| A2 Preserve (U3 (b) only) | `preserve_design_return_workspace` (§ Design-return preservation): walk and collision check re-run on the live worktree, HEAD ref, index ref and raw index, filesystem manifest and blobs; verified against the live worktree; then cleanup to the reviewed head and post-cleanup verification | Replay recognizes the stored manifest and refs, re-verifies, and never captures twice; a partial cleanup completes only on a worktree that matches the capture or the reviewed head path by path |
| A3 Child commit | `update-ref refs/heads/<branch> <expected child> <expected head>` with the pinned object (T for `remote-child`), then the worktree moves to the child for the four package paths (§ Deterministic child commit) | Replay classifies the ref and each package path's index and file state as intent-bound (parent or child bytes only) and completes; any other dirt → contained `revision-workspace-unclean`, nothing written |
| A4 Local commit | One `RuntimeTransaction` across the package and runtime roots: active package files; contract, frontier (confirmations ledger carried byte-identical, N03 I10), admission; generation record `revisions/generations/<operation_id>/`; coordination (snapshot receipt, `last_reviewed_commit` = child, intent cleared, consumed passive custody); pending checkpoint (admitted-design trigger at the child) and pending state publication on the base digest; `ready` and `finalization` cleared with a `head-drift` invalidation when present; journal `local.json` with the digest of every written artifact | Any runtime-root recoverer completes the transaction (A1 fix); the loader accepts the journal-bound local successor; publication replays |
| A5 Publish | Existing owners: checkpoint branch push (with `--force-with-lease=<branch>:<F>` only when `foreign-head.json` authorizes F; otherwise a fast-forward from the expected head), state snapshot, draft PR summary; bounded remote Git with unknown-write readback (N02-C); a remote head other than the expected head, the child or an authorized F → § Foreign Change head | Branch pushed, state not: same host replays the state; a fresh host follows § Fresh-host restore. Remote outage: stays pending with its reason |
| A6 Release | One transaction: journal `result.json`, `revision_hold` cleared (and `remote_activation_pending` for `remote-child`), publication acknowledged; then idempotent cleanup of the candidate slot and the snapshot child pin | Released; the Change continues under the new authority |

- **Who runs it.** The Designer calls `activate_revision` after approval. After any interruption the identical
  call, or the continuation engine action `reconcile-revision-activation` (D02 action framework, selected first
  for the Change, E3), resumes from the journal; the checkpoint supervisor may publish A5.
- **Replay rules.** Same operation ID (D19) and intent digest → resume. Same operation ID, different intent
  digest → `operation-conflict`, no write. A different operation while one is unfinished → `activation-pending`.
  A released operation's identical request returns its `result.json`.
- **Loader.** `_is_unpublished_revision_activation_successor(snapshot, local, journal)` runs before the remote
  branch-head check: the remote snapshot's `package_id`, `authority_digest` and `change_head` equal the journal
  base; the remote Change branch equals either the base head or the journal's expected child; local package,
  contract, admission, frontier and coordination receipt equal the `local.json` digests (or the frontier is a
  recognized pending-publication successor of them); then `_validate_local_snapshot` accepts and publication
  replays. Without a matching journal the existing mismatch and `remote-change-head-ahead` handling stands.

**Per-kind contract (D31).** Every kind uses the journal, operation identity, replay rules and loader
successor above; the table fixes what each kind requires, writes and owns. "n/a" steps are skipped and never
replayed. The ordinary first-checkpoint snapshot is not an activation: it uses only the A2a plumbing.

| Aspect | `revision` | `reassess` | `snapshot-reconcile` | `remote-child` | First-checkpoint snapshot |
| --- | --- | --- | --- | --- | --- |
| Started by | Designer `activate_revision` after approval | Designer `activate_revision` after approval | Engine action `reconcile-revision-snapshot` (selected at readiness `revision-snapshot-stale`) | Designer `activate_revision` after approval, on a fresh host with a `pending` marker | Admitted-design checkpoint trigger (existing owner, `snapshot_design_package`) |
| Hold before A0 | Candidate hold (`purpose: revision`) | `open_revision_hold(purpose: reassess)`, no candidate (E5) | None; A0 and A1 run under the acquisition lock and A1 writes a `purpose: reconcile` hold | The marker acts as the hold (§1.5 E6) | None (K3 snapshot start, N09-A2) |
| Custody during the operation | Journal plus E2 token | Journal plus E2 token | Its D02 continuation start marker (E3) plus the journal and E2 token; finishing the action releases the marker after A6 | Journal plus E2 token; marker `resolving` | Coordination snapshot intent (schema 2) |
| Base / candidate / contract | Active / candidate / candidate's compiled | Active / active / active | Active / active / active | Restored active / T's package / T's compiled | — / active / active |
| Approval; applicability review | Required; required (B) | Required; required against `history_ref` | None (no semantic change) | Required; fresh review required (B) | None |
| Extra request fields | — | `history_ref` | — | `adopt_child` = marker child | — |
| Preconditions beyond §1.5 | Candidate present | Not finalized or ready; no handoff of any route (`revision-custody-retained`) | No journal; branch snapshot package ≠ active package; active `authority.json` = runtime contract digest | Marker `pending`; T verified (§ Fresh-host restore); T's tree and parent equal the computed child's; no handoff (none survives a restore) | Branch at `last_reviewed_commit` |
| A0 Git objects | Builds and pins a new child | None (no object, no pin) | Builds and pins a new child | None built: T verified at `refs/owlbear/remote-activations/<change>/<op>` | Builds and pins a new child |
| A1 snapshot intent (E1) | Schema 2, origin `built` | None (the journal names no child; E1 unused) | Schema 2, origin `built` | Schema 2, origin `adopted`: child = T, tree, dates, message and signature read from T, pin = the remote-activation ref | Schema 2, origin `built` (the snapshot owner's own intent; no journal) |
| A1b | Ready only | n/a (refused while finalized or ready) | Ready only | Ready only; permitted heads: finalized head and T | n/a |
| A2 | U3 (b) handoff only | n/a | n/a (refused with any handoff) | n/a | n/a |
| A3 | New child via the schema-2 intent | n/a (no head move) | New child of the same active package | No new commit: CAS `update-ref` to T, path-limited checkout | New child via the schema-2 intent |
| A4 writes | Package, contract, frontier, admission, generation, coordination receipt, checkpoint and state queue, `head-drift` when finalized | Frontier (binding reset plus records), generation, state queue | Coordination receipt, generation, checkpoint queue, `head-drift` when finalized | As `revision` | Coordination receipt and `last_reviewed_commit` (existing owner) |
| A5 | Branch push, then state | State only | Branch push, then state | State only; the branch push is a verified no-op (remote already T) | Existing checkpoint publication |
| Loader successor (remote branch) | Base head or expected child | Base head only | Base head or expected child | T only | Existing replay |
| Restart owner | Identical call or `reconcile-revision-activation` | Same | `reconcile-revision-snapshot` only | Same as `revision` | Checkpoint supervisor's snapshot replay |

**Deterministic child commit (A2a; D17, D28, D32).** The existing owner writes package files into the
worktree, stages them and runs `git commit` (`workspace_snapshots.py:241-255`); its rollback runs only for an
`Exception` (`:257`), not a process death, and its replay requires a clean worktree (`:238`, `:294`), so a crash
between the write and the commit can never resume. Its durable intent, `ChangeDesignPackageSnapshotIntent`
schema 1 (`workspace_models.py:1055` on `dev`, `:1103` at `9a7fff990`), holds only operation, Change, package, branch,
worktree and expected head: no dates, tree or child SHA, so no caller can replay deterministically. N04-A2a
replaces `_commit_design_package_snapshot` for every caller (first-checkpoint snapshot and, from A2b,
activation and legacy reconcile):

1. **Carrier.** `ChangeDesignPackageSnapshotIntent` schema 2 (widen 1, 2) adds `blob_ids` (the four package
   blobs), `child_tree`, `child_commit`, `commit_time` (integer UTC seconds, fixed when the intent is first
   written), `message`, `signed`, `pin_ref` and `origin` (`built`, or `adopted` for a `remote-child` T whose
   fields are read from the object; A2a defines both values and refuses to write `adopted` until A2b); author
   and committer are the constant `OwlBear <owlbear@localhost>`. `intent_id` covers every field. It is the only
   carrier: an activation journal names its `intent_id` and never repeats the child identity.
2. **Build and pin (before the intent).** `git hash-object -w` the four files; a temporary `GIT_INDEX_FILE`
   reads the parent tree and `update-index --cacheinfo` sets the four paths; `write-tree`; `commit-tree` with
   parent = expected head, the constant identity, both dates = `commit_time`, message `chore: snapshot admitted
   Design package (<change>, <operation_id>)` (`chore: activate Design revision (…)` for activations). The
   object is pinned at `pin_ref` = `refs/owlbear/snapshot-children/<change>/<operation_id>` with
   `update-ref <pin> <child> ""` (create-only), then the intent is written. No hook runs (D32).
3. **Signing (D32).** The repository's own `commit.gpgsign` decides, as for today's `git commit`. Unsigned:
   `--no-gpg-sign`. Signed: one `commit-tree -S`; a signing failure refuses `snapshot-signing-failed` before
   the intent. Either way the pinned object is the authority: replay reads it, never recomputes or re-signs; a
   missing pinned object after the intent is contained `snapshot-child-lost` (no write). A pin without an
   intent (crash between pin and intent) is reused by the next A0 when its parent, tree, identity and message
   match (its `commit_time` is read back from the object); otherwise the next A0 deletes it (no authority) and
   pins anew.
4. **Move (A3).** `update-ref` with the expected old value (CAS), then for the worktree (whose HEAD follows the
   branch): `git checkout <child> -- <four paths>` updates index and files for those paths only.
5. **Replay classifier**, per package path: index entry and file bytes each equal either the parent's or the
   child's blob; branch at the expected head or the expected child; every other path clean
   (`status --porcelain=v1 -z --untracked-files=all` lists only package paths). Then it finishes the remaining
   sub-steps. A package path with other bytes, any other dirty or untracked path, or a branch elsewhere →
   contained `revision-workspace-unclean` with the exact paths; nothing is written or deleted.
6. **Receipt and cleanup.** The coordination update storing the receipt clears the intent; the pin is deleted
   afterwards by idempotent cleanup (a leftover pin whose operation has a receipt is deleted at the next call).
7. **Existing schema-1 intents** (a pre-N04 crash) are treated at the next snapshot call under the publication
   lock: branch at a direct child with the legacy message and the package bytes → the existing legacy replay
   completes the receipt (the commit is already durable on the branch); branch at the expected head with a
   clean worktree → step 2 first builds and pins the child for the schema-1 intent's operation ID and package
   (its `commit_time` fixed then), and only then one coordination update, under a CAS on the exact schema-1
   intent bytes, replaces it by the schema-2 intent naming that pinned child (D39); branch at the expected head
   with only package paths dirty, each index entry and file equal to the parent's or the target bytes → those
   paths are restored to the parent, then upgraded as before; anything else → contained
   `revision-workspace-unclean` with the paths. A crash after the pin and before the replacement leaves the
   schema-1 intent in force and the pin is reused under step 3's rule; a crash after the replacement replays
   the schema-2 intent; at no point does a schema-2 intent name an unbuilt or unpinned child.

**Design-return preservation (A2b, U3 (b); D16, D25, D30).** `quarantine_dirty_worktree` is not reused: it
builds one tree
from the filesystem through a temporary index (`workspace_snapshots.py:652-670`), so staged content that differs
from the file is lost; `reset --hard` then discards the real index (`:451-452`); ignored files are neither
inventoried nor verified, and Git trees keep only the executable bit. D03's raw preservation
(`workspace_preservation.py:284`) refuses staged content (`:328-330`) and is bound to a recovery journal. N04-A2b adds
`preserve_design_return_workspace(change_id, operation_id)` in `workspace_preservation.py`, reusing D03's
private store, index resolution, split-index refusal, path validation and bounds (`_MAX_PRESERVED_*`):

| Component | Captured | Verified before cleanup |
| --- | --- | --- |
| HEAD | Branch head (retained unreviewed commits) pinned at `refs/owlbear/preserved/<change>/<operation_id>/head` | Branch head and worktree HEAD equal it; reviewed head is an ancestor |
| Index | Raw index bytes (owner-private), entry records (path, mode, stage, object ID) and a tree written from a copy of the real index, committed under the head and pinned at `…/index` so staged blobs stay reachable; unmerged entries, split index, sparse or skip-worktree entries and gitlinks refused before the intent (A0) | Raw index digest and entry records equal the live index |
| Filesystem | Bounded walk (below): every untracked or modified file with bytes, every symlink (target), every non-ignored directory the walk visits with its full permission bits and an `empty` flag (untracked and empty ones included, which `git status` omits; Git keeps no directory modes), and every tracked clean file whose permission bits differ from Git's canonical 0644/0755 for its index mode (mode exception: path, `lstat` mode, index object ID; no bytes). Each entry: type, full permission bits, size, sha256 where bytes exist; bytes in `blobs/<sha256>` | Walk manifest recomputed from the live worktree equals the stored one |
| Ignored | Each ignored file (path, type, mode, size, sha256) and each ignored directory as one undescended entry (path, mode), left in place; every entry passes the collision check and the rule-change check | Inventory, collision check and rule-change check equal before cleanup; inventory equal after it |

**Bounded walk (D30).** `os.scandir` from the worktree root with `lstat`; symlinks are recorded, never
followed, and symlinked ancestors are refused; the `.git` entry is skipped; entries Git reports as ignored by
`status --porcelain=v1 -z --ignored=matching --untracked-files=all` are recorded but not descended. Two bounds,
both checked in A0 before the intent: visited entries ≤ `_MAX_DESIGN_RETURN_WALK_ENTRIES` (fixed at A2b start
from the largest supported fixture, G16) and recorded entries and bytes within D03's `_MAX_PRESERVED_PATHS`,
`_MAX_PRESERVED_FILE_BYTES` and `_MAX_PRESERVED_TOTAL_BYTES`. A nested repository (a directory holding `.git`)
is refused. Clean tracked files with canonical modes are reproduced from the head and index refs; restore
applies each recorded file and directory mode explicitly (directories last, deepest first, so a restrictive
mode never blocks writing its contents), so the restoring process's umask cannot change the result.

**Collision check (D25).** `reset --hard <reviewed head>` writes every path tracked at the reviewed head R and
replaces a file by a directory or the reverse, so it can overwrite or delete an ignored entry whose bytes the
inventory does not hold (for example, a file tracked at R, deleted by a retained commit and later recreated as
an ignored local file). Let P(R) be `ls-tree -r -z --name-only R`. An ignored entry at path p collides when
p ∈ P(R), p is an ancestor directory of some r ∈ P(R), or some r ∈ P(R) is an ancestor of p. A0 computes
the check from the walk and refuses `revision-preservation-collision` with the paths before the intent; nothing
is captured, moved or cleaned. A2 repeats it on the live worktree before cleanup; a new collision fails
verification and nothing is cleaned. Untracked (not ignored) entries need no check: their bytes are captured
and verified before cleanup.

**Rule-change check (D34).** Ignore status comes from in-tree `.gitignore` files, `$GIT_COMMON_DIR/info/exclude`
and `core.excludesFile`; only the in-tree files change with the reset. A retained commit, a staged edit or a
working-tree edit can add a rule absent at R, so an entry ignored now (bytes never captured) becomes untracked
after `reset --hard R`. A0 therefore classifies every ignored-inventory entry under R's rules: when the set of
`.gitignore` paths and their bytes in the live worktree equals `ls-tree -r R`'s, the rule sets are identical
and nothing flips; otherwise an owner-private scratch repository (outside the worktree) receives R's
`.gitignore` blobs at their paths, a copy of `info/exclude`, the same `core.excludesFile`, and a placeholder of
the recorded type at each inventory path, and `check-ignore --no-index -z --stdin` reports which entries R's
rules ignore. An entry (file, or undescended directory) not reported, or any evaluation failure, refuses
`revision-preservation-collision` with detail `ignore-rule-change` and the paths before the intent; nothing is
captured, moved or cleaned. The check is conservative: an entry is accepted only when R's rules ignore that
exact path. A2 repeats it on the live worktree before cleanup. The reverse flip (an untracked entry that R's
rules ignore) needs no refusal: its bytes are captured and cleanup deletes it explicitly.

Cleanup is `reset --hard <reviewed head>`, then the owner deletes exactly the manifest's untracked entries
(files and symlinks after an `lstat` and sha256 re-check, then directories deepest first when empty); `git clean`
never runs, so an entry the manifest does not hold is never deleted by Delivery. Post-cleanup verification:
worktree at the reviewed head, index equal to its tree, no untracked path, ignored inventory unchanged; it is a
consistency check, not the guard (the collision and rule-change checks are). Bounds exceeded or a refused
entry kind is detected in A0 and refuses `revision-preservation-unsupported` before the intent. The
receipt `DesignReturnPreservationReceipt` (in `local.json` and the revised Planner context) names the refs and
manifest digest. A test-only `restore_design_return_preservation` into a scratch worktree reproduces HEAD,
`git ls-files -s` entries and the filesystem manifest exactly (merge-blocking falsifiers, §3.3).

**Fresh-host restore (A5; D18).** On a fresh host, a crash after the branch push and before the state push
leaves the remote branch one commit ahead of the snapshot's `change_head`. Today's loader then raises
`_DeferredRemoteStateReconciliationError` (`delivery_application_loader.py:734-751`, `:2211-2221`) and does not
restore the Change: it is invisible and has no route. N04-A2b adds a verified restore policy:

1. **Classify.** The remote tip T is a *verified activation child* iff its only parent is `change_head`, its
   diff touches only the four package paths, its message matches the activation message pattern with an
   operation ID, and its package verifies (`DesignPackageStore` manifest and authority checks) while the package
   at `change_head` equals the snapshot's `package_id`. Anything else keeps today's diagnostic.
2. **Restore old, preserve T.** Restore the snapshot's approved state at `change_head` (package, local branch
   and worktree at `change_head`), pin T at `refs/owlbear/remote-activations/<change>/<operation_id>` (local
   only), and record in the restore transaction `ChangeCoordination.remote_activation_pending {operation_id,
   child, parent, state: pending, resolution_operation_id: null, replacement_id: null, restored}`. `restored`
   fences everything the restore wrote: package ID, contract, admission and frontier digests, the coordination
   digest computed with the marker omitted, branch head, raw index digest and the bounded-walk manifest digest
   of the clean worktree (D30), each measured after the restore, plus `captures` (revision-confirmation receipt
   IDs appended under E9, initially empty). Readiness `revision-remote-activation-pending`; every start is
   refused except E6–E9 (§1.5); state publication is suppressed while the marker exists, and E9's receipts are
   the L-row replay authority for the local ledger suffix, as for a retained handoff (§1.7). The remote branch
   is never pushed to, reset or force-updated from this host, and T is never treated as reviewed authority.
3. **Resolve.**
   - (i) **Origin publishes (D29, D38).** At a later startup the remote snapshot's `change_head` equals T. The
     loader replaces the old state with the new snapshot only if every `restored` value still matches (package,
     contract, admission, frontier, coordination without the marker, branch, index and walk manifest),
     `restored.captures` is empty, no custody, candidate, hold or pending publication exists and the marker is
     `pending`. The replacement has a durable owner that survives every crash until it completes:
     1. *Replacement intent.* One runtime transaction writes
        `remote-activations/<operation_id>/replacement.json` (`RemoteActivationReplacement` v1: replacement ID,
        remote state commit, snapshot digest, T, `change_head`, the matched `restored` values) with the exact
        snapshot bytes beside it (`replacement-snapshot.json`), and sets the marker `replacing` with that
        `replacement_id`. Replay never re-reads the remote: a later remote move does not change this
        replacement.
     2. *Git steps.* CAS `update-ref` from `change_head` to T, then `git checkout T -- <four package paths>`;
        on restart the A3 classifier (§ Deterministic child commit step 5, child = T) finishes them or contains
        `revision-workspace-unclean` with the paths (E7 then applies).
     3. *Install.* One runtime transaction installs the stored snapshot's authority (package, contract,
        admission, frontier, coordination with its receipt and `last_reviewed_commit` = T), clears the marker
        and writes `replaced.json`; root-aware recovery completes a torn transaction (D3).
     4. *Cleanup.* Idempotent deletion of the remote-activation pin.

     While the marker is `replacing`, the loader runs this replay before the Change becomes available,
     acquisition stays refused and the loader's local-versus-remote checks accept exactly the replacement's
     intermediate states (branch at `change_head` or T; local authority old or the stored snapshot's). A
     mismatch before step 1 replaces nothing. A differing index or worktree is
     contained: readiness stays `revision-remote-activation-pending` with detail
     `remote-activation-local-divergence` and the exact paths, and the user resolves it through E7, after
     which the next startup re-evaluates. A differing package, contract, admission or coordination cannot come
     from any Delivery writer while the marker refuses them, so it is treated as out-of-band state: the
     existing bootstrap integrity diagnostic makes the Change unavailable, nothing is overwritten (V20). With
     `restored.captures` non-empty the loader replaces nothing and shows detail
     `remote-activation-local-confirmations`: the user either continues (ii) or, once the remote snapshot
     shows T, discards the candidate under E6, which in the same transaction moves the captured receipts to
     `revision-confirmations/retired/<marker operation_id>/` (H, never an L-row source) and empties `captures`;
     the next startup then runs (i). The retired confirmations are listed in the revision context.
   - (ii) **Origin lost (D26).** `/design <change>` offers T's package as the candidate (the candidate slot is
     written under E6 only with bytes equal to T's package); candidate-scoped confirmations for its reused
     human steps are captured under E9 (§1.7). A0 refuses while the remote snapshot's `change_head` is already
     T (detail `remote-activation-origin-published`; (i) applies). After user approval, a fresh applicability review
     and full A0 validation, `activate_revision` kind `remote-child` with `adopt_child` = T runs under E6: its
     A1 sets the marker `resolving` with its operation ID in the intent transaction; T's parent and tree must
     equal the computed child's (message and dates aside; else `remote-child-mismatch` before the intent), so
     A3 moves the local branch to T and A5 pushes no
     branch. For a formerly ready Change the restored state is ready at `change_head` while the provider's PR
     head is T (the origin's A1b preceded its push): A1b observes the PR and accepts T as a permitted head;
     already draft → no provider write; ready at T (re-marked externally) → `return_to_draft` with
     `exact_head` = T; merged → refused at A0 `change-attention`. A4 clears `ready` and `finalization` with
     `head-drift` (change_head → T); A6 clears the marker.
   - (iii) Any other revision is refused `revision-remote-activation-pending` until (i) or (ii) (G12).

**Foreign Change head after the intent (A1b, A5; D35).** A0 refuses before the intent when the remote Change
branch is not at the expected head (`revision-remote-head-moved`), so a foreign head F appears only after the
intent, when another writer pushes the Change branch: A1b observes the PR head F outside its permitted set, or
the A5 push readback finds the remote branch at F (neither the expected head, the child nor an authorized
head). The activation may only roll forward (I3), and D03's `recover_out_of_band_head` cannot help: its caller
refuses a finalized Change (`application_recovery.py`, "out-of-band head recovery requires an unresolved
nonterminal Change"), it resets the local branch to the reviewed head and runs as a pause-fenced operator start
that queues checkpoint publication, which would race A5, and it is refused under the hold. N04 settles the
route inside the activation:

1. **Observe.** The step writes nothing to Git or the provider. It journals
   `foreign-heads/<F>.json` (F, source `provider` or `remote-branch`, PR state: open draft, open ready or
   merged, observed time), create-only, and the activation stays pending with readiness
   `revision-activation-pending` detail `revision-foreign-head` naming F. Replay re-observes: if the remote
   and PR return to a permitted head, the activation continues without authorization; a merged PR before any
   remote Git effect of the activation ends `superseded-by-merge` (I3), whatever its head, and the acceptance
   owner reports any head mismatch as today.
2. **Authorize (user only).** `resolve_revision_foreign_head(change_id, operation_id, foreign_head)` runs under
   E10 and asks the user through the D13 `Resolve` boundary with its own consent generation (§1.7, I13); the
   question shows F, its commits not in the reviewed head, the PR state and that F will be preserved locally
   and replaced on the remote branch by the activation's child. Predecessor fences, all re-checked in the
   authorizing transaction: the bound operation (E1) and its intent digest; F equal to the latest observation and
   to the provider and `ls-remote` heads read in this call; the local branch at the expected head or the
   expected child (A3 classifier); for a formerly ready Change the journal's finalization ID, finalized head and
   PR identity unchanged; no `result.json`.
3. **Preserve, then record.** `fetch` F and pin it create-only at
   `refs/owlbear/preserved/<change>/<operation_id>/foreign-<F>` (local only, like D03 preservation); then one
   transaction answers the consent generation and writes `foreign-head.json` (F, pin, observation digest,
   generation ID). A crash between the pin and the transaction leaves the generation open and the pin reused.
4. **Continue.** F joins the permitted set: a ready PR at F gets `return_to_draft` with `exact_head` = F and
   operation `revision-draft-<operation_id>-<F>`; a draft PR at F gets no provider write; A5 pushes the child
   with `--force-with-lease=<branch>:<F>`, and its readback treats the remote at the child as done and at F as
   not yet pushed. A later different head F′ repeats steps 1–4 with its own records; an authorization never
   covers another head.

Declining (or cancelling) consumes the generation and changes nothing else; the activation stays pending with
the same detail, and a new call asks again. F's commits are never adopted into the revision; a later Builder
may re-apply them from the pin.

**Generation history (D20).** Today `revisions/<contract digest>/` is written with create participants
(`delivery_admission.py:425-429`); a second departure from the same contract writes different frontier bytes to
the same path and the transaction is refused (`runtime_transaction.py:357`), so A → B → A → C cannot activate C.
Each activation instead writes `revisions/generations/<operation_id>/{contract,frontier,admission}.json` (the
replaced authority, create-only) and `generation.json` (`RevisionGeneration` v1: change, operation, kind,
ordinal = previous max + 1, replaced contract, frontier and admission digests, successor contract digest,
predecessor operation ID or `null`). The current generation is the highest ordinal; reads never scan legacy
directories. Legacy `revisions/<64-hex>/` directories stay read-only H history and are addressable only as
`legacy:<64-hex>` history refs whose `contract.json` digests to that name (frontier-named stranded-repair
directories are excluded).

- **Legacy reconcile (live B1).** No journal, `coordination.design_package_snapshot.package_id` differs from
  the active package, and the active `authority.json` equals the runtime contract digest → readiness
  `revision-snapshot-stale` and the engine action `reconcile-revision-snapshot`: a journal of kind
  `snapshot-reconcile` with base = candidate = active, A1, A3, A4 (coordination receipt, generation record and
  the queued checkpoint only), A5, A6. No package, contract or binding change; no user approval (no semantic
  change). Its operation ID differs from any `reassess` of the same package (D19).

### 1.7 Applicability

**Impact view** (B; engine, pure; `preview_revision_impact`). Inputs: base contract, candidate contract, current
frontier, history frontier for reassessment, N03 evaluator. Per candidate criterion (N03 §1.4 identities): mapping
`unchanged` (same ID and version), `revised` (same ID, new version), `new`, `legacy-version-match` (legacy IDs
match only by version), `legacy-unmatched`; prior N03 status under the base; the observations, results and
applicability records that established it. Also retired criteria, `_invalidated_outcomes`, affected blocks and
requests, custody and handoff impact, and per reused human step the confirmation it needs. `impact_digest` =
sha256 of its canonical JSON computed with the frontier's `confirmations` ledger omitted (cited receipts still
name their own confirmation IDs), so capturing a candidate-scoped confirmation after the review does not stale
the review; A0 checks every selected confirmation against the live ledger.

**Reviewer** (`build-reviewer`, mode `applicability`): given the impact view, the contract delta, the cited
receipts and the code diff since each cited commit over the task's maintained surfaces. It returns
`DeliveryApplicabilityReview{review_id, impact_digest, author_id, reviewer_id, dispositions, reviewed_at}`.

| Disposition | Engine-checked rule | Evaluator effect (N03 fold) |
| --- | --- | --- |
| `reusable` | ≥ 1 cited receipt with a satisfying verdict (or a legacy receipt under [U1](#u1--may-reviewed-applicability-attribute-legacy-evidence) (a)), at an ancestor of the current head, that covered this criterion ID or a version-matched legacy criterion. A cited `waived` or `human-confirmed` receipt, and a legacy human-procedure receipt, also needs an applicable ledger confirmation (§ Confirmation authority) | `covered` (`waived` for a cited waiver) |
| `partial` | Cited receipts plus `missing_scope` (1–240 chars) | `missing`, owner `agent`, scope as reason |
| `invalidated` | `changed_assumption` (1–240 chars) names the defeated code, procedure, target or condition | `uncovered` |
| `unknown` | `search_note` (1–240 chars): which history was searched | `unknown` |

Completeness: exactly one disposition per candidate criterion with prior evidence in an invalidated outcome;
criteria without prior evidence need none (they are `uncovered`). `reviewer_id != author_id`. The review binds
`impact_digest`; a stale digest is refused (`applicability-review-stale`).

**Records.** Activation writes `DeliveryApplicabilityRecord{record_id, operation_id, acceptance (new ref),
disposition, sources (≤ 8 embedded receipts, schema 1 or 2, unchanged, plus their source acceptance refs),
confirmations (≤ 8 selections {source_observation_id, confirmation_id}, D23, D27), rationale (≤ 480),
missing_scope, changed_assumption, search_note, review_id, reviewer_id}` onto the binding of each invalidated
outcome. The N03 fold processes a binding's applicability records before its task results, so later evidence
closes or reopens gaps (N03 D5).

**Confirmation authority (D23; N03 (as amended by #360) §1.5, I6, I10, §1.9).** Portable authority for a
reused human step or waiver is the Change-wide append-only ledger `DeliveryFrontier.confirmations`, which
travels in every snapshot and which `_reset_binding`, request-history moves and activation leave unchanged. It is
never a request, a request in `revisions/` history or a caller provenance value. For each `reusable` record,
every cited source that needs a human step has exactly one selection; the source receipt stays embedded
unchanged with its original `confirmation_id`:

- **Same ID and version** (`unchanged`): the selection is the source's own `confirmation_id`.
- **`revised`, `new` or legacy-matched criterion, or a legacy (schema-1) human-procedure receipt under U1 (a):**
  the source's original confirmation is `stale-acceptance-version` for the candidate (N03 §1.9; the impact view
  shows it as such), so the selection must name a candidate-scoped confirmation captured by
  `confirm_revision_criterion` (below). No selection, or a selection of the original →
  `applicability-confirmation-version-changed`.
- The engine resolves each selection with `resolve_confirmation(frontier, id)` and checks it with
  `confirmation_applies` on a `DeliveryConfirmationUse{change_id, outcome_id, acceptance refs, procedure,
  required decision}` (N04-B generalizes N03's observation argument to this view; the observation path becomes
  one caller; G13): same Change; the record's outcome; scope containing the exact candidate `(acceptance_id,
  acceptance_version)`; procedure equal to the source receipt's `command_or_procedure`; the affirmative
  decision for the source (`waive` for a waiver, `passed` for a human-confirmed or legacy human receipt).
- The check runs three times with identical inputs and results: at A0 (before the intent), in the evaluator
  fold after the reset moved requests to history, and after a fresh-host restore from the published snapshot.
  An ID absent from the ledger is `confirmation-unresolved`. A B1-style request resolved through the old
  caller-provenance route confers nothing (N03 R14).

**Candidate-scoped confirmation capture (D27).** N03's boundary answers only an existing scoped request of the
active frontier through MCP `answer`, and a candidate criterion version is not in the active contract, so N04-B
adds one capture tool that reuses N03-A's D13 machinery unchanged:
`confirm_revision_criterion(change_id, purpose: revision | reassess | remote-child,
expected_candidate_package_id, expected_frontier_digest, history_ref | None, outcome_id, scope:
DeliveryConfirmationScope, source_observation_id | None)`.

- **Boundary.** One server-injected `confirmation: Annotated[DeliveryConfirmationOutcome,
  Resolve(revision_confirmation_question)]`, registered by N03-A's `_flatten_tool` change and absent from the
  input schema; channel check first (`channel-unavailable`); legacy and modern routes; the default
  `RequestStateBoundary` binds the method, tool and the digest of all eight arguments; no lock is held while
  the user answers. Every question is bound to one consent generation (below), which its first answer consumes.
  Cockpit has no capture route and refuses `channel-unavailable` until N03 U2 decides (G17).
- **Question, by purpose (D37 fences).** Rendered only when every fence of its purpose holds; the candidate
  criteria are those of the package named by `expected_candidate_package_id`, and every scope ref must be a
  criterion of `outcome_id` in its compiled contract at that exact version:

  | Purpose | Policy state | Candidate package | Source receipt (`source_observation_id`) | Hold exception |
  | --- | --- | --- | --- | --- |
  | `revision` | `revision_hold.purpose = revision`, no bound activation | The candidate slot's ID | Current frontier or a generation record of this Change | E5 |
  | `reassess` | `revision_hold.purpose = reassess` with `history_ref` equal to the argument, no bound activation | The active package's ID (reassessment's candidate = active) | The history frontier named by `history_ref` | E5 |
  | `remote-child` | `remote_activation_pending.state = pending`, no hold | The candidate slot's ID, equal to T's package | The restored frontier | E9 |

  The frontier digest must equal `expected_frontier_digest`; `history_ref` is required for `reassess` and
  refused otherwise. The question shows the Change, purpose, outcome, each criterion ID, version and
  statement, the procedure, and for a reuse the source receipt's verdict, exact commit and procedure text
  (`scope.procedure` must equal it).
- **Request and receipt.** The engine synthesizes `DeliveryRequest{request_id: "REQ-REVISION-" +
  sha256(canonical {change_id, purpose, candidate_package_id, history_ref, outcome_id, scope,
  source_observation_id})[:24], kind: decision, outcome_id, summary, applies_to: scope}`. It is never placed in
  a binding (it is not active work and may name candidate versions). On an applied `accept`, one transaction
  under the `expected_frontier_digest` CAS, through the declared facade writer `append_revision_confirmation`
  (`_NORMAL_CHANGE_MUTATIONS`, K7): the frontier successor equals its predecessor plus one ledger entry built as
  N03 §1.5 builds it (`request_id`, `scope`, `decision`, `channel: mcp-elicitation`, `question_digest`) and
  nothing else; `RevisionConfirmationReceipt` v1 `{change_id, purpose, candidate_package_id, history_ref,
  outcome_id, request (resolved: provenance user-confirmed, confirmation_id), confirmation, generation_id,
  predecessor_frontier_digest, successor_frontier_digest, receipt_id}`; the consent generation answered
  `confirmed`; and for `remote-child` the marker's `restored.frontier` advanced to the successor digest with
  the receipt ID added to `restored.captures` (§1.6 Fresh-host restore).
- **Consent generation (D36; aligned with N05 D14 `merge_consent` in #360 `f4d09d774`).** The SDK
  authenticates `request_state` but does not consume it, and a decline, a cancel or an unapplied accept leaves
  the frontier unchanged (N03 D13 *Single use* says so), so the frontier digest alone cannot stop a replay of
  the original state with an affirmative answer. N04 therefore uses its own server-owned single-use generation,
  the same shape as N05's:
  - *Record.* `RevisionConsentGeneration` v1 (family `revision_consent`,
    `runtime/changes/<change>/revision-consents/<sequence>.json`, per-Change zero-padded sequence, exclusive
    create, M): Change, subject (the synthesized request ID, or `foreign-head:<operation_id>:<F>`), sequence,
    `generation_id` (256-bit nonce from `secrets`), created time, state `open` or `answered` with its
    disposition: `confirmed` (with `confirmation_id`), `authorized` (foreign head), `declined` (decline or
    cancel) or the typed refusal of the re-check (`frontier-stale`, `candidate-stale`, `ledger-full`,
    `confirmation-scope-invalid`, `revision-hold-absent`, `foreign-head-stale`).
  - *Issue.* The first round creates the generation under the fences above (a short coordination-lock
    transaction, released before asking) and seals `generation_id` in the `Resolve` dependency's request state,
    which the boundary authenticates with the method, tool and argument digest (G19). The legacy route keeps
    it in the call.
  - *Consume.* An answer applies only to the generation its state carries, and only while that generation is
    the subject's latest and `open`. In one transaction under the fences it writes the generation `answered`
    with its disposition and, for an `accept` that passes the re-check, the ledger append and receipt above (or
    the foreign-head record). Every answer consumes its generation: accept, decline, cancel and a failed
    re-check alike.
  - *Retry.* A continuation round whose generation is `answered` returns the recorded disposition and writes
    nothing; it never appends, never records a receipt and never elicits again. A round whose generation is
    absent, or is not the subject's latest, refuses `ERR_DELIVERY_CONFIRMATION` `question-closed`. A new call
    (first round) asks again under a new generation.
- **Replay.** The ledger append is published by the normal pending state publication. While a retained handoff
  or the remote-activation marker suppresses publication (P9, §1.6), the receipt is replay authority: N04-B
  adds it to N03's L row as a ledger-suffix source; an entry no receipt binds, a bound entry missing locally, a
  byte difference or a broken predecessor chain fails bootstrap exactly as in N03 (V20). Receipts retired under
  §1.6 (i) are history, never L-row sources.
- **Selection, not creation.** Activation and reassessment still never append (I11): the confirmation exists in
  the ledger before A0, and the record's selection names it.

The impact view shows each prior `waived` status and each cited confirmation, so the approval names every waiver
the revision ends.

**Finalization basis (D24).** N03's basis digest (`{schema: 1, contract_digest, change_head, diff_base,
result_digests, acceptance}`) does not cover applicability records or their confirmations, yet both decide
coverage. When any binding carries applicability records, N04-B computes basis schema 2: schema 1 plus
`applicability` (record IDs in fold order) and `confirmations` (each record's selections in fold order, each
with its decision). Without records the basis stays schema 1 byte-identical. `semantics` adds the
records and cited confirmations within N03's all-or-nothing budget. A review bound to the old basis is refused
`review-basis-stale` whenever applicability changes, including at the same head (reassessment moves no head).

**Carry-forward replacement.** `preserve_unresolved_outcome_ids` and `_carry_forward_unresolved_binding` are
removed (no compatibility path). An invalidated outcome is reset to Planning as today (prior tasks, results,
blocks and requests stay in the generation record) and gains its applicability records. Unchanged outcomes keep
their bindings, blocks and requests. `show_plan_context` adds the outcome's revision view (statuses, prior task
summaries from history), so the Planner plans only `uncovered`, `missing` and `unknown` criteria; a Builder
raises an N03-scoped request (`applies_to`) only for a genuinely human step.

**Reassessment** of an already admitted revision with a blanket carried request (live B1): an activation of kind
`reassess`. Request: `{kind: reassess, change_id, expected_base_package_id = expected_candidate_package_id =
active, expected_contract_digest = active, expected_head, expected_frontier_digest, history_ref, approval,
applicability_review}`; `history_ref` is `generation:<operation_id>` or `legacy:<contract digest>` (§1.6
Generation history) and is part of the operation ID (D19). Selection: the impact view lists every eligible
history ref with its contract digest, outcome stages and evidence counts; the Designer proposes the generation
that the carried request came from (its `binding.requests` entry names the old request ID found in that
frontier), and the user approves that exact ref; `open_revision_hold(purpose: reassess, history_ref)` binds it,
and captures and A0 require the same ref; the engine refuses a ref whose contract digest equals the active
one (`reassess-history-invalid`) or that is unreadable. Impact base = that history contract; prior evidence =
that history frontier. It resets the affected binding (the blanket request moves to the new generation record),
writes reviewed records and changes no package, contract or branch, so it is refused while `finalization` or
`ready` exists (`reassess-requires-unfinalized`). The Designer presents it and the user approves, because it
supersedes the user's open request. For B1 the ref is `legacy:216a787…` (P1); a reconcile then a reassess are
two operations with distinct IDs and journals.

### 1.8 Persisted families, versions and migration

Version numbers are assigned at merge (N05-P format-marker rule: whichever phase merges second renumbers and
reruns LC). "Widen" follows N03 I2: `Literal[old, new]`, old instances validated unchanged and constrained to
old content, new fields omitted when `None` or empty; every earlier readable version stays readable. Baseline at
N04-A1 start: coordination v2 (N09-A2), frontier 19 with `confirmations` and 18 `readable-legacy` (N03-A as
amended by #360: `Literal[18, 19]`, reads never write), snapshot 3 (2 native, 1 read-upcast), the N03 §1.7
receipt widenings, format marker 2 (N03) plus N09-A2's step; any intervening merge (N05-B, N08) is absorbed by
the renumber rule.

| Family | Change | Phase | Old records |
| --- | --- | --- | --- |
| `coordination` | v2 → v3 (widen 2, 3): `revision_hold` (omitted when `None`); K4 digest excludes it | A1 | Unchanged; first write emits v3 |
| `coordination` | v3 → v4 (widen 2–4): nested `design_package_snapshot_intent` schema 2 (widen 1, 2; §1.6 carrier with `origin`, D28); a v2 or v3 instance holding a schema-2 intent is rejected; schema-1 intents stay valid and are treated by §1.6 step 7 | A2a | Unchanged; first write emits v4; a pending schema-1 intent is replaced only by the snapshot owner, after its child is pinned (D39) |
| `coordination` | v4 → v5 (widen 2–5): `revision_hold.activation_operation_id`, `purpose` and `history_ref`; `remote_activation_pending` (with `state` `pending` \| `resolving` \| `replacing`, `resolution_operation_id`, `replacement_id`, `restored` including `captures`); nested `continuation_action: ChangeContinuationAction` kind widened with `reconcile-revision-activation`, `reconcile-revision-snapshot` and optional `revision_operation_id` (required for those kinds, `exclude_if` None); an older instance holding any of these is rejected; K4 digest excludes the new fields | A2b | Unchanged; first write emits v5 |
| `action_receipt` (R, unversioned: `intent.json`, `started.json` = `ChangeContinuationAction` content; `result.json` = `DeliveryEngineActionResult`) | Same nested widening; existing receipt bytes, `continuation_start_recorded` byte equality and operation IDs unchanged (new fields absent); result kinds and reason codes reused (re-checked at A2b start; a needed new value is an A2b schema change under this row) | A2b | Unchanged; covered by A2b's marker step (a predecessor refuses the marker before parsing) |
| `package_candidate` (new) | `runtime/package-candidates/<c>/manifest.json` (owner `DesignPackageManifest` v1, M), `authority.json` (`allow_empty`), documents (`read=False`) | A1 | None exist |
| `revision_activation` (new) | `revision-activations/<op>/(intent\|demotion\|local\|result\|foreign-head).json` and `revision-activations/<op>/foreign-heads/<F>.json`: models v1, R | A2b | None exist |
| `revision_consent` (new) | `revision-consents/<sequence>.json` (`RevisionConsentGeneration` v1, M, one CAS transition `open` → `answered`; §1.7 Consent generation) | A2b (foreign head); B reuses it for captures | None exist |
| `remote_activation_replacement` (new) | `remote-activations/<op>/(replacement\|replacement-snapshot\|replaced).json` (`RemoteActivationReplacement` v1 and the stored snapshot bytes, R; §1.6 (i)) | A2b | None exist |
| `revision_preservation` (new) | `revision-activations/<op>/preservation/manifest.json` (`DesignReturnPreservationManifest` v1 with walk (files, symlinks, directories with modes), mode-exception, ignored and rule-change entries, R); `blobs/<sha256>` (`read=False`, owner-private) | A2b | None exist |
| `revision_generation` (new) | `revisions/generations/<op>/generation.json` (`RevisionGeneration` v1, R); `revisions/generations/<op>/(contract\|frontier\|admission).json` (H, `read=False`); regex disjoint from `revision_record`'s 64-hex segment | A2b | None exist |
| `revision_confirmation` (new) | `revision-confirmations/<confirmation_id>.json` (`RevisionConfirmationReceipt` v1, R); `revision-confirmations/retired/<op>/<confirmation_id>.json` (H, `read=False`; §1.6 (i)) | B | None exist |
| `revision_record` (legacy H) | Unchanged; read only through `legacy:` history refs | — | Unchanged |
| `frontier` | 19 → 20 (widen 18, 19, 20): binding `applicability` with confirmation selections (omitted when empty); `confirmations` appended only by `confirm_revision_criterion`, never by activation (N03 I10). 18 stays `readable-legacy` and 19 readable; reads never write; the first N04 write emits 20. N03 §1.7 rows extended: S keeps each record's stored version (an 18 stays 18, a 19 stays 19); N composes the registered 18 → 19 → 20 transformations on both sides, limited to version fields; L adds the revision-confirmation source and the successor row | B | 18 and 19 `readable-legacy`; no rewrite (N03 D3) |
| `snapshot` (remote) | 3 → 4 (widen 2, 3, 4; v1 keeps read-upcast, now to 4); embeds a frontier of any readable version | B | v2, v3 parse natively; v1 upcast as today |
| Receipts embedding bindings or frontiers (N03 §1.7 list: `_DeliveryPlanningRetrySettlementReceipt`, `_DeliveryBuilderInvocationSettlementReceipt`, `_DeliveryBuilderPlanPromotionReceipt`, `_DeliveryBuilderHandoffChangeIntentReceipt`, `_DeliveryPlanningPauseReplay`, `_DeliveryBuilderRequestResolutionReceipt`) | 2 → widen 1, 2, 3: schema 3 admits an embedded binding with `applicability` and a v20 frontier; embedded frontiers keep their stored version (18 or 19 in schema 1 or 2) | B | Unchanged bytes and receipt IDs |
| Nested `DeliveryObservationReceipt` (1 \| 2), `DeliveryReviewReceipt` (1, 2), `DeliveryFinalizationReceipt` (2, 3) | Unchanged; embedded in applicability records as is | — | Unchanged |
| Finalization review basis | Basis schema 2 when records exist (§1.7 D24); a computation, not a stored family (the review stores only `basis_digest`) | B | Schema-1 reviews unchanged |
| `format` marker | One marker-only step per phase A1, A2a, A2b and B | A1, A2a, A2b, B | — |
| `contract`, `admission`, `package` | Unchanged | — | — |

Downgrade: a predecessor release refuses the new format and versions before parsing (N02 D3). The
`DeliveryFinalizationInvalidation` reason stays `head-drift` for head-moving kinds (D13); `reassess` refuses a
finalized or ready Change instead, so no nested literal changes.

### 1.9 Interfaces and error cases

| Interface | Phase | Behavior |
| --- | --- | --- |
| `revise_design_session(change_id, expected_package_id, intent, design)` | A1 | Unadmitted: unchanged. Admitted nonterminal: `expected_package_id` is the current candidate ID, or the active authored ID to open the first candidate; writes only the candidate slot and opens the hold in one transaction. `_admitted_design_revision_allowed` is removed |
| `read_revision_candidate(change_id)` / `discard_revision_candidate(change_id, expected_package_id)` | A1 | Candidate or `None`; discard removes the candidate and clears the hold; refused after an intent |
| `derive_delivery_contract(change_id, candidate=True)` | A1 | Compiles the candidate without publication |
| `admit_change` / `admit_delivery_change` | A2b | First admission and worktree-recovery admission only; an admitted Change → `revision-requires-activation`. `preserve_unresolved_outcome_ids`, `expected_frontier_digest` and `expected_design_package_snapshot_receipt_id` are removed from the request |
| `activate_revision(DeliveryRevisionActivationRequest)` | A2b (B adds the review, the confirmation selections and `reassess`) | `{kind: revision \| reassess \| remote-child, change_id, expected_base_package_id, expected_candidate_package_id, expected_contract_digest, expected_head, expected_frontier_digest, history_ref (reassess only), adopt_child (remote-child only), approval, applicability_review, handoff_disposition}` → `DeliveryRevisionActivationResult{operation_id, kind, state: intent \| local \| published \| released \| superseded-by-merge, replayed}`; `snapshot-reconcile` runs only as an engine action; per-kind rules in §1.6 |
| `open_revision_hold(change_id, expected_frontier_digest, purpose: reassess, history_ref)` | B | Opens the hold for a reassessment (no candidate) bound to one history ref; `clear_revision_hold` closes it before an intent |
| `confirm_revision_criterion(...)` (MCP; D13 boundary) | B | §1.7 capture for purposes `revision`, `reassess` and `remote-child`, each under one consent generation; refusals `channel-unavailable`, `declined`, `question-closed`, `ledger-full` (N03 `ERR_DELIVERY_CONFIRMATION`) and `revision-hold-absent`, `candidate-stale`, `frontier-stale`, `confirmation-scope-invalid`, `reassess-history-invalid`, `revision-remote-activation-pending` |
| `resolve_revision_foreign_head(change_id, operation_id, foreign_head)` (MCP; D13 boundary) | A2b | §1.6 Foreign Change head under E10 and one consent generation; refusals `channel-unavailable`, `declined`, `question-closed`, `foreign-head-stale`, `activation-pending` (no bound activation) |
| Engine actions `reconcile-revision-activation`, `reconcile-revision-snapshot` | A2b | Selected before every other action of the Change; executable through `acquire_change_action` / `execute_change_action` under hold exception E3; the action carries `revision_operation_id` |
| `preview_revision_impact(change_id, history_ref=None)` | B | Impact view and digest; lists eligible history refs (generation and legacy) |
| `show_revision_context(change_id)` | C | Active proposal, candidate, hold, criteria with N03 identities, per-outcome stage, task and evidence history, current blocks and requests, Design-return context, activation state |
| Readiness reasons `revision-hold`, `revision-activation-pending` (detail `revision-foreign-head` with F), `revision-snapshot-stale`, `revision-remote-activation-pending` (details `remote-activation-local-divergence` with paths, `remote-activation-local-confirmations`, `remote-activation-origin-published`) | A1, A2b, A2b, A2b | Each with TypeScript mirror, rendering, component test and parity (R16) |
| Error | A1–B | `DeliveryRevisionError(DeliveryRuntimeConflictError)`, code `ERR_DELIVERY_REVISION`, `reason` in: `change-terminal`, `change-paused`, `change-attention`, `review-repair-open`, `revision-hold-absent`, `candidate-stale`, `base-stale`, `contract-mismatch`, `frontier-stale`, `revision-custody-active`, `revision-drain-pending`, `revision-custody-retained`, `revision-workspace-unclean`, `revision-preservation-unsupported`, `revision-preservation-collision` (detail `ignore-rule-change` for D34), `revision-remote-head-moved`, `foreign-head-stale`, `snapshot-signing-failed`, `snapshot-child-lost`, `handoff-disposition-required`, `design-return-lineage-changed`, `activation-pending`, `operation-conflict`, `revision-requires-activation`, `revision-snapshot-stale`, `revision-remote-activation-pending`, `remote-child-mismatch`, `reassess-requires-unfinalized`, `reassess-history-invalid`, `applicability-review-required`, `applicability-review-incomplete`, `applicability-review-stale`, `applicability-confirmation-version-changed`, `confirmation-unresolved`, `confirmation-not-applicable`, `confirmation-scope-invalid`, `reviewer-not-independent`. `snapshot-signing-failed`, `snapshot-child-lost` and `revision-workspace-unclean` also surface from the first-checkpoint snapshot (A2a) as workspace failures with the same reason |
| MCP | each phase | Strict models for every new or changed tool in the phase that introduces it; error code mapping in `target_server.py` |
| HTTP / Cockpit | C | `GET /api/changes/{id}/revision` (revision context); **Change requirements** on Change detail and group: explanatory view plus copy of `/design <change-id>` (N09 D6 copy pattern); hold and activation states rendered |

### 1.10 Existing owners to reuse

`DesignPackageStore` (second root; ref namespace parameter) and its CAS, verification and checkpoint
(`design_package.py:106-399`); `RuntimeTransaction` multi-root participants (`runtime_transaction.py:120-428`);
`snapshot_design_package` intent and receipt (`workspace_snapshots.py:74-306`; its commit step replaced and its
intent widened, D17, D28);
D03 private preservation store, index resolution, path validation and bounds (`workspace_preservation.py`) for
U3 (b) (D16); `_delivery_frontier` and
`_invalidated_outcomes` (`delivery_admission.py:437-604`); D02 engine actions and receipts; `_publish_delivery_state`,
`_publish_checkpoint_branch`, `_reconcile_change_checkpoint`, `DeliveryPendingStatePublication`; N09-A2 K1–K7,
`require_pause_permits`, drain tokens and the start-site inventory (PR #357); N03 (as amended by #360) evaluator,
identities, `applies_to`, confirmation ledger, `resolve_confirmation`, `confirmation_applies`, basis digest, D13
`Resolve` registration and question rendering, and the L-row ledger replay;
the provider's `return_to_draft` draft-state operation (`ReturnChangePullRequestToDraft`); `FinalizationReportStore`
retire; `DeliveryFinalizationInvalidationReceipt`; the N02 registry, `delivery-migrate`, `delivery-lc`;
`Client(assemble_target_server(...))`, the Cockpit HTTP client and the E2E stack.

### 1.11 Contracts for successors

- **N05:** activation changes the head, so N05-B's approval invalidation applies. `revision-activation-pending`
  precedes the merge action in readiness; activation refuses while an N05 merge effect is started (a K2 owner).
  Under N05 U3 (strict proof; detection-only at execution, no GitHub enforcement required), the activated head
  is refinalized before any new approval offer; N04 relies on no target-rule fact.
- **N06:** criterion versions change at activation; N06 treats an interaction bound to a superseded version as
  stale.
- **N07:** B1 reassessment is a `reassess` activation; the exact gap per criterion is the N03-C projection plus
  applicability records.
- **N08:** an interrupted activation is replay, not repair; diagnosis lists `revision_activation` journals
  (including foreign-head observations), `remote_activation_pending` markers (including `replacing`) and open
  consent generations; degraded Cockpit shows `revision-activation-pending` and
  `revision-remote-activation-pending` Changes.
- **N09-P2:** capability-inventory rows for `/design`, **Change requirements** and user exposure of
  `administrative_move` (the user no longer moves an outcome backward to change requirements).
- **N10:** V14, V15, V16 and V21 regression; at N10-M, B1's `reconcile-revision-snapshot` and `reassess` run on
  live state only with the user's authorization, after the N04-D rehearsal on a copy and only on a pinned
  controller release that contains N04, installed through `/upgrade-delivery` (N02 U1, U2 (a)).

### 1.12 Exclusions

Per-outcome concurrent revision of independent outcomes (U2 (b), not chosen); successor-Change lineage
records (a successor is a new Change whose intent cites the old one); remote recovery of candidates; prepared
interactions (N06); B1 product tasks (N07); live activation of any reconcile or reassessment (N10-M); a generic
distributed transaction framework (programme §8.3).

### 1.13 Decisions

Agent-settled with probe evidence:

- **D1 Candidate slot, not in-place revision** (P9). A package directory must hold exactly four entries
  (`design_package.py:401-410`), so a nested candidate is impossible; packages are Git-tracked (P2), so the
  candidate lives in gitignored runtime state. In-place revision of an admitted package breaks every
  `_validate_package_authority` reader (`portfolio_application.py:1684-1692`; called from acquisition,
  publication and recovery).
- **D2 Roll forward only after the intent** (programme §8.3 step 5). All semantic checks run before the intent;
  later failures are environmental and replay.
- **D3 One local transaction and root-aware recovery** (P3). Every runtime-root recoverer allows the package and
  candidate roots, so a package participant never stops startup; activation then commits package and runtime
  authority in one transaction.
- **D4 Snapshot child of the reviewed head** (P8). Replacement today requires the branch at the previous
  snapshot head (`workspace_snapshots.py:159-162`), which fails after the first reviewed commit. The child is
  built deterministically (D17).
- **D5 Journal-bound loader successor** (P5). The loader's package check (`delivery_application_loader.py:579`)
  stays; only a journal whose base matches the remote snapshot and whose `local.json` matches local state is a
  recoverable successor, and only that journal's expected child is accepted as a remote branch ahead of the
  snapshot on the same host.
- **D6 Engine-owned resumption.** The Designer starts activation; `/continue-change` or the identical call
  completes it (U4: resume from persisted evidence).
- **D7 Portable applicability records embedding cited receipts.** Snapshots carry only the frontier, not
  `revisions/` (P1), so records must be self-contained to survive a fresh-host restore.
- **D8 Reviewer is `build-reviewer` in an `applicability` mode**, independent of the Designer; the engine checks
  structure and independence, not honesty (N03 R12).
- **D9 Reset plus applicability** for invalidated outcomes. Today's reset (`delivery_admission.py:460-475`)
  keeps outcome semantics simple; reuse happens at the evidence level, where V14 needs it.
- **D10 Remove the carry-forward path and its request fields** (execution plan: no compatibility paths).
- **D11 Legacy reconcile action** for pre-N04 revisions (P1, P2: live B1's branch holds package `7fd20cc1`
  while its active, local and remote package is `5f18111f`).
- **D12 Re-split N04-A into A1, A2a and A2b** (§3.7; round 2 split A2): hold and candidate; then deterministic
  snapshot plumbing with its format and LC companions; then activation, preservation and fresh-host recovery;
  each with its adapters and companions.
- **D13 Finalization invalidation reuses `head-drift`** for `revision` and `snapshot-reconcile`, which always
  move the head (child commit), so the existing validator (`runtime_models.py:564-597`, which rejects equal
  heads except for `review-repair`) accepts it without a schema change. `reassess` moves no head and therefore
  refuses a finalized or ready Change (`reassess-requires-unfinalized`).
- **D14 The hold is a separate coordination field, not a pause request.** It must not convert into a deferral
  (N09 K5) and must coexist with Pause.
- **D15 Activation joins the central mutability policy.** Its frontier write goes through a `DeliveryRuntime`
  facade method (`prepare_revision_activation`, registered in `_NORMAL_CHANGE_MUTATIONS`), unlike today's
  registry write, which bypasses `_require_change_mutable` (`delivery_admission.py:183-255`).

Added for Sol plan gate round 1 (§6):

- **D16 Three-component Design-return preservation** (finding 1). The commit quarantine loses staged content
  and the real index; D03 raw preservation refuses staged content. A new owner reuses D03's private store and
  bounds and records HEAD, index and filesystem separately (§1.6). Rejected: extending
  `quarantine_dirty_worktree` (its single-tree receipt and verification are used by D03 recovery as is).
- **D17 Deterministic plumbing child commit** (finding 2). Objects, tree and commit are built before the
  intent without touching the worktree or index; the intent records the child SHA; A3 is a CAS ref update plus
  a path-limited checkout whose partial states are classifiable. Fixed identity and dates make replay
  byte-identical; `commit-tree` runs no hooks. Applies to every caller of the snapshot owner.
- **D18 Verified fresh-host restore of an ahead activation child** (finding 3). Restoring the old approved
  state while pinning the remote child keeps the Change visible and never blesses or overwrites the child.
  Rejected: publishing state before the branch (the snapshot's `change_head` would not exist remotely) and a
  portable intent on the state branch (a second remote write with its own crash window).
- **D19 Operation identity includes kind and predecessor generation** (finding 6). Portable predecessor
  fields (expected head and frontier digest) keep identical-request replay, separate snapshot-reconcile from
  reassess, and distinguish repeated package pairs.
- **D20 Generation history keyed by operation** (finding 7), not by contract digest; legacy directories stay
  read-only history refs.
- **D21 Identity-bound hold exceptions** (finding 4) instead of reusing the Pause predicate; the start-site
  inventory test keeps every N09-A2 start site classified for both policies.
- **D22 Ready demotion inside the activation** (finding 5). `prepare_review_repair` takes the checkpoint lock
  that A0 already holds (`application_publication.py:860`), invalidates finalization with `review-repair`,
  rewrites the frontier and publishes state (`:875-879`; `delivery_runtime.py:1296-1338`), and is a pause-gated
  operator start in N09-A2. Activation instead calls the provider's `return_to_draft` after its intent under
  its own token and records the invalidation in A4.
- **D23 Confirmation authority from the N03 ledger** (finding 8): no request, history or provenance route.
- **D24 Applicability in the finalization basis** (finding 9): basis schema 2 when records exist.

Added for Sol plan gate round 2 (§6):

- **D25 Refuse cleanup collisions with ignored entries** (finding 1). The ignored inventory holds hashes, not
  bytes, so the only safe rule is that `reset --hard` never writes an ignored path: A0 and the pre-cleanup
  verification refuse a collision. Rejected: capturing ignored bytes (unbounded, and may hold secrets the user
  never consented to move) and relying on post-cleanup verification (too late).
- **D26 Fenced remote-child resolution and observed-head demotion** (finding 2). The marker admits exactly one
  resolution identity (E6) with its own kind; A1b binds the provider-observed head from a permitted set and
  journals its outcome before A3, because the provider's stored operation fixes its head
  (`draft_pull_request.py:656-696`, stored-operation equality `:680`, `_validate_draft_state_identity`
  `:746-762`) and the PR head follows the branch once pushed.
- **D27 Candidate-scoped confirmation capture** (finding 3). A dedicated tool reuses N03's D13 boundary and
  appends one ledger entry bound by its own receipt before A0; records select it beside the unchanged source
  receipt. Rejected: eliciting inside `activate_revision` (activation would append to the ledger, against N03
  I10 and §1.9) and placing candidate-version requests in active bindings (active work naming inactive
  versions).
- **D28 One durable snapshot identity carrier** (finding 4): `ChangeDesignPackageSnapshotIntent` schema 2
  holds every input of the child commit for every caller; activation journals reference it.
- **D29 Fully fenced fresh-host replacement** (finding 5): the marker records digests of every artifact the
  restore wrote, including the index and the bounded-walk manifest, because an external edit leaves the
  frontier digest unchanged.
- **D30 Bounded filesystem walk** (finding 6): Git status omits untracked empty directories and Git trees keep
  only the executable bit, so the inventory comes from an `lstat` walk with mode exceptions for clean files.
- **D31 Per-kind activation contract** (finding 7): one table fixes starter, hold source, custody, fields,
  steps, writes, loader successor and restart owner for each kind and for the plain snapshot.
- **D32 Pinned child object; repository signing honored once; no hooks** (finding 8). The child is pinned by a
  ref before the intent and replay never recomputes, so a signed child (whose re-signing would change the SHA)
  stays durable. The probe on lane D shows the managed repository's pre-commit configuration excludes
  `.owlbear/delivery/packages/` (only the warning-only `todo-check` runs on every commit), and package bytes
  are engine-verified authority that any rewriting hook already fails today's byte check, so `commit-tree`
  runs no hooks; server-side checks on the pull request are unaffected.
- **D33 Split A2 into A2a and A2b** (reviewer advice): A2a is independently useful (it makes today's
  first-checkpoint snapshot crash-safe) and carries its own format, fingerprint and LC companions.

Added for Sol plan gate round 3 (§6):

- **D34 Ignore-rule changes refuse; cleanup deletes only captured entries** (finding 1). In-tree `.gitignore`
  files change with `reset --hard`, so an ignored entry can become untracked and `clean -fd` would delete bytes
  never captured. A0 classifies the ignored inventory under the reviewed head's rules and refuses any entry R
  does not ignore; cleanup never runs `git clean` and deletes only manifest entries after a byte re-check.
  Rejected: capturing the bytes of flipped entries (same consent and secret objection as D25) and evaluating
  ignore status after the reset (too late). Directory modes join the walk for every visited directory
  (finding 8), extending D30.
- **D35 Activation-owned foreign-head route** (finding 6; settles G18). After the intent a foreign remote
  head is observed and journaled; a user-only authorization preserves it locally and lets the activation demote
  the PR at that head and push with a lease on it. Rejected: reusing `recover_out_of_band_head` (refuses
  finalized Changes, resets the local branch and queues checkpoint publication that races A5) and adopting the
  foreign head into the revision (roll-forward authority cannot gain unreviewed content after approval).
- **D36 Server-owned single-use consent generation** (finding 2), the shape of N05 D14 `merge_consent`: every
  answer, including decline, cancel and a failed re-check, consumes the generation its sealed request state
  names. N04 does not rely on N03 D13's frontier-as-generation argument, which by its own text leaves declines,
  cancels and unapplied accepts unconsumed; if #360 replaces it with a shared generation, N04-B adopts that
  owner instead of its own family (G19).
- **D37 Identity-fenced capture per purpose** (finding 3): `revision`, `reassess` (hold bound to one
  `history_ref`) and `remote-child` (marker `pending`, candidate equal to T's package, E9); remote-child
  captures advance the marker's frontier fence and block automatic replacement until resolved or retired.
- **D38 Durable fresh-host replacement owner** (finding 4): a replacement intent with the exact snapshot bytes
  and a `replacing` marker state survive every crash point until one install transaction clears the marker.
- **D39 Schema-1 intent upgrade after the pin** (finding 7): the child is built and pinned before a CAS
  replacement of the schema-1 intent, so a schema-2 intent never names an unbuilt child. Per-kind A0/A1
  carriers (finding 9) extend D31.

#### U1 — May reviewed applicability attribute legacy evidence?

**Decided 2026-10-03: (a).** Settled as an engineering decision: the user ruled that U1–U3 have one defensible
answer and need no user decision; they were listed to the user on 2026-10-03 without objection.

- **Status quo:** N03 classifies schema-1 observations (free text, no verdict, no criteria) as evidence for
  nothing; criteria they would have proven show `unknown` (N03 I3). Every live observation is schema 1 (N03 P1),
  including B1's prior work.
- **Problem:** V15 forbids repeating a proven check because a request ID changed, but reuse of a legacy receipt
  needs someone to attribute it to a criterion, which N03 forbids as a relabel.
- **Options:** (a) A reviewed `reusable` record may cite a legacy receipt for machine-observed evidence (exact
  commit an ancestor of the head, maintained surfaces unchanged since); human-procedure legacy evidence needs a
  user confirmation for the criterion version and procedure, captured through the N03 D13 boundary into the
  ledger (§1.7 Confirmation authority; N03 (as amended by #360)). The receipt is cited, never changed.
  (b) Every legacy citation needs a scoped user confirmation. (c) Legacy evidence never counts; agents re-run
  machine checks and the user repeats human checks.
- **Rationale for (a):** it keeps U7 (an independent review and, for human evidence, the user) and V15 (no
  repeated exercise), and keeps N03 I3 (the record is new authority; the receipt stays unlabeled).

#### U2 — Scope of the revision hold

**Decided 2026-10-03: (a).** Engineering decision, recorded as for U1.

- **Status quo:** nothing stops new work while a Design revision is drafted; admission requires the caller to
  pass no active claims (`delivery_admission.py:298-305`).
- **Problem:** programme §8.2 says the engine stops "new incompatible work", but which outcomes are affected is
  known only once a candidate compiles, and it can change with every edit.
- **Options:** (a) Whole-Change hold from the first persisted candidate until release or discard; draining
  owners finish (including a retained same-task Builder handoff). (b) Per-outcome hold for outcomes the current
  candidate invalidates, plus Change-level finalization, ready and merge actions, recomputed on every candidate
  revision. (c) No hold until approval; drain only then.
- **Rationale for (a):** it reuses N09-A2's fences with exact identity-bound exceptions (§1.5, D21), never
  wastes work on soon-invalidated outcomes and
  cannot starve activation. Its cost is visible: unaffected outcomes wait while a revision is open, and
  **Change requirements** says so; discarding the candidate lifts the hold. (c) can starve activation under
  continuous work.

#### U3 — Retained Builder work at Design-return readmission

**Decided 2026-10-03: (b).** Engineering decision, recorded as for U1.

- **Status quo:** a Builder Design return keeps its work in place as passive handoff custody, including
  unreviewed commits and staged, unstaged and untracked files (`w-packet-building/SKILL.md:191`; test helper
  `_return_builder`). Admission is then refused (`portfolio_application.py:894-902`), and quarantine refuses
  passive custody (`workspace_snapshots.py:427-432`).
- **Problem:** activation must commit the revised package on the reviewed head, but the retained work sits on
  the branch and worktree. The approved recovery boundary (programme §1.1) forbids moving staged or private
  content without established authority.
- **Options:** (a) **Carry custody:** convert the Design-route handoff to a Planning-route handoff on the
  revised outcome when its original task's outcome and commitment IDs survive; defer the branch snapshot until
  the successor Builder's result is promoted; refuse `design-return-lineage-changed` otherwise. Bytes stay in
  place, but the Change runs under a new authority with an old branch package until then. (b) **Preserve aside
  with consent:** the approval question asks the user to let Delivery move the retained work into local
  preservation (§1.6 Design-return preservation: HEAD, index and filesystem captured and verified separately;
  never pushed), reset to the reviewed head, then activate normally; the revised Planner receives the
  preservation receipt as prior work. Declining keeps
  (c). (c) **Contain:** readmission only when the retained work is already clean at the reviewed head.
- **Rationale for (b):** activation stays one coherent operation; bytes are preserved exactly and stay local;
  consent makes the move an established authority. (a) breaks I3 and the acquisition fence.

Inherited, not re-decided: N03 U1 was answered (b) by the user on 2026-10-03: an explicit user waiver, recorded
with a resolved user-confirmed request bound to that criterion and version, satisfies finalization and is shown
as waived. §1.7's waiver rule applies it across revisions.

## 2. Feasibility Probes

Ran on `ac3bf23f9` in the lane D worktree with `uv run --no-sync`; live state only read. Scripts and outputs:
`/Users/GGN7H9Q/Projects/owlbear-dev-lane-d/.owlbear/scratch/n04p/` (unversioned).

| ID | Executed | Result | Premise settled |
| --- | --- | --- | --- |
| P1 | `p1_live_revisions.py` on live `runtime/changes`, coordination, packages, `refs/owlbear/packages/*` and the remote state branch (read only) | 3 Changes, frontier v18. B1: one outcome in Planning, 0 tasks, blanket block on `REQ-TASK-004-MANAGED-MAC-PILOT-revised-76dcffc9d3e127f2` with 12 expected-evidence items; its history `revisions/216a787…` (contract-digest named) holds the pre-revision frontier with 4 tasks, 3 results and a resolved user-confirmed request; a second `revisions/42f0781…` holds only a v17 frontier named by frontier digest (stranded-frontier repair, `application_recovery.py:877`). Criteria old 10 → new 12, all legacy: 2 same position and version, 2 same position new version, 7 version-only matches, 1 new; OUT-001 invalidated. Package checkpoint refs: 2, 3 and 4 commits | V15/V16 fixture shape; history is mixed-naming H state, not a version store (D7, §3.7); N03 identity mapping works on real data |
| P2 | `p2_branch_package.sh` (read-only Git) | B1's reviewed head `4d31781` and snapshot head `aa67842` both hold package `7fd20cc1`; active, local and remote snapshot hold `5f18111f`; no package commit since the snapshot | Live B1 is an incomplete pre-N04 activation; a fresh-host restore would load the old package and fail the package check (D11) |
| P3 | `test_p3_activation_probe.py::test_s1…`: crash inside a package-store revision transaction, then the default loader | Startup fails `TransactionPathError` from `PortfolioCoordinator.__init__` (`workspace_coordination.py:66`) via `_bootstrap_remote_state` (`delivery_application_loader.py:447`), at `runtime_transaction.py:677` | Any Design package crash bricks the controller today (D3, A1 fix) |
| P4 | `…::test_s2…`: revision admission crashed after the registry commit, before the branch snapshot; reload | Branch snapshot old, active package new; health `attention` (`local Delivery package differs from its remote snapshot`); Change available with readiness `ready`, yet acquisition launches nothing and reports no failure | No activation fence; readiness and acquisition disagree (I5, R14) |
| P5 | `…::test_s3…`: revision admitted locally (branch snapshot replaced), process ends before publication; reload | Pending state publication; health shows `state-publication-pending` and the remote mismatch; acquisition fails `remote-state-reconciliation-required`; the replay can never publish | A revision cannot converge after an interruption today (D5) |
| P6 | `…::test_s4…`: same crash, local-only portfolio | Branch package stale; acquisition stopped only by the absent publisher | Same gap without a remote |
| P7 | `…::test_s5…`: after P4's crash, the identical revision request | Refused `Delivery frontier changed before authority revision`; the same request without the frontier fence replays | Admission is not replay-safe across its own partial success (`delivery_admission.py:193` precedes the replay check at `:195`) |
| P8 | `…::test_s6…`: one reviewed commit after admission, then a revision | `Design package snapshot branch moved before replacement` after the contract and package authority were already rebound | Revision fails for every Change with reviewed work; it reproduces B1 (D4) |
| P9 | Source reads on `ac3bf23f9` | D03 refusal `portfolio_application.py:894-902`, test `test_portfolio_application.py:14518`; in-place revision gate `:870-878` vs skill `w-design-session/SKILL.md:251` (S01); `_publish_delivery_state` skips with any handoff `:1701-1704`; quarantine refuses passive custody `workspace_snapshots.py:427-432`; Planning-return lineage `runtime_reads.py:596-621`, `runtime_receipts.py:258-283`; four-entry package rule `design_package.py:401-410`; registry bypasses `_require_change_mutable` (`delivery_admission.py:183-255` vs `runtime_support.py:59-85`); unrecognized records are not refused (`state_formats.py:711-747`), so a new family needs a format step | D1, D9, D14, D15, U3, §1.8 |

N03-A…C and N02-C are not merged (N09-A2 merged in round 3); N04 uses their planned interfaces
([G1](#5-verification-gaps)). Round 1
re-read N09-A2's implementation in PR #357 (`feadd6777`) and N03's amendment in PR #360 (`9c06c97cd`), read only.
Round 2 re-pinned both (`9a7fff990`: `repair_quarantined_delivery_state_snapshot` joined
`_APPLICATION_PAUSE_GATED_ENTRIES` and `_PAUSE_EXEMPT_PROVIDER_ENTRIES` was removed, no other inventory change;
`86289635f`: D13 routes, receipt-bound ledger replay, U2 widened and open) and added P10. Round 3 merged
`origin/dev` `141795676` (N09-A2 merged), re-pinned #360 at `f4d09d774` (N05 D14 `merge_consent`; N03 D13
*Single use*) and re-read the quarantine cleanup (`workspace_snapshots.py` `quarantine_dirty_worktree`:
`reset --hard` then `clean -fd`, no `-x`), D03's `recover_out_of_band_head` (`workspace_target_sync.py`;
caller in `application_recovery.py` refuses a finalized Change and runs under
`_operator_start(..., publishes_checkpoint=True)`), `ChangeDesignPackageSnapshotIntent` (schema 1) and the
frontier model (`Literal[18]` on `dev`).

| ID | Executed | Result | Premise settled |
| --- | --- | --- | --- |
| P10 | Round 2, read only in lane D: `git --version`; `git config` for `core.hooksPath`, `commit.gpgsign`, `gpg.format`; hooks in the common Git dir; `.pre-commit-config.yaml`; outputs in `.owlbear/scratch/n04r2-git.txt`, `n04r2-precommit.txt` | Git 2.56.0; no `hooksPath`, no signing configured; one installed `pre-commit` hook (pre-commit framework); its configuration excludes `.owlbear/delivery/(packages\|runtime)/`, so today's snapshot commit runs only the always-run, warning-only `todo-check`. Draft-state operations are stored once per operation ID and every call, including a replay with a stored receipt, requires the provider head to equal the stored head (`draft_pull_request.py:656-696`, `:746-762`) | D26, D32; G11 narrowed |

## 3. Phases

### 3.1 Shared rules

- **Layout.** Plans name symbols; re-resolve with `grep` at phase start. N04 starts after N03-C and N09-A2, so
  the post-N01 layout plus their additions holds.
- **Version numbering** follows §1.8: renumber at rebase if another format step merged first; rerun LC.
- **Ownership** (execution plan §1.6). Opus keeps formats, the hold, activation, the loader successor, the
  applicability evaluator rules and reconciliation. Luna may take frontend mirrors and rendering, parity
  assertions, MCP model plumbing, fixtures and skill text once Opus fixes the contract.
- **Assembled proof** uses the default loader, `Client(assemble_target_server(...))`, the Cockpit HTTP client and
  the E2E stack on disposable portfolios with local bare remotes (P3 harness pattern).
- **Crash injection** uses a `BaseException` raised at named boundaries and fresh-process restarts (N02-B
  `_step` pattern), not mocks above the owner.
- **Exports.** A phase that changes `owlbear_delivery.__all__` updates
  `serve/delivery/tests/fixtures/module_surface.json` and the N02 fingerprint fixture in the same PR.

### 3.2 N04-A1 — Candidate slot, revision hold and root-aware recovery

- **Prerequisites:** N04-P, N03-C, N09-A2 (package-added).
- **Editable paths:**
  - `serve/delivery/src/owlbear_delivery/design_package.py` (ref namespace parameter; candidate store use)
  - `runtime_transaction.py` (root-aware `recover_all` helper) and every runtime-root recoverer:
    `workspace_coordination.py` (`__init__`, `recover_pending_transactions`), `delivery_runtime.py:2361`,
    `recovery.py:1038, 1896`; `delivery_application_loader.py` (package and candidate roots wiring)
  - `workspace_models.py` (`ChangeRevisionHold`, `ChangeCoordination.revision_hold`, widened version);
    `workspace_coordination.py` (`open_revision_hold`, `clear_revision_hold`, `require_start_permitted`
    replacing each N09-A2 `pause_request` start check, exception E4, K4 digest exclusion, K6 field copy);
    `workspace_snapshots.py` and `change_workspace.py` only where N09-A2 start checks live
  - `portfolio_application.py` (`revise_design_session`, `read_revision_candidate`,
    `discard_revision_candidate`, `derive_delivery_contract(candidate=True)`; remove
    `_admitted_design_revision_allowed`); `application_models.py`
  - `application_readiness.py`, `work_items.py` (`revision-hold` reason, card copy, action)
  - `state_formats.py` (coordination version, `package_candidate` family, marker step); `state_migration.py`
    (marker-only migration); `serve/tools/src/owlbear_tools/delivery_diagnostics.py` (mirror)
  - `owlbear_delivery/__init__.py`; `serve/delivery/tests/fixtures/module_surface.json`; N02 fingerprint fixture
  - `serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py`, `target_models.py` (new and changed tools)
  - `serve/cockpit/src/owlbear_cockpit/target_models.py`; `serve/cockpit/web/src/api/workItems.ts`,
    `components/workItemPresentation.ts`, `components/WorkItemDetail.tsx`, `pages/WorkPortfolioPage.tsx` and
    their tests; `serve/cockpit/web/e2e/support/seed-work-portfolio-delivery.py`
  - tests: new `serve/delivery/tests/test_revision_candidate.py`; `test_design_package.py`,
    `test_runtime_transaction.py`, `test_portfolio_application.py`, `test_change_workspace.py`,
    `test_work_items.py`, `test_state_formats.py`, `test_state_migration.py`; N09's `test_change_pause.py`;
    `serve/delivery-mcp/tests/test_delivery_adapter.py`, `test_target_server.py`;
    `serve/tools/tests/test_delivery_diagnostics.py`; `tests/test_cockpit_boundary.py`,
    `tests/test_cockpit_work_items.py`, `tests/test_delivery_worktree_authority.py`
  - companion skill text (tool semantics only): `share/skills/w-design-session/SKILL.md` Steps 2–3,
    `share/agents/designer.agent.md` tool list; `tests/test_agent_ecosystem_validation.py`
  - this plan's A1 row; execution plan A1 status row
- **Positive scenarios:**
  - Unadmitted Change: create, revise and read unchanged (existing tests pass unmodified).
  - Admitted Planning Change: `revise_design_session` with the active authored ID creates a candidate and the
    hold in one transaction; the active package bytes, `authority.json` and every `_validate_package_authority`
    reader are unchanged; a second revise with the candidate ID replaces only the candidate; discard removes
    both; `derive_delivery_contract(candidate=True)` compiles the candidate.
  - Hold drain: a live Builder claim settles normally under the hold; a retained same-task handoff's successor
    claim runs (E4); an engine action started before the hold finishes (N09 K2 row reused).
  - Start-site inventory: `_HOLD_CLASSES` in `tests/test_delivery_worktree_authority.py` classifies every
    pause-gated coordinator, manager and application entry of PR #357 (`9a7fff990`, including
    `repair_quarantined_delivery_state_snapshot`) as hold-refused or hold-exception; an unclassified or doubly
    classified entry fails.
  - E8 before any intent: a quarantined-snapshot repair runs under an open hold and leaves hold and candidate
    unchanged.
  - Hold plus Pause: both recorded; Pause converts after drain; the hold stays; Resume leaves the hold.
  - A recovery journal issued before the hold completes after it (K4 digest unchanged).
  - Root-aware recovery: crash a package transaction at `after-first-publication` (P3 shape), restart through
    the default loader: the transaction completes and every Change is available.
  - `revision-hold` readiness through `get_change`, MCP, HTTP and Cockpit with its explanatory copy.
- **Negative scenarios:**
  - Under the hold, a new Planner claim, a new task claim, finalization, mark-ready, target sync and merge
    starts are refused in their start transactions with no marker or effect (each K3 site).
  - Candidate for a completed or abandoned Change → `change-terminal`, no write; for a deferred Change → allowed
    (drafting while paused), activation later refused.
  - Revise with a stale expected ID → CAS conflict, candidate unchanged; a symlinked or extra entry in the
    candidate root → refused, no write.
  - A candidate file under `packages/<change>/` (old in-place path) never appears; the active package is
    byte-identical before and after every candidate operation.
  - A coordination record with N04 content and the old version → rejected at parse; the predecessor release
    refuses the new marker and coordination version with unchanged tree hashes.
  - A runtime-root manifest naming a root outside the Delivery allowlist → still refused (`TransactionPathError`).
- **Inner loop:** `uv run pytest serve/delivery/tests/test_revision_candidate.py -q`, then
  `uv run pytest serve/delivery/tests/test_runtime_transaction.py serve/delivery/tests/test_design_package.py -q`.
- **Closeout:** `uv run test --changed`; scoped `uv run ruff check` / `ruff format --check`; `npm test`,
  `npm run build`, Biome on changed files, `npm run test:e2e:work`;
  `uv run pytest tests/test_agent_ecosystem_validation.py tests/test_cockpit_boundary.py
  tests/test_delivery_worktree_authority.py -q`.
- **LC:** full form with `delivery-lc`: the unmigrated copy is refused; the marker step migrates; every live
  Change is available; no live record has a hold or candidate; the predecessor release refuses the migrated
  copy; live record hashes unchanged.
- **Size / risk:** L / high (coordination version, K3 sites, recovery roots).

### 3.3 N04-A2a and N04-A2b — Snapshot plumbing; activation, Design-return readmission and legacy reconcile

Two PRs (D33). A2a makes every package snapshot deterministic and crash-safe and is useful on its own: it
repairs today's first-checkpoint snapshot (§1.6 Deterministic child commit). A2b adds the activation operation
on top of it.

#### N04-A2a — Deterministic snapshot plumbing

- **Prerequisites:** N04-A1.
- **Editable paths:**
  - `serve/delivery/src/owlbear_delivery/workspace_snapshots.py` (`_commit_design_package_snapshot` replaced for
    both existing callers; pin, classifier, schema-1 intent treatment, signing, pin cleanup)
  - `workspace_models.py` (`ChangeDesignPackageSnapshotIntent` schema 2; coordination v4);
    `workspace_coordination.py` (K6 copy of the widened field only)
  - `state_formats.py` (coordination v4, marker step); `state_migration.py`;
    `serve/tools/src/owlbear_tools/delivery_diagnostics.py`
  - `owlbear_delivery/__init__.py` and `module_surface.json` only if exports change; N02 fingerprint fixture
  - tests: new `serve/delivery/tests/test_snapshot_plumbing.py`; the existing snapshot tests in
    `test_change_workspace.py` (or their current home); `test_state_formats.py`, `test_state_migration.py`;
    `serve/tools/tests/test_delivery_diagnostics.py`; `tests/test_delivery_worktree_authority.py` where its Git
    command inventory names snapshot calls
  - this plan's A2a row; execution plan A2a status row
- **Positive scenarios:**
  - First-checkpoint snapshot: the branch commit equals the intent's `child_commit` (identity, dates, message,
    only the four package paths); the pin is gone after the receipt. In a fixture repository with a
    `pre-commit` hook that fails and one that rewrites files, the snapshot succeeds with unchanged bytes and the
    hooks' marker files are absent (D32).
  - Crash matrix, `BaseException` and a fresh process after each of: object and tree writes; `commit-tree`
    before the pin; the pin before the intent; the intent before `update-ref`; `update-ref` before checkout;
    checkout of 1, 2 and 3 of the 4 package paths (file publication); the index update before the files
    (staging); the receipt before pin deletion. Each completes through the default loader and the checkpoint
    supervisor with the intent's child, no second commit and a clean worktree; after the intent `commit-tree`
    is never called again (call count over all restarts).
  - Signed repository (`commit.gpgsign=true`, `gpg.format=ssh`, a test key): one signed child; crash after the
    intent, then `git gc --prune=now`: the pinned object survives and replay completes with the same SHA.
  - A pin without an intent is reused when parent, tree, identity and message match, and replaced otherwise.
  - Schema-1 intents, one seeded per state of §1.6 step 7: a committed legacy child completes by legacy
    replay; a clean expected head is upgraded to schema 2 and completes; package-only dirt with parent or target
    bytes is restored and completes. Upgrade ordering (D39): the child is pinned before the CAS replacement; a
    crash after the pin and before the replacement restarts with the schema-1 intent in force and reuses the pin
    (one `commit-tree` call over all restarts); a crash after the replacement replays the schema-2 intent; at
    every crash point any schema-2 intent present names a pinned object; a concurrent change to the schema-1
    intent bytes makes the replacement's CAS fail with nothing written.
  - The N02 fingerprint fixture records intent schema 2 and coordination v4; schema-1 intents parse
    byte-identically.
- **Negative scenarios:**
  - Signing configured but failing (no key) → `snapshot-signing-failed` before the intent: no intent, no pin,
    branch unchanged.
  - After the intent the pinned object is removed and pruned → contained `snapshot-child-lost`, nothing written.
  - Replay with non-package dirt or a branch elsewhere, and a schema-1 intent with any other dirt → contained
    `revision-workspace-unclean` with the paths; nothing written or deleted.
  - A v2 or v3 coordination holding a schema-2 intent → rejected at parse; the predecessor release refuses
    the new marker with unchanged tree hashes.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_snapshot_plumbing.py -q`.
- **Closeout:** `uv run test --changed`; scoped Ruff; `uv run pytest tests/test_delivery_worktree_authority.py -q`.
- **LC:** full form: the marker step migrates; the number of live pending schema-1 intents is recorded
  (expected 0); every live Change is available; the predecessor refuses the migrated copy; live hashes
  unchanged; on the copy, one seeded schema-1 intent per state completes.
- **Size / risk:** M / high (every snapshot caller; Git plumbing).

#### N04-A2b — Activation operation, Design-return readmission and legacy reconcile

- **Prerequisites:** N04-A2a.
- **Editable paths:**
  - new `serve/delivery/src/owlbear_delivery/revision_activation.py` (journal, generation and preservation
    models, operation steps, operation identity)
  - `delivery_admission.py` (first-admission only; `prepare_revision_authority` returning participants and the
    generation record; request fields removed)
  - `delivery_runtime.py` facade (`prepare_revision_activation`, registered mutation; ledger append-only guard
    reused); `runtime_models.py` (`_NORMAL_CHANGE_MUTATIONS`)
  - `workspace_snapshots.py` (child-of-reviewed-head replacement over the A2a plumbing, returning a coordination
    participant); `workspace_preservation.py` (`preserve_design_return_workspace` with the bounded walk,
    directory modes, collision and rule-change checks, capture-only cleanup, test-only restore);
    `workspace_models.py` (`ChangeContinuationAction` kinds and `revision_operation_id`,
    `revision_hold.activation_operation_id`, `purpose` and `history_ref`, `remote_activation_pending` with
    `replacing` and `captures`, coordination v5);
    `workspace_coordination.py` (participant helpers; exceptions E1–E3, E6–E8 and E10; E2 token kind)
  - `revision_activation.py` also owns the foreign-head steps and the `RevisionConsentGeneration` store
    (§1.6 Foreign Change head, §1.7 Consent generation), reused by N04-B
  - `portfolio_application.py` (`activate_revision`, `admit_delivery_change` refusal); `application_acquisition.py`
    (engine-action selection and execution, E3); `application_publication.py` (A1b provider call, A5 owner path);
    `application_readiness.py`, `work_items.py` (`revision-activation-pending`, `revision-snapshot-stale`,
    `revision-remote-activation-pending`); `application_models.py`
  - `delivery_application_loader.py` (`_is_unpublished_revision_activation_successor` before the remote-head
    check, legacy detection, fresh-host verified activation child restore with the `restored` fence, and the
    durable replacement owner of resolution (i): intent, `replacing` replay, install)
  - `state_formats.py` (`revision_activation`, `revision_preservation`, `revision_generation`,
    `revision_consent`, `remote_activation_replacement` families, coordination v5, action-receipt row, marker
    step); `state_migration.py`;
    `serve/tools/src/owlbear_tools/delivery_diagnostics.py`
  - `owlbear_delivery/__init__.py`, `module_surface.json`, N02 fingerprint fixture
  - MCP `target_server.py`, `target_models.py` (`activate_revision`, `resolve_revision_foreign_head` with the
    D13 `Resolve` parameter, changed `admit_change`); Cockpit
    `target_models.py`, `workItems.ts`, `workItemPresentation.ts`, `WorkItemDetail.tsx`,
    `WorkPortfolioPage.tsx` and tests; E2E seed
  - tests: new `serve/delivery/tests/test_revision_activation.py`; `test_source_bound_admission.py`,
    `test_portfolio_application.py` (including the D03 refusal test, rewritten to readmission),
    `test_change_workspace.py`, `test_delivery_state.py`, `test_checkpoint_publication_regressions.py`,
    `test_state_formats.py`, `test_state_migration.py`, `test_work_items.py`, `test_workspace_preservation.py`
    (or its current home), `test_delivery_application_loader.py` (or its current home); MCP and Cockpit tests as
    in A1; `tests/test_delivery_worktree_authority.py`
  - companion skill text (call shapes only): `w-design-session` Step 10, `designer.agent.md`,
    `w-orchestration` / `continue-change` routing of the two engine actions;
    `tests/test_agent_ecosystem_validation.py`
  - this plan's A2b row; execution plan A2b status row
- **Positive scenarios:**
  - Clean activation of a Change with two reviewed tasks (P8 shape): one child commit on the reviewed head;
    contract, frontier, admission, package and history change in one transaction; publication publishes branch
    then state; release clears the hold; acquisition resumes for the revised outcome; unchanged outcomes keep
    their bindings (V14).
  - Crash matrix (V21), fresh process after each of: A1, A1b (after the provider call before `demotion.json`,
    and after it), A2 (after capture, after verification, mid-cleanup), A3 (each A2a sub-step), inside A4 after
    its first participant, after A4, A5 after the branch push, A5 after the state push (response lost), before
    A6: restart reaches the old state (before A1) or the exact new state after replay; one child commit whose
    SHA equals the intent's; one state snapshot; blocks and requests not reset by the revision unchanged; the
    confirmation ledger byte-identical.
  - The A2a crash matrix reruns for the activation caller and for `snapshot-reconcile`.
  - Per-kind contract (finding 7 of round 2, finding 9 of round 3): one parametrized test per kind of §1.6
    asserts the required request fields, that every "n/a" step writes nothing, the hold source and custody, the
    A0 Git objects and A1 snapshot intent rows, the A4 artifact set and the restart owner. At every crash point:
    `reassess` never calls `commit-tree`, never creates a pin and coordination never holds a snapshot intent;
    `remote-child` never calls `commit-tree` and its snapshot intent has origin `adopted` with child = T;
    `revision` and `snapshot-reconcile` hold exactly one `built` intent from A1 to A4.
  - Fresh-host restore (finding 3), real local bare remote, a second clone as the fresh host: (1) crash after
    the branch push, before the state push: the fresh host restores the old approved state at `change_head`,
    pins the remote child, shows `revision-remote-activation-pending` through `get_change`, MCP and HTTP, and
    the remote branch ref is unchanged; then the origin completes A5 and the fresh host's next startup, with
    every `restored` value matching, replaces the old state with the new snapshot; alternatively the origin is
    discarded and the fresh host's user-approved `remote-child` activation adopts the pinned child (tree and
    parent equal) and pushes no branch.
    (2) crash after the state push (response lost): the fresh host restores the new state directly. Both:
    the same-host restart also converges through the journal successor (remote branch equal to the expected
    child is accepted).
  - Origin lost for a formerly ready Change (finding 2 of round 2): the origin crashes after its branch push;
    the fresh host restores the ready state at `change_head` with the marker; with the PR already draft at T
    the resolution makes no provider write; with the PR re-marked ready at T it makes exactly one
    `return_to_draft` with `exact_head` = T; A4 clears `ready` and `finalization` with `head-drift`; A5 pushes
    no branch; A6 clears the marker. On the same host, a ready Change crashing after its A5 branch push replays
    without any provider call (`demotion.json` present) although the PR head is now the child.
  - Both resumption routes: identical `activate_revision` and `/continue-change` engine action.
  - Ready Change (finding 5): A1 records the demotion binding; A1b demotes under the activation token while A0's
    checkpoint lock is held (no deadlock, no `review-repair` invalidation, no intermediate state publication);
    A4 clears `ready` and `finalization` with `head-drift`; readiness rebuilds. Crash after A1b, then restart:
    readiness `revision-activation-pending`, replay observes the draft PR and the ready Change activates; the
    provider sees exactly one draft-state operation `revision-draft-<operation_id>-<finalized head>`.
  - Report-backed Finalizer attention consumed in A4; the report is retired.
  - Design-return readmission (rewritten `test_design_return_revised_admission_…`) under U3 (b), merge-blocking
    falsifiers (finding 1), each built in a real worktree before the return: a path whose staged blob differs
    from its working-tree bytes; a staged new file deleted from the working tree; an executable bit change and a
    `0o600` file; a tracked clean file whose mode changed from 0644 to 0600 (no Git diff); a symlink to a file
    inside and one pointing outside the worktree (never followed); an untracked file and an untracked empty
    directory (absent from `git status` output, asserted); an untracked `0o700` directory holding a file and a
    tracked directory changed to `0o750` (finding 8 of round 3); an ignored file (`.env`-style) and an ignored
    directory, neither colliding with the reviewed head nor flipping under its rules. After
    activation: the head ref equals the old branch head; the index ref's tree and stored entry records equal
    the original `git ls-files -s` output; the walk manifest equals the original `lstat`/sha256 inventory,
    including the mode exception, the empty directory and every directory mode;
    the ignored inventory is unchanged in place; a test-only restore into a scratch worktree reproduces HEAD,
    index entries and filesystem manifest exactly, run once under umask `0o022` and once under `0o077`, both
    reproducing the `0o700` and `0o750` directory modes. Cleanup never invokes `git clean` (command
    inventory). A crash after capture and mid-cleanup completes without a
    second capture; the revised Planner context names the preservation receipt.
  - Hold exceptions (finding 4), each a race test with barriers in the start transactions: E1 activation
    intent vs an unrelated snapshot intent start (only the bound one commits); E2 activation A5 reservation vs a
    `mark-ready` direct start (the latter refused); E3 `reconcile-revision-activation` acquisition vs a
    `sync-target` continuation (only the bound kind and operation acquire); E4 same-task successor vs a
    different-task claim racing the hold opening (exactly one of hold or claim wins; afterwards only the
    same-task successor starts). A forged `reconcile-revision-activation` action naming another operation is
    refused. E6: under a `pending` marker only `remote-child` with the marker's child starts; E7: the D03
    containment route runs only while the marker records a divergence; E8: a quarantined-snapshot repair runs
    under a hold with no bound activation, is refused between A1 and A4, and after A4 republishes exactly the
    `local.json` bytes. E10: under the hold only `resolve_revision_foreign_head` for the bound operation and its
    latest observed F starts; one naming another head or operation is refused.
  - Operation identity (finding 6): legacy reconcile then `reassess` on the B1 shape produce two distinct
    operation IDs, journals and generation records; each identical request replays its own result; a
    `revision` repeated over an equal package pair at a later head gets a new ID.
  - Generation history (finding 7): activations A → B → A → C each write one generation record: three records
    with ordinals 1–3 holding the replaced authority byte-correctly, contract A replaced twice (records 1 and 3)
    under different operation IDs, and C active; `legacy:` refs resolve only contract-named legacy directories.
  - Persisted action schema (finding 10): a v4 coordination and an action receipt holding a new kind are
    rejected by the predecessor format gate; old action receipts parse byte-identically; the N02 fingerprint
    fixture records the widened `ChangeContinuationAction`, coordination v5 and the five new families.
  - Legacy reconcile on a seeded B1 shape (branch snapshot of an older package, active package newer, remote
    snapshot of the active package): `revision-snapshot-stale`, then one action makes branch, local and remote
    agree; a fresh-host restore then succeeds.
  - Pause after the intent: the activation finishes, then Pause converts (activation is a K2 owner row).
- **Negative scenarios:**
  - Each §1.5 refusal row before any write; the identical request after the refusal changes nothing.
  - Changed candidate, base, contract digest or frontier after approval → refused before the intent.
  - Same operation ID, different intent digest → `operation-conflict`; a second activation while one is
    unfinished → `activation-pending`.
  - `admit_change` on an admitted Change → `revision-requires-activation`, no registry write.
  - A journal whose base differs from the remote snapshot, or whose `local.json` digests differ from local
    state → the loader keeps today's mismatch failure; the Change is not blessed (V20).
  - A3 replay finds a branch head that is neither the expected head nor the expected child, a package path whose
    index or file bytes are neither the parent's nor the child's, or any other dirty or untracked path (an
    unrelated edit made during the crash window) → contained `revision-workspace-unclean` naming the paths; no
    write, no deletion, no second commit.
  - Preservation: an unmerged index entry, split index, skip-worktree entry, gitlink, nested repository,
    symlinked ancestor, a walk or capture bound exceeded → `revision-preservation-unsupported` before the
    intent; a live worktree changed between capture and cleanup → verification fails, nothing cleaned,
    activation stays pending with the paths.
  - Collision falsifier (finding 1 of round 2, merge-blocking): the reviewed head tracks `config/local.env`, a
    retained commit deletes it, the branch head's `.gitignore` ignores it, and an ignored local file with
    secret bytes sits at that path → A0 refuses `revision-preservation-collision` naming the path; no intent,
    capture or cleanup; the file's bytes, mode and mtime are unchanged. Variants: an ignored directory `cache/`
    where the reviewed head tracks a file `cache`; an ignored file `build` where it tracks `build/x`; a
    collision created between A0 and A2 → pre-cleanup verification fails and nothing is cleaned.
  - Rule-change falsifier (finding 1 of round 3, merge-blocking): R has no rule for `local.env` or `cache/`; a
    retained commit adds both lines to `.gitignore`; an ignored file `local.env` with secret bytes and an
    ignored directory `cache/` holding a file sit in the worktree → A0 refuses `revision-preservation-collision`
    detail `ignore-rule-change` naming both; no intent, capture or cleanup; bytes, modes and mtimes unchanged.
    Variants: the rule added only by an unstaged `.gitignore` edit, and only by a staged one; a nested
    `sub/.gitignore` added by an untracked file; a rule change made between A0 and A2 → pre-cleanup
    verification fails and nothing is cleaned. Reverse flip (positive): R ignores `tmp.log` while the branch
    head's rules do not; the untracked `tmp.log` is captured, deleted explicitly by cleanup and restored by the
    test-only restore. With every falsifier, a `git clean` invocation would have deleted the entry: the test
    also runs `clean -fd -n` after the reset on a scratch copy and asserts it lists the entry (premise check).
  - Fresh host: a remote tip that is not a verified activation child (two commits ahead, a non-package path, a
    wrong parent or message, a package that fails verification) keeps today's `remote-change-head-ahead`
    diagnostic; nothing restored, nothing pinned. With `remote_activation_pending` set, any other revision →
    `revision-remote-activation-pending`.
  - Fenced replacement (finding 5 of round 2): after the restore, stage an edit to a tracked file and modify
    another without staging, leaving every runtime file and the frontier digest unchanged; the origin
    publishes; the next startup replaces nothing, readiness detail `remote-activation-local-divergence` lists
    both paths, their bytes and the remote are unchanged; after E7 containment the next startup replaces.
    Variants: an edited active package file → the Change is unavailable with the integrity diagnostic and
    nothing is overwritten; a candidate or custody present → no replacement.
  - Replacement restart proof (finding 4 of round 3): crash with a fresh process after each of: the
    replacement-intent transaction; the `update-ref` to T; the index update before the files; checkout of 1, 2
    and 3 package paths; inside the install transaction after its first participant; after the install before
    pin cleanup. Each restart completes from the stored snapshot bytes (the remote state branch is moved again
    during the crash window and the replay ignores it), ends with the marker cleared, branch, index and
    worktree at T and local authority equal to the stored snapshot's; acquisition is refused at every
    intermediate restart; an unrelated edit made during the window → contained `revision-workspace-unclean`,
    then E7, then completion.
  - Foreign head (finding 6 of round 3; settles G18), real bare remote and the fake provider: after A1 another
    writer pushes F to the Change branch. (1) Formerly ready Change, PR ready at F: A1b journals
    `foreign-heads/<F>.json`, makes no provider write, readiness `revision-activation-pending` detail
    `revision-foreign-head`; `recover_out_of_band_head` is refused under the hold; `resolve_revision_foreign_head`
    asks once through an elicitation-capable client; accept → F pinned locally, `foreign-head.json` written,
    exactly one `return_to_draft` with `exact_head` = F, A5 pushes the child with a lease on F, the PR head is
    the child, A4 clears `ready` and `finalization` with `head-drift`, the pin still resolves to F. (2) Not
    ready: A5 readback finds F; same authorization; lease push. Crashes after the pin and before the authorizing
    transaction, after it, after the demotion and after the lease push each replay without a second fetch,
    question or provider call. Decline → nothing but the generation changes; the remote is returned to the
    expected head externally → replay continues without authorization. A second foreign head F′ after
    authorizing F → new observation and question; the lease on F fails and nothing is overwritten. A merged
    PR at F before the push → `superseded-by-merge`.
  - `remote-child`: T's tree differs from the computed child → `remote-child-mismatch`; the PR is merged →
    `change-attention`; both before the intent.
  - A remote Change branch not at the expected head at A0 → `revision-remote-head-moved` before the intent;
    `resolve_revision_foreign_head` with a stale F, another operation or no observation → `foreign-head-stale`
    or `activation-pending`, nothing written; a replayed foreign-head request state after a decline → the
    recorded `declined`, no pin, no provider write and no second elicitation.
  - Ready Change: the PR merged before A1b → `superseded-by-merge`, no Git effect, hold cleared; a
    `review-repair` invalidation present → `review-repair-open` before the intent.
  - Under the hold without the bound identity: snapshot intent, continuation acquisition, publication
    reservation, provider draft call and new claims are each refused in their start transaction (inventory).
  - Under U3 (b), a declined consent → `handoff-disposition-required`, nothing moved.
  - Activation of a completed Change via any route → `change-terminal`; the mutability-policy test enumerates
    `prepare_revision_activation`.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_revision_activation.py -q -k "crash or replay"`.
- **Closeout:** as A1, plus `uv run pytest serve/delivery/tests/test_delivery_state.py -q -k "revision or restore"`.
- **LC:** full form: migration (coordination v5, the five new families, action-receipt row, marker), every live
  Change available; untouched legacy records (v18 frontiers, schema-1 receipts, v2 snapshots, legacy
  `revisions/` directories) load with unchanged bytes; on the copy, B1 shows `revision-snapshot-stale` (record,
  do not run on live); predecessor refuses; live hashes unchanged.
- **Size / risk:** L / high (multi-root commit, loader, Git effects, preservation, fresh-host fences).

### 3.4 N04-B — Applicability assessment and carry-forward replacement

- **Prerequisites:** N04-A2b.
- **Editable paths:**
  - new `serve/delivery/src/owlbear_delivery/applicability.py` (impact view, review validation, records,
    `RevisionConfirmationReceipt`, candidate-scoped question rendering)
  - `evidence.py` [N03] (fold: records before results; `DeliveryConfirmationUse` view for
    `confirmation_applies`; basis schema 2 in `finalization_basis_digest`); `runtime_models.py`
    (`DeliveryApplicabilityRecord`, binding `applicability`, frontier version); `runtime_receipts.py` (widened
    embedding receipts); `delivery_state.py` (snapshot version); `delivery_application_loader.py` (S and N rows
    of N03's comparison inventory for the new version; the L-row revision-confirmation source)
  - `delivery_runtime.py` facade (`append_revision_confirmation`, declared mutation); `runtime_models.py`
    (`_NORMAL_CHANGE_MUTATIONS`); `workspace_coordination.py` (`open_revision_hold` purpose `reassess` with
    `history_ref`; E5, E9; the E9 marker update)
  - `delivery_admission.py` (remove `_carry_forward_unresolved_binding`, `_carry_forward_request_id`,
    `preserve_unresolved_outcome_ids`); `revision_activation.py` (review binding, `reassess` kind)
  - `portfolio_application.py` (`preview_revision_impact`); `application_acquisition.py`
    (`show_plan_context` revision view); `application_models.py`; `application_lifecycle.py` (finalization
    `semantics` includes records and cited confirmations; basis re-check under the checkpoint lock)
  - `state_formats.py`, `state_migration.py` (frontier and snapshot widening, `revision_confirmation` family,
    marker step); `delivery_diagnostics.py`
  - `__init__.py`, `module_surface.json`, fingerprint fixture; MCP `target_server.py`, `target_models.py`
    (`preview_revision_impact`; `open_revision_hold`; `confirm_revision_criterion` with the D13 `Resolve`
    parameter; `activate_revision` review and selection fields required)
  - companion text: `share/agents/build-reviewer.agent.md` (`applicability` mode output),
    `share/skills/w-frontier-planning/SKILL.md` (plan only uncovered/partial/unknown criteria),
    `share/agents/planner-challenger.agent.md`; `tests/test_agent_ecosystem_validation.py`
  - tests: new `serve/delivery/tests/test_revision_applicability.py`; N03's `test_evidence.py`;
    `test_source_bound_admission.py` (carry-forward tests replaced), `test_delivery_runtime.py`,
    `test_delivery_state.py`, `test_state_formats.py`, `test_state_migration.py`; MCP tests;
    `serve/tools/tests/test_delivery_diagnostics.py`
  - this plan's B row; execution plan B status row
- **Positive scenarios:**
  - Impact view on the P1 B1 shape: 12 criteria; mappings match P1 (2 / 2 / 7 / 1); digest deterministic.
  - Reviewed `reusable` for a machine-observed schema-2 result at an ancestor commit → `covered` after
    activation; finalization with no new observation for it (N03 D10) (V15).
  - Revised target criterion (`invalidated`, changed assumption names the target class) → `uncovered`, the
    projection names the exact criterion and version; the Planner's context lists only it plus `partial` and
    `unknown` (V16, R9).
  - `partial` → `missing` owner `agent`; `unknown` → `unknown` with the search note.
  - `reassess` on a seeded copy of B1's carried state with `history_ref = legacy:216a787…`: the blanket request
    moves to the new generation record; records written; no package, contract or branch change; one
    publication; the ledger is byte-identical.
  - Confirmation authority (finding 8), through `Client(assemble_target_server(...))` with an
    elicitation-capable test client: (1) a schema-2 `human-confirmed` result whose ledger confirmation names
    `(AC-003, v)`, the outcome and the procedure, criterion `unchanged`, cited as `reusable` → `covered`;
    (2) the same after the outcome reset moved its request to the generation record → still `covered`
    (`resolve_confirmation` by ID); (3) publish, restore on a fresh host from the snapshot → identical status;
    (4) under U1 (a) a legacy human-procedure receipt and a legacy machine receipt, see the next scenario.
  - Candidate-scoped capture without pre-seeded confirmations (finding 3 of round 2), on both D13 routes
    (`mode="legacy"` and `mode="2026-07-28"`) through `Client(assemble_target_server(...))`: the fixture's
    ledger holds only the original `(AC-003, v1)` confirmation of a `human-confirmed` result, or nothing for a
    legacy human receipt; the candidate revises AC-003 to v2. The review marks it `reusable`; activation without
    a selection → `applicability-confirmation-version-changed`. `confirm_revision_criterion` asks once (the
    rendered question names AC-003 v2, its statement, the procedure and the source receipt); the
    `elicitation_callback` accepts `passed`; one ledger entry and one `RevisionConfirmationReceipt` appear in one
    transaction; the review stays valid (impact digest unchanged); activation with the selection → `covered`;
    the source receipt is byte-identical and still cites its v1 confirmation; the frontier stores the selection.
    A crash after the capture while a same-task handoff is retained restarts through the L-row receipt. A legacy
    machine receipt → `covered` without a selection.
  - Capture for every purpose without pre-seeded confirmations (finding 3 of round 3), assembled, both D13
    routes: (1) `reassess` on the seeded B1 copy: the hold opened with `history_ref = legacy:216a787…`, a
    revised criterion whose source receipt sits only in that history frontier; the question names the active
    version and the history receipt; accept → one ledger entry and a receipt with purpose `reassess`; the
    `reassess` activation selects it → `covered`. (2) `remote-child` on a fresh host under a `pending`
    marker with T's package as candidate: capture under E9 appends one entry, advances `restored.frontier` and
    `captures` in the same transaction, publishes no state; the `remote-child` activation selects it →
    `covered`; a restart before activation replays the ledger through the L-row receipt. Then (3) the origin
    publishes T: the next startup replaces nothing (detail `remote-activation-local-confirmations`); discarding
    the candidate retires the receipt to history and the following startup replaces through (i).
  - Consent replay (finding 2 of round 3), modern route with captured request states: decline, then resend
    the first round's state with an affirmative answer → the recorded `declined`, no ledger append, no receipt,
    no second elicitation (callback count 1); same after cancel, and after an accept refused at the re-check
    (`frontier-stale`, `ledger-full`); an applied accept resent → its recorded confirmation, nothing written. A
    new call after a decline asks again under the next sequence, and the old state replayed against that newer
    open generation → `question-closed`, nothing written. Two concurrent first rounds for one subject → only
    the latest generation can be answered.
  - Legacy authority (finding 5 of round 3): a v18 frontier with schema-1 embedding receipts and a v2 snapshot
    load unchanged (stored bytes and digests), compare equal through the N row, and a Change holding them
    activates: the first write emits frontier 20 and the receipts' bytes and IDs stay unchanged; a v19 frontier
    likewise.
  - A user waiver (N03 U1 (b)) of an `unchanged` criterion with its applicable `waive` confirmation, cited as
    `reusable`, stays `waived` and satisfies finalization after activation and after a fresh-host restore; the
    projection shows it as waived.
  - Finalization basis (finding 9): without records the basis digest equals N03's schema-1 digest byte for
    byte; with records, `show_finalization_context` returns basis schema 2 and finalization with the matching
    review succeeds.
  - Records survive a fresh-host restore (snapshot carries them) with identical statuses.
- **Negative scenarios:**
  - Missing disposition, duplicate disposition, `reviewer_id == author_id`, stale `impact_digest`, a cited
    receipt absent from history or with a mismatched `observation_id`, a failed verdict cited as `reusable`, a
    non-ancestor commit → refused before the intent with the named reason.
  - A `waived` or `human-confirmed` receipt cited as `reusable` for a `revised`, `new` or legacy-matched
    criterion with only its old-version confirmation → `applicability-confirmation-version-changed`, nothing
    written; a confirmation for another Change, outcome, criterion version or procedure, or with a non-affirmative
    decision (`keep-required`, `failed`) → `confirmation-not-applicable`; an ID absent from the ledger →
    `confirmation-unresolved`; a B1-style request resolved through the old caller-provenance route, present only
    in request history → `confirmation-unresolved`. Each checked before the intent, after the reset and after a
    fresh-host restore; activation and reassessment never append to the ledger (ledger bytes compared).
  - Capture: `decline` or `cancel` → `declined`, ledger and receipts unchanged, the generation answered; no form
    elicitation, or a legacy
    session without a back-channel → `channel-unavailable`; a `revision` scope naming the active version, another
    outcome's criterion or a criterion absent from the candidate → `confirmation-scope-invalid`, nothing asked;
    purpose `reassess` with another `history_ref`, purpose `remote-child` without a marker or with a candidate
    other than T's package, and purpose `revision` under a `reassess` hold → refused before any question;
    the candidate or frontier changed between the rounds of the modern route → the SDK boundary refuses
    `INVALID_PARAMS` or the CAS refuses `frontier-stale`, nothing written; Cockpit → `channel-unavailable`; a
    local ledger entry with no revision-confirmation receipt during a retained handoff → bootstrap fails (V20).
  - Same-head applicability change (finding 9): take the finalization context and an exact review at head H;
    run `reassess` (no head move) so the records change; `finalize_change` with the old review →
    `review-basis-stale`, no receipt; a fresh context and review then finalize. A record whose cited
    confirmation list differs with records otherwise equal also changes the basis.
  - `reassess` while `finalization` or `ready` exists → `reassess-requires-unfinalized`; a `history_ref`
    naming the active contract, a frontier-named legacy directory or an unreadable record →
    `reassess-history-invalid`.
  - No path creates a request automatically; the removed MCP fields are rejected by strict models.
  - Corruption: a record whose embedded receipt was altered → parse failure, Change unavailable with its
    existing diagnostic, never rehashed (V20).
  - Downgrade: the predecessor refuses the new frontier and snapshot versions.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_revision_applicability.py
  serve/delivery/tests/test_evidence.py -q`.
- **Closeout:** `uv run test --changed`; Ruff; `tests/test_agent_ecosystem_validation.py`; `npm run test:e2e:work`
  (seed changed).
- **LC:** full form; untouched legacy records (every live v18 frontier, schema-1 embedding receipt and v2
  snapshot) load with unchanged bytes and compare through the N row; no live record is rewritten by reading;
  additionally compute the impact view for B1 on the copy against `legacy:216a787…` and record it (read only).
- **Size / risk:** L / high (frontier version, evaluator rule, reviewer contract).

### 3.5 N04-C — Designer workflow, Change requirements and revision context

- **Prerequisites:** N04-B.
- **Editable paths:** `portfolio_application.py` / `application_readiness.py` (`show_revision_context`);
  `application_models.py`; MCP `target_server.py`, `target_models.py`;
  `serve/cockpit/src/owlbear_cockpit/routes/target_work.py`, `serve/cockpit/src/owlbear_cockpit/target_models.py`;
  `serve/cockpit/web/src/api/workItems.ts`, `components/WorkItemDetail.tsx`, `components/DesignWorkDetail.tsx`,
  `components/workItemPresentation.ts`, `pages/WorkPortfolioPage.tsx`, their tests; E2E seed and the
  work-portfolio spec; `tests/test_cockpit_boundary.py`;
  `share/skills/w-design-session/SKILL.md` (same-Change revision route; S01 resolved; approval question including
  the U3 consent), `share/agents/designer.agent.md`, `share/prompts/design.prompt.md`,
  `share/agents/designer-challenger.agent.md`; `tests/test_agent_ecosystem_validation.py`;
  `serve/delivery/README.md` (revision model); this plan's C row; execution plan C status row.
- **Positive scenarios:** `/design <change-id>` on an admitted Change loads the revision context and asks one
  material question at a time; the Designer drafts the candidate, previews impact, dispatches the reviewer,
  asks the user through `confirm_revision_criterion` for each reused human step whose criterion version
  changed (Cockpit lists them read-only while N03 U2 is open, G17),
  presents the delta and approves through one question; activation replays after a closed chat. Cockpit
  **Change requirements** on Change detail and group copies the complete prompt with "Run it in Copilot Chat";
  the hold and activation states render. Host rehearsal on a disposable portfolio with real VS Code: a
  requirement change of a Change with one reviewed task, a Design-return readmission per U3, and a crash
  resumed by `/continue-change`.
- **Negative scenarios:** ecosystem tests fail when the skill reintroduces "do not revise the admitted package"
  for nonterminal Changes, lets the Designer choose stages or invalidation IDs, calls `admit_change` for a
  revision, or omits independent review; the control never claims to start an agent; a completed Change shows
  successor guidance instead of the control.
- **Inner loop:** `uv run pytest tests/test_agent_ecosystem_validation.py -q`; `npm test -- WorkItemDetail`.
- **Closeout:** `uv run test --changed`; `npm test`; `npm run build`; Biome; `npm run test:e2e:work`; host
  rehearsal evidence on the PR.
- **LC:** load form (no format change; loader untouched).
- **Size / risk:** M / medium.

### 3.6 N04-D — Cumulative proof and B1 rehearsal

- **Prerequisites:** N04-C.
- **Editable paths:** tests only (`serve/delivery/tests/test_revision_activation.py`,
  `test_revision_applicability.py`, `tests/test_cockpit_work_items.py`) and their fixtures; this plan's D row and
  §5; execution plan D status row.
- **Positive scenarios:** B1-like fixtures end to end through MCP and HTTP: repeated request IDs with an
  unchanged proven criterion reuse evidence (V15); a revised target not covered shows the exact gap and gets a
  prepared-step-free plan (V16); requirement change with old code and proof (V14); crash matrix rerun through
  the assembled stack (V21); interrupted activation visible in Cockpit (R14). LC rehearsal on an isolated live
  copy: `reconcile-revision-snapshot` then `reassess` for B1; every Change available; a fresh-host restore of
  the copy succeeds.
- **Negative scenarios:** the same fixtures with a stale review, a terminal Change and a declined U3 consent
  stay contained with their reasons.
- **Closeout:** package closeout: full `uv run test` once; `npm test`, `npm run build`, `npm run test:e2e:work`;
  cumulative Sol challenge of the whole N04 diff against this plan.
- **LC:** full form (rehearsal above); live unchanged.
- **Size / risk:** M / medium.

### 3.7 Required execution-plan deltas and false premises

Deltas (applied by the N04-P PR only after the plan gate and the user's approval, execution plan §1.1):

1. §4.1 N04 stays XL / high; §5 N04 phases become **N04-A1** (candidate slot, hold, root-aware recovery),
   **N04-A2a** (deterministic snapshot plumbing for every snapshot caller: schema-2 intent, pinned child,
   signing and hook rules, with its own format, fingerprint and LC companions), **N04-A2b** (activation
   operation, Design-return readmission engine path, fresh-host restore and resolution, legacy reconcile),
   **N04-B**, **N04-C** (workflow, Cockpit control, revision context), **N04-D** (D12, D33). Design-return
   readmission moves from C to A2b; MCP adapters ship with their contracts in A1, A2b and B (execution plan
   Implement action).
2. §4.2: `N04-A1` ← N04-P, N03-C, N09-A2; `N04-A2a` ← N04-A1; `N04-A2b` ← N04-A2a; `N04-B`, `N04-C`, `N04-D` ←
   the previous phase. N07-A keeps N04-D. §4.3 schedule stage 4 lane A: `N04-P … N04-D` unchanged in order.
3. §4.4: rows `N04-A1`, `N04-A2a`, `N04-A2b` replace `N04-A`.
4. §5 N04 LC line: full form for A1, A2a, A2b, B and D; load form for C.
5. §7: record N04 U1 (a), U2 (a) and U3 (b) as engineering decisions of 2026-10-03 (listed to the user without
   objection), beside the inherited N03 U1 (b) answer.
6. Round-2 delta (D33, Sol reviewer advice): the A2 split is now part of the plan, not a conditional fallback;
   §4.1 sizes become A2a M / high and A2b L / high. §4.3 notes that N04-B and N04-C depend on N03 U2 only for
   whether Cockpit may capture candidate-scoped confirmations; chat capture does not wait for it (G17).

Premises found false or incomplete on `ac3bf23f9`:

1. §5 N04 "reusing `DesignPackageStore` revisions and admission `revisions/`": the store has one active slot
   that `revise` overwrites (`design_package.py:239-293`); `revisions/` mixes contract-digest and frontier-digest
   names (P1; `delivery_admission.py:425`, `application_recovery.py:877`) and cannot hold two departures from one
   contract (D20). N04 adds a candidate slot (D1) and an operation-keyed generation history; legacy `revisions/`
   stays read-only history.
2. §2.2 frames only the retained-handoff refusal as open. Every revision of a Change with reviewed work already
   fails after committing authority (P8), cannot be replayed (P7) and cannot publish after an interruption (P5);
   live B1 is in that state (P1, P2).
3. Not listed anywhere: a crash inside any Design package transaction stops controller startup (P3).
4. The registry's frontier write bypasses the central mutability policy (P9; D15).
5. Found in Sol round 1 (§6): the package snapshot owner cannot resume after a process death between its
   file writes and its commit (D17); the commit quarantine flattens staged content (D16); a fresh host leaves a
   Change whose remote branch is ahead of its snapshot unrestored and invisible (D18).
6. Found in Sol round 2 (§6): the snapshot intent carries no child identity, so no snapshot caller can replay
   deterministically (D28); the provider's draft-state operation fixes its head, so a demotion bound to the
   finalized head cannot be replayed once the child is pushed (D26); `git status` omits untracked empty
   directories and Git cannot hold non-canonical modes of clean files (D30); N03's boundary can confirm only
   requests already in the active frontier (D27).
7. Found in Sol round 3 (§6): `clean -fd` deletes entries a reverted ignore rule no longer covers (D34); an
   SDK-authenticated request state is not consumed by a decline, a cancel or an unapplied accept (D36); D03's
   out-of-band recovery cannot serve a finalized Change inside an activation (D35).

## 4. Progress

| Phase | PR | Exact head | Proof | Challenges | Status |
| --- | --- | --- | --- | --- | --- |
| N04-P | #358 | — | Probes P1–P9; round-1 source re-reads (§6); round-2 dependency re-pins and source re-reads, P10 Git hook and signing probe (§6); round-3 merge of `origin/dev` `141795676`, #360 re-pin `f4d09d774` and source re-reads (§6) | Sol plan round 1: revision-required (10 findings: 8 high, 2 medium; all accepted, none rebutted) → revised; Sol plan round 2: revision-required (round-1 findings 5, 6, 7, 9, 10 resolved; 1–4 and 8 incomplete as 8 findings: 5 high, 3 medium; all accepted, none rebutted) → revised, A2 split; Sol plan round 3: revision-required (9 findings: 6 high, 3 medium; all accepted, none rebutted; G18 settled) → revised | in review |
| N04-A1 | — | — | — | — | — |
| N04-A2a | — | — | — | — | — |
| N04-A2b | — | — | — | — | — |
| N04-B | — | — | — | — | — |
| N04-C | — | — | — | — | — |
| N04-D | — | — | — | — | — |

## 5. Verification Gaps

| ID | Claim | Why unproven | Evidence available | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | N03-A…C (as amended by #360) and N02-C land with the interfaces this plan names (`evidence.py` fold, `applies_to`, confirmation ledger, `resolve_confirmation`, `confirmation_applies`, basis digest, D13 `Resolve` registration and both routes, schema-2 request-resolution receipts and the L row, bounded remote Git); N09-A2 merged (`141795676`) with K3 sites, `require_pause_permits`, drain tokens and the K4 digest | Not merged (N09-A2 merged) | Their plans; PR #360 `f4d09d774` read only; `dev` `141795676` | N04-A1 (re-check at start; a divergence stops for a plan revision) | N04-A1 start |
| G2 | Every runtime-root recoverer can learn the package and candidate roots without a layout assumption | Tests construct coordinators with non-sibling package roots (`test_portfolio_application.py:851-925`) | P3 | N04-A1 | N04-A1 merge |
| G3 | One `RuntimeTransaction` spanning package and runtime roots recovers from every crash point through every reader | Not executed for a cross-root commit | P3 (single-root package participants) | N04-A2b crash matrix | N04-A2b merge |
| G4 | Three-component preservation (D16, D25, D30, D34) captures and restores divergent staged and working-tree content, full file and directory modes, symlinks, untracked files and empty directories, refuses ignored collisions and ignore-rule flips (scratch `check-ignore` evaluation) and leaves ignored entries verified in place, on macOS and Ubuntu file systems | Not implemented; D03 raw preservation refuses staged content and the commit quarantine flattens it (§6 round 1 finding 1, round 2 findings 1 and 6, round 3 findings 1 and 8) | Source reads; D03 preservation tests | N04-A2b falsifiers (§3.3) | N04-A2b merge |
| G5 | A real reviewer gives sound applicability dispositions | Semantic judgment | Engine structure checks | N04-C host rehearsal | N04-C merge |
| G6 | The B1 live copy reconciles and reassesses cleanly | Needs the isolated LC copy, not taken in P | P1, P2 (read-only) | N04-D LC rehearsal | N04-D merge |
| G7 | Live B1, `delivery-action-readiness` and `frontier-serialization-contract` revision state | Live activation is out of scope | P1 | N10-M with user authorization | N10-M |
| G8 | LC runs in CI | Needs a live copy | `delivery-lc` unit tests | Each phase | Nothing (recorded per phase) |
| G9 | U2 (a) wait time is acceptable to users | Product judgment; U2 was settled as an engineering decision | — | N10-H host acceptance | Nothing |
| G10 | A cited `human-confirmed` or `waived` receipt keeps an applicable confirmation after the outcome reset and after a fresh-host restore | Resolved in design by N03 (as amended by #360): the Change-wide ledger travels in the snapshot and survives resets (N03 I10); not yet executed | N03 §1.5, §1.9; §1.7 Confirmation authority | N04-B scenarios (finding 8) | N04-B merge |
| G11 | Remote rules that require signed commits on Change branches while the managed repository does not sign locally | Resolved in design for local configuration (D32: signing honored once, child pinned before the intent, replay never recomputes or re-signs; no hooks, P10). A provider-side signature rule is not observable from the repository; an unsigned child would be refused at push and stay pending. This exposure already applies to every Builder commit, so N04 adds none | P10; `draft_pull_request.py` provider surface | N04-A2a start (re-check whether the N05-A provider exposes branch rules; if so, A0 refuses `snapshot-signing-failed` before the intent) | Nothing |
| G12 | With the origin host lost, a different revision on a fresh host first needs the `remote-child` resolution for the pinned child, then a second activation | Accepted limitation of D18 (no remote overwrite); the resolution itself is now a fenced entry (E6) | — | N04-C revision context shows it; N10-H host acceptance | Nothing |
| G13 | N03's `confirmation_applies` can take the `DeliveryConfirmationUse` view without changing N03 results | N03-A not merged; the generalization edits an N03 owner | N03 §1.5 | N04-B start (re-check; a divergence stops for a plan revision) | N04-B start |
| G14 | Every N09-A2 start site is classified for the hold and the marker, including sites added by N05-B or N08 after PR #357 | Inventory read at `9a7fff990`; later sites unknown | `_COORDINATOR_PAUSE_CLASSES`, `_MANAGER_PAUSE_CLASSES`, `_APPLICATION_PAUSE_GATED_ENTRIES` | N04-A1 (`_HOLD_CLASSES` completeness test fails on an unclassified site) | N04-A1 merge |
| G15 | N03's ledger validation is structural (digest, append-only, ≤ 256, scope well-formed) and accepts an entry whose scope names candidate criterion versions and whose request is not in a binding | N03-A not merged; N03 §1.5 does not state whether the ledger checks scope against the admitted contract | N03 §1.5, I10, L row | N04-B start (re-check; if N03 validates scope against the active contract, the plan is revised before B) | N04-B start |
| G16 | `_MAX_DESIGN_RETURN_WALK_ENTRIES` admits realistic retained worktrees | The bound is fixed at A2b start from the largest supported fixture | D03 bounds (`_MAX_PRESERVED_PATHS` = 256, file 16 MiB, total 64 MiB) | N04-A2b start | N04-A2b merge |
| G17 | Whether Cockpit may capture candidate-scoped confirmations | N03 U2 is an open user decision | N03 U2 | User (N03 U2) | Nothing in N04-B; N04-C Cockpit copy only |
| G18 | An activation whose A1b or A5 observes a foreign Change head after the intent has a recovery route | Settled in design in round 3 (D35, §1.6 Foreign Change head): observe and journal, user-only authorization under E10 with a consent generation, local pin, observed-head demotion and a lease push; not yet executed | §3.3 foreign-head scenarios | N04-A2b | N04-A2b merge |
| G19 | The D13 `Resolve` dependency can seal `generation_id` in the SDK request state so that the boundary authenticates it with the method, tool and argument digest | N03-A not merged; N05 D14 needs the same capability; #360 is under review and may replace N03 D13's frontier-as-generation rule with a shared owner | N05 D14, N03 D13 *Single use* (#360 `f4d09d774`) | N04-A2b start (re-check; if sealing is unavailable, the generation ID becomes a server-issued required argument returned by the first round, and a shared #360 owner replaces `revision_consent`) | N04-A2b start |

## 6. Round Dispositions

Sol plan gate round 1 (on `561b2db3f`): `revision-required`, 10 findings. Each premise was re-read in source on
lane D `561b2db3f` (= `origin/dev` `634a77be7` + plan), lane A `feadd6777` (N09-A2) and lane C `9c06c97cd`
(N03 amendment). No finding was rebutted; two were accepted with a narrower premise (noted).

| # | Finding | Premise check | Disposition | Plan change |
| --- | --- | --- | --- | --- |
| 1 | HIGH: preservation loses distinct staged content | Confirmed: `_quarantine_commit` builds one tree from the filesystem via a temporary index (`workspace_snapshots.py:652-670`), then `reset --hard` and `clean -fd` (`:451-452`); staged-vs-file divergence is lost. Narrower: `clean -fd` keeps ignored files in place (not deleted, but not inventoried or verified); Git trees record the executable bit and symlinks but not other permission bits. D03 raw preservation refuses staged content (`workspace_preservation.py:328-330`) | Accepted | I12; §1.6 A2 and Design-return preservation; D16; §3.3 falsifiers and negatives; G4 |
| 2 | HIGH: A3 cannot replay an interrupted pre-commit snapshot | Confirmed: files written and staged before `git commit` (`:241-255`); rollback only on `Exception` (`:257`); replay requires a clean worktree (`:238`, `:294`) | Accepted | I4; §1.6 A0, A1, A3 and Deterministic child commit; D17; §3.3 crash injections at file publication, staging and commit; G11 |
| 3 | HIGH: fresh-host restore fails between branch push and state push | Confirmed: a remote branch ahead of `change_head` raises `_DeferredRemoteStateReconciliationError` (`delivery_application_loader.py:734-751`, `:2211-2221`); the Change is not restored. A local Change whose remote branch is ahead meets the same check in `_validate_local_snapshot` (`:625-633`) | Accepted | §1.1; §1.6 A5, Loader, Fresh-host restore; D5, D18; `remote_activation_pending`; §3.3 tests at both push boundaries; G12 |
| 4 | HIGH: the hold blocks its own required starts | Confirmed on PR #357: `_validate_update` refuses an intent-creating snapshot replacement under a policy; `acquire`, `acquire_continuation_action`, `start_continuation_action`, `reserve_publication` and `prepare_review_repair` (`start_pause_fenced`) are pause-gated (`tests/test_delivery_worktree_authority.py:1676-1835`) | Accepted | §1.5 Hold exceptions E1–E5 and start-site table; I5; D21; §3.2 inventory test; §3.3 race tests; G14 |
| 5 | HIGH: A0b's owner is unsafe inside activation | Confirmed: `prepare_review_repair` takes the checkpoint lock (`application_publication.py:860`), writes a `review-repair` invalidation and clears `ready` (`delivery_runtime.py:1296-1338`) and publishes state (`application_publication.py:879`); pause-gated in PR #357 | Accepted | §1.5 ready and review-repair rows; §1.6 A1, A1b, A4; I3 merged-PR exception; D22; §3.3 crash-after-A1b scenario |
| 6 | HIGH: operation ID collides across kinds | Confirmed from the plan text: snapshot-reconcile and reassess both have base = candidate = active with an unchanged contract | Accepted | §1.4 Operation identity; §1.7 Reassessment request and history selection; D19; §3.3 reconcile-then-reassess test |
| 7 | HIGH: history keyed by contract digest | Confirmed: create participants at `revisions/<contract digest>/` (`delivery_admission.py:425-429`); a differing existing file conflicts (`runtime_transaction.py:357`) | Accepted | I2; §1.4 layout; §1.6 Generation history; §1.8 `revision_generation`; D20; §3.3 A → B → A → C test |
| 8 | HIGH: portable confirmation authority undefined | Confirmed for the old text (request-bound waiver rule, G10 open); N03 (as amended by #360) supplies the ledger and resolver | Accepted | I11; §1.7 records and Confirmation authority; U1 text; D23; §3.4 positives and negatives; G10, G13 |
| 9 | MEDIUM: applicability not in the finalization basis | Confirmed: N03's basis holds contract, head, diff base, result digests and acceptance only; reassessment changes records without a head move | Accepted | §1.7 Finalization basis; §1.8 basis row; D13, D24; §3.4 same-head staleness test |
| 10 | MEDIUM: persisted action-schema changes missing | Confirmed: `ChangeContinuationAction.kind` is a closed literal (`workspace_models.py:551-571`) embedded in coordination and in unversioned action receipts (`state_formats.py` `action_receipt`) | Accepted | §1.8 coordination v4 and `action_receipt` rows, baseline versions; §3.3 paths, persisted-schema test and LC |

Sol plan gate round 2 (on `dba34da20`): `revision-required`. Round-1 findings 5, 6, 7, 9 and 10 were resolved;
findings 1–4 and 8 were incomplete and returned as eight findings. Dependencies were re-pinned first (lane A
`9a7fff990`, lane C `86289635f`; header, §2, G1, G14) and each premise was re-read in source on lane D
(`dba34da20`) and lane A. No finding was rebutted; three were accepted with a noted scope difference. The
reviewer's split advice was applied (D33).

| # | Finding | Premise check | Disposition | Plan change |
| --- | --- | --- | --- | --- |
| 1 | HIGH: `reset --hard` can overwrite an ignored file at a path tracked at the reviewed head | Confirmed: the reset writes every path of the reviewed head, and file/directory replacement deletes the other kind; the ignored inventory held hashes only, and post-cleanup verification runs after the bytes are gone. Narrower: untracked (not ignored) entries are captured byte-exactly, so only ignored entries need the refusal | Accepted | I12; §1.6 A0, A2, Collision check, cleanup paragraph; D25; §1.9 `revision-preservation-collision`; §3.3 A2b merge-blocking collision falsifier and variants; G4 |
| 2 | HIGH: fresh-host resolution (ii) blocked by its own marker; A1b binds the finalized head while the PR shows T | Confirmed: the marker refused every start; the provider stores one operation per ID (`draft_pull_request.py:680`) and checks the stored head on every call, including a replay with a receipt (`:746-762`). Broader: the same head mismatch breaks a same-host A1b replay after the A5 branch push | Accepted | §1.5 E6, E8; §1.6 A1, A1b (observed head, `demotion.json`), per-kind table, Fresh-host (ii); D26; §1.8 coordination v5 marker fields; §3.3 A2b origin-lost ready-Change test and same-host replay test; G12, G18; P10 |
| 3 | HIGH: candidate-version confirmations have no capture route | Confirmed: N03's `resolve_request` and MCP `answer` confirm only an existing scoped request (N03 §1.8 rows); N04 created none and kept the ledger unchanged at activation | Accepted | I11; §1.4 layout; §1.7 impact digest, record selections, Confirmation authority, Candidate-scoped capture; §1.8 `revision_confirmation`, frontier row; §1.9 `confirm_revision_criterion`, `open_revision_hold`; D27; §3.4 paths, capture test on both routes without pre-seeded confirmations, negatives; §3.5; G15, G17 |
| 4 | HIGH: deterministic replay incomplete for first-checkpoint callers | Confirmed: `ChangeDesignPackageSnapshotIntent` schema 1 (`workspace_models.py:1055` on `dev`) holds operation, Change, package, branch, worktree and expected head only | Accepted | I4; §1.6 A1, Deterministic child commit (carrier, schema-1 treatment); §1.8 coordination v4 (A2a); D28; §3.3 A2a crash matrix, schema-1 states, fingerprint and LC |
| 5 | HIGH: fresh-host replacement (i) checks too little | Confirmed: round-1 (i) compared only the frontier digest, custody and pending publication; a staged or filesystem edit changes none of them | Accepted | §1.6 Fresh-host step 2 `restored` fence and (i); §1.5 E7; §1.9 readiness detail; D29; §3.3 A2b fenced-replacement test and variants |
| 6 | MEDIUM: inventory cannot enumerate empty directories or non-Git modes | Confirmed: `status --untracked-files=all` lists no empty directory; Git records only 100644/100755 for files, so a clean file's 0600 is invisible | Accepted | §1.6 preservation rows and Bounded walk; D30; §3.3 A2b falsifiers (clean 0600 file, empty directory absent from status); G16 |
| 7 | MEDIUM: activation steps lack a per-kind contract | Confirmed from the plan text: `reassess` moves no head; legacy reconcile has no candidate or prior hold | Accepted | §1.6 Per-kind contract (incl. first-checkpoint snapshot, hold source, custody, restart owner); §1.4 kinds; §1.9; D31; §3.3 A2b parametrized test |
| 8 | MEDIUM: G11 signed-commit fallback not durable; hook behavior unresolved | Confirmed: an unreferenced signed object is prunable and re-signing changes the SHA. Hooks: P10 shows this repository's pre-commit excludes package paths | Accepted | I4; §1.4 pin row; §1.6 Deterministic child commit steps 2, 3, 6; D32; §3.3 A2a signed, pruned and hook tests; G11 narrowed; P10 |
| — | Advice: split A2 | Agreed: A2a is independently useful | Accepted | D12, D33; §3.3; §3.7 deltas 1–4 and 6; §1.8; §4 |

Sol plan gate round 3 (on `909998159`): `revision-required`, 9 findings (6 high, 3 medium). First `origin/dev`
`141795676` (N09-A2 merged) was merged into lane D and #360 re-pinned at `f4d09d774` (header, §2, G1). Each
premise was re-read in source on lane D and in the lane C plans at `f4d09d774`. No finding was rebutted; two
were accepted with a noted scope difference.

| # | Finding | Premise check | Disposition | Plan change |
| --- | --- | --- | --- | --- |
| 1 | HIGH: an ignored entry can lose its rule at the reset and be deleted by `clean -fd` | Confirmed: the quarantine path runs `reset --hard` then `clean -fd` (`workspace_snapshots.py` `quarantine_dirty_worktree`), and the plan reused that cleanup; in-tree `.gitignore` files revert with the reset while `info/exclude` and `core.excludesFile` do not. Broader: a staged or unstaged `.gitignore` edit has the same effect as a retained commit | Accepted | I12; §1.6 preservation rows, Rule-change check, cleanup without `git clean`; D34; §1.9 detail `ignore-rule-change`; §3.3 rule-change falsifiers (file and directory, staged, unstaged, nested, late change, reverse flip); G4 |
| 2 | HIGH: an unconsumed request state can be replayed with an affirmative answer | Confirmed from #360 `f4d09d774`: N03 D13 *Single use* says a decline or cancel writes nothing and an unapplied accept consumed nothing; N05 D14 adopts a single-use `merge_consent` generation for that reason. N04's capture wrote nothing on decline | Accepted | I13; §1.7 Consent generation (aligned with N05 D14); §1.8 `revision_consent`; §1.9 `question-closed`; D36; §3.4 replay tests; G19 |
| 3 | HIGH: capture unreachable for `reassess` and `remote-child` | Confirmed: the question required a `purpose: revision` hold, and the marker admitted only E6–E8 | Accepted | §1.5 E5, E6, E9; §1.6 marker `captures` and (i)/(ii); §1.7 per-purpose fences and request identity; `open_revision_hold` binds `history_ref`; D37; §3.4 assembled capture for both kinds without pre-seeded confirmations |
| 4 | HIGH: fresh-host replacement has no durable replay owner | Confirmed from the plan text: (i) was one transaction plus separate Git steps with the marker cleared somewhere between | Accepted | §1.6 (i) steps 1–4 with `replacement.json`, stored snapshot bytes and marker `replacing`; §1.8 `remote_activation_replacement`, marker fields; D38; §3.3 restart proof at every boundary |
| 5 | HIGH: frontier widening drops v18 | Confirmed: `dev` frontier is `Literal[18]`; N03 (#360) widens to `Literal[18, 19]` with 18 `readable-legacy`, a v2/v3 snapshot union and receipt widenings that keep embedded frontiers at 18; the plan's `Literal[19, 20]` lost 18 | Accepted | §1.8 baseline, frontier `Literal[18, 19, 20]` with S/N/L rows, snapshot `2, 3, 4` plus v1 upcast, enumerated embedding receipts (schema 3) and unchanged nested receipts; §3.3 and §3.4 legacy tests; A2b and B LC include untouched legacy records |
| 6 | HIGH: G18 strands an activation after the intent | Confirmed: `recover_out_of_band_head`'s caller refuses a finalized Change and runs under `_operator_start(..., publishes_checkpoint=True)`; the workspace step resets the local branch and preserves at `refs/owlbear/recovery/...`. Narrower: it does not force-update the remote; the stranding comes from the activation having no route to replace the foreign remote head | Accepted; G18 settled | §1.5 E10 and inventory note; §1.6 A0 remote check, A1b and A5 rows, Foreign Change head (observe, user-only authorization, predecessor fences, preserve, lease push, replay per head, formerly ready and merged cases); §1.8 journal files; §1.9 tool and reasons; D35; §3.3 scenarios; G18 |
| 7 | MED: schema-1 upgrade wrote schema 2 before building the child | Confirmed from the plan text (step 7) | Accepted | §1.6 step 7 (build and pin, then CAS replacement); §1.8 v4 row; D39; §3.3 A2a crash checks around the replacement |
| 8 | MED: nonempty directory modes omitted | Confirmed: the walk recorded only empty directories; Git keeps no directory modes; D03's receipt keeps only the worktree root's mode | Accepted | §1.6 Filesystem row and restore order; D34 note; §3.3 `0o700`/`0o750` falsifiers under two umasks; G4 |
| 9 | MED: A0/A1 contradict the per-kind matrix | Confirmed: A0 always built a child and A1 always wrote a snapshot intent | Accepted | §1.5 E1; §1.6 A0, A1 rows and per-kind rows (A0 Git objects, A1 snapshot intent); carrier `origin`; D39 note; §3.3 per-kind assertions |
