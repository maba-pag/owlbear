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

When the entry supplies a serialized `DeliveryFinalizationLaunch`, apply Step 0a before this step's
readiness gate. An issued attempt already holds durable finalizer custody, so the idle-readiness gate
below describes a user-invoked attempt only.

Require one `change_id` from the prompt and call `show_finalization_context` before inspecting or
running proof. Require the returned context to contain the supplied Change identity and retain its
exact values for the attempt:

- managed `branch` and `worktree_path`;
- current `change_head` and `reviewed_change_head`;
- `publication_phase`.

For a user-invoked attempt, proceed only when the phase is `ready-for-finalization` or
`finalization-invalidated` and the context reports `ready_for_finalization`. Normally its Change head
equals its reviewed head. The engine may also admit a clean
local descendant for finalization; the Change head is the exact head that observations and review
must bind. After an engine-validated external head adoption, the Change head may differ and remains
the exact head that observations and review must bind. Adoption is provenance only; Builder
acquisition requires a separate `promote_external_head` admission. For a completed adopted Change,
this finalization workflow owns the finalization-bound promotion after the exact review is durable.
Do not resolve a target ref, read a verification profile, or invoke a separate finalization proof
executor.

If `finalization_id` is present, first call `reconcile_finalization_head(change_id)` and re-read the
context. Treat the Change as already finalized when `finalized_head` equals the current `change_head`
and the reviewed head also equals it. If the finalized head differs from the current Change head,
return `dispatch_failure`; head-drift reconciliation belongs to its owning Delivery operation.

## Step 0a - Bind One Issued Finalization Attempt

A continuation entry may dispatch this role with one serialized `DeliveryFinalizationLaunch` instead
of a bare Change ID. That launch is already durable finalizer custody: do not acquire, re-acquire,
release, recover, or transition it, and do not run a second attempt beside it.

Bind its `attempt` as the identity of this attempt:

- `attempt.writer.attempt_id` is the finalization `operation_id` in Step 4 and the `attempt_key` in
  Step 2a. Never mint, derive, or substitute either value.
- `attempt.exact_head` is the exact head that custody, observations, and review must bind.
- `attempt.contract_digest` and `attempt.frontier_digest` must still match current authority; the
  engine rejects a mismatched attempt as a stale action selection rather than finalizing it.

Retain the launch `context` as the pre-acquisition observation. It is the ready-phase evidence for
this attempt, because the engine required a ready context before issuing the attempt and acquiring
custody. Still call `show_finalization_context` yourself and require the fresh context to preserve the
launch context's Change identity, branch, and worktree, its `change_head` to equal
`attempt.exact_head`, and its `readiness.basis` contract and frontier digests to equal
`attempt.contract_digest` and `attempt.frontier_digest`. Any difference in those exact values is a
bounded failure, not a reason to re-bind the attempt to a newer head.

Do not apply Step 0's idle-readiness gate to that fresh read. Under acquired custody the fresh context
reports `ready_for_finalization: false` with an `active-custody` diagnostic because this attempt holds
the custody; treat exactly that self-owned state as expected and never as a stale attempt. Any other
blocking phase or readiness diagnostic is still a bounded failure.

An issued attempt bypasses nothing else. Custody proof in Step 1, exact-head observations in Step 2,
independent review in Step 3, and evidence construction in Step 4 remain required exactly as for a
user-invoked attempt, and a bounded failure reports `attempt.writer.attempt_id` as its attempt key -
never a minted or derived one.

Without an issued launch, the entry is a user-invoked attempt: keep using the supplied Change ID, its
fresh context, Step 0's readiness gate, and this workflow's own operation ID.

## Step 1 - Establish Exact Managed Custody

Use read-only Git commands against the returned `worktree_path` and require:

- the path resolves to the managed worktree;
- `branch --show-current` equals the returned `branch`;
- worktree `HEAD` equals `change_head`;
- when `change_head` differs from `reviewed_change_head`, the engine has authorized the exact clean
  local descendant or adopted head for this finalization attempt;
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

## Step 2a - Retain A Trusted Failure

When a trusted current context reaches a failed custody preflight, maintained check, or independent
review, call `report_finalization_failure` with only its registered structural fields: the current
contract and frontier digests, candidate and reviewed heads, observed diagnostic sequence, stable
attempt key, category, registered code, checks state, and any category-allowed workspace fingerprint
or dirty paths. Under an issued attempt the stable attempt key is exactly `attempt.writer.attempt_id`;
any other value is rejected as a diagnostic conflict. Do not include commands, logs, URLs, summaries,
exit details, observer identities, or repair instructions. Preserve the returned report identity and
checks state in the bounded failure result; a report is diagnostic history, not proof, a custody
repair, a claim transition, or a successful finalization. A recorded report for an issued attempt key
retains that attempt's custody: the same attempt cannot then finalize, and supported recovery is not
part of this workflow. If context is untrusted or the report store rejects the basis, return the
bounded failure without inventing a report identity or calling `finalize_change`.

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
For a trusted independent-review failure, retain the registered `independent-review` diagnostic
before returning the review failure; unavailable context or report storage remains a bounded failure
without a fabricated report identity.
Do not repair reviewer findings inside this workflow and do not turn reviewer prose into a lifecycle
transition.

Validate the optional `memory_candidate` against `h-memory-structure`. When it qualifies, call
`save_memory` with the reviewer-provided `source_agent` and no scope; discard malformed or low-signal
candidates without repair. Memory handling must not change the review or Delivery result.

## Step 4 - Construct Exact Evidence

Only after observations and review pass, use the core Delivery models to construct values in memory:

- one `DeliveryObservationReceipt.create(DeliveryObservation(...))` for each relevant passing check,
  including the command or procedure, its exit status or artifact locator, and the exact Change head;
- one `DeliveryReviewReceipt.create(DeliveryReview(...))` using the exact reviewer evidence, the
  finalizer as `author_id`, and the independent reviewer as `reviewer_id`;
- one `FinalizeDeliveryChange` containing the operation ID, exact head, canonical observations, and
  canonical review.

Under an issued attempt, the operation ID is exactly `attempt.writer.attempt_id` and the exact head
is exactly `attempt.exact_head`; every observation binds that same operation ID and head.

Use a timezone-aware timestamp and serialize model output with `model_dump(mode="json")`. Never
calculate, copy, or invent observation or review IDs. Never use free-form evidence to replace the
typed observations or exact reviewer response.

## Step 5 - Re-check And Finalize

Call `show_finalization_context` again immediately before mutation. Re-read the managed worktree's
branch, exact `HEAD`, and clean state. Require the second context to preserve the Change ID, branch,
worktree, Change head, and reviewed head used by the observations and review. Discard the request if
any identity, head, or cleanliness value changed.

Call `finalize_change` once with the unchanged Change ID and the typed `FinalizeDeliveryChange`. Treat
its returned `DeliveryFinalizationReceipt` as the only successful finalization result. It is also the
only mutation this workflow performs for an issued attempt: never submit a result, forward a
transition, or release custody beside it. Do not call `promote_external_head` separately from this
workflow; finalization owns that promotion when the exact head is an adopted completed head. Do not
call checkpoint reconciliation, mark-ready, acceptance observation, Integration, repair, or any
target mutation operation from this workflow.

## Optional Process Observation

After exact-head review, load `h-process-observations` only when the result exposes a documented
trigger. Preserve any sidecar outside the finalization request and receipts; it records process
learning and has no authority over the Change head, publication, or acceptance.

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
