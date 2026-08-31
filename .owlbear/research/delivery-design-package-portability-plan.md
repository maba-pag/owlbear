# Delivery Design Package And Portability Plan

> **Owning task:** Pending Delivery durability Change; no implementation task admitted yet
> **Date:** 2026-08-23
> **Question:** How can Design history and active Delivery work survive a fresh clone or new machine without committing every draft revision or relying on local-only refs?
> **Status:** Proposed implementation plan

## 1. Context And Question

The current Delivery implementation has three different kinds of state, but only one is reliably
backed by the remote repository:

1. The Change implementation branch and its GitHub pull request are remote-backed once the first
   checkpoint is published.
2. The active Design package is written under `.owlbear/delivery/packages/<change-id>/` in the
   primary checkout. Its local checkpoint is stored under `refs/owlbear/packages/<change-id>`, but
   that ref is not published by the normal remote refspec.
3. The admitted Delivery frontier, task results, claims, and publication receipts are written under
   ignored `.owlbear/delivery/runtime/`. A fresh clone has neither the active runtime nor its local
   checkpoint refs.

This creates two concrete failures:

- Active package files appear as uncommitted repository changes even though they are valid Delivery
  state.
- A fresh clone or new laptop cannot recover an admitted Change until somebody copies hidden local
  package refs and runtime state.

The desired recovery contract is narrower than "commit every write" and stronger than "keep a local
backup":

- Draft Design revisions may remain local until the Design is stable and admitted.
- The admitted package (`intent.md`, `design.md`, `authority.json`, `manifest.json`) must be present
  in normal remote Git history through the Change PR.
- The Change implementation and its latest durable Delivery progress must be recoverable from normal
  remote branches after a machine loss.
- Active process claims, locks, capacity ledgers, and warm worktrees are disposable and must be
  recreated or re-acquired.
- No operation may commit to whichever branch happens to be checked out in the user's primary
  worktree.
- No local `refs/owlbear/*` ref may be the only recovery source.

This plan treats "stable" as the point after explicit Design approval and successful Delivery
admission. Pre-admission drafts remain an explicit, bounded loss window. A later user-invoked draft
backup can be added if that loss window becomes unacceptable, but it is not part of this first
solution.

## 2. Sources Studied

| Source | Evidence used | Limit |
|---|---|---|
| [`design_package.py`](../../serve/delivery/src/owlbear_delivery/design_package.py) | Active package names, transactional `create`, `revise`, `publish_contract`, and local-ref `checkpoint` behavior | Current code, not a future persistence design |
| [`target_admission.py`](../../serve/delivery/src/owlbear_delivery/target_admission.py) | Admission compiles the package, publishes generated authority, checkpoints the package, and writes runtime authority | Does not publish the package into the Change branch |
| [`portfolio_application.py`](../../serve/delivery/src/owlbear_delivery/portfolio_application.py) | Application exposes Design operations, creates runtime instances, and publishes Change checkpoints | Current admission and publication sequencing requires extension |
| [`change_publication.py`](../../serve/delivery/src/owlbear_delivery/change_publication.py) | Change PR publication uses the managed Change worktree, exact reviewed head, clean state, and remote Change branch | It does not inspect the primary package root |
| [`delivery_application_loader.py`](../../serve/delivery/src/owlbear_delivery/delivery_application_loader.py) | Startup reconstructs admitted Changes from ignored `runtime/changes/*` and derives package root from the primary checkout | This is the main new-machine bootstrap boundary |
| [`change_workspace.py`](../../serve/delivery/src/owlbear_delivery/change_workspace.py) | One Change-specific managed worktree, reviewed boundary, clean-head checks, and worktree recovery | No package materialization or remote state bootstrap exists |
| [`.owlbear/README.md`](../../.owlbear/README.md) | `.owlbear` combines tracked authority with host-local runtime state and directs callers to owning workflows | Describes policy but does not enforce tracking |
| [`.owlbear/.gitignore`](../../.owlbear/.gitignore) | Ignores runtime, worktrees, locks, and host-local state, but not active packages | Current tracking policy is incomplete for the intended split |
| [`.github/sync-manifest.json`](../../.github/sync-manifest.json) | `.owlbear` is excluded from consumer `main`; `dev` remains the development recovery branch | Consumer portability is not the goal of this state |
| [`w-design-session`](../../share/skills/w-design-session/SKILL.md) | `create_design_session` and `revise_design_session` are the only normal authored package writes; admission follows approval | Does not define remote package persistence |
| [`w-packet-building`](../../share/skills/w-packet-building/SKILL.md) | Builder commits exact implementation heads and requires clean worktrees | Does not own Design package files |
| [`r-workspace-governance`](../../share/skills/r-workspace-governance/SKILL.md) | Scoped commits must name owned paths; direct broad Delivery-state commits are prohibited | A new Delivery-owned snapshot operation needs its own exact scope |
| [`delivery-change-worktree-authority.md`](delivery-change-worktree-authority.md) | Existing authority calls packages tracked and runtime host-local, and defines Change branch/worktree ownership | Current implementation has drifted from parts of this authority |
| [`target-delivery-information-flow-step-09.md`](target-delivery-information-flow-step-09.md) | Admission should prepare package-history snapshots before the visible receipt | Describes intended architecture, not current branch publication |
| [`target-delivery-information-flow-step-14.md`](target-delivery-information-flow-step-14.md) | Completed history should retain a Change-owned package and completion binding | Current acceptance path still relies partly on ignored runtime receipts |

## 3. Current Lifecycle And Root Cause

### 3.1 Current write points

The four active package files are changed at these points:

| Process point | Operation | Files changed | Current persistence |
|---|---|---|---|
| New `/ideate` or `/design` session | `create_design_session` | `intent.md`, `design.md`, empty `authority.json`, `manifest.json` | Primary checkout only |
| Design revision | `revise_design_session` | `intent.md`, `design.md`, clears `authority.json`, `manifest.json` | Primary checkout only |
| Design checkpoint | `publish_design_checkpoint` | No active-file change | Local `refs/owlbear/packages/<change-id>` only |
| Admission | `publish_contract` inside `admit_delivery_change` | `authority.json`, `manifest.json` | Primary checkout plus local package ref; runtime authority is separate |
| Planning, Build, finalization | No package-store write | None | Package is read or ignored |
| PR publication | `ChangeBranchPublisher.publish` | Only files already in the managed Change worktree | Does not see primary checkout package files |
| GitHub acceptance | `observe_acceptance` | No active-package write | Completion is recorded in runtime state |

`intent.md` and `design.md` therefore reach their final normal lifecycle version at the last Design
revision before admission. `authority.json` and `manifest.json` reach their final admitted version
inside admission. Finalization and positive acceptance are too late to be the package snapshot trigger.

### 3.2 Why the current package is not backed up by the PR

The active package is rooted in the primary checkout. A Change branch gets its own worktree from the
integration target and does not copy untracked files from the primary checkout. The publisher then
pushes only the managed Change branch head. Therefore an untracked active package is not included in
the first PR automatically.

`DesignPackageStore.checkpoint()` does create a real Git commit, but it writes it to
`refs/owlbear/packages/<change-id>`. The current remote exposes no such refs, and ordinary clone/fetch
does not retrieve them. This is local integrity history, not a remote recovery mechanism.

### 3.3 Why committing every revision is the wrong correction

Every `revise_design_session` call may represent unresolved exploration. Committing each revision
would:

- expose draft meaning as branch history before approval;
- create unnecessary commits and review noise;
- couple the low-level package store to an arbitrary checked-out branch;
- create a second Git writer beside Delivery's compare-and-swap package transaction; and
- still fail to persist ignored runtime/frontier state.

The correct unit is a stable admitted snapshot, not an individual file write.

## 4. Target Architecture

### 4.1 Three persistence tiers

| Tier | Contents | Location | Recovery guarantee |
|---|---|---|---|
| Draft | Unadmitted `intent.md` and `design.md`, unresolved choices, empty/generated authority | Primary checkout active package root | Local only until admission; explicit loss window |
| Change snapshot | Admitted four-file package and implementation commits | Managed `owlbear/change/<change-id>` branch and its PR | Normal remote branch while open; merged `dev` history after acceptance |
| Delivery checkpoint | Sanitized frontier, task results, publication/finalization/completion identities | Normal remote `owlbear/delivery-state` branch | Recover from remote after machine loss at the last published checkpoint |

Host-local claims, locks, capacity, transaction journals, and worktrees remain disposable. They are
recreated from the durable tiers and never treated as portable authority.

### 4.2 Stable package snapshot

Add a Delivery-owned operation, used internally by admission rather than exposed as an independent
Designer command:

`publish_admitted_design_snapshot(change_id, expected_package_id, operation_id)`

The operation returns an exact `DesignPackageSnapshotReceipt` containing at least:

- `change_id`;
- `package_id` and the four source digests from `manifest.json`;
- managed Change branch and worktree identity;
- snapshot commit;
- prior reviewed boundary;
- resulting reviewed boundary; and
- stable operation identity and timestamp.

The operation must:

1. Read the verified active package through `DesignPackageStore`; never read arbitrary files without
   manifest validation.
2. Require the package to have generated admitted authority and to match the expected package ID.
3. Require the canonical Change worktree to exist, be on `owlbear/change/<change-id>`, have no active
   Builder writer, and have `HEAD == last_reviewed_commit` with a clean index and worktree.
4. Materialize exactly these four files under
   `.owlbear/delivery/packages/<change-id>/` in the managed Change worktree:
   `authority.json`, `design.md`, `intent.md`, and `manifest.json`.
5. Commit only that package path with a Delivery-owned fixed Git argument path or equivalent temporary
   index. Do not invoke the generic helper from the primary checkout and do not stage unrelated
   paths.
6. Verify the new commit, package hashes, branch, ancestry, and clean worktree.
7. Advance `ChangeCoordination.last_reviewed_commit` to the snapshot commit through a dedicated
   receipt-backed workspace operation. This is an admitted-authority boundary, not a Builder result.
8. Replay the same operation without a second commit when the receipt, package ID, branch, and commit
   already match. Reject a divergent package or branch with typed attention.

The operation must never commit to `dev`, the current user branch, or a branch selected from the
caller's current directory. The only commit target is the exact managed Change branch.

### 4.3 Admission sequencing

Refactor `PortfolioApplication.admit_delivery_change` and the admission registry into a replay-safe
sequence with these observable boundaries:

1. Validate the authored package, contract derivation, approval identity, and configured target.
2. Ensure the canonical Change branch/worktree from the configured integration target.
3. Publish generated `authority.json` and `manifest.json` through the existing package transaction.
4. Publish the admitted package snapshot into the managed Change worktree and record its receipt.
5. Initialize or update the admitted runtime with the snapshot commit as its reviewed boundary.
6. Queue a new `ADMITTED_DESIGN` checkpoint trigger whose head is the snapshot commit.
7. Reconcile that checkpoint through the existing `ChangeBranchPublisher` and
   `DraftPullRequestPublisher`, creating the first draft PR at admission.
8. Publish the initial sanitized Delivery checkpoint to the remote state branch.
9. Expose the admission receipt only after the local snapshot exists. If remote publication is
   unavailable, retain a typed `checkpoint-pending` state and block new worker acquisition until
   the initial snapshot can be published or explicitly resolved.

The first PR is therefore created from a clean managed Change worktree that already contains the
stable package. Later Builder commits extend that branch. No later package commit is needed merely
because the PR was merged.

The existing `FIRST_PROMOTED_TASK` trigger should be retained only for its task-checkpoint meaning,
not as the first PR creation mechanism. Add tests for the new `ADMITTED_DESIGN` trigger and update
summary text so users understand that the PR opened from admitted Design authority.

### 4.4 Freeze the admitted package

Once a Change has an admitted runtime or an admitted snapshot receipt, `revise_design_session` must
reject a revision against that Change. The returned error must name the Change and the reason that
its package is already execution authority. A semantic change after admission starts a new or
superseding Change through the existing Design workflow; it does not mutate the package that the
active PR and frontier reference.

This closes the current gap where the public application method delegates directly to
`DesignPackageStore.revise` without visibly checking admitted runtime state.

### 4.5 Remote Delivery state branch

Create one normal remote branch named `owlbear/delivery-state`. Add it to tracked Delivery
configuration as an explicit state branch identity, with a safe default for newly initialized
workspaces. Do not use `refs/owlbear/*` as the only transport.

Store one current snapshot per Change at:

`.owlbear/delivery/state/<change-id>/snapshot.json`

The snapshot is a separate typed model, not a raw dump of `DeliveryFrontier` or `ChangeCoordination`.
It contains:

- schema version;
- Change ID, admitted package ID, and contract digest;
- Change branch and exact remote Change head represented;
- last reviewed implementation boundary;
- integration target identity;
- outcome stages, immutable task definitions, promoted result commit identities, blocks, requests,
  finalization, readiness, publication, and completion identities required for rehydration; and
- snapshot sequence, parent digest, and timestamp.

It must not contain:

- active process IDs or owner IDs;
- writer leases, acquisition locks, capacity ledgers, or transaction journals;
- absolute local paths;
- credentials, provider tokens, raw exception internals, or unbounded logs; or
- an active claim that could be mistaken for live ownership.

Add `DeliveryStatePublisher` under `serve/delivery/src/owlbear_delivery/`. It must publish snapshots
with an expected remote state-branch head, operation identity, idempotent replay, and a typed
response-unknown/divergence attention. It must use Git plumbing or an isolated state publication
workspace, never the user's primary checkout index.

Publish a state snapshot only at these existing semantic boundaries:

- admitted Design snapshot;
- promoted implementation result / first task checkpoint;
- verified Outcome checkpoint;
- finalization checkpoint; and
- acceptance/completion observation.

Do not commit state for every claim acquisition, heartbeat, lock change, or draft Design revision.
A failure between state checkpoints has a defined recovery point: the next machine requeues any
uncompleted task after the last remote snapshot rather than pretending to resume a live process.

### 4.6 Fresh-clone bootstrap

Extend `load_delivery_application` with a read-only remote bootstrap phase:

1. Validate the configured remote, target branch, state branch, and repository identity.
2. Fetch normal remote-tracking refs for `owlbear/delivery-state`, the configured target, and open
   `owlbear/change/<change-id>` branches without mutating the user's target branch.
3. Read and validate each state snapshot from the remote state branch.
4. Verify that its package ID, Change head, branch ancestry, and contract digest match the remote
   Change branch or merged target branch. A mismatch produces typed portability attention; never
   choose one side silently.
5. Recreate local ignored `runtime/changes/<change-id>` from the sanitized snapshot, with no active
   claims or writer custody. Preserve task results and user requests; make incomplete work claimable.
6. Restore the active package cache from the verified package tree in the remote Change branch for
   open Changes, or from the merged target tree for completed Changes. Revalidate `manifest.json`.
7. Recreate each missing local Change branch from its remote branch and call the existing
   `recover_change_worktree` path to create the managed worktree. Do not recreate a worktree from a
   stale local branch when the remote snapshot names another head.
8. Reconcile provider PR state and acceptance read-only before presenting the portfolio.
9. Allow new acquisition only after state, package, and Change-head identities agree.

A fresh clone test must use a local bare remote fixture and ordinary clone/fetch refspecs. It must
not copy `.git`, local `refs/owlbear/*`, ignored runtime files, or the original worktree.

### 4.7 Acceptance and completed history

`observe_acceptance` remains read-only with respect to the target branch and active package. It must
publish the accepted completion binding to `owlbear/delivery-state` after provider observation,
including the accepted merge commit, finalization ID, package ID, and completion identity.

No post-merge package commit is needed when the admitted package was already in the Change PR. The
merged `dev` history is the package archive; the state branch carries the completion binding needed
to reconstruct Delivery status.

The existing `CompletedHistoryCatalog` and current receipt readers must be updated to consume the
remote-backed completion snapshot after bootstrap, while retaining the legacy target-history reader
for old `.owlbear/legacy/completed` records. Do not create a second copy of the Design package just
to make completed-history search work.

## 5. Trade-Offs And Rejected Alternatives

| Option | Benefit | Cost | Risk | Confidence | Decision |
|---|---|---|---|---|---|
| Commit every Design revision | Maximum draft retention | Noise, premature history, second-writer conflicts | High | 0.98 | Reject |
| Commit admitted package once into the Change PR | One stable snapshot, normal GitHub backup, no draft noise | Requires managed-worktree materialization and one Delivery commit operation | Medium | 0.91 | Recommend |
| Commit packages directly to `dev` | Easy to find after clone | Mutates the wrong branch and can mix user work | High | 0.99 | Reject |
| Push only `refs/owlbear/packages/*` | Reuses local checkpoint code | Normal clone does not fetch it; hidden refspec dependency | High | 0.99 | Reject |
| Dedicated remote state branch for sparse frontier snapshots | Recovers active progress without PR metadata noise | New publisher, config, CAS, and bootstrap path | Medium-high | 0.84 | Recommend for full new-machine goal |
| Put runtime snapshots in every Change PR commit | One ref to recover | PR noise and reviewed-head changes after each task | Medium-high | 0.82 | Reject |
| Auto-commit inside `DesignPackageStore` | Covers all callers | Branch-agnostic storage gains surprising Git side effects | Severe | 0.99 | Reject |
| Designer invokes `commit-owned` | Small apparent code change | Designer is intentionally read-only and cannot safely select a branch | High | 0.97 | Reject |
| Dedicated commit agent | Keeps Designer narrow | Adds model discretion to deterministic persistence | High | 0.91 | Reject |
| Ignore active packages | Removes status noise | Loses branch/clone history and hides the recovery gap | Critical | 0.99 | Reject |
| Post-merge package commit only | Avoids PR changes | Leaves the pre-merge loss window and needs a target-writing owner | High | 0.94 | Reject as primary |

The recommended design deliberately combines the second and fifth rows. Package history travels with
the normal Change PR. Runtime progress travels through a normal remote state branch at sparse
semantic checkpoints. Neither mechanism commits every draft or process event.

## 6. Step-By-Step Implementation Sequence

### Step 0 - One-time state audit and migration decision

**Owner:** Delivery design/migration task, before code changes.

1. Inventory active packages with `DesignPackageStore.list_verified()` and record package IDs.
2. Inventory remote Change branches, local Change branches, package checkpoint refs, and runtime
   `changes/*` records.
3. Classify `website-to-knowledge-vertical` explicitly as retired or active. If retired, remove its
   four tracked files through a separate user-visible maintenance commit; do not let a new ignore
   rule silently remove it.
4. Inspect current static and Cockpit package manifests and verify their package IDs against active
   bytes and local checkpoint trees.
5. Define the recovery point policy in tracked Delivery documentation: admitted Changes are remote-
   recoverable; pre-admission drafts are not guaranteed; uncommitted process state is requeued.

**Exit proof:** a table of every current Change with package ID, admitted/runtime status, Change
branch availability, remote PR/branch availability, and the chosen migration action. No package or
runtime file is discarded in this step.

### Step 1 - Package snapshot model and managed-worktree operation

**Files:**

- `serve/delivery/src/owlbear_delivery/design_package.py`
- `serve/delivery/src/owlbear_delivery/change_workspace.py`
- `serve/delivery/src/owlbear_delivery/portfolio_application.py`
- `serve/delivery/tests/test_design_package.py`
- `serve/delivery/tests/test_change_workspace.py`
- `serve/delivery/tests/test_portfolio_application.py`

**Work:**

1. Add `DesignPackageSnapshotReceipt` and canonical identity validation.
2. Add a workspace-manager operation that materializes exactly four verified package files and
   commits them only on the managed Change branch.
3. Add a compare-and-swap receipt path that advances the reviewed boundary only from the expected
   prior head.
4. Preserve unrelated primary-checkout staged/untracked state by never using its index for the
   snapshot commit.
5. Make replay and divergent package/head behavior explicit and typed.
6. Add a negative test that a package snapshot cannot target `dev` or a caller-selected branch.

**Exit proof:** repeated identical operation returns the same receipt and commit; a changed package,
changed branch head, dirty worktree, active writer, or staged unrelated path fails without mutation.

### Step 2 - Admission integration and first PR checkpoint

**Files:**

- `serve/delivery/src/owlbear_delivery/portfolio_application.py`
- `serve/delivery/src/owlbear_delivery/target_admission.py`
- `serve/delivery/src/owlbear_delivery/delivery_runtime.py`
- `serve/delivery/src/owlbear_delivery/work_items.py`
- `serve/delivery/src/owlbear_delivery/change_publication.py`
- `serve/delivery-mcp/src/owlbear_delivery_mcp/target_models.py`
- `serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py`
- matching Delivery and MCP tests

**Work:**

1. Add the `ADMITTED_DESIGN` checkpoint trigger and its projection text.
2. Sequence admission so generated authority, package materialization, reviewed-boundary update,
   runtime admission, and initial checkpoint are replay-safe.
3. Create the first draft PR at admission from the package-bearing Change branch.
4. Block acquisition while the required initial package snapshot or remote checkpoint is pending.
5. Keep `FIRST_PROMOTED_TASK` for later implementation evidence, not initial Design backup.
6. Expose snapshot/pending identities in typed admission or work-item projections; do not expose
   raw paths or Git internals as prose-only diagnostics.

**Exit proof:** an admission test using a local remote fixture produces one clean Change branch and
one draft PR containing the four package files, and a second identical admission produces no new
package commit. A provider-unavailable test leaves typed pending state and no Builder claim.

### Step 3 - Freeze admitted Design authority

**Files:**

- `serve/delivery/src/owlbear_delivery/portfolio_application.py`
- `serve/delivery/src/owlbear_delivery/design_package.py`
- `serve/delivery/tests/test_portfolio_application.py`
- `serve/delivery/tests/test_design_package.py`
- `share/skills/w-design-session/SKILL.md`
- `share/agents/designer.agent.md` only if a direct pointer is needed

**Work:**

1. Reject `revise_design_session` after admission/snapshot publication.
2. Route required semantic changes to a new or superseding Design Change rather than mutating the
   package referenced by an active PR.
3. Document that draft revisions are local until admission and that admission is the first remote
   recovery guarantee.

**Exit proof:** a post-admission revision cannot change active package bytes or manifest, while a
pre-admission revision still replays through the existing CAS package transaction.

### Step 4 - Remote Delivery-state publisher

**Files:**

- `serve/delivery/src/owlbear_delivery/delivery_state.py` (new)
- `serve/delivery/src/owlbear_delivery/delivery_runtime.py`
- `serve/delivery/src/owlbear_delivery/portfolio_application.py`
- `serve/delivery/src/owlbear_delivery/delivery_application_loader.py`
- configuration model and setup path
- Delivery tests and local-remote integration fixtures

**Work:**

1. Add explicit `delivery_state_branch` to `DeliveryStartupConfig`, with migration and a safe
   default of `owlbear/delivery-state`.
2. Define `DurableDeliveryStateSnapshot` with an allowlisted, sanitized field set.
3. Add state-branch commit and push CAS with operation records and response-unknown handling.
4. Publish only at admission, task/outcome checkpoint, finalization, and acceptance boundaries.
5. Keep local runtime as a cache and active coordination store, not the remote source of truth.
6. Do not serialize active claims, writer leases, locks, absolute paths, or transient candidates.

**Exit proof:** state snapshots survive a new local clone, replay without duplicate commits, reject a
stale expected branch head, and preserve no host-specific or secret values.

### Step 5 - Fresh-clone bootstrap and worktree recovery

**Files:**

- `serve/delivery/src/owlbear_delivery/delivery_application_loader.py`
- `serve/delivery/src/owlbear_delivery/change_workspace.py`
- `serve/delivery/src/owlbear_delivery/design_package.py`
- `serve/delivery/tests/test_delivery_application_loader.py` or the nearest loader test module
- `serve/delivery/tests/test_change_workspace.py`
- setup and Delivery documentation

**Work:**

1. Add a bare-remote test fixture and create a source clone with no local OwlBear refs or runtime.
2. Fetch state and Change branches through ordinary remote refs.
3. Rehydrate local runtime from the newest verified state snapshot.
4. Recreate package cache and managed worktrees from remote branch heads.
5. Clear claims and writer custody on bootstrap; leave incomplete work dependency-ready.
6. Surface package/state/branch divergence as typed portability attention.
7. Require a second read-only identity check before acquisition after bootstrap.

**Exit proof:** delete the source clone, clone again from the bare remote, start Delivery, and observe
that the admitted package, task results, open PR identity, and next claimable task are present. No
copy of the old `.git` directory, ignored runtime, or local `refs/owlbear/*` is used.

### Step 6 - Completion and historical backfill

**Files:**

- `serve/delivery/src/owlbear_delivery/portfolio_application.py`
- `serve/delivery/src/owlbear_delivery/completed_history.py`
- `serve/delivery/src/owlbear_delivery/acceptance.py`
- completed-history and acceptance tests
- `serve/delivery/README.md`
- `.owlbear/README.md`

**Work:**

1. Publish completion binding to the remote Delivery-state branch during acceptance observation.
2. Make completed-history lookup bootstrap from the remote state snapshot plus the merged package
   path, while retaining legacy `.owlbear/legacy/completed` verification.
3. Do not add a post-merge package commit when the package already arrived through the PR.
4. Create a one-time maintenance Change/PR to backfill package snapshots for already completed
   Changes whose merged history lacks them. Do not write directly to `dev` from Delivery.
5. Resolve the old tracked `website-to-knowledge-vertical` package through explicit maintenance
   disposition rather than silently treating it as the new model.

**Exit proof:** a merged Change is recoverable from `dev` plus the remote state branch, its package
history is searchable, and acceptance replay does not create a second package snapshot commit.

### Step 7 - Documentation and operator workflow

**Files:**

- `.owlbear/README.md`
- `serve/delivery/README.md`
- `share/skills/w-design-session/SKILL.md`
- `share/skills/r-workspace-governance/SKILL.md`
- `share/skills/w-orchestration/SKILL.md`
- `.github/copilot-instructions.md`
- `seed/` configuration and documentation templates

**Work:**

1. Document the three persistence tiers and the admission recovery guarantee.
2. State that active draft edits are not individually committed.
3. State that the admitted package is committed by Delivery to the managed Change branch and reaches
   the remote through the first draft PR.
4. State that runtime snapshots are sparse and process claims are re-acquired after recovery.
5. Remove any wording that calls local `refs/owlbear/packages/*` a remote backup.
6. Document the explicit `delivery_state_branch` setup and fresh-clone recovery command/path.
7. Keep user-facing diagnostics typed and bounded; do not make users parse Git internals.

**Exit proof:** documentation and seed validation pass, and the documented recovery procedure is
executed by the fresh-clone integration test.

## 7. Acceptance And Regression Matrix

| Behavior | Required proof | Failure that must remain visible |
|---|---|---|
| Draft revision does not create branch history | Two `revise_design_session` calls before admission; no Change-branch commit | Draft loss before admission is documented, not hidden |
| Admission snapshot is exact | Four package files in managed Change commit hash to active package manifest | Any digest mismatch blocks admission |
| Snapshot targets only Change branch | Primary `dev` head and index unchanged; Change branch advances exactly once | Branch-selection ambiguity blocks |
| Initial PR contains stable package | Remote Change branch and draft PR head contain package path | Provider unavailable leaves pending state |
| Builder starts after snapshot | Acquisition sees package-bearing reviewed boundary and clean worktree | Missing snapshot cannot produce a claim |
| Later package revision is rejected | Post-admission `revise_design_session` fails without byte mutation | Semantic change must use a new/superseding Change |
| Sparse state checkpoint | Task/result/outcome/finalization events create state snapshots; claims do not | State publication failure is typed and retryable |
| No host-only state leaks | Snapshot inspection finds no absolute paths, PIDs, locks, credentials, or raw logs | Sanitization failure blocks publication |
| Fresh clone resumes | Bare remote clone reconstructs package, runtime progress, Change worktree, and next claimable task | Branch/state/package divergence becomes attention |
| Active claim recovery | Clone during an active claim starts with no live claim and requeues incomplete work | Never infer process liveness |
| Acceptance is idempotent | Repeated acceptance observation keeps one completion identity and no package duplicate | Provider mismatch remains waiting/attention |
| Existing user checkout is protected | Staged/untracked unrelated primary files survive admission snapshot | Delivery never normalizes the user checkout |
| Legacy package migration is deliberate | Old tracked package is explicitly retained or removed by a named maintenance Change | No phantom draft is silently resurrected |

## 8. Risks, Confidence, And Limits

### Recommendation

Implement two related but separate Delivery Changes:

1. **Admitted Design snapshot in the Change PR.** This is the first and highest-value slice. It
   fixes the current uncommitted-package problem, gives Design/intent history normal remote Git
   provenance, and avoids per-revision commit noise.
2. **Sparse remote Delivery-state checkpoints.** This is required for the stronger new-machine goal
   of resuming active frontier progress. It should reuse existing checkpoint cadence and Change
   publication identity rather than adding a custom-ref-only backup system.

Do not ignore active packages, auto-commit from `DesignPackageStore`, let Designer invoke generic Git,
or commit to `dev` from the primary checkout.

### Confidence

- **0.95:** package files are changed only by Design creation/revision and admission authority
  publication; finalization and acceptance are not package mutation points.
- **0.92:** the first stable package snapshot belongs in the managed Change branch, not the primary
  checkout, and should be published by the existing PR mechanism.
- **0.86:** a normal remote Delivery-state branch is the smallest practical way to make sparse
  frontier progress recoverable without putting process state into product PRs.
- **0.82:** admission-time initial PR creation is preferable to waiting for the first Builder result,
  because it closes the remote backup window immediately after Design becomes authoritative.

### Limits

- Pre-admission Design drafts remain local by policy. A separate explicit draft-backup operation is
  needed if those drafts must survive hardware loss.
- A state snapshot recovers the last durable frontier, not an in-flight model invocation or
  uncommitted Builder work. The next machine safely requeues that work.
- Remote publication is not a multi-ref atomic transaction. The implementation must retain typed
  divergence/response-unknown attention when Change-branch and state-branch publication outcomes
  cannot be proven together.
- The current primary checkout contains unrelated dirty files and an old tracked package deletion;
  migration must use explicit path ownership and user-visible maintenance Changes.
- `.owlbear` remains excluded from consumer `main`. This plan targets the development `dev` branch
  and Delivery operator recovery, not consumer product distribution.

## 9. Immediate Next Work Item

Create a new Design/Delivery Change for **Admitted Design Snapshot In Change PR** with these first
implementation outcomes:

1. Exact package snapshot receipt and managed Change-worktree commit.
2. Admission sequencing, initial `ADMITTED_DESIGN` checkpoint, and first draft PR publication.
3. Post-admission Design revision freeze and fresh-clone package recovery proof.

Create the remote Delivery-state branch/bootstrap work as a dependent second Change. Do not begin
that second Change by committing every current runtime file; first define and test the sanitized
snapshot schema and sparse checkpoint cadence.
