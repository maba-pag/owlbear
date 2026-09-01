---
name: w-change-publication
description: "Workflow: Advance one finalized Delivery Change through target convergence, publication, and acceptance"
user-invocable: false
---

# Change Publication

Advance one exact finalized Change through the provider-facing publication tail. This workflow owns
Delivery publication operations, not implementation, finalization proof, semantic conflict
resolution, provider merge approval, or raw repository mutation. One invocation may perform
consecutive retry-safe operations only while every fresh state exposes a single unambiguous agent
action.

## Step 0 - Bind Current Publication Authority

Validate the supplied value as one lowercase-hyphenated `change_id`. If Delivery tools are deferred,
run `tool_search` for
`OwlBear Delivery list_work_items show_work_item show_finalization_context reconcile_finalization_head reconcile_change_checkpoint mark_change_ready sync_change_with_target abort_target_sync_conflict resolve_target_sync_conflict observe_change_publication_checks observe_acceptance show_completed_change`.

Call `list_work_items` and select the exact Change publication card. Use `show_work_item` when the
card does not expose the publication head, target, pull-request identity, current disposition, or
next action needed for the decision. Re-read `show_finalization_context(change_id)` before any
checkpoint operation. Treat Delivery state as authority and local/provider observations only as
fences for an operation that Delivery already permits.

Classify the current state as exactly one of:

- `needs-finalization` - no valid finalization exists for the current Change head;
- `target-convergence` - a finalized head exists but does not contain the current integration target;
- `checkpoint-pending` - the finalized head contains the current target and needs publication;
- `pull-request-draft` - the exact published pull request can be marked ready after required checks;
- `awaiting-merge` - provider merge is the user's next action;
- `acceptance` - provider merge can be observed and recorded;
- `attention` - exact retained Change attention blocks ordinary publication;
- `completed` - accepted completion already exists;
- `unknown` - current authority cannot support one of the other classifications.

Do not infer completion from finalization. A finalization receipt and `checkpoint-pending` together
mean the reviewed head is finalized but not yet durably published.

## Step 1 - Converge With The Integration Target

Before first publication of a finalized head, read the configured remote and integration target from
Delivery configuration and resolve that branch's current exact head with a read-only remote
observation. Confirm whether that target head is an ancestor of the managed Change head. Do not
fetch, merge, checkout, update a reference, or inspect another worktree with raw Git.

When the target is already contained, continue to Step 2. When it is not contained, call
`sync_change_with_target(change_id, expected_target=target_head, operation_id)` with a deterministic
operation identity bound to the Change and exact target. A successful sync moves the managed Change
head, invalidates the prior finalization, and queues republication. Re-read the publication card and
return `needs-finalization` with `/finalize-change <change_id>`; do not publish the unfinalized merge.

When synchronization preserves merge conflicts, re-read the exact publication attention and report
its disposition identity, target head, operation identity, and conflict paths. Do not edit conflict
files, stage paths, create the merge commit, call `resolve_target_sync_conflict`, clear the
disposition, abort the merge, or retry synchronization. Semantic conflict resolution is reviewed
implementation work and requires separately admitted Delivery authority. Call
`abort_target_sync_conflict` only after an explicit user decision to abandon that exact sync attempt;
aborting is not a conflict-resolution fallback.

## Step 2 - Publish The Finalized Checkpoint

For `checkpoint-pending`, require a valid finalization whose exact head still equals the clean managed
Change head and contains the current integration target. Call
`reconcile_change_checkpoint(change_id)` once, then re-read the publication card. A reconciled
checkpoint must bind the published branch and draft pull request to the finalized head. If the
operation invalidates finalization, changes attention, or remains pending, stop and report that exact
state rather than continuing optimistically.

## Step 3 - Mark The Pull Request Ready

For `pull-request-draft`, require current Delivery authority to confirm that the finalized head,
published head, and pull-request head match. Call `mark_change_ready` with `change_id`, a
deterministic `operation_id`, the current `finalization_id`, and the current `exact_head`. The
operation observes required provider checks and may retain resulting attention; it does not treat
those checks as a readiness gate. Re-read the publication card after the operation.

If required checks fail or provider state creates attention, stop with the exact disposition identity
and route the user to `/resolve-delivery-attention <change_id> <disposition_id>`. Do not select,
dispatch, rerun, waive, or reinterpret provider checks.

## Step 4 - Observe Acceptance

For `awaiting-merge`, report the exact repository and pull-request number and stop for the user to
merge in the provider. Delivery never merges the pull request.

For `acceptance`, call `observe_acceptance(change_id)` once. An open pull request remains
`awaiting-merge`; a matching merged pull request records accepted completion. Re-read the publication
card or `show_completed_change` and require a persisted completion identity before returning
`completed`.

## Step 5 - Report The Transition

Return exactly one mapping:

```yaml
published:
  change_id: <change-id>
  finalized_head: <40-hex>
  published_head: <40-hex>
  pull_request: <repository>#<number>
  next_action: <mark-ready-or-merge>
```

```yaml
needs_finalization:
  change_id: <change-id>
  current_head: <40-hex>
  reason: <target-synchronized-or-finalization-invalidated>
  next_command: /finalize-change <change-id>
```

```yaml
attention:
  change_id: <change-id>
  disposition_id: <64-hex>
  condition: <bounded-current-condition>
  preserved_evidence: <target-operation-and-conflict-paths-or-provider-evidence>
  next_command: <exact-authorized-handoff-or-null>
```

```yaml
awaiting_merge:
  change_id: <change-id>
  pull_request: <repository>#<number>
  published_head: <40-hex>
  next_action: Merge the pull request in GitHub
```

```yaml
completed:
  change_id: <change-id>
  completion_id: <64-hex>
  accepted_head: <40-hex>
```

```yaml
blocked:
  change_id: <change-id>
  condition: <missing-or-ambiguous-authority>
  next_action: <one-specific-remedy>
```

## Known Pitfalls

- **Equating finalization with completion:** publication, provider merge, and acceptance remain.
- **Publishing before target convergence:** synchronize the exact current target first.
- **Automatically resolving conflicts:** preserve them and require reviewed implementation authority.
- **Continuing from stale state:** re-read the publication card after every mutation.
- **Treating provider waiting as failure:** an open ready pull request correctly waits for user merge.
- **Bypassing Delivery with Git:** read-only Git may verify ancestry; it never owns publication mutation.
