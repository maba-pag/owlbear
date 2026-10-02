---
description: "Release one stopped Delivery worker after Delivery verifies a quiet worktree"
agent: orchestrator
tools:
  - owlbear-delivery/get_change
  - owlbear-delivery/release_stuck_worker
---
Release a stopped Delivery worker for ${input:change_id:Native Change ID}

Read the named Change once with `get_change`. Identify one exact active outcome claim in
`unresolved_outcomes` or the active Finalizer writer attempt in `finalization_attempt`. Copy
`outcome_id` (use `null` for Finalizer), `attempt_id`, and `claim_id` exactly from that view. Do not infer
identity from this conversation or unrelated diagnostics. If the Change is unavailable or has no
matching active claim, report the returned state and stop.

If the user has not already stated that this specific worker chat/window was stopped, ask them to
confirm that it was stopped. Treat this as user intent for the release decision, not permission to
operate the process. If they do not confirm, stop without a mutation.

After confirmation, call `release_stuck_worker` exactly once with the Change ID and the exact claim
identity from `get_change`. Report the returned result unchanged. If Delivery returns
`ERR_DELIVERY_WORKER_ACTIVE`, include its retry time and stop; do not retry, reacquire, or dispatch a
replacement in this cycle. Delivery alone decides whether the worktree has been quiet long enough.

Do not use terminal, Git, process-control, or edit tools. Do not settle through
`settle_worker_invocation`, call `recover_claim`, or modify the worktree.
