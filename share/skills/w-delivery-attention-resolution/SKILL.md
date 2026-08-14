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
`OwlBear Delivery list_work_items list_retained_change_worktrees show_work_item show_integration_attention resolve_change_disposition defer_change resume_change abandon_change cleanup_abandoned_change_worktree cleanup_completed_change_worktree recover_change_worktree reconcile_change_checkpoint mark_change_ready supersede_publication sync_change_with_target recover_claim recover_integration_repair_claim observe_change_publication_checks observe_acceptance show_completed_change`.
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
- provider acceptance required: after re-reading the exact finalization, ready receipt, reconciled
  checkpoint, and publication evidence, call `observe_acceptance(change_id)` once. This operation
  reads the current provider pull request and creates the receipt-backed completion record only when
  repository, pull request, base branch, finalized head, merged state, merge commit, and merge time
  all match. It does not create a proposal, merge a pull request, move a target ref, or infer
  completion from local Git state;
- Design or admitted-authority revision: hand off with `/design <change_id>` and explain the exact
  revision required;
- reviewed merge conflict: report `authority-gap` unless the current context supplies an exact
  legacy repair claim for recovery; do not create a new claim, candidate, review, or admission;
- target-sync merge conflict: when the Change attention diagnostics identify a preserved target
  synchronization conflict, retain the managed worktree, `MERGE_HEAD`, and conflict paths and
  report `authority-gap` unless the current context supplies an exact Delivery-owned operation for
  conflict resolution, validation, and review. Do not resolve the generic Change disposition,
  retry synchronization, abort the merge, reset the worktree, or use raw Git as a substitute;
- target, publication, or finalization prerequisite: hand off to the owning Delivery workflow and
  report the exact missing authority rather than inventing a local Integration route;
- claim recovery: use the exact claim-bound recovery operation only when current context supplies
  its attempt and claim identities.
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
