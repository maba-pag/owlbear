# Delivery Authority Repair Workflow Plan

> **Owning task:** B1 Delivery authority recovery after stranded frontier and snapshot repair
> **Date:** 2026-09-12
> **Question:** How should Delivery recover malformed local frontier, quarantined remote snapshot, pending publication, and revised package-snapshot state without raw state edits or loss of the B1 pilot gate?
> **Status:** Plan and evidence only; implementation authority remains in Delivery Design/admission workflows.

## 1. Status Quo

B1 (`macos-managed-browser-authentication`) had two persisted authority defects:

1. `frontier.json` contained a free-text request resolution without `provenance: "user-confirmed"`.
2. The remote Delivery-state snapshot was quarantined because the same request resolution failed validation.

The local frontier repair now succeeds through `repair_stranded_frontier`. It preserves the old frontier under `changes/<change-id>/revisions/<digest>/frontier.json` and adds the missing provenance. The quarantined remote snapshot repair now succeeds through `repair_quarantined_delivery_state_snapshot`, using an exact remote branch head and raw snapshot digest fence.

B1's revised authority was then re-admitted with its unresolved pilot gate carried forward. The current B1 outcome is Planning with a user action request for the revised SharePoint/Confluence pilot. D1 is completed and no longer has the original snapshot attention.

A further pending-publication mismatch was found after B1 re-admission: the local `state-publication.json` marker still referenced the frontier from before authority revision. Delivery now re-anchors that marker only when the remote snapshot proves the marker's previous frontier digest, then replays publication normally.

The current separate gap is the managed Change-branch package snapshot. B1 already has a `ChangeDesignPackageSnapshotReceipt` for the previous package identity. Re-admission of the revised package reaches `snapshot_design_package()` and rejects the new package ID as a different snapshot. This prevents the revised package from becoming the current branch snapshot even though the Delivery authority has been revised.

## 2. Evidenced Problem

The repair workflow has multiple authority owners with different identity fences:

- authored Design package identity;
- admitted `contract.json`, `frontier.json`, and `admission.json`;
- local pending state-publication intent;
- remote state snapshot identity and branch head;
- managed Change-branch Design package snapshot receipt.

The original repair sequence handled local and remote state but did not complete the package-snapshot transition. That leaves a split state in which:

- current Delivery authority refers to the revised B1 package;
- the managed Change branch still records the earlier package snapshot receipt;
- re-admission/finalization cannot prove one consistent package identity;
- the B1 pilot block is preserved in Delivery authority, but the branch evidence is stale.

A raw branch edit or direct JSON rewrite would erase the identity boundary that Delivery is intended to protect.

## 3. Implemented Repair Delta

### 3.1 Quarantined Snapshot Repair Self-Block

**Control point:** `PortfolioApplication.repair_quarantined_delivery_state_snapshot()`.

The operation previously called `_reconcile_runtimes()` and then required `_runtime(..., for_mutation=True)`. A quarantined remote snapshot creates the reconciliation diagnostic that this operation owns, so the operation rejected itself before checking its exact raw-byte fence.

The implementation now uses the locally reconciled runtime object when available, while still rejecting a missing runtime or unrelated reconciliation error. Existing remote branch-head, raw snapshot digest, diagnostic-code, package-authority, and publication checks remain in force.

### 3.2 Pending Publication Re-anchor

**Control points:** `DeliveryRuntime.reanchor_pending_publication()` and pending replay in `PortfolioApplication._replay_pending_state_publications()`.

After authority revision, the local marker could reference the prior frontier while the remote snapshot still represented that prior frontier. The replay path now:

1. detects the marker/current-frontier mismatch;
2. reads the remote snapshot inventory;
3. accepts either the marker's prior frontier digest or the current frontier digest;
4. transactionally changes the marker to `base=prior frontier` when the remote still has the prior state, or `base=current frontier` when the remote already has the revised state;
5. continues through normal CAS-bound publication replay and full snapshot-authority validation.

If the remote snapshot matches neither the marker's prior frontier nor the current frontier, replay still fails closed.

Focused proof:

- quarantined snapshot application repair: 1 passing test;
- adjacent snapshot proposal/state repair tests: 2 passing tests;
- pending publication replay/re-anchor/current-frontier tests: 4 passing tests;
- editor diagnostics: clear.

## 4. Remaining Proposed Fix: Package Snapshot Revision

### Option A - Version-bound package snapshot replacement (recommended)

Extend the managed workspace package-snapshot owner with a Delivery-owned revision operation or a narrowly extended `snapshot_design_package()` contract.

Required behavior:

1. Read the current `ChangeDesignPackageSnapshotReceipt` and require its exact package ID, branch, worktree, and snapshot head.
2. Require no active Writer, active claim, finalization, target-sync conflict, or dirty/untracked worktree.
3. Verify the current branch is still at the recorded snapshot head.
4. Preserve the previous package snapshot through the existing branch history; do not create a second external archive.
5. Commit the revised package files as one exact child commit using `--only` for the four package paths.
6. Replace the coordination receipt with a new receipt bound to the revised package ID and child head using the coordinator's publication lock.
7. Reconcile the B1 frontier and pending state-publication marker against the new package/authority identity.
8. Make replay with the same expected old receipt, package ID, and operation identity idempotent.
9. Reject stale branch heads, a different existing snapshot, a dirty worktree, or an active claim.

Acceptance proof:

- A revised B1 package replaces the old package snapshot only when the old receipt and branch head match.
- The old package commit remains reachable in branch history.
- A stale expected receipt cannot replace the new snapshot.
- Replaying the same operation returns the same receipt without a second commit.
- The resulting package snapshot, runtime authority, admission receipt, and pending publication refer to the revised package consistently.
- B1 remains Planning and blocked on the revised pilot request; it is not claimable.

### Option B - Successor Change

Keep package snapshots immutable and create a successor Change for the revised B1 authority. This avoids changing workspace snapshot semantics but loses same-Change carry-forward, duplicates Design/admission identity, and complicates the existing B1 pilot history. Use only if package snapshots are deliberately immutable by product policy.

### Option C - Direct branch/state mutation

Reject. Editing the managed branch, coordination receipt, or Delivery JSON outside the owning operations would bypass CAS, receipt identity, and recovery evidence.

## 5. Recommended Task Order

1. Complete and validate the existing remote snapshot repair and pending-publication re-anchor path.
2. Design the version-bound package snapshot replacement contract under the Delivery workspace owner.
3. Add coordinator/workspace tests for old-receipt fencing, child-commit creation, replay, dirty worktree rejection, and active-claim rejection.
4. Add the application/admission integration test using a revised package with one preserved unresolved outcome.
5. Expose the operation through Delivery MCP only after its application contract is stable; update operation inventory, annotations, adapter models, and focused MCP tests together.
6. Re-run B1 re-admission using the revised package ID and `preserve_unresolved_outcome_ids=("OUT-001",)`.
7. Replay pending state publication and verify `delivery_health()` is healthy or reports only the intentional user-owned B1 pilot block through work-item projection.
8. Keep the real SharePoint/Confluence pilot as the subsequent operator action; do not mark B1 complete from synthetic tests or historical Jira evidence.

## 6. Acceptance Risks

- **Receipt split:** authority may be revised while branch package evidence remains old. The package snapshot replacement must be atomic with its coordination receipt.
- **Concurrent writer:** a Builder or publication operation could change the branch between validation and package commit. The operation must hold the existing publication lock and recheck the exact branch head.
- **Dirty worktree:** overwriting package files could destroy unrelated work. Require the existing clean-worktree boundary and preserve the current dirty-worktree attention route.
- **Duplicate publication:** a lost response could lead to a second package commit. Bind operation identity and replay to the old receipt, package ID, and resulting child head.
- **Pilot gate loss:** revised admission must preserve an unresolved request-bound block. Verify work acquisition sees no launch for B1.
- **Stale publication marker:** the marker must be re-anchored only when remote state proves the prior frontier, never by blindly replacing its digest.
- **Health interpretation:** a user-owned pilot block is not a Delivery health failure. Health should be clear after persistence repair while the work-item projection reports the B1 action request.

## 7. Evidence and Limits

- Current source shows `repair_quarantined_delivery_state_snapshot()` previously self-blocked on `_reconcile_runtimes()`; the focused regression now passes with the known snapshot diagnostic present.
- Current source shows `snapshot_design_package()` rejects a different existing package ID rather than creating a revised package snapshot.
- The existing source-bound admission test proves state-preserving carry-forward for a revised unresolved gate.
- The managed worktree package snapshot problem has not been implemented in this pass.
- Full repository validation was not run; focused Delivery tests used the existing `.venv` interpreter.
- No raw Git, Delivery-state hand edit, GitHub mutation, or pilot execution was performed by this plan artifact.
