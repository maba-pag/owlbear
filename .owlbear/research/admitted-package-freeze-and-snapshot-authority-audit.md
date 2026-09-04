# Admitted Package Freeze And Snapshot Authority Audit

> **Owning task:** Pending Delivery package-collision decision
> **Date:** 2026-08-23
> **Question:** Is it true that admission freezes a Design package and makes the Change snapshot
> authoritative, such that Git may safely overwrite an ignored local copy during pull?
> **Status:** Audited; the condition is only partially satisfied

## 1. Context And Question

The proposed minimal correction for package-bearing pull requests is to ignore
`.owlbear/delivery/packages/` in the primary checkout. The managed Change worktree already force-adds
the four admitted package files, so ignored working files would still enter the Change pull request.
An isolated Git experiment confirmed that a later merge succeeds when an incoming tracked package
overlaps an ignored local package.

That behavior has an important consequence: Git silently replaces differing ignored bytes. This is
safe only if both statements below are enforced:

1. Admission freezes the local package, so a post-admission difference is not legitimate authored
   work.
2. The package snapshot in Change history is authoritative and verified, so the incoming tracked
   bytes are the accepted replacement.

This audit tests those statements against current source, tests, history, and the fresh-clone
bootstrap path. It does not decide whether pre-admission drafts should be ignored; that remains a
separate durability and visibility choice.

## 2. Sources Studied

| Source | Evidence used | Limit |
| --- | --- | --- |
| [`portfolio_application.py`](../../serve/delivery/src/owlbear_delivery/portfolio_application.py) | Public revision guard, admission sequence, acquisition source preparation, package/runtime validation, state publication, and worker launch package | Does not prevent direct filesystem or low-level store mutation |
| [`design_package.py`](../../serve/delivery/src/owlbear_delivery/design_package.py) | Compare-and-swap revision, generated-authority publication, manifest verification, package identity, and exported low-level store | Store methods do not know whether a Change is admitted |
| [`change_workspace.py`](../../serve/delivery/src/owlbear_delivery/change_workspace.py) | Snapshot receipt identity, exact package-only commit, replay behavior, and writer-head validation | Later writer commits are not checked for package-path preservation |
| [`delivery_runtime.py`](../../serve/delivery/src/owlbear_delivery/delivery_runtime.py) | Admitted checkpoint queue, package snapshot re-anchoring, task authority, and result publication validation | Result publication validates task/result/head identity, not changed path sets |
| [`delivery_state.py`](../../serve/delivery/src/owlbear_delivery/delivery_state.py) | Remote state records `package_id`, authority digest, Change head, and completion state | Snapshot model does not retain `ChangeDesignPackageSnapshotReceipt` |
| [`delivery_application_loader.py`](../../serve/delivery/src/owlbear_delivery/delivery_application_loader.py) | Fresh bootstrap selects a remote Change head or accepted merge commit and restores package blobs | Restored package identity is not compared with `snapshot.package_id` |
| [`target_server.py`](../../serve/delivery-mcp/src/owlbear_delivery_mcp/target_server.py) | MCP revision delegates through `PortfolioApplication.revise_design_session` | Proves the supported MCP route, not arbitrary Python callers |
| [`test_portfolio_application.py`](../../serve/delivery/tests/test_portfolio_application.py) | Regression proves application-level revision is rejected for an admitted runtime without package mutation | Does not cover restart plus corrupt runtime, low-level mutation, or manual edits |
| [`test_change_workspace.py`](../../serve/delivery/tests/test_change_workspace.py) | Regression proves initial snapshot commit contains the four supplied files and no unexpected path | Does not prove later Change commits preserve those files |
| [`test_delivery_state.py`](../../serve/delivery/tests/test_delivery_state.py) | Fresh-clone test proves package restoration and package-ID equality for an unchanged snapshot | Does not inject a valid but different package at the later Change head |
| [`w-packet-building`](../../share/skills/w-packet-building/SKILL.md) | Builder is instructed not to edit Design, package internals, runtime, or unlisted surfaces | Agent policy is not deterministic engine enforcement |
| Commit `66ee4d62a` | Introduced the revision guard, snapshot operation, state `package_id`, and package/runtime validation together | No later safeguard closes the bootstrap or later-commit gaps |
| Isolated Git experiments on 2026-08-23 | Existing ignore rule plus incoming force-added package permits merge; differing ignored bytes are overwritten; an ignore rule arriving in the same merge is too late | Git behavior only; it does not establish Delivery authority |

No external source was required because the relevant authority and failure boundary are local.

## 3. Findings

### 3.1 Supported Design revision is frozen after admission

`PortfolioApplication.revise_design_session` reconciles persisted runtimes and rejects revision when
the Change ID is present in the admitted runtime map. The MCP adapter delegates to this method. The
portfolio regression test proves rejection leaves the verified package unchanged.

This is a real freeze at the supported Application and MCP boundary.

The boundary is not absolute:

- `DesignPackageStore.revise` remains a public exported Python method and has no admission context;
- package files can be edited manually; and
- `publish_design_checkpoint` and `derive_delivery_contract` still read the local package after
  admission without first comparing it to the snapshot receipt.

Those lower-level routes do not make post-admission mutation legitimate, but they mean the filesystem
copy is protected by validation and convention rather than access control.

**Assessment:** application-level freeze is enforced; universal immutability is not.

### 3.2 Runtime validation detects local semantic divergence

Before worker acquisition and Delivery-state publication, `_validate_package_authority` verifies:

- SHA-256 of `authority.json` equals the runtime authority digest; and
- the manifest hashes for `intent.md` and `design.md` equal the admitted contract source bindings.

`DesignPackageStore.read_verified` also requires the manifest to be canonical for the three content
files. Together these checks reject changed package content during normal acquisition and state
publication. Because package identity is the digest of that canonical manifest, the validated bytes
also imply the admitted package identity.

The comparison is indirect: `_validate_package_authority` does not compare the local package ID with
`coordination.design_package_snapshot.package_id`. A direct comparison would make the invariant
explicit and produce a clearer failure.

**Assessment:** normal active operations fail closed on local semantic divergence, but not through a
single explicit package/snapshot identity check.

### 3.3 The original snapshot commit is exact and immutable

`snapshot_design_package` accepts only the four canonical files, writes them in the managed Change
worktree, force-adds those explicit paths, commits only those paths, and verifies the commit changed
that path set. Its receipt binds:

- Change ID;
- package ID;
- managed branch and worktree;
- previous reviewed head; and
- exact snapshot commit.

Git commit immutability therefore preserves the original admitted package. Snapshot replay requires
the managed worktree to remain at the receipt head and clean.

**Assessment:** the original snapshot is strong durable evidence.

### 3.4 The current Change head is not package-path immutable

Later Builder commits extend the same Change branch. Builder policy says not to edit Design or
package internals, but deterministic result publication validates only:

- active claim and task identity;
- authority and task digests;
- reviewed result commit identity; and
- writer-owned clean branch head.

It does not inspect the diff from the previous reviewed head or reject changes under
`.owlbear/delivery/packages/<change-id>/`. `DeliveryTaskDefinition.maintained_surfaces` is typed task
authority but has no package-path exclusion validator. A malformed plan or non-conforming writer can
therefore commit a valid but different canonical package at a later Change head while preserving the
original snapshot commit in history.

**Assessment:** package immutability after the snapshot is policy-only at the current Change head.

### 3.5 Fresh bootstrap does not verify restored package identity

Remote state records `package_id`, but not the package snapshot receipt. Fresh bootstrap:

1. selects `snapshot.change_head` when the remote Change branch exists, or the accepted merge commit
   for a completed Change;
2. reads the four package blobs from that selected revision;
3. calls `DesignPackageStore.restore`; and
4. reconstructs runtime and coordination state.

`restore` verifies internal manifest consistency, but `_restore_remote_snapshot` does not compare its
returned package ID with `snapshot.package_id`. A later Change commit containing a different,
internally consistent package can therefore be restored during startup. Existing local-state
validation does compare package IDs, but that check is used only when local runtime state already
exists, not for fresh restoration.

Later acquisition should reject changed intent, design, or authority against runtime bindings, but:

- startup itself succeeds;
- `read_design_session` can expose the restored different package before acquisition; and
- the error is delayed and does not identify remote archive divergence as the source.

**Assessment:** the Change snapshot is not fully authoritative at the fresh-clone boundary.

### 3.6 Git ignore changes the custody model

With an ignore rule already present before the package-bearing merge:

- the managed Change worktree still commits package files because it uses `git add -f`;
- an identical ignored local package is replaced by the tracked package without conflict;
- a differing ignored local package is also replaced without conflict or preservation; and
- the resulting tracked package is clean because ignore rules do not apply to tracked files.

If the ignore rule arrives in the same merge as the first tracked package, Git evaluates the existing
checkout before that rule is active and still aborts on the untracked overwrite. The ignore policy
must therefore land before later package-bearing pull requests.

Ignoring the directory declares local untracked bytes disposable at the Git boundary. Current
Delivery behavior does not yet justify that declaration for every admitted package because the
archive can drift at a later Change head and bootstrap does not bind restored bytes to recorded
package identity.

It also declares pre-admission drafts invisible to normal Git status and vulnerable to
`git clean -X`. Admission freeze and snapshot authority do not protect that earlier tier.

## 4. Claim Matrix

| Required claim | Current status | Strongest evidence | Missing proof or enforcement |
| --- | --- | --- | --- |
| Supported callers cannot revise after admission | Enforced | Application guard, MCP delegation, regression test | Direct store/filesystem mutation remains possible |
| Normal active operations reject changed local bytes | Enforced indirectly | Manifest verification plus runtime source/authority digest checks | Explicit comparison to snapshot receipt package ID |
| Original admitted snapshot remains recoverable | Enforced | Exact package-only commit and receipt | Remote state does not retain the receipt |
| Later Change commits preserve package bytes | Policy-only | Builder skill prohibition | Engine path/digest guard at result/checkpoint/finalization boundaries |
| Fresh bootstrap restores the recorded package | Not enforced | State stores `package_id` | Compare restored package ID to `snapshot.package_id` before state restoration |
| Ignored differing local bytes are disposable | Not established | None | All post-admission authority must come from verified durable snapshot bytes |
| Pre-admission ignored drafts are safely durable | False | Prior portability plan explicitly accepts a local-only loss window | Separate draft backup or explicit acceptance of invisibility/deletion risk |

## 5. Options

| Option | Effect | Risk | Decision |
| --- | --- | --- | --- |
| Add only `delivery/packages/` to `.gitignore` | Removes future pull collisions after the ignore rule lands | Silently discards divergence before snapshot authority is fully enforced; hides drafts | Reject for now |
| Ignore packages plus add identity/path guards | Makes local admitted bytes an explicitly replaceable cache backed by verified Change history | Draft visibility and `git clean -X` risk remain | Viable if draft risk is accepted |
| Keep packages visible and move the tracked archive path | Avoids silent overwrite and draft invisibility | Requires old/new archive lookup for prior snapshots | Safest narrow path separation |
| Keep current layout and require manual cleanup | Preserves loud Git protection | Repeats the incident and relies on operator memory | Reject |

## 6. Minimum Hardening Before Ignoring Packages

If the project chooses the `.gitignore` approach, the smallest credible prerequisite change is:

1. **Bind fresh restore to recorded identity.** Capture the result of `package_store.restore` and
   reject startup unless `restored.package_id == snapshot.package_id` before runtime or coordination
   restoration.
2. **Protect the archive through later Change heads.** Add a workspace-manager validator that reads
   the canonical package tree at the current candidate head and proves it has the package ID recorded
   by `coordination.design_package_snapshot`. Invoke it before accepting a Builder result, before
   finalization, and before publishing a Delivery-state snapshot. A package-path diff is then an
   engine conflict, not only a reviewer finding.
3. **Make local validation explicit.** Compare the verified local package ID with the coordination
   snapshot receipt package ID in `_prepare_source` and state publication. Preserve the existing
   source and authority digest checks because they explain which admitted binding differs.
4. **Retain snapshot identity remotely.** Either add the snapshot receipt or its package commit to
   `DeliveryStateSnapshot`, or prove the package at each recorded `change_head` by package ID. The
   latter is a smaller schema change but loses the direct original-snapshot locator when branches are
   rewritten before publication.
5. **Land the ignore rule first.** Update root and seed ignore policy in a package-free change. The
   pull-collision regression must then prove a later force-added package merge succeeds.
6. **Decide draft custody explicitly.** Document that unadmitted drafts are ignored, absent from Git
   status, local-only, and removable by `git clean -X`, or retain visible drafts through a separate
   working/archive path design.

Items 1 and 2 are required to call the Change package authoritative. Item 3 provides clear local
diagnostics. Item 4 determines recovery strength. Items 5 and 6 are required by Git behavior and
user custody rather than package identity.

## 7. Acceptance Scenarios

**AC-B1:** Given an admitted Change, calling the MCP `revise_design_session` operation returns the
admitted-change error and byte comparison shows no change in `authority.json`, `design.md`,
`intent.md`, or `manifest.json`.

**AC-B2:** Given a local admitted package whose canonical package ID differs from the coordination
snapshot receipt, acquisition and Delivery-state publication return package-authority conflict and
create no claim or remote state commit.

**AC-B3:** Given a Builder candidate whose current Change head changes one canonical archive file,
`publish_delivery_result` rejects the candidate even when writer custody, task digest, observations,
and review identities otherwise pass.

**AC-B4:** Given a remote Delivery-state snapshot whose `package_id` differs from a canonical package
stored at `snapshot.change_head`, fresh-clone startup fails before writing local runtime,
coordination, package, or worktree state.

**AC-B5:** Given an ignore rule committed before admission, an ignored local package matching the
recorded package ID, and a later package-bearing merge, the primary checkout fast-forwards without
an overwrite error and the resulting tracked package ID equals the remote state package ID.

**AC-B6:** Given an ignored local package with differing bytes, the chosen custody policy has one
explicit outcome: either a pre-pull Delivery check rejects divergence and preserves the bytes, or
documentation classifies those bytes as disposable cache and the Git-boundary test proves they are
replaced by the recorded authoritative package.

**AC-P1:** Given an unadmitted ignored Design package, project documentation names its local-only
status, absence from Git status, and `git clean -X` deletion risk; verification compares the text with
the implemented ignore rule and Design lifecycle.

## 8. Recommendation, Confidence, And Limits

The quoted condition is **not currently strong enough** to justify ignoring the package directory.
Admission freezes revision through supported Application and MCP operations, and the original
snapshot commit is durable. However, later Change commits are not deterministically prohibited from
changing the archive, and fresh bootstrap does not compare restored bytes with the remote state's
recorded package ID.

Before adopting `.gitignore`, implement fresh-restore package-ID validation and an engine-level
package-preservation check on later Change heads. Then decide whether pre-admission drafts may be
hidden and removable as ignored local state. If that draft custody is unacceptable, separating the
visible authored path from a distinct tracked archive remains the safer design.

Confidence is **0.96**. The remaining uncertainty is product intent: whether ignored pre-admission
drafts are acceptable. The technical authority gaps are directly evidenced in current source and
tests.
