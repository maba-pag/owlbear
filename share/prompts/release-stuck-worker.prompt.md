---
description: "Release one stopped Delivery worker after Delivery verifies its worktree and process guard"
agent: orchestrator
tools:
  - owlbear-delivery/get_change
  - owlbear-delivery/release_stuck_worker
---
Release a stopped Delivery worker for ${input:change_id:Native Change ID}

Read the named Change once with `get_change`. Identify one exact active Planner or Builder claim in
`unresolved_outcomes`, or the active Finalizer writer attempt in `finalization_attempt`. Use the
outcome card's readiness or the Finalizer readiness. If its `reason_code` is `worker-stall-wait`, do
not ask or release; report the wait and leave it for Delivery's later automatic settlement. For a
`running` claim, copy `outcome_id` (use `null` for Finalizer), `attempt_id`, and `claim_id` exactly
from that view. Do not infer identity from this conversation or unrelated diagnostics. If the Change
is unavailable, the claim is no longer active, or readiness is not `running`, report the state and
stop.

If the user has not already stated that this specific worker chat/window was stopped, ask them to
confirm that it was stopped. Treat this as user intent for the release decision, not permission to
operate the process. If they do not confirm, stop without a mutation.

After confirmation, call `release_stuck_worker` exactly once with the Change ID and the exact claim
identity from `get_change`. Report the returned result unchanged. If Delivery returns
`ERR_DELIVERY_WORKER_ACTIVE`, include its retry time or process details and stop; do not retry,
reacquire, or dispatch a replacement in this cycle. Delivery requires no worktree writes for 30
seconds and no live same-user process with a cwd or open file under the managed worktree or Git admin
directory. Terminal-attached idle shells whose only link is the worktree cwd and which have no live
child are ignored; open files still block. Restarting the MCP server while the issuing VS Code window remains alive
does not prove that the worker stopped.

Do not use terminal, Git, process-control, or edit tools. Do not settle through
`settle_worker_invocation`, call `recover_claim`, or modify the worktree.
