---
name: w-change-finalization
description: "Workflow: Prove and finalize one exact reviewed Change head"
user-invocable: false
---

# Change Finalization

Own one user-invoked finalization attempt for one named Delivery Change. The Delivery context is the
source of truth for the managed worktree, Change branch, exact reviewed Change head, and current
publication phase. Produce heterogeneous exact-head observations, obtain an independent review, and
call only the finalization operation.

## Step 0 - Resolve Current Authority

Require one `change_id` from the prompt and call `show_finalization_context` before inspecting or
running proof. Require the returned context to contain the supplied Change identity and retain its
exact values for the attempt:

- managed `branch` and `worktree_path`;
- current `change_head` and `reviewed_change_head`;
- `publication_phase`.

Proceed only when the phase is `ready-for-finalization` or `finalization-invalidated`. The context
must be ready and its Change head must equal its reviewed head. Do not resolve a target ref, read a
verification profile, or invoke a separate finalization proof executor.

If `finalization_id` is present, treat the Change as already finalized when `finalized_head` equals
the current `change_head` and return `already_finalized` without running proof. If the finalized head
differs from the current Change head, return `dispatch_failure`; head-drift reconciliation belongs to
its owning Delivery operation.

## Step 1 - Establish Exact Managed Custody

Use read-only Git commands against the returned `worktree_path` and require:

- the path resolves to the managed worktree;
- `branch --show-current` equals the returned `branch`;
- worktree `HEAD` equals `change_head` and `change_head` equals `reviewed_change_head`;
- the worktree is clean, including untracked files;
- the Change identity and reviewed-head context remain unchanged.

The managed Change worktree is the only checkout permitted. Never create a proof worktree, enter the
user's primary checkout, fetch, push, update a target ref, reset, clean, checkout, restore, rebase,
merge, or alter Delivery files. A custody mismatch or dirty worktree is a bounded finalization
failure; do not repair it by discarding state.

## Step 2 - Capture Exact-Head Observations

Run the relevant maintained checks for the changed surfaces read-only in the managed Change worktree.
Capture at least one discriminating `DeliveryObservationReceipt` for the exact `change_head`, using
the actual command or procedure, exit status or artifact locator, observer identity, and a
timezone-aware observation time. Different checks may use different commands, tools, or evidence
types; there is no target-bound profile or required step list. A failed check, dirty worktree, or
changed head produces no finalization request. Do not mutate target refs, create another worktree, or
author evidence for a different commit.

## Step 3 - Obtain Independent Exact-Commit Review

Dispatch `build-reviewer` with `review_mode: finalization`, the complete fresh context, the exact
Change head, the observations, and the finalization diff boundary. Require the reviewer to
independently resolve and inspect the exact commit with read-only Git. Accept only a response with:

- `review_mode: finalization`;
- the exact reviewed commit equal to `change_head`;
- `disposition: pass`;
- `finding_boundary: none`;
- non-empty source-grounded evidence; and
- reviewer identity different from the finalizer identity.

A finding, stale head, malformed response, or unavailable reviewer produces no finalization request.
Do not repair reviewer findings inside this workflow and do not turn reviewer prose into a lifecycle
transition.

## Step 4 - Construct Exact Evidence

Only after observations and review pass, use the core Delivery models to construct values in memory:

- one `DeliveryObservationReceipt.create(DeliveryObservation(...))` for each relevant passing check,
  including the command or procedure, its exit status or artifact locator, and the exact Change head;
- one `DeliveryReviewReceipt.create(DeliveryReview(...))` using the exact reviewer evidence, the
  finalizer as `author_id`, and the independent reviewer as `reviewer_id`;
- one `FinalizeDeliveryChange` containing the operation ID, exact head, canonical observations, and
  canonical review.

Use a timezone-aware timestamp and serialize model output with `model_dump(mode="json")`. Never
calculate, copy, or invent observation or review IDs. Never use free-form evidence to replace the
typed observations or exact reviewer response.

## Step 5 - Re-check And Finalize

Call `show_finalization_context` again immediately before mutation. Re-read the managed worktree's
branch, exact `HEAD`, and clean state. Require the second context to preserve the Change ID, branch,
worktree, Change head, and reviewed head used by the observations and review. Discard the request if
any identity, head, or cleanliness value changed.

Call `finalize_change` once with the unchanged Change ID and the typed `FinalizeDeliveryChange`. Treat
its returned `DeliveryFinalizationReceipt` as the only successful finalization result. Do not call
checkpoint reconciliation, mark-ready, acceptance observation, Integration, repair, or any target
mutation operation from this workflow.

## Output Template

On success, return exactly:

```yaml
kind: finalized
change_id: <change_id>
operation_id: <operation_id>
exact_head: <exact Change head>
finalization_id: <returned finalization ID>
```

For an exact replay of an already-finalized current head, return:

```yaml
kind: already_finalized
change_id: <change_id>
exact_head: <current Change head>
finalization_id: <existing finalization ID>
```

For a bounded observation or custody failure, return:

```yaml
kind: proof_failed
change_id: <change_id>
failed_operation: <preflight or maintained check>
reason: <non-empty bounded reason>
```

For an independent review failure, return:

```yaml
kind: review_failed
change_id: <change_id>
exact_head: <exact reviewed head>
reason: <non-empty bounded reason>
```

For unavailable or invalid Delivery context, return:

```yaml
kind: dispatch_failure
change_id: <change_id>
failed_operation: show_finalization_context
reason: <non-empty bounded reason>
```

Do not expose raw diffs, target-update instructions, receipt calculations, or unrelated portfolio
state.

## Known Pitfalls

- **Wrong head:** observations and review must all bind to the current managed Change head, not the
  integration target or a stale branch ancestor.
- **Evidence overclaim:** passing checks prove only the declared observations at the exact Change
  head. They are not evidence that GitHub can merge the Change or that the merged result passes.
- **Dirty worktree:** commands that modify the managed worktree invalidate finalization; never discard
  edits whose ownership is uncertain.
- **Publication leap:** finalization queues the checkpoint; it does not publish, mark ready, or
  observe acceptance.
