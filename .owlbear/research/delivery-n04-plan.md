# Delivery N04 — Same-Change Revision Activation and Evidence Applicability

> **Package:** N04 of the
> [execution plan](delivery-redesign-execution-plan.md#n04--same-change-revision-activation-and-evidence-applicability).
> **Planned on:** `origin/dev` `ac3bf23f9` (N00, N01, N02-A, N02-B and N09-A1 merged; N03-P, N05-P, N08-P and
> N09-P1 approved; N02-C, N02-D, N03-A…C, N05-A…D and N09-A2 not merged; Python 3.14.8). Live state read only:
> main checkout on `delivery-live` (D03). Rebased on `origin/dev` `634a77be7`: it adds only N05-A
> (`delivery-github`, `publication_provider.py`, forbidden-effect gates), so no locator here moved; P3–P8 rerun
> there with identical outcomes.
> **Status:** draft for the plan gate. Product code is unchanged by this phase. U1–U3 are recorded engineering
> decisions of 2026-10-03 ([1.13](#113-decisions)).
> Dependencies: the approved [N03 plan](delivery-n03-plan.md) (evidence model; its U1 was answered (b) by the
> user on 2026-10-03), the [N02 plan](delivery-n02-plan.md) (registry, gate, migration core; its U1 and U2 were
> answered (a): pinned live controller, `/upgrade-delivery`) and the [N09 plan](delivery-n09-plan.md) §1.11 (A2
> custody contract, which N04 extends).

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
- Activation is one replayable engine operation: intent → managed-branch snapshot child commit → one local
  transaction (package, contract, frontier, admission, history, coordination, pending publication, journal) →
  publication → release. Acquisition is blocked from intent to release. A crash at any boundary restarts to the
  old approved state (before the intent) or rolls forward to the exact new state, with no duplicate child commit.
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
  checkpoint ref, `revisions/<base contract digest>/` and the managed branch history.
- **I3 Roll forward only.** Before the activation intent the Change is in its old approved state and the user may
  discard the candidate. After the intent the operation only rolls forward; it never silently falls back
  (programme §8.3 step 5).
- **I4 One child commit.** An activation creates at most one managed-branch commit: the direct child of the
  intent's expected head, touching only `.owlbear/delivery/packages/<change>/`, with an operation-bound message.
- **I5 Acquisition fence.** From the hold, no new custody or effect start except draining owners (§1.5); from
  the intent to the release, only the activation owner's own steps.
- **I6 Immutable history.** No stored observation, review, result, finalization, snapshot or receipt changes
  bytes or identity (N03 I1). Applicability records embed the receipts they cite unchanged.
- **I7 No fabricated provenance.** Applicability records are reviewer statements. They never create
  `user-confirmed` provenance, resolve a request or satisfy a `human-confirmed` requirement on their own (V20).
- **I8 Terminal immutability.** Candidate creation, activation and admission refuse a completed or abandoned
  Change before any write.
- **I9 Gate first.** N02 I1 and I5 unchanged; every N04 family and version joins the registry with a format step.
- **I10 Policy, not custody.** The hold never stops a running worker or a started effect (N09 I6).

### 1.4 Authority layout

| Artifact | Location (under `.owlbear/delivery/`) | Owner | Class | Portable |
| --- | --- | --- | --- | --- |
| Active package | `packages/<change>/` (layout unchanged) | `DesignPackageStore` (active root) | T, R | via branch snapshot |
| Active package history | `refs/owlbear/packages/<change>` | `DesignPackageStore.checkpoint` | Git | no |
| Candidate package (admitted Changes only) | `runtime/package-candidates/<change>/{authority.json,design.md,intent.md,manifest.json}`; `authority.json` always empty | second `DesignPackageStore` instance | M | no (host-local, like unadmitted drafts) |
| Candidate history | `refs/owlbear/package-candidates/<change>` | `DesignPackageStore.checkpoint` with a ref namespace | Git | no |
| Revision hold | `ChangeCoordination.revision_hold` | `PortfolioCoordinator` | M | no |
| Activation journal | `runtime/changes/<change>/revision-activations/<sha256(operation_id)>/{intent,local,result}.json` | activation owner (A2) | R | no |
| Contract, frontier, admission history | `runtime/changes/<change>/revisions/<base contract digest>/` (existing) | `DeliveryAuthorityRegistry` | H | no |
| Applicability records | frontier binding `applicability` (B) | runtime | M (nested) | yes (snapshot) |

- **Unadmitted Changes** keep today's in-place `create_design_session` / `revise_design_session` / `put_design`.
- **Candidate identity.** The candidate's authored package ID is the manifest digest with empty authority
  (`_approved_package_id` pattern). The activated package adds the compiled contract as `authority.json`.
- **Operation identity.** `operation_id = "revision-" + sha256(change_id, base authored package ID, candidate
  authored package ID, contract digest)[:40]`, valid under the existing operation-ID pattern.
- **Approval record.** The intent stores `approval {approved_package_id, contract_digest, impact_digest,
  review_id, approved_at}` from the Designer's call after explicit user approval: the same trust as today's
  `admit_change` (an engine cannot prove what the user said; it binds what was approved).

### 1.5 Revision hold and quiescence

The hold reuses N09-A2's start serialization: every K3 start site refuses `CoordinationConflictError`
"Change revision hold" when `revision_hold` is present, in the same transaction as its start marker, exactly as
for `pause_request`. Opening a hold is a K1-style admission (one transaction: candidate files plus the
coordination replacement, observed frontier bytes as an exact no-op participant), never waits and never takes
custody. Rows below follow U2 (a).

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
| Finalized or ready (awaiting merge) | — | Allowed: the ready PR is demoted to draft through the existing draft-state owner before the intent; the local transaction records a finalization invalidation (`head-drift`: the head changes) |
| Change attention (publication or acceptance disposition) | — | Refused `change-attention` (existing resolution route first) |
| Completed or abandoned | Candidate creation refused | Refused `change-terminal` with successor guidance |
| Branch not at the reviewed head, or dirty worktree without custody | — | Refused `revision-workspace-unclean` (D03 containment routes) |
| Pre-N04 stale branch snapshot (§1.6 legacy reconcile) | — | Refused `revision-snapshot-stale` until reconciled |

K4 (N09): `recovery_authority_digest` also excludes `revision_hold`, so opening or clearing a hold never
invalidates an issued recovery journal or preservation receipt. K6 field rule: every coordination replacement
built from a captured model copies `revision_hold` from the bytes it replaces.

### 1.6 Activation operation

| Step | Durable effect | Crash after this step → restart |
| --- | --- | --- |
| A0 Validate | None. Under the acquisition and checkpoint locks: hold present for this base; §1.5 preconditions; candidate verified and compiles to `contract_digest`; base package equals active; frontier digest equals expected; branch head equals `last_reviewed_commit`, worktree clean (except U3 handoff); approval and (from B) applicability review bound | Old approved state; nothing to replay |
| A0b Demote (ready only) | Existing draft-state operation (`prepare_review_repair` route) | Finalized, draft PR: an existing state; the identical request resumes |
| A1 Intent | One transaction: journal `intent.json` (all §1.4 identities, expected frontier, branch head and snapshot receipt, approval, review ID, handoff disposition) and coordination with a `design_package_snapshot_intent` for this operation, parent = reviewed head, fenced by K3 | Old authority plus intent: readiness `revision-activation-pending`; acquisition refused; replay continues |
| A2 Preserve (U3 (b) only) | Retained Design-route handoff captured into `refs/owlbear/quarantine/<change>/<attempt>` with its receipt; worktree reset to the reviewed head | Replay recognizes ref and receipt; never captures twice |
| A3 Child commit | Package files (candidate bytes plus compiled `authority.json`) committed as the direct child of the intent's expected head | Replay recognizes the child by parent, tree and message (`_replay_design_package_snapshot` rule); never commits twice |
| A4 Local commit | One `RuntimeTransaction` across the package and runtime roots: active package files; contract, frontier, admission; `revisions/<base contract digest>/`; coordination (snapshot receipt, `last_reviewed_commit` = child, intent cleared, consumed passive custody); pending checkpoint (admitted-design trigger at the child) and pending state publication on the base digest; finalization invalidation; journal `local.json` with the digest of every written artifact | Any runtime-root recoverer completes the transaction (A1 fix); the loader accepts the journal-bound local successor; publication replays |
| A5 Publish | Existing owners: checkpoint branch push, state snapshot, draft PR summary; bounded remote Git with unknown-write readback (N02-C) | Branch pushed but state not: replay publishes the state. Remote outage: stays pending with its reason |
| A6 Release | One transaction: journal `result.json`, `revision_hold` cleared, publication acknowledged, then candidate slot removed by idempotent cleanup | Released; the Change continues under the new authority |

- **Who runs it.** The Designer calls `activate_revision` after approval. After any interruption the identical
  call, or the continuation engine action `reconcile-revision-activation` (D02 action framework, selected first
  for the Change), resumes from the journal; the checkpoint supervisor may publish A5.
- **Replay rules.** Same operation ID and intent digest → resume. Same operation ID, different digest →
  `operation-conflict`, no write. Another operation while one is unfinished → `activation-pending`.
- **Loader.** `_is_unpublished_revision_activation_successor(snapshot, local, journal)`: the remote snapshot's
  `package_id` and `authority_digest` equal the journal base; local package, contract, admission, frontier and
  coordination receipt equal the `local.json` digests (or the frontier is a recognized pending-publication
  successor of them); then `_validate_local_snapshot` accepts and publication replays. Without a matching
  journal the existing mismatch failure stands.
- **Fresh host.** A restore reads the remote snapshot and the package at its `change_head`, so a crash before
  A5 restores the old approved state and after A5 the new one. Branch-before-state publication order keeps both
  coherent.
- **Legacy reconcile (live B1).** No journal, `coordination.design_package_snapshot.package_id` differs from
  the active package, and the active `authority.json` equals the runtime contract digest → readiness
  `revision-snapshot-stale` and the engine action `reconcile-revision-snapshot`: a journal of kind
  `snapshot-reconcile` with base = candidate = active, A1, A3, A4 (coordination receipt and the queued
  checkpoint only), A5, A6. No package, contract or binding change; no user approval (no semantic change).

### 1.7 Applicability

**Impact view** (B; engine, pure; `preview_revision_impact`). Inputs: base contract, candidate contract, current
frontier, history frontier for reassessment, N03 evaluator. Per candidate criterion (N03 §1.4 identities): mapping
`unchanged` (same ID and version), `revised` (same ID, new version), `new`, `legacy-version-match` (legacy IDs
match only by version), `legacy-unmatched`; prior N03 status under the base; the observations, results and
applicability records that established it. Also retired criteria, `_invalidated_outcomes`, affected blocks and
requests, custody and handoff impact. `impact_digest` = sha256 of its canonical JSON.

**Reviewer** (`build-reviewer`, mode `applicability`): given the impact view, the contract delta, the cited
receipts and the code diff since each cited commit over the task's maintained surfaces. It returns
`DeliveryApplicabilityReview{review_id, impact_digest, author_id, reviewer_id, dispositions, reviewed_at}`.

| Disposition | Engine-checked rule | Evaluator effect (N03 fold) |
| --- | --- | --- |
| `reusable` | ≥ 1 cited receipt with a satisfying verdict (or a legacy receipt under [U1](#u1--may-reviewed-applicability-attribute-legacy-evidence) (a)), at an ancestor of the current head, that covered this criterion ID or a version-matched legacy criterion; a `waived` receipt only for an `unchanged` criterion | `covered` (`waived` for a cited waiver) |
| `partial` | Cited receipts plus `missing_scope` (1–240 chars) | `missing`, owner `agent`, scope as reason |
| `invalidated` | `changed_assumption` (1–240 chars) names the defeated code, procedure, target or condition | `uncovered` |
| `unknown` | `search_note` (1–240 chars): which history was searched | `unknown` |

Completeness: exactly one disposition per candidate criterion with prior evidence in an invalidated outcome;
criteria without prior evidence need none (they are `uncovered`). `reviewer_id != author_id`. The review binds
`impact_digest`; a stale digest is refused (`applicability-review-stale`).

**Records.** Activation writes `DeliveryApplicabilityRecord{record_id, operation_id, acceptance (new ref),
disposition, sources (≤ 8 embedded receipts, schema 1 or 2, unchanged, plus their source acceptance refs),
rationale (≤ 480), missing_scope, changed_assumption, search_note, review_id, reviewer_id}` onto the binding of
each invalidated outcome. The N03 fold processes a binding's applicability records before its task results, so
later evidence closes or reopens gaps (N03 D5).

**Waivers (N03 U1 (b)).** A user waiver satisfies finalization only for the exact criterion version its resolved
`user-confirmed` request binds (N03 I6) and is shown as waived. A `reusable` record may cite a `waived` receipt
only when the criterion's mapping is `unchanged` (same ID and version); for a `revised`, `new` or legacy-matched
criterion the review is refused (`applicability-waiver-version-changed`), so a waiver never crosses a version
change. The impact view shows each prior `waived` status, so the approval names every waiver the revision ends.

**Carry-forward replacement.** `preserve_unresolved_outcome_ids` and `_carry_forward_unresolved_binding` are
removed (no compatibility path). An invalidated outcome is reset to Planning as today (prior tasks, results,
blocks and requests stay in `revisions/` history) and gains its applicability records. Unchanged outcomes keep
their bindings, blocks and requests. `show_plan_context` adds the outcome's revision view (statuses, prior task
summaries from history), so the Planner plans only `uncovered`, `missing` and `unknown` criteria; a Builder
raises an N03-scoped request (`applies_to`) only for a genuinely human step.

**Reassessment** of an already admitted revision with a blanket carried request (live B1): an activation of kind
`reassess` with base = candidate package, impact base = the history contract in `revisions/<digest>/`, prior
evidence from that history frontier. It resets the affected binding (the blanket request moves to history),
writes reviewed records and changes no package, contract or branch. The Designer presents it and the user
approves, because it supersedes the user's open request.

### 1.8 Persisted families, versions and migration

Version numbers are assigned at merge (N05-P format-marker rule: whichever phase merges second renumbers and
reruns LC). "Widen" follows N03 I2: `Literal[old, new]`, old instances validated unchanged, new fields omitted
when `None` or empty.

| Family | Change | Phase | Old records |
| --- | --- | --- | --- |
| `coordination` | +1 after N09-A2: `revision_hold` (omitted when `None`); widen; K4 digest excludes it | A1 | Unchanged; first write emits the new version |
| `package_candidate` (new) | `runtime/package-candidates/<c>/manifest.json` (owner `DesignPackageManifest` v1, M), `authority.json` (`allow_empty`), documents (`read=False`) | A1 | None exist |
| `revision_activation` (new) | `intent`, `local`, `result` models, version 1, R | A2 | None exist |
| `frontier` | +1 after N03: binding `applicability` (omitted when empty); widen under N03's stored-byte contract and comparison inventory | B | `readable-legacy`; no rewrite (N03 D3) |
| `snapshot` (remote) | +1 widen (embeds the frontier) | B | Parse natively |
| Receipts embedding bindings or frontiers (N03 §1.7 list) | Widen | B | Unchanged |
| `format` marker | One marker-only step per phase A1, A2 and B | A1, A2, B | — |
| `contract`, `admission`, `package`, `revision_record` | Unchanged | — | — |

Downgrade: a predecessor release refuses the new format and versions before parsing (N02 D3). The
`DeliveryFinalizationInvalidation` reason stays `head-drift` (D13), so no nested literal changes.

### 1.9 Interfaces and error cases

| Interface | Phase | Behavior |
| --- | --- | --- |
| `revise_design_session(change_id, expected_package_id, intent, design)` | A1 | Unadmitted: unchanged. Admitted nonterminal: `expected_package_id` is the current candidate ID, or the active authored ID to open the first candidate; writes only the candidate slot and opens the hold in one transaction. `_admitted_design_revision_allowed` is removed |
| `read_revision_candidate(change_id)` / `discard_revision_candidate(change_id, expected_package_id)` | A1 | Candidate or `None`; discard removes the candidate and clears the hold; refused after an intent |
| `derive_delivery_contract(change_id, candidate=True)` | A1 | Compiles the candidate without publication |
| `admit_change` / `admit_delivery_change` | A2 | First admission and worktree-recovery admission only; an admitted Change → `revision-requires-activation`. `preserve_unresolved_outcome_ids`, `expected_frontier_digest` and `expected_design_package_snapshot_receipt_id` are removed from the request |
| `activate_revision(DeliveryRevisionActivationRequest)` | A2 (B adds the review) | `{change_id, expected_base_package_id, expected_candidate_package_id, expected_contract_digest, expected_frontier_digest, approval, applicability_review, handoff_disposition}` → `DeliveryRevisionActivationResult{operation_id, state: intent \| local \| published \| released, replayed}` |
| Engine actions `reconcile-revision-activation`, `reconcile-revision-snapshot` | A2 | Selected before every other action of the Change; executable through `acquire_change_action` / `execute_change_action` |
| `preview_revision_impact(change_id)` | B | Impact view and digest |
| `show_revision_context(change_id)` | C | Active proposal, candidate, hold, criteria with N03 identities, per-outcome stage, task and evidence history, current blocks and requests, Design-return context, activation state |
| Readiness reasons `revision-hold`, `revision-activation-pending`, `revision-snapshot-stale` | A1, A2, A2 | Each with TypeScript mirror, rendering, component test and parity (R16) |
| Error | A1–B | `DeliveryRevisionError(DeliveryRuntimeConflictError)`, code `ERR_DELIVERY_REVISION`, `reason` in: `change-terminal`, `change-paused`, `change-attention`, `revision-hold-absent`, `candidate-stale`, `base-stale`, `contract-mismatch`, `frontier-stale`, `revision-custody-active`, `revision-drain-pending`, `revision-custody-retained`, `revision-workspace-unclean`, `handoff-disposition-required`, `design-return-lineage-changed`, `activation-pending`, `operation-conflict`, `revision-requires-activation`, `revision-snapshot-stale`, `applicability-review-required`, `applicability-review-incomplete`, `applicability-review-stale`, `applicability-waiver-version-changed`, `reviewer-not-independent` |
| MCP | each phase | Strict models for every new or changed tool in the phase that introduces it; error code mapping in `target_server.py` |
| HTTP / Cockpit | C | `GET /api/changes/{id}/revision` (revision context); **Change requirements** on Change detail and group: explanatory view plus copy of `/design <change-id>` (N09 D6 copy pattern); hold and activation states rendered |

### 1.10 Existing owners to reuse

`DesignPackageStore` (second root; ref namespace parameter) and its CAS, verification and checkpoint
(`design_package.py:106-399`); `RuntimeTransaction` multi-root participants (`runtime_transaction.py:120-428`);
`snapshot_design_package` intent, receipt and child replay (`workspace_snapshots.py:74-306`);
`quarantine_dirty_worktree` capture (`workspace_snapshots.py:417-455`) for U3 (b); `_delivery_frontier` and
`_invalidated_outcomes` (`delivery_admission.py:437-604`); D02 engine actions and receipts; `_publish_delivery_state`,
`_publish_checkpoint_branch`, `_reconcile_change_checkpoint`, `DeliveryPendingStatePublication`; N09-A2 K1–K7;
N03 evaluator, identities and `applies_to`; `prepare_review_repair` draft demotion; `FinalizationReportStore`
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
- **N08:** an interrupted activation is replay, not repair; diagnosis lists `revision_activation` journals;
  degraded Cockpit shows `revision-activation-pending` Changes.
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
  snapshot head (`workspace_snapshots.py:159-162`), which fails after the first reviewed commit.
- **D5 Journal-bound loader successor** (P5). The loader's package check (`delivery_application_loader.py:579`)
  stays; only a journal whose base matches the remote snapshot and whose `local.json` matches local state is a
  recoverable successor.
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
- **D12 Re-split N04-A into A1 and A2** (§3.7): hold and candidate before the activation operation, each with
  its adapters and companions.
- **D13 Finalization invalidation reuses `head-drift`.** Activation always moves the head (child commit), so the
  existing validator (`runtime_models.py:564-597`) accepts it without a schema change.
- **D14 The hold is a separate coordination field, not a pause request.** It must not convert into a deferral
  (N09 K5) and must coexist with Pause.
- **D15 Activation joins the central mutability policy.** Its frontier write goes through a `DeliveryRuntime`
  facade method (`prepare_revision_activation`, registered in `_NORMAL_CHANGE_MUTATIONS`), unlike today's
  registry write, which bypasses `_require_change_mutable` (`delivery_admission.py:183-255`).

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
  user confirmation scoped to the criterion version (N03 `applies_to`). The receipt is cited, never changed.
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
- **Rationale for (a):** it reuses N09-A2's fences unchanged, never wastes work on soon-invalidated outcomes and
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
  with consent:** the approval question asks the user to let Delivery move the retained work into a local
  quarantine ref (existing capture: commits, index and worktree including untracked; never pushed), reset to the
  reviewed head, then activate normally; the revised Planner receives the ref as prior work. Declining keeps
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

N03-A…C, N02-C and N09-A2 are not implemented; N04 uses their planned interfaces ([G1](#5-verification-gaps)).

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
    `workspace_coordination.py` (`open_revision_hold`, `clear_revision_hold`, K3 checks beside
    `pause_request`, K4 digest exclusion, K6 field copy)
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
    claim runs; an engine action started before the hold finishes (N09 K2 row reused).
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

### 3.3 N04-A2 — Activation operation, Design-return readmission and legacy reconcile

- **Prerequisites:** N04-A1.
- **Editable paths:**
  - new `serve/delivery/src/owlbear_delivery/revision_activation.py` (journal models, operation steps)
  - `delivery_admission.py` (first-admission only; `prepare_revision_authority` returning participants;
    request fields removed)
  - `delivery_runtime.py` facade (`prepare_revision_activation`, registered mutation); `runtime_models.py`
    (`_NORMAL_CHANGE_MUTATIONS`)
  - `workspace_snapshots.py` (child-of-reviewed-head replacement returning a coordination participant;
    U3 (b): `quarantine_dirty_worktree` accepts a settled Design-route handoff under activation authority);
    `workspace_coordination.py` (participant helpers)
  - `portfolio_application.py` (`activate_revision`, `admit_delivery_change` refusal); `application_acquisition.py`
    (engine-action selection and execution); `application_publication.py` (A5 owner path);
    `application_readiness.py`, `work_items.py` (`revision-activation-pending`, `revision-snapshot-stale`);
    `application_models.py`
  - `delivery_application_loader.py` (`_is_unpublished_revision_activation_successor`, legacy detection)
  - `state_formats.py` (`revision_activation` family, marker step); `state_migration.py`;
    `serve/tools/src/owlbear_tools/delivery_diagnostics.py`
  - `owlbear_delivery/__init__.py`, `module_surface.json`, N02 fingerprint fixture
  - MCP `target_server.py`, `target_models.py` (`activate_revision`, changed `admit_change`); Cockpit
    `target_models.py`, `workItems.ts`, `workItemPresentation.ts`, `WorkItemDetail.tsx`,
    `WorkPortfolioPage.tsx` and tests; E2E seed
  - tests: new `serve/delivery/tests/test_revision_activation.py`; `test_source_bound_admission.py`,
    `test_portfolio_application.py` (including the D03 refusal test, rewritten to readmission),
    `test_change_workspace.py`, `test_delivery_state.py`, `test_checkpoint_publication_regressions.py`,
    `test_state_formats.py`, `test_state_migration.py`, `test_work_items.py`; MCP and Cockpit tests as in A1;
    `tests/test_delivery_worktree_authority.py`
  - companion skill text (call shapes only): `w-design-session` Step 10, `designer.agent.md`,
    `w-orchestration` / `continue-change` routing of the two engine actions;
    `tests/test_agent_ecosystem_validation.py`
  - this plan's A2 row; execution plan A2 status row
- **Positive scenarios:**
  - Clean activation of a Change with two reviewed tasks (P8 shape): one child commit on the reviewed head;
    contract, frontier, admission, package and history change in one transaction; publication publishes branch
    then state; release clears the hold; acquisition resumes for the revised outcome; unchanged outcomes keep
    their bindings (V14).
  - Crash matrix (V21), fresh process after each of: A0b, A1, A2, A3 (after the commit, before A4), inside A4
    after its first participant, after A4, A5 after the branch push, A5 after the state push (response lost),
    before A6: restart reaches the old state (before A1) or the exact new state after replay; one child commit;
    one state snapshot; blocks and requests not reset by the revision unchanged; a fresh-host restore before A5
    restores the old approved package and after A5 the new one.
  - Both resumption routes: identical `activate_revision` and `/continue-change` engine action.
  - Ready Change: the PR is demoted first; finalization invalidated (`head-drift`); readiness rebuilds.
  - Report-backed Finalizer attention consumed in A4; the report is retired.
  - Design-return readmission (rewritten `test_design_return_revised_admission_…`): per U3; under (b) the
    quarantine ref holds the exact committed, staged, unstaged and untracked bytes (content snapshot equality),
    the worktree is clean at the reviewed head before A3, and the revised Planner context names the ref.
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
  - A3 replay finds a branch head that is not the intent's child → contained, no second commit.
  - Under U3 (b), a declined consent → `handoff-disposition-required`, nothing moved.
  - Activation of a completed Change via any route → `change-terminal`; the mutability-policy test enumerates
    `prepare_revision_activation`.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_revision_activation.py -q -k "crash or replay"`.
- **Closeout:** as A1, plus `uv run pytest serve/delivery/tests/test_delivery_state.py -q -k "revision or restore"`.
- **LC:** full form: migration, every live Change available; on the copy, B1 shows `revision-snapshot-stale`
  (record, do not run on live); predecessor refuses; live hashes unchanged.
- **Size / risk:** L / high (multi-root commit, loader, Git effects).

### 3.4 N04-B — Applicability assessment and carry-forward replacement

- **Prerequisites:** N04-A2.
- **Editable paths:**
  - new `serve/delivery/src/owlbear_delivery/applicability.py` (impact view, review validation, records)
  - `evidence.py` [N03] (fold: records before results); `runtime_models.py` (`DeliveryApplicabilityRecord`,
    binding `applicability`, frontier version); `runtime_receipts.py` (widened embedding receipts);
    `delivery_state.py` (snapshot version); `delivery_application_loader.py` (S and N rows of N03's comparison
    inventory for the new version)
  - `delivery_admission.py` (remove `_carry_forward_unresolved_binding`, `_carry_forward_request_id`,
    `preserve_unresolved_outcome_ids`); `revision_activation.py` (review binding, `reassess` kind)
  - `portfolio_application.py` (`preview_revision_impact`); `application_acquisition.py`
    (`show_plan_context` revision view); `application_models.py`; `application_lifecycle.py` (finalization
    `semantics` includes records)
  - `state_formats.py`, `state_migration.py` (frontier and snapshot widening, marker step);
    `delivery_diagnostics.py`
  - `__init__.py`, `module_surface.json`, fingerprint fixture; MCP `target_server.py`, `target_models.py`
    (`preview_revision_impact`; `activate_revision` review field required)
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
  - `reassess` on a seeded copy of B1's carried state: the blanket request moves to history; records written;
    no package, contract or branch change; one publication.
  - Under U1 (a): a legacy machine receipt cited as `reusable` covers; a legacy human-procedure receipt covers
    only with a resolved `user-confirmed` request scoped to that criterion version and procedure.
  - A user waiver (N03 U1 (b)) of an `unchanged` criterion cited as `reusable` stays `waived` and satisfies
    finalization after activation; the projection shows it as waived.
  - Records survive a fresh-host restore (snapshot carries them) with identical statuses.
- **Negative scenarios:**
  - Missing disposition, duplicate disposition, `reviewer_id == author_id`, stale `impact_digest`, a cited
    receipt absent from history or with a mismatched `observation_id`, a failed verdict cited as `reusable`, a
    non-ancestor commit → refused before the intent with the named reason.
  - A `waived` receipt cited as `reusable` for a `revised`, `new` or legacy-matched criterion →
    `applicability-waiver-version-changed`, nothing written; a waiver never crosses a version change.
  - No path creates a request automatically; the removed MCP fields are rejected by strict models.
  - Corruption: a record whose embedded receipt was altered → parse failure, Change unavailable with its
    existing diagnostic, never rehashed (V20).
  - Downgrade: the predecessor refuses the new frontier and snapshot versions.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_revision_applicability.py
  serve/delivery/tests/test_evidence.py -q`.
- **Closeout:** `uv run test --changed`; Ruff; `tests/test_agent_ecosystem_validation.py`; `npm run test:e2e:work`
  (seed changed).
- **LC:** full form; additionally compute the impact view for B1 on the copy against `revisions/216a787…` and
  record it (read only).
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
   **N04-A2** (activation operation, Design-return readmission engine path, legacy reconcile), **N04-B**,
   **N04-C** (workflow, Cockpit control, revision context), **N04-D** (D12). Design-return readmission moves
   from C to A2; MCP adapters ship with their contracts in A1, A2 and B (execution plan Implement action).
2. §4.2: `N04-A1` ← N04-P, N03-C, N09-A2; `N04-A2` ← N04-A1; `N04-B`, `N04-C`, `N04-D` ← the previous phase.
   N07-A keeps N04-D. §4.3 schedule stage 4 lane A: `N04-P … N04-D` unchanged in order.
3. §4.4: rows `N04-A1`, `N04-A2` replace `N04-A`.
4. §5 N04 LC line: full form for A1, A2, B and D; load form for C.
5. §7: record N04 U1 (a), U2 (a) and U3 (b) as engineering decisions of 2026-10-03 (listed to the user without
   objection), beside the inherited N03 U1 (b) answer.

Premises found false or incomplete on `ac3bf23f9`:

1. §5 N04 "reusing `DesignPackageStore` revisions and admission `revisions/`": the store has one active slot
   that `revise` overwrites (`design_package.py:239-293`); `revisions/` mixes contract-digest and frontier-digest
   names (P1; `delivery_admission.py:425`, `application_recovery.py:877`). N04 adds a candidate slot (D1) and keeps
   `revisions/` as history only.
2. §2.2 frames only the retained-handoff refusal as open. Every revision of a Change with reviewed work already
   fails after committing authority (P8), cannot be replayed (P7) and cannot publish after an interruption (P5);
   live B1 is in that state (P1, P2).
3. Not listed anywhere: a crash inside any Design package transaction stops controller startup (P3).
4. The registry's frontier write bypasses the central mutability policy (P9; D15).

## 4. Progress

| Phase | PR | Exact head | Proof | Challenges | Status |
| --- | --- | --- | --- | --- | --- |
| N04-P | — | — | Probes P1–P9 | — | draft |
| N04-A1 | — | — | — | — | — |
| N04-A2 | — | — | — | — | — |
| N04-B | — | — | — | — | — |
| N04-C | — | — | — | — | — |
| N04-D | — | — | — | — | — |

## 5. Verification Gaps

| ID | Claim | Why unproven | Evidence available | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | N03-A…C, N09-A2 and N02-C land with the interfaces this plan names (`evidence.py` fold, `applies_to`, K3 sites, K4 digest, bounded remote Git) | Not implemented | Their approved plans | N04-A1 (re-check at start; a divergence stops for a plan revision) | N04-A1 start |
| G2 | Every runtime-root recoverer can learn the package and candidate roots without a layout assumption | Tests construct coordinators with non-sibling package roots (`test_portfolio_application.py:851-925`) | P3 | N04-A1 | N04-A1 merge |
| G3 | One `RuntimeTransaction` spanning package and runtime roots recovers from every crash point through every reader | Not executed for a cross-root commit | P3 (single-root package participants) | N04-A2 crash matrix | N04-A2 merge |
| G4 | U3 (b) capture preserves symlinks, modes and ignored-but-relevant files exactly | D03 quarantine was exercised for active writers only | `quarantine_dirty_worktree` tests | N04-A2 | N04-A2 merge |
| G5 | A real reviewer gives sound applicability dispositions | Semantic judgment | Engine structure checks | N04-C host rehearsal | N04-C merge |
| G6 | The B1 live copy reconciles and reassesses cleanly | Needs the isolated LC copy, not taken in P | P1, P2 (read-only) | N04-D LC rehearsal | N04-D merge |
| G7 | Live B1, `delivery-action-readiness` and `frontier-serialization-contract` revision state | Live activation is out of scope | P1 | N10-M with user authorization | N10-M |
| G8 | LC runs in CI | Needs a live copy | `delivery-lc` unit tests | Each phase | Nothing (recorded per phase) |
| G9 | U2 (a) wait time is acceptable to users | Product judgment; U2 was settled as an engineering decision | — | N10-H host acceptance | Nothing |
| G10 | A cited `human-confirmed` or `waived` receipt keeps a resolvable N03 I6 confirmation after the outcome reset moves its request to `revisions/` history and after a fresh-host restore (snapshots omit `revisions/`, P1) | The record embeds the receipt but not the request it cites (D7) | N03 I6; P1 | N04-B (embed or re-bind the resolved request, or refuse such citations) | N04-B merge |
