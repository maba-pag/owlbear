---
name: w-orchestration
description: "Workflow: Acquire Delivery work, dispatch bounded workers, and forward their transitions"
user-invocable: false
---

# Delivery Orchestration

Run the portfolio until acquisition is quiescent or bounded attention requires a user/operator.
Kanban owns readiness, capacity, claims, identities, reviewer policy, writer custody, transitions,
and Integration. Orchestrator performs only the mechanical dispatch loop around that authority.

## Step 1 - Acquire One Current Batch

If target tools are deferred, load them once with `tool_search` using:

`OwlBear Kanban target portfolio list_work_items acquire_frontier_work transition_delivery recover_claim integrate_ready_change`

Call `list_work_items` only for bounded portfolio reporting. Call `acquire_frontier_work` once for the
current cycle. Its `DeliveryAcquisitionResult` is the sole source of launch order,
`integration_ready_change_ids`, and acquisition failures. Do not filter for capacity, infer
readiness, create identities, or reserve writer custody.

## Step 2 - Dispatch Or Recover Each Launch

Process `launch_packages` in returned order. For worker role `planner` or `builder`, dispatch exactly
`launch.policy.worker_agent` using `launch.policy.worker_model` and pass only the serialized
`DeliveryLaunchPackage`. Do not substitute a role, model, reviewer, worktree, branch, or source head.

The current public surface has no Assembly context or publication operation. For worker role
`assembly-reviewer`, call `recover_claim` immediately with the launch's exact `change_id`,
`outcome_id`, `claim.attempt_id`, and `claim.claim_id`. Report the returned recovery status or
attention and stop processing that affected change. Do not dispatch Build Reviewer, inspect
composition, construct a transition, or leave the unsupported claim silently active.

If Planner or Builder dispatch fails before returning a structurally valid worker result, use that
same exact `recover_claim` request. Recovery attention remains runtime-owned evidence; report it
without interpreting Git, liveness, or custody. An acquisition failure carrying attempt and claim
IDs uses the same route. A failure without claim IDs is reported as bounded acquisition attention
and is not recoverable by Orchestrator.

## Step 3 - Forward One Worker Transition

Require the worker result to be one `DeliveryTransition` mapping. Validate only identity binding:

- `outcome_id` and `claim_id` equal the launch values;
- any transition `attempt_id` equals `launch.claim.attempt_id`;
- any nested output uses the launch claim ID.

Do not select, rewrite, enrich, or reconstruct action, output, result, request, reason, evidence, or
commit fields. Call `transition_delivery` with outer `change_id=launch.change_id` and the returned
transition as `request` byte-for-structure unchanged. A worker-owned `block`, `retry`, or `return`
is forwarded normally and must not be recovered.

An identity mismatch or malformed result is a failed dispatch result: publish no substitute and use
the exact Step 2 recovery route for the still-active claim.

## Step 4 - Integrate Only Acquisition-Provided IDs

For each `integration_ready_change_id` in returned order, call `integrate_ready_change(change_id)`.
Report its completion or typed Integration attention unchanged. Never discover Integration
candidates from work-item stages, worker prose, branch state, or cached results.

## Step 5 - Refresh

Finish the current acquired batch, discard it, and call `acquire_frontier_work` again. Continue
independent changes when one outcome returns or blocks. Stop when both launch packages and
Integration-ready IDs are empty, or when a fail-closed diagnostic requires user/operator action.

## Output

Report forwarded transition identities, Integration completion or attention, exact recovery results,
unclaimed acquisition failures, and cycle count. Do not translate those typed results into invented
completion or scheduling state.

## Known Pitfalls

- **Local scheduling:** acquisition already owns stable readiness and capacity.
- **Identity generation:** launch claims and role policies are runtime output, not Orchestrator input.
- **Transition interpretation:** worker action and payload remain unchanged.
- **Fake Assembly support:** unsupported Assembly claims are recovered exactly, never sent to Builder
  or Build Reviewer.
- **Integration discovery:** only acquisition-provided IDs authorize the Integration call.
