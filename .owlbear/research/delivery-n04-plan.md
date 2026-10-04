# Delivery N04 — Same-Change Revision Activation and Evidence Applicability

> **Package:** N04 of the
> [execution plan](delivery-redesign-execution-plan.md#n04--same-change-revision-activation-and-evidence-applicability).
> **Planned on:** `origin/dev` `ac3bf23f9` (N00, N01, N02-A, N02-B and N09-A1 merged; N03-P, N05-P, N08-P and
> N09-P1 approved; N02-C, N02-D, N03-A…C, N05-A…D and N09-A2 not merged; Python 3.14.8). Live state read only:
> main checkout on `delivery-live` (D03). Rebased on `origin/dev` `634a77be7`: it adds only N05-A
> (`delivery-github`, `publication_provider.py`, forbidden-effect gates), so no locator here moved; P3–P8 rerun
> there with identical outcomes.
> **Status:** draft for the plan gate; revised after Sol plan gate round 1 ([§6](#6-round-dispositions)).
> Product code is unchanged by this phase. U1–U3 are recorded engineering decisions of 2026-10-03
> ([1.13](#113-decisions)).
> Dependencies: **N03 (as amended by #360)**: the [N03 plan](delivery-n03-plan.md) with PR #360 (lane C
> `9c06c97cd`): evidence model, user-only confirmation through MCP elicitation (N03 D13, R14, I6) and the
> Change-wide append-only confirmation ledger `DeliveryFrontier.confirmations` read only through
> `resolve_confirmation` / `confirmation_applies` (N03 §1.5, I10, §1.9 N04 contract); its U1 was answered (b)
> by the user on 2026-10-03. The [N02 plan](delivery-n02-plan.md) (registry, gate, migration core; its U1 and
> U2 were answered (a): pinned live controller, `/upgrade-delivery`). The [N09 plan](delivery-n09-plan.md) §1.11
> (A2 custody contract, which N04 extends), checked against its implementation in PR #357 (lane A
> `feadd6777`: K3 fences, drain tokens and the start-site inventory in `tests/test_delivery_worktree_authority.py`).

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
  preserves an unpublished remote child without adopting or overwriting it.
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
- **I4 One deterministic child commit.** An activation creates at most one managed-branch commit: the direct
  child of the intent's expected head, touching only `.owlbear/delivery/packages/<change>/`, with an
  operation-bound message and the intent's fixed author, committer and dates, so its SHA is recorded in the
  intent before any Git write (§1.6 A3).
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
  derive authority from requests, request history or caller provenance.
- **I12 Complete preservation before cleanup.** Retained Design-return work is captured as three verified
  components (HEAD commits, the real index, the filesystem state including modes, symlinks and untracked
  files; ignored files inventoried and left in place) and re-verified against the live worktree before any
  cleanup byte changes.

### 1.4 Authority layout

| Artifact | Location (under `.owlbear/delivery/`) | Owner | Class | Portable |
| --- | --- | --- | --- | --- |
| Active package | `packages/<change>/` (layout unchanged) | `DesignPackageStore` (active root) | T, R | via branch snapshot |
| Active package history | `refs/owlbear/packages/<change>` | `DesignPackageStore.checkpoint` | Git | no |
| Candidate package (admitted Changes only) | `runtime/package-candidates/<change>/{authority.json,design.md,intent.md,manifest.json}`; `authority.json` always empty | second `DesignPackageStore` instance | M | no (host-local, like unadmitted drafts) |
| Candidate history | `refs/owlbear/package-candidates/<change>` | `DesignPackageStore.checkpoint` with a ref namespace | Git | no |
| Revision hold | `ChangeCoordination.revision_hold` (A1); bound activation operation added at A1 of the operation (A2) | `PortfolioCoordinator` | M | no |
| Activation journal | `runtime/changes/<change>/revision-activations/<operation_id>/{intent,local,result}.json` | activation owner (A2) | R | no |
| Design-return preservation | `runtime/changes/<change>/revision-activations/<operation_id>/preservation/{manifest.json,blobs/<sha256>}` (owner-private, D03 store rules); refs `refs/owlbear/preserved/<change>/<operation_id>/{head,index}` | activation owner (A2) | R | no |
| Generation history | `runtime/changes/<change>/revisions/generations/<operation_id>/{contract,frontier,admission}.json` (the replaced authority, H) and `generation.json` (R) | activation owner (A2) via `DeliveryAuthorityRegistry` participants | H, R | no |
| Legacy history | `runtime/changes/<change>/revisions/<64-hex>/` (existing; contract- or frontier-digest named) | none (read only) | H | no |
| Remote activation pin (fresh host) | `refs/owlbear/remote-activations/<change>/<operation_id>`; `ChangeCoordination.remote_activation_pending` | loader restore (A2) | Git, M | no |
| Applicability records | frontier binding `applicability` (B) | runtime | M (nested) | yes (snapshot) |

- **Unadmitted Changes** keep today's in-place `create_design_session` / `revise_design_session` / `put_design`.
- **Candidate identity.** The candidate's authored package ID is the manifest digest with empty authority
  (`_approved_package_id` pattern). The activated package adds the compiled contract as `authority.json`.
- **Operation identity.** `operation_id = "revision-" + sha256(canonical JSON {kind, change_id,
  base_package_id, candidate_package_id, contract_digest, predecessor: {reviewed_head, frontier_digest},
  history_ref})[:40]`, valid under the existing operation-ID pattern. `kind` is `revision`, `snapshot-reconcile`
  or `reassess`; the predecessor generation is the exact authority being replaced, named by the request's
  `expected_head` and `expected_frontier_digest` (both portable, both fixed from intent to release);
  `history_ref` is `null` except for `reassess` (§1.7). An identical request therefore recomputes the same ID at
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
| E1 | Activation intent | The replacement adds `design_package_snapshot_intent` whose `operation_id` equals `revision_hold.activation_operation_id` written by the same A1 transaction, whose `expected_head` equals the journal intent's expected head and whose `package_id` equals the intent's activated package ID | A2 |
| E2 | Activation owner steps | Process-local `revision-activation` drain token rebuilt at call start from the journal `intent.json` (operation ID, intent digest) whose ID equals `revision_hold.activation_operation_id`; permits only that operation's A1b draft operation `revision-draft-<operation_id>`, A3 ref update, A4 participants, A5 reservation for `_checkpoint_operation_id("branch", change, expected child)`, state publication `revision-<operation_id>`, and A6 | A2 |
| E3 | Reconciliation actions | `acquire_continuation_action` / `start_continuation_action` with kind `reconcile-revision-activation` and `revision_operation_id` equal to the hold's bound operation, or kind `reconcile-revision-snapshot` whose recomputed `snapshot-reconcile` operation ID equals `revision_operation_id` while no other activation is bound; every other kind refused | A2 |
| E4 | Retained same-task successor | Coordinator `acquire` and `prepare_builder_handoff_acquisition` for a Builder writer whose outcome, task and attempt lineage equal the passive `builder_handoff` (route `same-task`); a new task, a Planner claim, a Finalizer attempt or a different task refused | A1 |
| E5 | Hold policy writes | `open_revision_hold`, `clear_revision_hold`, candidate revise and discard (K1-style admission; no start) | A1 |

Every other N09-A2 start site stays refused under the hold. The inventory, from PR #357 (`feadd6777`), is
classified in `tests/test_delivery_worktree_authority.py` by a new `_HOLD_CLASSES` map beside
`_COORDINATOR_PAUSE_CLASSES`, `_MANAGER_PAUSE_CLASSES` and `_APPLICATION_PAUSE_GATED_ENTRIES`; an entry that is
pause-gated but has no hold class fails the test:

| N09-A2 start site | Hold class |
| --- | --- |
| Coordinator `acquire`, manager `acquire`, `prepare_builder_handoff_acquisition` | refused, except E4 |
| `acquire_continuation_action`, `start_continuation_action` | refused, except E3 |
| `update` (intent-creating snapshot replacement, `_validate_update`), manager `snapshot_design_package` | refused, except E1 (and E2 for the receipt completion) |
| `reserve_publication` | refused, except E2 and existing K2 tokens |
| `start_direct_operation` (`sync-target`, `mark-ready`), manager `sync_with_target` | refused |
| `start_pause_fenced` operator starts: `adopt_external_head`, `adopt_external_head_after_acceptance_attention`, `promote_external_head`, `abort_target_sync_conflict`, `resolve_target_sync_conflict`, `prepare_review_repair`, `reconcile_finalization_head`, `recover_out_of_band_head`, `repair_target_sync_publication`, `recover_publication_baseline`, `recover_change_worktree` | refused (`recover_change_worktree` and `recover_out_of_band_head` stay D03 containment routes: they run after Discard, or after the activation releases) |
| `prepare_pause_fence` (`observe-acceptance` provider fence; `complete_change`) | refused before A1; after A1 only the A1b merged-PR path (I3) reaches completion |
| `prepare_runtime_custody_guard` pause-gated class (K7) | refused, except E2 participants; completion class unchanged |
| Finalization repair release (`delivery_runtime.py` request check) and checkpoint publication refusal (`application_publication.py`) | refused, except E2 |

### 1.6 Activation operation

| Step | Durable effect | Crash after this step → restart |
| --- | --- | --- |
| A0 Validate | None. Under the acquisition and checkpoint locks: hold present for this base; §1.5 preconditions; candidate verified and compiles to `contract_digest`; base package equals active; frontier digest equals expected; branch head equals `last_reviewed_commit`, worktree clean (except U3 handoff, whose preservation inventory must fit the bounds); approval and (from B) applicability review bound. Computes the expected child (A3) by writing only Git objects | Old approved state; nothing to replay (unreachable objects only) |
| A1 Intent | One transaction: journal `intent.json` (kind, all §1.4 identities, predecessor generation, expected frontier, branch head, expected child SHA and tree, commit dates, approval, review ID, handoff disposition, ready-demotion binding: finalization ID, head, PR identity) and coordination with `revision_hold.activation_operation_id` and a `design_package_snapshot_intent` for this operation, parent = reviewed head (E1) | Old authority plus intent: readiness `revision-activation-pending`; acquisition refused; replay continues |
| A1b Demote (ready only) | Provider `return_to_draft` with operation `revision-draft-<operation_id>` under the E2 token, inside the activation's held checkpoint lock (no lock re-entry, no frontier write, no state publication); the provider's draft-state operation record is replay evidence | Ready frontier, draft PR, intent: fenced by `revision-activation-pending`; replay observes draft and continues. PR observed merged before any Git effect → journal `result.json` `superseded-by-merge`, hold cleared, acceptance owner completes (I3) |
| A2 Preserve (U3 (b) only) | `preserve_design_return_workspace` (§ Design-return preservation): HEAD ref, index ref and raw index, filesystem manifest and blobs; verified against the live worktree; then cleanup to the reviewed head and post-cleanup verification | Replay recognizes the stored manifest and refs, re-verifies, and never captures twice; a partial cleanup completes only on a worktree that matches the capture or the reviewed head path by path |
| A3 Child commit | `update-ref refs/heads/<branch> <expected child> <expected head>`, then the worktree moves to the child for the four package paths (§ Deterministic child commit) | Replay classifies the ref and each package path's index and file state as intent-bound (parent or child bytes only) and completes; any other dirt → contained `revision-workspace-unclean`, nothing written |
| A4 Local commit | One `RuntimeTransaction` across the package and runtime roots: active package files; contract, frontier (confirmations ledger carried byte-identical, N03 I10), admission; generation record `revisions/generations/<operation_id>/`; coordination (snapshot receipt, `last_reviewed_commit` = child, intent cleared, consumed passive custody); pending checkpoint (admitted-design trigger at the child) and pending state publication on the base digest; `ready` and `finalization` cleared with a `head-drift` invalidation when present; journal `local.json` with the digest of every written artifact | Any runtime-root recoverer completes the transaction (A1 fix); the loader accepts the journal-bound local successor; publication replays |
| A5 Publish | Existing owners: checkpoint branch push, state snapshot, draft PR summary; bounded remote Git with unknown-write readback (N02-C) | Branch pushed, state not: same host replays the state; a fresh host follows § Fresh-host restore. Remote outage: stays pending with its reason |
| A6 Release | One transaction: journal `result.json`, `revision_hold` cleared, publication acknowledged, then candidate slot removed by idempotent cleanup | Released; the Change continues under the new authority |

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

**Deterministic child commit (A3; D17).** The existing owner writes package files into the worktree, stages
them and runs `git commit` (`workspace_snapshots.py:241-255`); its rollback runs only for an `Exception`
(`:257`), not a process death, and its replay requires a clean worktree (`:238`, `:294`), so a crash between the
write and the commit can never resume. N04-A2 replaces
`_commit_design_package_snapshot` for every caller (activation, legacy reconcile and the first-checkpoint
snapshot) with:

1. Before the intent (A0): `git hash-object -w` the four package files; a temporary `GIT_INDEX_FILE` reads the
   parent tree and `update-index --cacheinfo` sets the four paths; `write-tree`; `commit-tree --no-gpg-sign`
   with parent = expected head, author and committer `OwlBear <owlbear@localhost>`, both dates fixed to the
   intent's `created_at`, message `chore: activate Design revision (<change>, <operation_id>)`
   (`chore: snapshot admitted Design package (…)` for the existing callers). No hooks run. The intent records the
   resulting child SHA and tree; recomputation at replay is byte-identical.
2. A3: `update-ref` with the expected old value (CAS), then for the worktree (whose HEAD follows the branch):
   `git checkout <child> -- <four paths>` updates index and files for those paths only.
3. Replay classifier, per package path: index entry and file bytes each equal either the parent's or the
   child's blob; branch at the expected head or the expected child; every other path clean
   (`status --porcelain=v1 -z --untracked-files=all` lists only package paths). Then it finishes the remaining
   sub-steps. A package path with other bytes, any other dirty or untracked path, or a branch elsewhere →
   contained `revision-workspace-unclean` with the exact paths; nothing is written or deleted.

**Design-return preservation (A2, U3 (b); D16).** `quarantine_dirty_worktree` is not reused: it builds one tree
from the filesystem through a temporary index (`workspace_snapshots.py:652-670`), so staged content that differs
from the file is lost; `reset --hard` then discards the real index (`:451-452`); ignored files are neither
inventoried nor verified, and Git trees keep only the executable bit. D03's raw preservation
(`workspace_preservation.py:284`) refuses staged content (`:328-330`) and is bound to a recovery journal. N04-A2 adds
`preserve_design_return_workspace(change_id, operation_id)` in `workspace_preservation.py`, reusing D03's
private store, index resolution, split-index refusal, path validation and bounds (`_MAX_PRESERVED_*`):

| Component | Captured | Verified before cleanup |
| --- | --- | --- |
| HEAD | Branch head (retained unreviewed commits) pinned at `refs/owlbear/preserved/<change>/<operation_id>/head` | Branch head and worktree HEAD equal it; reviewed head is an ancestor |
| Index | Raw index bytes (owner-private), entry records (path, mode, stage, object ID) and a tree written from a copy of the real index, committed under the head and pinned at `…/index` so staged blobs stay reachable; unmerged entries, split index, sparse or skip-worktree entries and gitlinks refused before the intent (A0) | Raw index digest and entry records equal the live index |
| Filesystem | Every path from `status --porcelain=v1 -z --untracked-files=all` plus tracked paths differing from the index: type (file, symlink, empty directory), full permission bits (`lstat`), size, sha256, symlink target (never followed; symlinked ancestors refused); bytes in `blobs/<sha256>` | Manifest recomputed from the live worktree equals the stored one |
| Ignored | `status --ignored=matching` inventory (path, type, mode, size, sha256), left in place | Inventory equal before cleanup and after it |

Cleanup is `reset --hard <reviewed head>` and `clean -fd` (never `-x`). Post-cleanup verification: worktree at
the reviewed head, index equal to its tree, no untracked path, ignored inventory unchanged. Bounds exceeded or a
refused entry kind is detected in A0 and refuses `revision-preservation-unsupported` before the intent. The
receipt `DesignReturnPreservationReceipt` (in `local.json` and the revised Planner context) names the refs and
manifest digest. A test-only `restore_design_return_preservation` into a scratch worktree reproduces HEAD,
`git ls-files -s` entries and the filesystem manifest exactly (merge-blocking falsifiers, §3.3).

**Fresh-host restore (A5; D18).** On a fresh host, a crash after the branch push and before the state push
leaves the remote branch one commit ahead of the snapshot's `change_head`. Today's loader then raises
`_DeferredRemoteStateReconciliationError` (`delivery_application_loader.py:734-751`, `:2211-2221`) and does not
restore the Change: it is invisible and has no route. N04-A2 adds a verified restore policy:

1. **Classify.** The remote tip T is a *verified activation child* iff its only parent is `change_head`, its
   diff touches only the four package paths, its message matches the activation message pattern with an
   operation ID, and its package verifies (`DesignPackageStore` manifest and authority checks) while the package
   at `change_head` equals the snapshot's `package_id`. Anything else keeps today's diagnostic.
2. **Restore old, preserve T.** Restore the snapshot's approved state at `change_head` (package, local branch
   and worktree at `change_head`), pin T at `refs/owlbear/remote-activations/<change>/<operation_id>` (local only),
   and record `ChangeCoordination.remote_activation_pending {operation_id, child, parent, restored_frontier_digest}`
   in the restore transaction. Readiness `revision-remote-activation-pending`; every start is refused (hold
   semantics with no exceptions). The remote branch is never pushed to, reset or force-updated from this host,
   and T is never treated as reviewed authority.
3. **Resolve.** (i) The origin host publishes its state: at the next startup the remote snapshot's
   `change_head` equals T; if local runtime bytes still equal `restored_frontier_digest` with no custody and no
   pending publication, the loader restores the new snapshot over the old one in one transaction and clears the
   marker. (ii) The origin host is lost: `/design <change>` offers T's package as the candidate; after user
   approval and full A0 validation (including a fresh applicability review), this host's activation adopts T as
   its child iff T's parent and tree equal the computed child (message aside), so A5 pushes nothing new. (iii) Any
   other revision is refused `revision-remote-activation-pending` until (i) or (ii) (G12).

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
requests, custody and handoff impact. `impact_digest` = sha256 of its canonical JSON.

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
confirmation_ids (≤ 8, ledger IDs, D23), rationale (≤ 480), missing_scope, changed_assumption, search_note,
review_id, reviewer_id}` onto the binding of each invalidated outcome. The N03 fold processes a binding's
applicability records before its task results, so later evidence closes or reopens gaps (N03 D5).

**Confirmation authority (D23; N03 (as amended by #360) §1.5, I6, I10, §1.9).** Portable authority for a
reused human step or waiver is the Change-wide append-only ledger `DeliveryFrontier.confirmations`, which
travels in every snapshot and which `_reset_binding`, request-history moves and activation leave unchanged. It is
never a request, a request in `revisions/` history or a caller provenance value. For each `reusable` record:

- A cited schema-2 `waived` or `human-confirmed` receipt contributes its own `confirmation_id`; a cited legacy
  (schema-1) human-procedure receipt under U1 (a) needs a `confirm-check` confirmation captured through the N03
  D13 boundary for the candidate criterion version and the receipt's `command_or_procedure` text.
- The engine resolves each ID with `resolve_confirmation(frontier, id)` and checks it with
  `confirmation_applies` on a `DeliveryConfirmationUse{change_id, outcome_id, acceptance refs, procedure,
  required decision}` (N04-B generalizes N03's observation argument to this view; the observation path becomes
  one caller; G13): same Change; the record's outcome; scope containing the exact candidate `(acceptance_id,
  acceptance_version)`; the exact procedure; the affirmative decision for the use (`waive`, or `passed`).
- For a `revised`, `new` or legacy-matched criterion an old confirmation is `stale-acceptance-version` (N03
  §1.9): the review is refused `applicability-confirmation-version-changed` until the user confirms the new
  version through the boundary. Same ID and version: the original confirmation applies.
- The check runs three times with identical inputs and results: at A0 (before the intent), in the evaluator
  fold after the reset moved requests to history, and after a fresh-host restore from the published snapshot.
  An ID absent from the ledger is `confirmation-unresolved`. A B1-style request resolved through the old
  caller-provenance route confers nothing (N03 R14).

The impact view shows each prior `waived` status and each cited confirmation, so the approval names every waiver
the revision ends.

**Finalization basis (D24).** N03's basis digest (`{schema: 1, contract_digest, change_head, diff_base,
result_digests, acceptance}`) does not cover applicability records or their confirmations, yet both decide
coverage. When any binding carries applicability records, N04-B computes basis schema 2: schema 1 plus
`applicability` (record IDs in fold order) and `confirmations` (the ledger IDs those records cite, in fold
order, each with its decision). Without records the basis stays schema 1 byte-identical. `semantics` adds the
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
frontier), and the user approves that exact ref; the engine refuses a ref whose contract digest equals the active
one (`reassess-history-invalid`) or that is unreadable. Impact base = that history contract; prior evidence =
that history frontier. It resets the affected binding (the blanket request moves to the new generation record),
writes reviewed records and changes no package, contract or branch, so it is refused while `finalization` or
`ready` exists (`reassess-requires-unfinalized`). The Designer presents it and the user approves, because it
supersedes the user's open request. For B1 the ref is `legacy:216a787…` (P1); a reconcile then a reassess are
two operations with distinct IDs and journals.

### 1.8 Persisted families, versions and migration

Version numbers are assigned at merge (N05-P format-marker rule: whichever phase merges second renumbers and
reruns LC). "Widen" follows N03 I2: `Literal[old, new]`, old instances validated unchanged and constrained to
old content, new fields omitted when `None` or empty. Baseline at N04-A1 start: coordination v2 (N09-A2),
frontier 19 with `confirmations` (N03-A as amended by #360), snapshot 3, format marker 2 (N03) plus N09-A2's
step; any intervening merge (N05-B, N08) is absorbed by the renumber rule.

| Family | Change | Phase | Old records |
| --- | --- | --- | --- |
| `coordination` | v2 → v3 (widen 2, 3): `revision_hold` (omitted when `None`); K4 digest excludes it | A1 | Unchanged; first write emits v3 |
| `coordination` | v3 → v4 (widen 2–4): `revision_hold.activation_operation_id`; `remote_activation_pending`; nested `continuation_action: ChangeContinuationAction` kind widened with `reconcile-revision-activation`, `reconcile-revision-snapshot` and optional `revision_operation_id` (required for those kinds, `exclude_if` None); a v2 or v3 instance holding any of these is rejected; K4 digest excludes the new fields | A2 | Unchanged; first write emits v4 |
| `action_receipt` (R, unversioned: `intent.json`, `started.json` = `ChangeContinuationAction` content; `result.json` = `DeliveryEngineActionResult`) | Same nested widening; existing receipt bytes, `continuation_start_recorded` byte equality and operation IDs unchanged (new fields absent); result kinds and reason codes reused (re-checked at A2 start; a needed new value is an A2 schema change under this row) | A2 | Unchanged; covered by A2's marker step (a predecessor refuses the marker before parsing) |
| `package_candidate` (new) | `runtime/package-candidates/<c>/manifest.json` (owner `DesignPackageManifest` v1, M), `authority.json` (`allow_empty`), documents (`read=False`) | A1 | None exist |
| `revision_activation` (new) | `revision-activations/<op>/(intent\|local\|result).json`: models v1, R | A2 | None exist |
| `revision_preservation` (new) | `revision-activations/<op>/preservation/manifest.json` (`DesignReturnPreservationManifest` v1, R); `blobs/<sha256>` (`read=False`, owner-private) | A2 | None exist |
| `revision_generation` (new) | `revisions/generations/<op>/generation.json` (`RevisionGeneration` v1, R); `revisions/generations/<op>/(contract\|frontier\|admission).json` (H, `read=False`); regex disjoint from `revision_record`'s 64-hex segment | A2 | None exist |
| `revision_record` (legacy H) | Unchanged; read only through `legacy:` history refs | — | Unchanged |
| `frontier` | 19 → 20 (widen 19, 20): binding `applicability` (omitted when empty); `confirmations` carried unchanged (N03 I10); stored-byte contract and comparison inventory of N03 §1.7 extended by the new successor row | B | `readable-legacy`; no rewrite (N03 D3) |
| `snapshot` (remote) | 3 → 4 widen (embeds the frontier) | B | Parse natively |
| Receipts embedding bindings or frontiers (N03 §1.7 list) | Widen | B | Unchanged |
| Finalization review basis | Basis schema 2 when records exist (§1.7 D24); a computation, not a stored family (the review stores only `basis_digest`) | B | Schema-1 reviews unchanged |
| `format` marker | One marker-only step per phase A1, A2 and B | A1, A2, B | — |
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
| `admit_change` / `admit_delivery_change` | A2 | First admission and worktree-recovery admission only; an admitted Change → `revision-requires-activation`. `preserve_unresolved_outcome_ids`, `expected_frontier_digest` and `expected_design_package_snapshot_receipt_id` are removed from the request |
| `activate_revision(DeliveryRevisionActivationRequest)` | A2 (B adds the review and `reassess`) | `{kind: revision \| reassess, change_id, expected_base_package_id, expected_candidate_package_id, expected_contract_digest, expected_head, expected_frontier_digest, history_ref (reassess only), approval, applicability_review, handoff_disposition}` → `DeliveryRevisionActivationResult{operation_id, kind, state: intent \| local \| published \| released \| superseded-by-merge, replayed}`; `snapshot-reconcile` runs only as an engine action |
| Engine actions `reconcile-revision-activation`, `reconcile-revision-snapshot` | A2 | Selected before every other action of the Change; executable through `acquire_change_action` / `execute_change_action` under hold exception E3; the action carries `revision_operation_id` |
| `preview_revision_impact(change_id, history_ref=None)` | B | Impact view and digest; lists eligible history refs (generation and legacy) |
| `show_revision_context(change_id)` | C | Active proposal, candidate, hold, criteria with N03 identities, per-outcome stage, task and evidence history, current blocks and requests, Design-return context, activation state |
| Readiness reasons `revision-hold`, `revision-activation-pending`, `revision-snapshot-stale`, `revision-remote-activation-pending` | A1, A2, A2, A2 | Each with TypeScript mirror, rendering, component test and parity (R16) |
| Error | A1–B | `DeliveryRevisionError(DeliveryRuntimeConflictError)`, code `ERR_DELIVERY_REVISION`, `reason` in: `change-terminal`, `change-paused`, `change-attention`, `review-repair-open`, `revision-hold-absent`, `candidate-stale`, `base-stale`, `contract-mismatch`, `frontier-stale`, `revision-custody-active`, `revision-drain-pending`, `revision-custody-retained`, `revision-workspace-unclean`, `revision-preservation-unsupported`, `handoff-disposition-required`, `design-return-lineage-changed`, `activation-pending`, `operation-conflict`, `revision-requires-activation`, `revision-snapshot-stale`, `revision-remote-activation-pending`, `reassess-requires-unfinalized`, `reassess-history-invalid`, `applicability-review-required`, `applicability-review-incomplete`, `applicability-review-stale`, `applicability-confirmation-version-changed`, `confirmation-unresolved`, `confirmation-not-applicable`, `reviewer-not-independent` |
| MCP | each phase | Strict models for every new or changed tool in the phase that introduces it; error code mapping in `target_server.py` |
| HTTP / Cockpit | C | `GET /api/changes/{id}/revision` (revision context); **Change requirements** on Change detail and group: explanatory view plus copy of `/design <change-id>` (N09 D6 copy pattern); hold and activation states rendered |

### 1.10 Existing owners to reuse

`DesignPackageStore` (second root; ref namespace parameter) and its CAS, verification and checkpoint
(`design_package.py:106-399`); `RuntimeTransaction` multi-root participants (`runtime_transaction.py:120-428`);
`snapshot_design_package` intent and receipt (`workspace_snapshots.py:74-306`; its commit step replaced, D17);
D03 private preservation store, index resolution, path validation and bounds (`workspace_preservation.py`) for
U3 (b) (D16); `_delivery_frontier` and
`_invalidated_outcomes` (`delivery_admission.py:437-604`); D02 engine actions and receipts; `_publish_delivery_state`,
`_publish_checkpoint_branch`, `_reconcile_change_checkpoint`, `DeliveryPendingStatePublication`; N09-A2 K1–K7,
`require_pause_permits`, drain tokens and the start-site inventory (PR #357); N03 (as amended by #360) evaluator,
identities, `applies_to`, confirmation ledger, `resolve_confirmation`, `confirmation_applies` and basis digest;
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
- **N08:** an interrupted activation is replay, not repair; diagnosis lists `revision_activation` journals and
  `remote_activation_pending` markers; degraded Cockpit shows `revision-activation-pending` and
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
- **D12 Re-split N04-A into A1 and A2** (§3.7): hold and candidate before the activation operation, each with
  its adapters and companions.
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

N03-A…C, N02-C and N09-A2 are not merged; N04 uses their planned interfaces ([G1](#5-verification-gaps)). Round 1
re-read N09-A2's implementation in PR #357 (`feadd6777`) and N03's amendment in PR #360 (`9c06c97cd`), read only.

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
    pause-gated coordinator, manager and application entry of PR #357 as hold-refused or hold-exception; an
    unclassified or doubly classified entry fails.
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
  - new `serve/delivery/src/owlbear_delivery/revision_activation.py` (journal, generation and preservation
    models, operation steps, operation identity)
  - `delivery_admission.py` (first-admission only; `prepare_revision_authority` returning participants and the
    generation record; request fields removed)
  - `delivery_runtime.py` facade (`prepare_revision_activation`, registered mutation; ledger append-only guard
    reused); `runtime_models.py` (`_NORMAL_CHANGE_MUTATIONS`)
  - `workspace_snapshots.py` (deterministic child commit for every caller of `_commit_design_package_snapshot`,
    intent-bound replay classifier, child-of-reviewed-head replacement returning a coordination participant);
    `workspace_preservation.py` (`preserve_design_return_workspace`, test-only restore);
    `workspace_models.py` (`ChangeContinuationAction` kinds and `revision_operation_id`,
    `revision_hold.activation_operation_id`, `remote_activation_pending`, coordination v4);
    `workspace_coordination.py` (participant helpers; exceptions E1–E3; E2 token kind)
  - `portfolio_application.py` (`activate_revision`, `admit_delivery_change` refusal); `application_acquisition.py`
    (engine-action selection and execution, E3); `application_publication.py` (A1b provider call, A5 owner path);
    `application_readiness.py`, `work_items.py` (`revision-activation-pending`, `revision-snapshot-stale`,
    `revision-remote-activation-pending`); `application_models.py`
  - `delivery_application_loader.py` (`_is_unpublished_revision_activation_successor` before the remote-head
    check, legacy detection, fresh-host verified activation child restore and resolution (i))
  - `state_formats.py` (`revision_activation`, `revision_preservation`, `revision_generation` families,
    coordination v4, action-receipt row, marker step); `state_migration.py`;
    `serve/tools/src/owlbear_tools/delivery_diagnostics.py`
  - `owlbear_delivery/__init__.py`, `module_surface.json`, N02 fingerprint fixture
  - MCP `target_server.py`, `target_models.py` (`activate_revision`, changed `admit_change`); Cockpit
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
  - this plan's A2 row; execution plan A2 status row
- **Positive scenarios:**
  - Clean activation of a Change with two reviewed tasks (P8 shape): one child commit on the reviewed head;
    contract, frontier, admission, package and history change in one transaction; publication publishes branch
    then state; release clears the hold; acquisition resumes for the revised outcome; unchanged outcomes keep
    their bindings (V14).
  - Crash matrix (V21), fresh process after each of: A1, A1b (after the provider call, before the next step),
    A2 (after capture, after verification, mid-cleanup), A3 (each sub-step below), inside A4 after its first
    participant, after A4, A5 after the branch push, A5 after the state push (response lost), before A6: restart
    reaches the old state (before A1) or the exact new state after replay; one child commit whose SHA equals
    the intent's; one state snapshot; blocks and requests not reset by the revision unchanged; the confirmation
    ledger byte-identical.
  - Deterministic child (finding 2), `BaseException` injected: after object and tree writes before the intent;
    after `update-ref` before checkout; after the checkout has written 1, 2 and 3 of the 4 package paths
    (file publication); after the index update but before the files (staging); after `commit-tree` before
    `update-ref` (commit). Each restarts through the default loader and the identical call or engine action and
    completes with the recorded child, a clean worktree and no second commit; the same matrix passes for the
    first-checkpoint snapshot caller.
  - Fresh-host restore (finding 3), real local bare remote, a second clone as the fresh host: (1) crash after
    the branch push, before the state push: the fresh host restores the old approved state at `change_head`,
    pins the remote child, shows `revision-remote-activation-pending` through `get_change`, MCP and HTTP, and
    the remote branch ref is unchanged; then the origin completes A5 and the fresh host's next startup restores
    the new snapshot over the old one; alternatively the origin is discarded and the fresh host's user-approved
    activation of the child's package adopts the pinned child (tree and parent equal) and pushes nothing new.
    (2) crash after the state push (response lost): the fresh host restores the new state directly. Both:
    the same-host restart also converges through the journal successor (remote branch equal to the expected
    child is accepted).
  - Both resumption routes: identical `activate_revision` and `/continue-change` engine action.
  - Ready Change (finding 5): A1 records the demotion binding; A1b demotes under the activation token while A0's
    checkpoint lock is held (no deadlock, no `review-repair` invalidation, no intermediate state publication);
    A4 clears `ready` and `finalization` with `head-drift`; readiness rebuilds. Crash after A1b, then restart:
    readiness `revision-activation-pending`, replay observes the draft PR and the ready Change activates; the
    provider sees exactly one draft-state operation `revision-draft-<operation_id>`.
  - Report-backed Finalizer attention consumed in A4; the report is retired.
  - Design-return readmission (rewritten `test_design_return_revised_admission_…`) under U3 (b), merge-blocking
    falsifiers (finding 1), each built in a real worktree before the return: a path whose staged blob differs
    from its working-tree bytes; a staged new file deleted from the working tree; an executable bit change and a
    `0o600` file; a symlink to a file inside and one pointing outside the worktree (never followed); an untracked
    file and an untracked empty directory; an ignored file (`.env`-style) and an ignored directory. After
    activation: the head ref equals the old branch head; the index ref's tree and stored entry records equal
    the original `git ls-files -s` output; the filesystem manifest equals the original `lstat`/sha256 inventory;
    the ignored inventory is unchanged in place; a test-only restore into a scratch worktree reproduces HEAD,
    index entries and filesystem manifest exactly. A crash after capture and mid-cleanup completes without a
    second capture; the revised Planner context names the preservation receipt.
  - Hold exceptions (finding 4), each a race test with barriers in the start transactions: E1 activation
    intent vs an unrelated snapshot intent start (only the bound one commits); E2 activation A5 reservation vs a
    `mark-ready` direct start (the latter refused); E3 `reconcile-revision-activation` acquisition vs a
    `sync-target` continuation (only the bound kind and operation acquire); E4 same-task successor vs a
    different-task claim racing the hold opening (exactly one of hold or claim wins; afterwards only the
    same-task successor starts). A forged `reconcile-revision-activation` action naming another operation is
    refused.
  - Operation identity (finding 6): legacy reconcile then `reassess` on the B1 shape produce two distinct
    operation IDs, journals and generation records; each identical request replays its own result; a
    `revision` repeated over an equal package pair at a later head gets a new ID.
  - Generation history (finding 7): activations A → B → A → C each write one generation record: three records
    with ordinals 1–3 holding the replaced authority byte-correctly, contract A replaced twice (records 1 and 3)
    under different operation IDs, and C active; `legacy:` refs resolve only contract-named legacy directories.
  - Persisted action schema (finding 10): a v3 coordination and an action receipt holding a new kind are
    rejected by the predecessor format gate; old action receipts parse byte-identically; the N02 fingerprint
    fixture records the widened `ChangeContinuationAction`, coordination v4 and the three new families.
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
  - Preservation: an unmerged index entry, split index, skip-worktree entry, gitlink, symlinked ancestor or a
    bound exceeded → `revision-preservation-unsupported` before the intent; a live worktree changed between
    capture and cleanup → verification fails, nothing cleaned, activation stays pending with the paths.
  - Fresh host: a remote tip that is not a verified activation child (two commits ahead, a non-package path, a
    wrong parent or message, a package that fails verification) keeps today's `remote-change-head-ahead`
    diagnostic; nothing restored, nothing pinned. With `remote_activation_pending` set, any other revision →
    `revision-remote-activation-pending`; local work after the restore (frontier digest differs) blocks the
    automatic replacement in resolution (i) and reports it.
  - Ready Change: the PR merged before A1b → `superseded-by-merge`, no Git effect, hold cleared; a
    `review-repair` invalidation present → `review-repair-open` before the intent.
  - Under the hold without the bound identity: snapshot intent, continuation acquisition, publication
    reservation, provider draft call and new claims are each refused in their start transaction (inventory).
  - Under U3 (b), a declined consent → `handoff-disposition-required`, nothing moved.
  - Activation of a completed Change via any route → `change-terminal`; the mutability-policy test enumerates
    `prepare_revision_activation`.
- **Inner loop:** `uv run pytest serve/delivery/tests/test_revision_activation.py -q -k "crash or replay"`.
- **Closeout:** as A1, plus `uv run pytest serve/delivery/tests/test_delivery_state.py -q -k "revision or restore"`.
- **LC:** full form: migration (coordination v4, three new families, action-receipt row, marker), every live
  Change available; on the copy, B1 shows `revision-snapshot-stale` (record, do not run on live); predecessor
  refuses; live hashes unchanged.
- **Size / risk:** L / high (multi-root commit, loader, Git effects, preservation). If the merge-blocking
  preservation or fresh-host falsifiers make A2 exceed one reviewable PR, the deterministic child commit and
  generation history may land first as A2a (with LC) and activation, preservation and fresh-host restore as A2b,
  recorded as a delta under §3.7 before the split.

### 3.4 N04-B — Applicability assessment and carry-forward replacement

- **Prerequisites:** N04-A2.
- **Editable paths:**
  - new `serve/delivery/src/owlbear_delivery/applicability.py` (impact view, review validation, records)
  - `evidence.py` [N03] (fold: records before results; `DeliveryConfirmationUse` view for
    `confirmation_applies`; basis schema 2 in `finalization_basis_digest`); `runtime_models.py`
    (`DeliveryApplicabilityRecord`, binding `applicability`, frontier version); `runtime_receipts.py` (widened
    embedding receipts); `delivery_state.py` (snapshot version); `delivery_application_loader.py` (S and N rows
    of N03's comparison inventory for the new version)
  - `delivery_admission.py` (remove `_carry_forward_unresolved_binding`, `_carry_forward_request_id`,
    `preserve_unresolved_outcome_ids`); `revision_activation.py` (review binding, `reassess` kind)
  - `portfolio_application.py` (`preview_revision_impact`); `application_acquisition.py`
    (`show_plan_context` revision view); `application_models.py`; `application_lifecycle.py` (finalization
    `semantics` includes records and cited confirmations; basis re-check under the checkpoint lock)
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
  - `reassess` on a seeded copy of B1's carried state with `history_ref = legacy:216a787…`: the blanket request
    moves to the new generation record; records written; no package, contract or branch change; one
    publication; the ledger is byte-identical.
  - Confirmation authority (finding 8), through `Client(assemble_target_server(...))` with an
    elicitation-capable test client: (1) a schema-2 `human-confirmed` result whose ledger confirmation names
    `(AC-003, v)`, the outcome and the procedure, criterion `unchanged`, cited as `reusable` → `covered`;
    (2) the same after the outcome reset moved its request to the generation record → still `covered`
    (`resolve_confirmation` by ID); (3) publish, restore on a fresh host from the snapshot → identical status;
    (4) under U1 (a) a legacy human-procedure receipt plus a new boundary confirmation scoped to the candidate
    version and the receipt's procedure text → `covered`; a legacy machine receipt → `covered` without one.
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
- **LC:** full form; additionally compute the impact view for B1 on the copy against `legacy:216a787…` and
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

## 4. Progress

| Phase | PR | Exact head | Proof | Challenges | Status |
| --- | --- | --- | --- | --- | --- |
| N04-P | #358 | — | Probes P1–P9; round-1 source re-reads (§6) | Sol plan round 1: revision-required (10 findings: 8 high, 2 medium; all accepted, none rebutted) → revised | in review |
| N04-A1 | — | — | — | — | — |
| N04-A2 | — | — | — | — | — |
| N04-B | — | — | — | — | — |
| N04-C | — | — | — | — | — |
| N04-D | — | — | — | — | — |

## 5. Verification Gaps

| ID | Claim | Why unproven | Evidence available | Owner | Blocks |
| --- | --- | --- | --- | --- | --- |
| G1 | N03-A…C (as amended by #360), N09-A2 (PR #357) and N02-C land with the interfaces this plan names (`evidence.py` fold, `applies_to`, confirmation ledger, `resolve_confirmation`, `confirmation_applies`, basis digest, K3 sites and `require_pause_permits`, drain tokens, K4 digest, bounded remote Git) | Not merged | Their plans; PR #357 `feadd6777` and PR #360 `9c06c97cd` read only | N04-A1 (re-check at start; a divergence stops for a plan revision) | N04-A1 start |
| G2 | Every runtime-root recoverer can learn the package and candidate roots without a layout assumption | Tests construct coordinators with non-sibling package roots (`test_portfolio_application.py:851-925`) | P3 | N04-A1 | N04-A1 merge |
| G3 | One `RuntimeTransaction` spanning package and runtime roots recovers from every crash point through every reader | Not executed for a cross-root commit | P3 (single-root package participants) | N04-A2 crash matrix | N04-A2 merge |
| G4 | Three-component preservation (D16) captures and restores divergent staged and working-tree content, modes, symlinks, untracked files and leaves ignored files verified in place, on macOS and Ubuntu file systems | Not implemented; D03 raw preservation refuses staged content and the commit quarantine flattens it (§6 finding 1) | Source reads; D03 preservation tests | N04-A2 falsifiers (§3.3) | N04-A2 merge |
| G5 | A real reviewer gives sound applicability dispositions | Semantic judgment | Engine structure checks | N04-C host rehearsal | N04-C merge |
| G6 | The B1 live copy reconciles and reassesses cleanly | Needs the isolated LC copy, not taken in P | P1, P2 (read-only) | N04-D LC rehearsal | N04-D merge |
| G7 | Live B1, `delivery-action-readiness` and `frontier-serialization-contract` revision state | Live activation is out of scope | P1 | N10-M with user authorization | N10-M |
| G8 | LC runs in CI | Needs a live copy | `delivery-lc` unit tests | Each phase | Nothing (recorded per phase) |
| G9 | U2 (a) wait time is acceptable to users | Product judgment; U2 was settled as an engineering decision | — | N10-H host acceptance | Nothing |
| G10 | A cited `human-confirmed` or `waived` receipt keeps an applicable confirmation after the outcome reset and after a fresh-host restore | Resolved in design by N03 (as amended by #360): the Change-wide ledger travels in the snapshot and survives resets (N03 I10); not yet executed | N03 §1.5, §1.9; §1.7 Confirmation authority | N04-B scenarios (finding 8) | N04-B merge |
| G11 | Deterministic plumbing commits (D17) are acceptable to the managed repository: no required commit signing, no required hook on Change branches, and `commit-tree` output is byte-stable across the supported Git versions | Repository rules and Git versions not probed in round 1 | The existing snapshot uses `git commit` with hooks (`workspace_snapshots.py:243-255`) | N04-A2 start (probe; if signing is required, the intent records the signed SHA after a one-time signed `commit-tree` and replay uses the stored object) | N04-A2 merge |
| G12 | With the origin host lost, a different revision on a fresh host first needs resolution (ii) for the pinned child, then a second activation | Accepted limitation of D18 (no remote overwrite) | — | N04-C revision context shows it; N10-H host acceptance | Nothing |
| G13 | N03's `confirmation_applies` can take the `DeliveryConfirmationUse` view without changing N03 results | N03-A not merged; the generalization edits an N03 owner | N03 §1.5 | N04-B start (re-check; a divergence stops for a plan revision) | N04-B start |
| G14 | Every N09-A2 start site is classified for the hold, including sites added by N05-B or N08 after PR #357 | Inventory read at `feadd6777`; later sites unknown | `_COORDINATOR_PAUSE_CLASSES`, `_MANAGER_PAUSE_CLASSES`, `_APPLICATION_PAUSE_GATED_ENTRIES` | N04-A1 (`_HOLD_CLASSES` completeness test fails on an unclassified site) | N04-A1 merge |

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
