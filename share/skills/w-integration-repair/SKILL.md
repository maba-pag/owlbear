---
name: w-integration-repair
description: "Workflow: Repair one current Integration merge conflict through reviewed additive admission"
user-invocable: false
---

# Integration Repair

Repair one orchestrator-supplied `DeliveryIntegrationRepairLaunchPackage` whose current typed
Integration attention reports a merge conflict. This is change-level claimed work, not a Build task
or user-selected recovery path.

## Step 0 - Bind Current Attention And Coordination

Call `show_integration_repair_context` with the launch's exact `change_id`, `claim.attempt_id`, and
`claim.claim_id`. Require the returned launch to equal the supplied launch, the attention code to be
`merge-conflict`, and writer custody to bind the same repair claim and owner. Require the assigned
worktree to be clean, on its exact branch, and at `attention.change_head`.

Any absent, stale, mismatched, or non-conflict context returns the claim-bound `dispatch_failure`
defined below without mutation. Never edit startup configuration, coordination, Delivery state,
package bytes, completed history, another checkout, or either source or target reference.

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

If proof or commit validation fails after edits but before a valid repair commit exists, restore only
the edits made by this repair attempt to the exact launch source head and verify the assigned
worktree is clean on its branch before returning `dispatch_failure`. If a clean candidate commit
already exists, leave it intact so exact recovery can preserve it. Never ask recovery to erase a
dirty worktree or discard edits whose ownership is uncertain.

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

Call `admit_reviewed_integration_repair` once with the launch's exact `attempt_id`, `claim_id`, and
that typed repair. Treat the returned repair as the only successful result. Never call
`integrate_ready_change`, retry Integration, move the target, publish a Build result, or select a
Delivery transition from this workflow.

## Output

On admission, return exactly:

```yaml
kind: integration_repair_admitted
change_id: <launch.change_id>
attempt_id: <launch.claim.attempt_id>
claim_id: <launch.claim.claim_id>
attention_id: <launch.attention.attention_id>
```

If fresh context, custody, review, or admission cannot be established, return exactly:

```yaml
kind: dispatch_failure
change_id: <launch.change_id>
attempt_id: <launch.claim.attempt_id>
claim_id: <launch.claim.claim_id>
failed_operation: <operation>
reason: <non-empty bounded reason>
```

Do not expose raw diffs, internal Git hashes, target-update instructions, or unrelated portfolio
state.

## Known Pitfalls

- **Treating attention as permission to merge:** repair admission only advances the reviewed change
  boundary; a later normal orchestration cycle owns any Integration retry.
- **Repairing a non-conflict attention:** only `merge-conflict` has an additive source repair path.
- **Using reviewer prose as admission:** require exact commit echo, independent identity, and pass.
