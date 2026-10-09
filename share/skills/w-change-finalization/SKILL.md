---
name: w-change-finalization
description: "Workflow: Prove and finalize one exact reviewed Change head"
user-invocable: false
---

# Change Finalization

Own one user-invoked finalization attempt for one named Delivery Change. The Delivery context is the
source of truth for the managed worktree, Change branch, exact reviewed Change head, and current
publication phase. Prove every criterion that carried evidence does not cover, obtain an independent review, and
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

For a user-invoked attempt, proceed only when the phase is `ready-for-finalization`,
`finalization-invalidated`, or `review-repair` and the context reports `ready_for_finalization`.
Normally its Change head equals its reviewed head. The engine may also admit a clean
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
Read `semantics` from the context and plan coverage before running proof: its `coverage` shows which
acceptance criteria carried task evidence already covers or waives. A `covered` or `waived` criterion
needs no new observation; each `missing`, `uncovered`, or `unknown` criterion needs exact-head
evidence. Choose its procedure from the criterion statement and the task `acceptance_observations`
and `proof_boundaries` in `semantics.task_authority`. Capture schema-2 `DeliveryObservation`s
for the exact `change_head` only for criteria that are not yet covered; when carried evidence covers
every criterion, no new observation is required. Each observation names the exact `procedure`, a typed
`result` (a `command` result records its real `exit_status`; Delivery derives the verdict), the
`covers` criterion IDs and versions from `semantics`, the observer identity, and a timezone-aware
observation time. Different checks may use different commands, tools, or evidence types; there is no
target-bound profile or required step list. A failed check, dirty worktree, or changed head produces
no finalization request. Do not mutate target refs, create another worktree, or author evidence for a
different commit.
Submit only satisfying records: a `passed` or `expected-negative` result, or an applicable waiver;
never a `missing` or failed record. When no procedure available here can observe an open criterion,
stop before review: report `maintained-check-unavailable` with `checks_state: not-run` (Step 2a) and
return `proof_failed`. Never cover it with a check that does not observe it. A failed check is
`maintained-check-failed` with `checks_state: failed`.
`semantics.confirmations` lists every waiver or person-only check request the user answered in
Cockpit. Submit a `waived` or `human-confirmed` record only when its `request_id` cites one of them:
its `outcome_id` owns every criterion the record `covers`, those criteria and versions are in its
`scope.acceptance`, the record's `procedure` equals `scope.procedure`, and its `decision` is `waive`
for a waiver or `passed` for a passed `human-confirmed` assessment. Never invent or answer such a
request yourself; the `answer` tool refuses it. When `semantics_refusal` is set, the context is withheld
as a whole; stop before any proof and never request, reconstruct, or review a partial context. Report
`independent-review-unavailable` with `checks_state: not-run` (Step 2a) and return `review_failed`;
for `finalization-context-oversized` the remedy is a requirement change or split, not a retry.
When every new observation passes, call `derive_evidence_receipts` once with those `DeliveryObservation`
values in their final order (skip the call when there is none) and keep the returned receipts unchanged;
they carry the `observation_id`s the review must cite. Never compute receipts or IDs yourself.

## Step 2a - Retain A Trusted Failure

When a trusted current context reaches a failed custody preflight, maintained check, independent
review, or a maintained proof procedure that changed the managed worktree, call
`report_finalization_failure` with only its registered structural fields: the current
contract and frontier digests, candidate and reviewed heads, observed diagnostic sequence, stable
attempt key, category, registered code, checks state, and any category-allowed workspace fingerprint
or dirty paths. For `category: proof-mutation`, use only the registered
`proof-mutated-worktree` code, the maintained `procedure_id`, distinct
`proof_fingerprint_before`/`proof_fingerprint_after` values, and the changed relative paths; do not
report a zero exit as a pass. Under an issued attempt the stable attempt key is exactly `attempt.writer.attempt_id`;
any other value is rejected as a diagnostic conflict. Do not include commands, logs, URLs, summaries,
exit details, observer identities, or repair instructions. When `report_finalization_failure` returns
a stored `FinalizationReport`, copy its actual `report_id`, `request.code`, and
`request.checks_state` unchanged into the bounded failure result. Under an issued launch, also copy
`operation_id` exactly from `attempt.writer.attempt_id`; never mint or derive either identity. A
report is diagnostic history, not proof, a custody repair, a claim transition, successful
finalization, or evidence that the Finalizer process and its descendants have stopped. A recorded
report for an issued attempt key retains that attempt's custody: the same attempt cannot then
finalize, and supported recovery is not part of this workflow. If the reporter returns a
`DeliveryReadiness`, fails, or cannot access the report store, there is no stored report identity,
code, or checks state to return: omit those fields and never synthesize them. The issued
`operation_id` may still be returned; without the actual `report_id`, Orchestrator cannot settle and
must retain custody as unknown. If context is untrusted or the report store rejects the basis, return
the bounded failure without inventing a report identity or calling `finalize_change`.

When Delivery settles a lost or user-released Finalizer attempt that produced no report, it may author
category `worker-ended`, code `finalizer-ended-without-report`, and `checks_state: unknown`. This
records that no result arrived; it is not an observation, proof, or finalization receipt. A later
Finalizer attempt requires fresh exact-head checks and independent review and does not reset the
Change's original attempt budget.

## Step 3 - Obtain Independent Exact-Commit Review

Dispatch `build-reviewer` with `review_mode: finalization`, the complete fresh context including
`semantics` with its `basis_digest` and `diff_base`, the exact Change head, and the final ordered
observation receipts with their `observation_id`s (none when carried evidence covers every
criterion). The finalization diff boundary is `diff_base..change_head`. Require the reviewer to
independently resolve and inspect the exact commit with read-only Git. Accept only a response with:

- `review_mode: finalization`;
- the exact reviewed commit equal to `change_head`;
- `basis_digest` equal to `semantics.basis_digest`;
- `observation_ids` equal to the submitted receipts' IDs in submission order;
- `disposition: pass`;
- `finding_boundary: none`;
- non-empty source-grounded evidence; and
- reviewer identity different from the finalizer identity.

A finding, stale head, malformed response, or unavailable reviewer produces no finalization request.
Any change to the observation set after review requires a fresh review. A finding whose only evidence
is that carried evidence for named criteria does not apply to the assembled head permits one fresh
exact-head observation of those criteria and a fresh review; it is the only reason to exercise a
covered criterion again.
For a trusted independent-review failure, retain the registered `independent-review` diagnostic
(`independent-review-failed` for a finding, `independent-review-unavailable` for an unavailable
reviewer or malformed response) before returning the review failure; unavailable context or report
storage remains a bounded failure without a fabricated report identity.
Do not repair reviewer findings inside this workflow and do not turn reviewer prose into a lifecycle
transition.

Validate the optional `memory_candidate` against `h-memory-structure`. When it qualifies, call
`save_memory` with the reviewer-provided `source_agent` and no scope; discard malformed or low-signal
candidates without repair. Memory handling must not change the review or Delivery result.

## Step 4 - Construct Exact Evidence

Only after observations and review pass, construct values from Delivery's receipts:

- the observation receipts returned in Step 2 and reviewed in Step 3, unchanged and in the reviewed
  order, each from the exact `procedure`, its typed `result`, the `covers` criterion references, and
  the exact Change head;
- one review receipt returned by `derive_evidence_receipts` for a `DeliveryReview` with
  `review_mode: finalization`, the `basis_digest` from `semantics`, the ordered `observation_ids` of
  the submitted receipts (`[]` when there is none), the exact reviewer evidence, the finalizer as
  `author_id`, and the independent reviewer as `reviewer_id`; send only the review in that call;
- one `FinalizeDeliveryChange` containing the operation ID, exact head, canonical observations (none
  when carried evidence covers every criterion), and canonical review.

Under an issued attempt, the operation ID is exactly `attempt.writer.attempt_id` and the exact head
is exactly `attempt.exact_head`; every observation binds that same operation ID and head.

Use timezone-aware timestamps and pass the returned receipts unchanged. Never calculate, copy, or
invent observation or review IDs. Never use free-form evidence to replace the typed observations or
exact reviewer response.

## Step 5 - Re-check And Finalize

Call `show_finalization_context` again immediately before mutation. Re-read the managed worktree's
branch, exact `HEAD`, and clean state. Require the second context to preserve the Change ID, branch,
worktree, Change head, and reviewed head used by the observations and review. Discard the request if
any identity, head, or cleanliness value changed.

Call `finalize_change` once with the unchanged Change ID and the typed `FinalizeDeliveryChange`. Treat
its returned `DeliveryFinalizationReceipt` as the only successful finalization result. A refusal with
`ERR_DELIVERY_ACCEPTANCE_EVIDENCE` wrote nothing; its `gaps` name the criteria. Report a gap whose
reason starts with `review-` or `finalization-` as `independent-review-unavailable` and return
`review_failed`; report any other gap as `maintained-check-unavailable` and return `proof_failed`.
Never resubmit an altered request in the same attempt. The `finalize_change` call is the
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
operation_id: <exact attempt.writer.attempt_id; only under an issued launch>
report_id: <actual stored FinalizationReport.report_id; only when one was returned>
code: <actual stored FinalizationReport.request.code; only when one was returned>
checks_state: <actual stored FinalizationReport.request.checks_state; only when one was returned>
```

For an independent review failure, return:

```yaml
kind: review_failed
change_id: <change_id>
exact_head: <exact reviewed head>
reason: <non-empty bounded reason>
operation_id: <exact attempt.writer.attempt_id; only under an issued launch>
report_id: <actual stored FinalizationReport.report_id; only when one was returned>
code: <actual stored FinalizationReport.request.code; only when one was returned>
checks_state: <actual stored FinalizationReport.request.checks_state; only when one was returned>
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
