---
name: w-integration-repair
description: "Workflow: Repair one current Integration merge conflict through reviewed additive admission"
user-invocable: false
---

# Integration Repair

Repair one user-selected change whose current typed Integration attention reports a merge conflict.
This is an on-demand recovery path, not part of automatic orchestration or normal Build execution.

## Step 0 - Bind Current Attention And Coordination

Require one non-empty `change_id`. Call `show_integration_attention` for that exact identity and
require a current `DeliveryIntegrationAttention` whose `change_id` matches and whose code is
`merge-conflict`. Stop without mutation for absent, stale, or any other attention code.

Read only `.owlbear/target/target-runtime/coordination/{change_id}.json`. Require one exact
coordination record with matching
change and Integration target, no active writer, `last_reviewed_commit == attention.change_head`,
and `target_head == attention.target_head`. Require its assigned worktree to be clean, on its exact
branch, and at the attention change head. Never edit startup configuration, coordination, Delivery
state, package bytes, completed history, another checkout, or either source or target reference.

## Step 1 - Make One Additive Conflict Repair

Identify the original conflict paths by comparing the attention target head and change head with
Git's merge machinery. Edit only those conflicting source paths in the existing change worktree.
The repair must preserve completed history, remove the conflict when merged with the exact attention
target head, and introduce no unrelated behavior or cleanup.

Run focused proof for the affected paths. Create one explicit commit whose sole parent is
`attention.change_head`; do not amend, rebase, merge, squash, cherry-pick, or create another
worktree. Require the branch and clean worktree to end at that exact repair commit. If any identity,
head, custody, path, ancestry, or cleanliness check changes, stop without admission or target
mutation and report that the current attention must be reloaded.

## Step 2 - Obtain Independent Exact-Commit Review

Dispatch `build-reviewer` with the complete current attention, exact coordination identities,
original conflict paths, complete repair diff, changed paths, exact repair commit, focused proof,
and the Builder owner identity. Require the reviewer to echo the exact commit, return `pass |
finding`, and provide non-empty source-grounded evidence. The reviewer identity must differ from the
Builder owner identity.

On an implementation finding, preserve the rejected commit, create at most one new single-child
repair commit inside the same conflict-path boundary, rerun affected proof, and obtain fresh review.
Any invalid review or non-implementation finding preserves current Delivery state and performs no
admission.

## Step 3 - Admit Only The Reviewed Repair

Only an independent `pass` may construct one `DeliveryIntegrationRepair` with:

- the exact attention ID, change ID, Integration target, prior change head, and prior target head;
- the exact clean current repair commit as `reviewed_repair_commit`;
- Builder's owner identity; and
- one `DeliveryIntegrationRepairReview` containing a stable review ID, the independent reviewer
  identity, and that same exact candidate commit.

Call `admit_reviewed_integration_repair` once with that typed repair. Treat the returned repair as
the only successful result. Never call `integrate_ready_change`, retry Integration, move the target,
publish a Build result, or select a Delivery transition from this workflow.

## Output

Report only whether the exact change's reviewed repair was admitted or why no admission occurred.
Do not expose raw diffs, internal Git hashes, target-update instructions, or unrelated portfolio
state in the user-facing response.

## Known Pitfalls

- **Treating attention as permission to merge:** repair admission only advances the reviewed change
  boundary; a later normal orchestration cycle owns any Integration retry.
- **Repairing a non-conflict attention:** only `merge-conflict` has an additive source repair path.
- **Using reviewer prose as admission:** require exact commit echo, independent identity, and pass.
