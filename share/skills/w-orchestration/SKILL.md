---
name: w-orchestration
description: "Workflow: Acquire Delivery work, dispatch bounded workers, and forward their transitions"
user-invocable: false
---

# Delivery Orchestration

Run the portfolio until acquisition is quiescent or bounded attention requires a user/operator.
Delivery owns readiness, capacity, claims, identities, reviewer policy, writer custody, transitions,
provider-observed acceptance, and retained Integration attention. Orchestrator performs only the mechanical
dispatch loop around that authority.

## Step 1 - Acquire One Current Batch

If target tools are deferred, load them once with `tool_search` using:

`OwlBear Delivery target portfolio list_work_items acquire_frontier_work transition_delivery recover_claim recover_integration_repair_claim`

Before calling `acquire_frontier_work`, require callable bindings for `transition_delivery`,
`recover_claim`, and `recover_integration_repair_claim`. Run one focused `tool_search` for each
missing operation. If any binding remains unavailable or its focused search returns a tool error,
report the exact missing operation and end the session without acquisition. Transition and recovery
are required dispatch safety authority, not optional operations to discover after a claim has been
acquired.

Call `list_work_items` only for bounded portfolio reporting. Call `acquire_frontier_work` once for the
current cycle. Its `DeliveryAcquisitionResult` is the sole source of task launch order,
typed `integration_attention`, and acquisition failures. Active claims remain occupied until the
exact recovery operation completes. `recover_claim` automatically preserves dirty Builder bytes in
an isolated quarantine ref, cleans the managed worktree, releases stale custody, and permits the
next acquisition; it returns attention only when preservation or exact custody verification fails.
Report the typed result unchanged. Do not filter for capacity, infer readiness, create identities,
or reserve writer custody.

## Step 2 - Dispatch Or Recover Each Launch

Process `launch_packages` in returned order. For worker role `planner` or `builder`, dispatch exactly
`launch.policy.worker_agent` and pass only the serialized `DeliveryLaunchPackage`. The selected
agent's frontmatter owns its model. Do not substitute a role, agent, reviewer, worktree, branch, or
source head.

If Builder returns `kind: dispatch_failure`, require its change, outcome, attempt, and claim IDs to
equal the launch and require non-empty `failed_operation` and `reason`. Use that same exact
`recover_claim` request. Never forward this result to `transition_delivery` or translate it into a
worker lifecycle action.

If Planner or Builder dispatch otherwise fails before returning a structurally valid worker result,
use that same exact `recover_claim` request. Recovery attention remains runtime-owned evidence;
report it without interpreting Git, liveness, or custody. An acquisition failure carrying attempt
and claim IDs uses the same route. A failure without claim IDs is reported as bounded acquisition
attention and is not recoverable by Orchestrator. Do not report a recovery operation as unavailable
unless its Step 1 focused search or an exact recovery call returned a recorded tool error.

When exact recovery returns `recovered`, discard the failed launch and continue with the next
acquisition cycle; do not inspect or classify the quarantined files. When it returns `attention`,
report the returned reason and retry condition as machine-owned evidence. Do not ask the user to
choose which dirty files to keep, discard, adopt, or commit.

## Step 3 - Forward One Worker Transition

Require the worker result to be one `DeliveryTransition` mapping. Validate only identity binding:

- `outcome_id` and `claim_id` equal the launch values;
- any transition `attempt_id` equals `launch.claim.attempt_id`;
- any nested output uses the launch claim ID.

Do not select, rewrite, enrich, or reconstruct action, output, result, request, reason, evidence, or
commit fields. Call `transition_delivery` with outer `change_id=launch.change_id` and the returned
transition as `request` byte-for-structure unchanged. A worker-owned `block`, `retry`, or `return`
is forwarded normally and must not be recovered.

Immediately before forwarding, if the `transition_delivery` binding is unavailable, run one focused
`tool_search` for that exact operation. If it remains unavailable or the search returns a tool
error, call `recover_claim` with the launch's exact change, outcome, attempt, and claim IDs, report
the routing failure and recovery result, and end the session after the current acquired batch. Do
not redispatch Planner, Builder, or another agent to echo, relay, reconstruct, or apply a transition.

An identity mismatch or malformed result is a failed dispatch result: publish no substitute and use
the exact Step 2 recovery route for the still-active claim. A rejected `transition_delivery` call
for worker-output schema validation is also a malformed dispatch result and requires that recovery
before session completion.

## Step 4 - Preserve Typed Integration Attention

Do not call a local Integration or completion operation from the orchestration loop. Acquisition
returns `integration_attention` as retained evidence for the owning attention or provider-acceptance
workflow. A legacy repair condition is visibility only: do not create a new repair claim, dispatch a
repair worker, or synthesize a repair result. Never infer completion from work-item stages, worker
prose, branch state, or cached results.

Continue independent task work when possible, then report the exact attention as bounded action at
the end of the cycle.

## Step 5 - Run Periodic Housekeeping

Count completed acquisition cycles from 1 within this orchestrator invocation. A completed cycle is
a non-empty acquisition batch whose launches have been handled and whose worker transitions or exact
recovery results have been recorded. Do not count an empty acquisition, an acquisition failure, or
an interrupted batch. Dispatch `memory-curator` after cycle 3, then after cycles 13, 23, and so on
every tenth completed cycle thereafter, with exactly `Curate: Periodic curation`. This is
non-Delivery housekeeping, not a launch package: provide no task, Change, outcome, attempt, or claim
identity; do not call `transition_delivery` or `recover_claim` for it.

The curator's successful Channel A result must use the `w-mem-curation` form
`DONE | {P} promoted, {D} pruned`, adding reportable pending conflict or uncertainty IDs when
present. If the dispatch binding is unavailable, the `runSubagent` invocation itself returns a
tool-layer error, or capability dispatch fails before a child result exists, record a fail-closed
housekeeping failure, report it separately, and stop after the current batch; do not use Delivery
recovery. If the invocation completes but returns no result, a result without the curator's Channel A
verdict, or a child report of its own internal failure, record a malformed housekeeping result, do
not retry it, and continue acquisition. A scheduled attempt consumes its cadence slot regardless of
its result.

## Step 6 - Refresh

Finish the current acquired batch, discard it, and call `acquire_frontier_work` again. Continue
independent changes when one outcome returns or blocks. Stop when launch packages are empty, or when
a fail-closed diagnostic requires user/operator action.
Non-empty `integration_attention` is bounded action, not quiescence.

Before reporting portfolio quiescence after an empty acquisition, call `list_work_items`. Quiescence
requires that projection to be empty as well. If work items remain, report their identities and
stages as bounded acquisition attention and stop; do not infer a launch or mutate their state.

## Output

Report forwarded transition identities, typed Integration attention, periodic housekeeping results,
exact recovery results, unclaimed acquisition failures, bounded acquisition attention, and cycle
count. Report quiescence
only when both acquisition and the final work-item projection are empty. Do not translate those typed
results into invented completion or scheduling state.

## Known Pitfalls

- **Local scheduling:** acquisition already owns stable readiness and capacity.
- **Identity generation:** launch claims and role policies are runtime output, not Orchestrator input.
- **Transition interpretation:** worker action and payload remain unchanged.
- **Completion inference:** orchestration never synthesizes local completion; provider acceptance
 must be observed through its receipt-backed Delivery operation.
