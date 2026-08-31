---
name: w-delivery-attention-resolution
description: "Workflow: Diagnose and resolve one exact Delivery Change or Integration attention through an interactive user decision"
user-invocable: false
---

# Delivery Attention Resolution

Resolve one exact retained Delivery Change or Integration attention outside the portfolio worker
chain. This is an interactive operator session: inspect current evidence, explain materially
different remedies, ask the user to choose, and perform only a selected operation that current
Delivery authority permits. Local Integration execution and completion-proposal operations are
retired; completion is recorded only from a fresh provider observation bound to finalized Delivery
authority.

## Step 0 - Bind The Exact Current Attention

Parse the supplied value as exactly one lowercase-hyphenated `change_id` followed by one
64-character lowercase hexadecimal identity. A Change publication or acceptance attention uses its
`disposition_id`; a retained Integration repair attention uses its `attention_id`. Reject missing,
extra, or malformed identities.

If Delivery tools are deferred, run `tool_search` for
`OwlBear Delivery list_work_items list_retained_change_worktrees show_work_item show_integration_attention resolve_change_disposition defer_change resume_change abandon_change cleanup_abandoned_change_worktree cleanup_completed_change_worktree recover_change_worktree recover_publication_baseline reconcile_change_checkpoint mark_change_ready supersede_publication sync_change_with_target adopt_external_head promote_external_head recover_claim recover_integration_repair_claim observe_change_publication_checks observe_acceptance show_completed_change`.
For a Change attention, call `list_work_items` and require the Change publication card's
`action.attention_id` to equal the supplied disposition identity; use `show_work_item` for the
publication detail when needed. For an Integration attention, call
`show_integration_attention(change_id)` and require its change and attention identities to equal
the supplied values. An ordinary open and unmerged provider pull request is retry-safe waiting,
not an attention; report that state and stop without resolution. If no attention exists, its
identity differs, or Delivery reports that the retained condition is superseded, report the
current state and stop without mutation. Never substitute a newer attention silently.

Treat the returned code, heads, target, diagnostics, and retry condition as retained evidence, not
as permission to edit a worktree or target.

## Step 1 - Diagnose Current State Read-Only

Read the owning Delivery coordination and relevant repository state without mutation. Verify the
current source branch, reviewed boundary, Change finalization and publication identities, provider
pull-request state, Integration target, worktree existence, worktree branch and head, and staged,
unstaged, and untracked paths when they bear on the reported condition.
Inspect only enough diff, package, completed-history, or verification evidence to distinguish the
current cause and viable remedy classes.

Use structured Delivery operations for Delivery facts and structured Git commands for repository
facts. Do not run checkout, switch, reset, restore, clean, commit, merge, rebase, worktree removal,
reference updates, target updates, or another mutating command while diagnosing.

Classify the result as one of:

- `resolved-or-stale` - current state no longer supports the retained condition;
- `single-authorized-route` - one non-destructive existing Delivery operation can advance it;
- `provider-waiting` - the provider pull request is open and unmerged, so no attention resolution
  is required;
- `decision-required` - two or more materially different valid remedies remain;
- `authority-gap` - the selected remedy needs a Delivery-owned operation that does not exist;
- `unknown` - current evidence cannot responsibly identify the cause or remedy.

## Step 2 - Present One Decision

When a material choice remains, present exactly one decision before calling `askQuestions`:

```markdown
### Decision: <one precise Delivery resolution choice>

**Current condition:** <current evidence and whether retained evidence still matches>
**Why this blocks Integration:** <bounded causal explanation>
**Options:** <two to four genuine remedies, each with pros, cons, risks, confidence, and outcome>
**Recommendation:** <one evidence-based option and why>
**Confidence:** <calibrated confidence and remaining uncertainty>
```

Use `askQuestions` with those options and stop for the answer. Do not batch another decision, infer
approval from discussion, or turn a single responsible route into artificial alternatives.

For uncommitted work, distinguish at least preservation, adoption into reviewed Delivery work, and
intentional discard when each is genuinely viable. Explain exactly what evidence each option keeps
or loses. Never describe destructive loss as cleanup.

## Step 3 - Apply Only Existing Authority

After an explicit answer, re-read the exact attention and all preconditions used by the chosen
route. Abort if the attention, heads, target, worktree state, or relevant evidence changed.

Use only an existing operation whose contract owns the selected result:

- Required publication-check failure: when the Change publication diagnostics begin with
  `required-publication-check-failure`, treat the condition as provider-owned check evidence, not a
  supersession request. Re-observe the exact published head with
  `observe_change_publication_checks(change_id)`. If a provider-marked required check still has a
  terminal non-success conclusion, retain the exact attention and stop without resolution; Delivery
  never selects, dispatches, reruns, or classifies workflows. When the re-observation no longer
  reports a required failure, call `resolve_change_disposition(change_id, expected_disposition_id)`
  and re-read finalization and checkpoint authority before retrying `mark_change_ready(change_id)`.
  If the exact head changed, reconcile finalization first and hand the Change back to its owning
  finalization/review workflow; do not supersede the publication solely because a check failed.
- Change attention: use the exact disposition identity and call
  `resolve_change_disposition(change_id, expected_disposition_id)`. This clears the current Change
  attention and retained provider identity; it does not restore ready authority. For a closed,
  unmerged provider pull request, first reopen that exact pull request in GitHub, then resolve the
  attention, reconcile the current finalization/publication checkpoint with
  `reconcile_change_checkpoint(change_id)`, and call `mark_change_ready(change_id)` only after the
  reconciled publication is valid. Observe acceptance only after the reopened pull request is
  merged. An open, unmerged pull request needs no attention resolution; call
  `observe_acceptance(change_id)` only as a retry-safe waiting observation.
- User disposition: after the user explicitly selects pause or termination, call
  `defer_change(change_id, reason)` to retain the Change and its worktree, or
  `abandon_change(change_id, reason)` to terminate the uncompleted Change. Call
  `resume_change(change_id)` only for an exact currently deferred Change. Abandonment is
  irreversible and must not be inferred from an attention diagnosis.
- External Change head adoption: after the user explicitly selects adoption and the exact expected
  reviewed head and remote adopted head have been re-read, call
  `adopt_external_head(change_id, expected_head, adopted_head, operation_id)`. When the managed
  branch is at the reviewed head, Delivery fast-forwards it; when an intentional out-of-band push
  has already put the clean managed branch at the exact adopted head, Delivery verifies the remote
  tip and records observed provenance. Both paths preserve the prior reviewed boundary; adoption
  proves provenance but does not grant review authority. Before Builder acquisition, re-read the
  exact adopted receipt and call
  `promote_external_head(change_id, expected_head=adopted_head, operation_id)` to admit review
  authority for that exact head. For a completed adopted Change, hand off to the finalization
  workflow, which performs the finalization-bound promotion after exact review. Do not use target
  synchronization to advance an adopted head.
- Terminal worktree cleanup: after an exact abandoned Change is confirmed, re-read
  `list_retained_change_worktrees` or the Change publication detail and call
  `cleanup_abandoned_change_worktree(change_id)` only when Delivery reports cleanup eligibility.
  For a completed Change, require the exact `completion_id` from the current completion receipt and
  call `cleanup_completed_change_worktree(change_id, completion_id)`. A dirty, missing, ambiguous,
  locked, or head-mismatched worktree remains attention; preserve its content and do not substitute
  raw Git removal. Cleanup removes only the managed directory, preserves the Change branch, and is
  replay-safe through its durable receipt.
- Missing Change worktree recovery: after the current Change publication detail or retained-worktree
  projection reports a missing directory or registration, present one explicit user confirmation and
  re-read the exact `recovery_reviewed_head`. Call
  `recover_change_worktree(change_id, recovery_reviewed_head, confirmed_recovery=true)` only when the
  reviewed head is a valid exact lowercase 40-character commit identity and matches Delivery's
  retained authority. Recovery recreates only the canonical managed worktree from the existing
  `owlbear/change/<change-id>` branch and preserves that branch and reviewed boundary. Active writers,
  active publication leases, dirty or content-bearing unregistered directories, foreign registrations,
  branch/head mismatches, and other typed ownership attention remain blocked. Never force-remove a
  worktree, overwrite preserved content, or use raw Git as a recovery shortcut.
- Publication-baseline recovery: when the exact Change publication attention identifies
  `publication-baseline-unavailable`, re-read `show_work_item` and the current retained Change
  evidence. Present one explicit confirmation for the exact baseline commit; never derive it from the
  current target head or a merge base. Require exact lowercase 40-character identities for both
  `expected_change_head` and `publication_base_head`, and call
  `recover_publication_baseline(change_id, expected_change_head, publication_base_head, operation_id,
  confirmed_recovery=true)` only after the reviewed head, clean managed worktree, and idle custody
  preconditions are re-read. Recovery records immutable provenance and does not resolve the existing
  attention; re-read the exact disposition and resolve it separately before reconciling the pending
  checkpoint. If the baseline evidence or current head is missing or stale, report `authority-gap`.
- provider acceptance required: after re-reading the exact finalization, ready receipt, reconciled
  checkpoint, and publication evidence, call `observe_acceptance(change_id)` once. This operation
  reads the current provider pull request and creates the receipt-backed completion record only when
  repository, pull request, base branch, finalized head, merged state, merge commit, and merge time
  all match. It does not create a proposal, merge a pull request, move a target ref, or infer
  completion from local Git state;
- Design or admitted-authority revision: hand off with `/design <change_id>` and explain the exact
  revision required;
- reviewed merge conflict: report `authority-gap` unless the current context supplies an exact
  Integration repair claim for recovery; do not create a new claim, candidate, review, or admission;
- target-sync merge conflict: when the Change attention diagnostics identify a preserved target
  synchronization conflict, retain the managed worktree, `MERGE_HEAD`, and conflict paths and
  report `authority-gap` unless the current context supplies an exact Delivery-owned operation for
  conflict resolution, validation, and review. Do not resolve the generic Change disposition,
  retry synchronization, abort the merge, reset the worktree, or use raw Git as a substitute;
- target, publication, or finalization prerequisite: hand off to the owning Delivery workflow and
  report the exact missing authority rather than inventing a local Integration route;
- dirty Builder claim recovery: call the exact `recover_claim` operation with the supplied change,
  outcome, attempt, and claim identities. Delivery preserves uncommitted tracked, staged, deleted,
  renamed, and untracked non-ignored bytes in an isolated quarantine ref, verifies the evidence,
  resets and cleans the managed worktree without removing ignored environments, releases stale
  custody, and allows successor acquisition. Do not inspect, classify, adopt, discard, or commit
  dirty files on the user's behalf. If recovery returns `recovered`, report the quarantine evidence
  and continue the owning workflow. If it returns `attention`, report the machine-owned preservation
  or custody failure and its retry condition; do not turn it into a Git decision for the user.
- claim recovery: use the exact claim-bound recovery operation only when current context supplies
  its attempt and claim identities. A recovery result of `attention` is not recovery; report the
  retained claim, custody, and machine-owned retry condition without performing Git cleanup.
- retained Integration repair attention: preserve the existing
  `show_integration_attention(change_id)` and `recover_integration_repair_claim(change_id,
  attempt_id, claim_id)` route. Do not use Change disposition resolution for an Integration repair
  claim.

If preservation, adoption, discard, worktree recreation, package restoration, completed-history
repair, target correction, or verification-profile correction lacks a public Delivery operation,
return `authority-gap`. Name the missing operation and the evidence it must preserve; do not replace
it with raw Git or filesystem mutation.

Never overwrite the Integration target, force-update a reference, discard uncommitted work,
force-remove a worktree, hand-edit Delivery state, or bypass review and compare-and-swap boundaries.
Explicit user preference selects among admitted routes; it does not manufacture missing authority.

## Step 4 - Verify And Close

After any operation, re-read the Change publication Work Item or exact Integration attention, as
applicable. Report:

- prior attention identity and condition;
- selected route and operation actually performed;
- current attention or completion state;
- preserved evidence and any remaining authority gap;
- the exact next command only when another interactive workflow is required.

Do not claim resolution from a command exit alone. Resolution requires Delivery state to show the
attention cleared, superseded by a newly identified condition, or advanced through the selected
owned route.

## Known Pitfalls

- **Trusting copied prompt evidence:** always re-read current Delivery and repository state.
- **Treating user approval as Git authority:** use a Delivery-owned mutation or report an authority gap.
- **Retrying an operator condition:** generic retry text does not make an operator-required attention retryable.
- **Treating acceptance waiting as attention:** an open, unmerged pull request remains retry-safe
  waiting and must not freeze the Change or create a disposition.
- **Assuming resolution restores publication authority:** exact Change disposition resolution
  clears attention only; reconciliation and ready-marking are separate authority steps.
- **Choosing for the user:** preservation, adoption, and discard have materially different outcomes.
- **Resolving the wrong attention:** bind and revalidate the exact attention ID before every mutation.
