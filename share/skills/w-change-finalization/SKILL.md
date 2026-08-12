---
name: w-change-finalization
description: "Workflow: Prove and finalize one exact reviewed Change head"
user-invocable: false
---

# Change Finalization

Own one user-invoked finalization attempt for one named Delivery Change. The Delivery context is the
source of truth for the managed worktree, Change branch, exact target commit, target-governed
verification profile, and current publication phase. Produce exact evidence, obtain an independent
review, and call only the finalization operation.

## Step 0 - Resolve Current Authority

Require one `change_id` from the prompt and call `show_finalization_context` before inspecting or
running proof. Require the returned context to contain the supplied Change identity and retain its
exact values for the attempt:

- managed `branch` and `worktree_path`;
- current `change_head` and `reviewed_change_head`;
- engine-resolved `target_branch` and `target_head`;
- explicit `target_ref`, `target_provenance`, and local `target_observed_at`;
- target-only `profile_digest`, parsed `profile` steps, and proof scope `change-head-profile`;
- `publication_phase`.

Proceed only when the phase is `ready-for-finalization` or `finalization-invalidated`. A missing or
invalid target profile is a Delivery context failure. Do not read a profile from the Change head,
compare it to the target profile, or invoke the legacy Integration verifier.

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
- the context target and Change identities remain unchanged.

The managed Change worktree is the only checkout permitted. Never create a proof worktree, enter the
user's primary checkout, fetch, push, update a target ref, reset, clean, checkout, restore, rebase,
merge, or alter Delivery files. A custody mismatch or dirty worktree is a bounded finalization
failure; do not repair it by discarding state.

## Step 2 - Run Target-Governed Proof

Call `run_finalization_verification` with the unchanged Change ID and retain its engine-produced
receipt. This is the only permitted profile executor. Require `status: passed`, `clean: true`, the
exact Change and target identities from Step 0, `target_provenance: cached-remote-tracking`, the
replayed `target_observed_at`, `proof_scope: change-head-profile`, `observed_head` equal to `change_head`, every declared step ID exactly
once and in order, and every step status `passed`. A failed, timed-out, execution-error, head-drift,
target-changed, or worktree-mutation receipt produces no finalization request. This proof executes the
target-declared profile at the Change head; it does not prove a merge result, conflict absence, or
current GitHub state. Do not execute profile commands directly, create a proof worktree, or construct
a client-authored verification receipt.

## Step 3 - Obtain Independent Exact-Commit Review

Dispatch `build-reviewer` with `review_mode: finalization`, the complete fresh context, the exact
Change head, the target/profile identities, the persisted proof receipt, and the finalization diff
boundary. Require the reviewer to independently resolve and inspect the exact commit with read-only
Git. Accept only a response with:

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

Only after proof and review pass, use the core Delivery models to construct values in memory:

- one `DeliveryObservationReceipt.create(DeliveryObservation(...))` for each passing engine proof
  step, including the engine `step_id`, exact argv joined with spaces, `exit:0`, and the exact Change
  head;
- one `DeliveryReviewReceipt.create(DeliveryReview(...))` using the exact reviewer evidence, the
  finalizer as `author_id`, and the independent reviewer as `reviewer_id`;
- one `FinalizeDeliveryChange` containing the operation ID, exact head, proof `run_id`, target ref,
  target head, `cached-remote-tracking` provenance, `change-head-profile` scope, the proof's observation time, profile digest,
  canonical observations, and canonical review.

Use a timezone-aware timestamp and serialize model output with `model_dump(mode="json")`. Never
calculate, copy, or invent observation or review IDs. Never use free-form evidence to replace the
profile-step observations or exact reviewer response.

## Step 5 - Re-check And Finalize

Call `show_finalization_context` again immediately before mutation. Re-read the managed worktree's
branch, exact `HEAD`, and clean state. Require the second context to preserve the Change ID, branch,
worktree, reviewed head, target branch, target head, and profile digest used by proof and review.
Discard the request if any identity, head, profile, or cleanliness value changed.

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

For a bounded proof or custody failure, return:

```yaml
kind: proof_failed
change_id: <change_id>
failed_operation: <preflight or profile step>
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

- **Wrong profile source:** finalization context is governed by the engine-selected target commit;
  Change-head profile bytes are not finalization authority.
- **Cached target freshness:** the target identity is read from the local remote-tracking ref without
  fetch; `target_observed_at` records local observation time, not GitHub freshness. A changed target
  identity requires a new proof.
- **Verifier reuse:** legacy Integration verification uses an extra proof worktree and candidate
  profile equality; finalization does neither.
- **Client-side proof:** profile execution or verification receipts authored by the finalizer are
  invalid; use `run_finalization_verification` and bind its persisted run ID.
- **Merge-safety overclaim:** a passing profile proves only the declared steps at the exact Change
  head. It is not evidence that GitHub can merge the Change or that the merged result passes.
- **Dirty proof:** commands that modify the managed worktree invalidate finalization; never discard
  edits whose ownership is uncertain.
- **Publication leap:** finalization queues the checkpoint; it does not publish, mark ready, or
  observe acceptance.
