# Delivery Package Authority And Collision Rollout Plan

> **Owning task:** Pending Delivery package-collision Change
> **Date:** 2026-08-23
> **Question:** What is the smallest safe correction for local Design packages that collide with the
> same package when its Change pull request is merged?
> **Status:** Reconciled after challenger review; authority work is implementation-ready and the
> collision remedy has one explicit topology decision

## 1. Decision Summary

Do not relocate the active package store as part of authority hardening and do not add startup
migration.

Keep authored and locally verified packages at:

`.owlbear/delivery/packages/<change-id>/`

Continue force-adding the admitted package snapshot in the managed Change worktree. First bind fresh
restore to the package ID already recorded in remote state, prove the Git boundary under the actual
default pull strategy, and enforce package identity at lifecycle consumption points.

The workstation's obsolete global `pull.rebase=true` preference was disabled on 2026-08-23. Ordinary
`git pull` now uses merge semantics. This configuration change does not solve the untracked-package
collision; it makes the required regression proof match the operation users actually run.

After authority hardening and Git proof exist, compare two collision remedies before changing path
policy: move only the committed package snapshot to a distinct archive root, or ignore the active
package root and accept its merge-time custody switch. Implement one remedy, not both.

This plan supersedes
[Delivery Package Cache And Archive Separation Plan](delivery-package-cache-archive-separation-plan.md).
The detailed evidence for the revised authority boundary is in
[Admitted Package Freeze And Snapshot Authority Audit](admitted-package-freeze-and-snapshot-authority-audit.md).

## 2. Why The Plan Changed

The earlier plan moved working packages under ignored runtime state and retained the tracked package
path as an archive. Follow-up research rejected that broad migration, but challenger review found
that the narrower alternative of moving only committed snapshots had been costed too broadly.

The `.gitignore` approach remains mechanically plausible:

- `ChangeWorkspaceManager.snapshot_design_package` already uses `git add -f` for the four package
  paths, so managed Change worktrees still commit ignored package files;
- a pre-existing ignore rule permits a merge-based pull to replace an ignored local copy with an
  incoming tracked package; and
- tracked package files remain tracked after merge because ignore rules do not affect tracked files.

Those facts still require executable proof through ordinary `git pull` with `pull.rebase=false`, for
both fast-forward and diverged merge cases. The ignore option is not safe as a standalone edit. Git
silently overwrites differing ignored bytes, while current Delivery has two authority gaps:

1. fresh bootstrap restores package bytes from the latest Change head without comparing the restored
   package ID with `DeliveryStateSnapshot.package_id`; and
2. later Builder commits are governed by agent policy not to edit package internals, but result
   publication does not deterministically reject a candidate whose package tree changed.

The revised plan closes those gaps under either path topology. It no longer requires a broad helper
refactor or a portfolio-wide `DeliveryStateSnapshot` model validator to close the narrow bootstrap
gap.

## 3. Preserved And Rejected Decisions

### Preserved

- Admission remains the first remote durability boundary for Design intent, design, generated
  authority, and manifest.
- The admitted package travels in the normal managed Change branch and pull request.
- `refs/owlbear/packages/*` remains local integrity history, not remote backup.
- `/finalize-change` remains read-only with respect to the primary checkout.
- No agent performs package cleanup around `git pull`.
- The first pull-collision correction still requires one explicit local cleanup because its ignore
  rule was not already present.

### Rejected

- Moving active packages under `.owlbear/delivery/runtime/packages/`.
- A journaled package-root migration.
- Ignoring packages before package authority is enforced.
- A cross-field `DeliveryStateSnapshot` model validator that can turn one invalid remote snapshot
  into an untyped portfolio-wide startup failure.
- Treating public package-verification helpers as prerequisite authority when existing manifest,
  source-binding, and authority checks already imply package identity.
- Deleting packages during finalization or acceptance observation.
- Requiring users to repeat manual cleanup for each merged Change.

## 4. Target Invariants

### I1 - Supported revision freeze

After admission, Application and MCP revision operations reject authored package replacement. The
four verified files remain unchanged.

### I2 - Derived admitted package identity

The expected package ID is derived without trusting mutable package bytes:

- `change_id` comes from the admitted contract;
- intent and design hashes come from `DeliveryContract.source_bindings`; and
- the authority hash comes from `DeliveryRuntime.authority_digest`.

These values construct canonical `DesignPackageManifest` bytes whose SHA-256 is the expected package
ID. When a `DeliveryStateSnapshot` is the authority source, its contract and authority digest derive
the same identity and must equal its stored `package_id`.

### I3 - Local package identity

For an admitted Change, the locally verified package ID equals the package ID in its package snapshot
receipt when that receipt is locally available and equals the package ID derived from admitted
authority. Its source and authority digests also equal runtime authority.

### I4 - Consumption-point package identity

At each lifecycle operation that consumes a candidate or reviewed Change head, the canonical package
files parse to the admitted package ID. A missing, incomplete, unsafe, or different package tree
blocks result publication, finalization, and Delivery-state publication. Externally authored heads
must fail at the next consumption point unless later evidence justifies an earlier guard.

### I5 - Fresh-bootstrap package identity

Before fresh bootstrap writes package, runtime, coordination, or worktree state, package bytes read
from the remote Change head or accepted merge commit parse to `DeliveryStateSnapshot.package_id`, and
that stored ID equals the identity derived from the snapshot contract and authority digest.

### I6 - Default-pull proof and ignore ordering

Collision behavior is proven through ordinary `git pull` with effective `pull.rebase=false`, covering
fast-forward and diverged merge cases. If ignore wins the topology decision, the target branch
contains the package ignore rule before a package-bearing pull request is merged. An ignore rule and
the first conflicting tracked package cannot rely on the same pull.

### I7 - Draft custody is explicit

Pre-admission packages remain local-only. If the ignore rollout is accepted, they are absent from
normal Git status and may be removed by `git clean -X`. Documentation must state this without calling
drafts remote-backed or reconstructable.

## 5. Design

### 5.1 Narrow fresh-restore binding

Extend the existing pre-write validation in `DesignPackageStore.restore` to compare the canonically
validated package ID with the expected `DeliveryStateSnapshot.package_id`. The comparison must happen
before transaction creation. A mismatch raises the existing typed package conflict and leaves package,
runtime, coordination, branch, and worktree state absent.

Do not add a `DeliveryStateSnapshot` model validator. Snapshot identity is checked within each
Change's restore path so one invalid remote record cannot abort portfolio loading before per-Change
failure handling applies. Keep expected-ID derivation as a local implementation detail only where a
caller needs it; `_validate_package_authority` already proves the equivalent source and authority
bindings during normal active operations.

### 5.2 Exact-commit package reads

Add one read-only `ChangeWorkspaceManager` operation that reads the four package blobs from a supplied
exact commit and validates the canonical package. It returns the verified package or fails with a
typed workspace conflict. It must not inspect whichever branch happens to be checked out and must
distinguish an absent blob from a present empty blob.

The path remains:

`.owlbear/delivery/packages/<change-id>/<canonical-name>`

### 5.3 Authority checks at semantic boundaries

Derive the expected admitted identity from runtime contract bindings and authority digest. Compare the
locally verified package and the local snapshot receipt, when present, with that identity. Then verify
the package at these immutable commits:

- `PublishDeliveryResult.result.completed_commit` before accepting the Build result;
- `FinalizeDeliveryChange.exact_head` before accepting finalization;
- `ChangeCoordination.last_reviewed_commit` immediately before publishing Delivery state; and
- the remote revision selected by `_fetch_snapshot_change_head` before fresh restoration.

The exact-commit check and the existing branch-head or writer-head check must both pass. If the branch
moves between checks, existing exact-head validation rejects the operation.

### 5.4 Fresh-bootstrap ordering

Change `_restore_remote_snapshot` to:

1. select the remote Change head or accepted merge commit;
2. read the four package blobs;
3. restore only when canonical validation yields `snapshot.package_id`;
4. stop with a typed per-Change failure and no local writes on mismatch; and
5. only then restore branch, worktree, coordination, and runtime state.

No Delivery-state schema change is required because schema version 1 already contains `package_id`
and `change_head`. Add a repository-level compatibility test that enumerates current published
snapshots and proves the comparison, rather than changing Pydantic's accepted wire shape.

### 5.5 Git boundary proof

Use a bare remote and two checkouts to exercise ordinary `git pull` with effective
`pull.rebase=false`. Cover a fast-forward pull and a pull that creates a merge commit. For each,
assert behavior when the ignore rule predates the incoming package, when the rule arrives in the same
package-bearing commit, and when ignored local bytes differ from incoming tracked bytes.

Separately prove that `snapshot_design_package` still succeeds under ignore through both `git add -f`
and `git commit --only`, and that its staged-path rollback remains correct. This proof informs the
topology decision; it does not itself select ignore.

### 5.6 Collision topology decision

Compare these options after Changes 1 through 3:

- **Distinct committed archive root:** keep local authored packages visible at the active path, write
  committed snapshots to a path local workflows never populate, and retain the minimum legacy read
  fallback needed for already-published state.
- **Ignored active root:** add `delivery/packages/` to root and seed ignore policy, accept that
  in-flight packages are invisible and removable by `git clean -X`, and document that the same paths
  become tracked after merge.

Evaluate the exact Git blob-reader, setup propagation, documentation, test-fixture, and legacy-state
surfaces for both options. Do not infer that archive relocation is only a literal rename, and do not
select ignore merely because force-add works.

## 6. Workable Implementation Sequence

### Change 1 - Bind fresh restore to recorded identity

**Result:** Fresh bootstrap cannot write a package different from the package ID already recorded in
remote state.

**Likely files:**

- `serve/delivery/src/owlbear_delivery/design_package.py`
- `serve/delivery/src/owlbear_delivery/delivery_application_loader.py`
- focused package and loader tests

**Work:** Compare the canonically validated restored package with `snapshot.package_id` inside the
existing pre-write validation boundary. Preserve typed per-Change failure handling and avoid a state
model validator or broad verification refactor.

**Proof:** a valid but different remote package fails before package, runtime, coordination, branch,
or worktree state exists. Current published snapshots pass a point-in-time compatibility check.

**Dependency:** none.

### Change 2 - Prove the default Git boundary

**Result:** Executable tests establish the behavior of the now-configured merge-based `git pull`
before either path topology is selected.

**Likely files:** a focused Git integration module under `serve/delivery/tests/` and existing snapshot
workspace tests.

**Work:** Cover default fast-forward pull, default diverged merge pull, pre-existing versus same-pull
ignore timing, differing ignored bytes, force-add plus partial commit, and rollback under ignore.

**Proof:** each fixture asserts exit status, exact package bytes and package ID, tracked path state,
unrelated untracked files, and expected refusal when ignore arrives too late.

**Dependency:** none.

### Change 3 - Enforce package identity at consumption points

**Result:** Later Change commits cannot make altered, incomplete, or missing admitted package authority
executable, finalizable, or publishable.

**Likely files:**

- `serve/delivery/src/owlbear_delivery/change_workspace.py`
- `serve/delivery/src/owlbear_delivery/portfolio_application.py`
- focused workspace and portfolio tests

**Work:** Add an exact-commit package reader that distinguishes absent from empty blobs. Verify package
identity before accepting a Build result, finalization, and Delivery-state publication. Exercise an
externally authored head and prove it fails at the next consumption point; add an earlier guard only
if that proof exposes a mutation window.

**Proof:** each boundary rejects mutated and missing package trees without writing its result,
finalization receipt, or remote state commit.

**Dependency:** Change 1.

### Decision Gate - Collision topology

Use Change 2 evidence and a focused surface inventory to select either a distinct committed archive
root or an ignored active root. The decision must explicitly cover draft visibility, `git clean -X`,
consumer setup propagation, legacy state reads, and the merge-time tracked/ignored custody switch.

### Change 4 - Implement the selected collision remedy

**Result:** Later package-bearing pulls do not collide with local active package files under one
documented custody model.

If the archive option wins, change snapshot write/read ownership, preserve only required legacy
reads, and update path authority documentation and tests. If ignore wins, change root and seed ignore
policy, setup parity and uninstall coverage, affected plain-`git add` fixtures, and documentation of
in-flight versus merged custody.

**Proof:** rerun Change 2's Git fixtures against the selected implementation, then run all affected
Delivery, setup, and documentation checks.

**Dependency:** Changes 2 and 3 plus the topology decision.

## 7. Acceptance Scenarios

**AC-B1:** Given an admitted Change and a revision request through the MCP adapter, the operation
returns the admitted-change error and package byte comparison shows no mutation.

**AC-B2:** Given a Build candidate whose exact commit changes one canonical package file,
`publish_delivery_result` rejects the candidate and writes no result candidate.

**AC-B3:** Given a finalization request whose exact head carries a different canonical package ID,
`finalize_change` rejects the request and writes no finalization receipt.

**AC-B4:** Given a state-publication attempt whose reviewed Change head carries a different package
ID, Delivery writes no remote state commit.

**AC-B5:** Given one serialized state snapshot whose recorded package identity is inconsistent with
its restored package, startup records a typed failure for that Change without aborting unrelated
portfolio reconciliation.

**AC-B6:** Given a remote snapshot whose selected package tree differs from `snapshot.package_id`,
fresh startup fails before creating local package, runtime, coordination, branch, or worktree state.

**AC-B7:** Given effective `pull.rebase=false` and an ignore rule present before the incoming package,
ordinary `git pull` succeeds in both fast-forward and diverged merge fixtures, and the resulting four
tracked package files have the admitted package ID.

**AC-B8:** Given the ignore rule only in the incoming package-bearing commit, ordinary `git pull`
observes Git's untracked-overwrite refusal, proving rollout ordering is enforced by the plan.

**AC-B9:** Given an exact candidate or reviewed head with one absent canonical package blob, the next
consuming lifecycle operation rejects it as missing rather than treating it as empty bytes.

**AC-B10:** Given an externally authored descendant with a changed package tree, adoption cannot lead
to accepted Build output, finalization, or Delivery-state publication.

**AC-P1:** Given the selected collision topology, `w-design-session`, operator documentation, path
policy, and snapshot implementation state the same persistence, visibility, and deletion guarantees.

## 8. Validation Scope

Run focused tests after each implementation slice, followed by domain coverage for all touched
owners:

- `uv run test serve/delivery/` for package, workspace, portfolio, state, and loader behavior;
- `uv run test serve/tools/tests/` if setup or target diagnostics change;
- `uv run test tests/test_init_scaffold.py tests/test_init_exports.py` if seed or initializer policy
  changes;
  and
- the Cockpit E2E seed path if package construction or configured roots change.

The bare-remote two-checkout test through ordinary `git pull` is the required proof for the original
user-visible failure. Unit tests alone cannot prove Git's untracked-overwrite boundary. The effective
workstation setting must remain `pull.rebase=false` while reproducing that supported operation.

## 9. Risks And Exclusions

### Risks

- Disabling pull rebase changes default pull integration globally for this workstation; explicit
  `git pull --rebase` remains available when needed.
- If ignore wins, in-flight packages can be removed by broad ignored-file cleanup and become tracked
  at merge time.
- If archive relocation wins, legacy package reads and path-authority documentation require bounded
  compatibility handling.
- Direct filesystem or low-level store mutation remains possible, but the derived identity and
  exact-commit checks make changed bytes non-executable, non-finalizable, non-publishable, and
  non-restorable after admission.
- An ignore bootstrap Change has one unavoidable final collision in an original checkout that already
  authored its package before the rule existed.

### Exclusions

- No migration of active authored packages into runtime state.
- No startup mutation of old-layout paths.
- No finalization or acceptance cleanup agent.
- No completed-package pruning.
- No remote publication of each draft revision.

## 10. Recommendation, Confidence, And Remaining Decision

Proceed with Changes 1 through 3. They close the verified authority gaps and establish executable Git
evidence under the now-supported merge-based default pull. None requires a custody decision.

Do not schedule Change 4 until the distinct committed archive and ignored active-root options are
compared against the same proof and compatibility surfaces. The disabled rebase preference resolves
the operation mismatch identified by the challenger; it does not select either topology.

Confidence is **0.95** for Changes 1 through 3 and **0.85** that the topology comparison is now
bounded enough for one explicit decision.

## 11. Decision Required

Choose a distinct committed archive root or an ignored active root before Change 4. Changes 1 through
3 should proceed first.
