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

## Change Continuation Entry

`/continue-change <change_id>` is the normal entry for one named Change and uses this section instead
of the portfolio batch loop. `/orchestrate` remains the unchanged portfolio entry. A continuation
session carries exactly one Change: never acquire, dispatch, recover, or report a sibling Change from
it, and never fall back to `acquire_actions` when a continuation operation is unavailable.

### Continuation Bindings

Before the first acquisition, require callable `get_change`, `acquire_change_action`, and
`execute_change_action` bindings. Invoke any directly bound operation as granted; run one focused
`tool_search` only for an operation with no direct callable binding:

`OwlBear Delivery get_change acquire_change_action execute_change_action`

If a required binding remains unavailable or its focused search returns a tool error, report the
exact missing operation and end the session without acquiring. A missing continuation operation is
never a reason to call the underlying checkpoint, target-sync, mark-ready, acceptance, finalization,
or transition operation directly.

### Continuation Observation

Call `get_change(change_id)` once per continuation cycle. Pass its returned `readiness.basis`
unchanged as `expected_basis`. Do not edit, complete, reorder, recompute, or infer basis fields; the
engine compares the observed basis exactly and answers `stale` when it no longer matches.

Declare `capabilities` truthfully for this session only:

- `planner` and `builder` only while their dispatch bindings are callable here;
- `engine` only while `execute_change_action` is callable here;
- `finalizer` only when this host can actually dispatch the `finalizer` agent and that dispatch can
  obtain its own independent review. The shared `orchestrator` agent does not list `finalizer` among
  its delegates, so omit that capability unless the running host actually exposes that dispatch.

Never declare a capability to unlock an action. An undeclared capability returns `waiting` /
`host-capability-unavailable` with no custody consumed; for the finalization case report the exact
`/finalize-change <change_id>` command as the user's next step instead of finalizing in this loop.

Call `acquire_change_action` once per cycle with the selected `change_id`, that observed basis, the
truthful capabilities, and stable `host_id` and `session_id` values for this session.

### Continuation Dispatch

An `acquired` result carries exactly one of `launch`, `finalization`, or `engine_action`. Dispatch
strictly what it carries and nothing else:

| Acquired field | The only permitted action |
| --- | --- |
| `launch` | Dispatch `launch.policy.worker_agent` with only the serialized `DeliveryLaunchPackage`, then apply Steps 2 and 3 unchanged |
| `finalization` | Dispatch `finalizer` with the serialized `DeliveryFinalizationLaunch`; its `attempt` is the issued finalization identity and its `context` is the retained pre-acquisition context |
| `engine_action` | Call `execute_change_action` once with exactly `change_id` and `engine_action.operation_id` |

`execute_change_action` is the fixed executor for every engine action kind. Do not call the
underlying checkpoint, target-sync, mark-ready, or acceptance operation, do not dispatch an agent to
perform it, and do not author effect, target, receipt, success, or recovery arguments. Its returned
`DeliveryEngineActionResult` is the complete outcome: `completed`, `waiting`, and `stale` release the
action, while `blocked` retains custody and forbids a replacement operation.

A dispatched Builder that already called `submit_result` returns `kind: submitted`; record it and do
not call `transition_delivery` again for that result. Worker transitions, malformed worker results,
and dispatch failures follow Steps 2 and 3 unchanged.

### Continuation Dispositions

A non-acquired result carries no launch. Respond to its `kind` exactly:

| `kind` | Required response |
| --- | --- |
| `busy` | Yield. Report the in-progress operation; do not poll in a loop, revoke custody, or recover a claim |
| `waiting` | Yield to the named condition and report the reason code; no dispatch, no capability upgrade |
| `human` | Yield to the user with the reason code and readiness; the next actor is not this loop |
| `stale` | Refresh once: re-read `get_change` and re-acquire once with the fresh basis. If the second attempt is stale again, report both observations and stop |
| `reconciled` | Report the preserved `engine_result` unchanged; continue only from a fresh observation |
| `unsupported` | Report the exact reason. There is no raw-operation fallback and no invented repair; `repair-required` uses the Step 4 Change repair route |
| `unavailable` | Custody is retained. Report `failure` and its retry condition unchanged; never redispatch, replay the effect, acquire a replacement operation, or reconstruct journals |
| `terminal` | Report completion or abandonment. Never merge, clean up, remove a worktree, or transition anything implicitly |

When the selected Change's action is `resume-design`, report its engine-authored
`/design <change_id>` command for that same Change. Do not create another Change identity, restate
design content, or treat the handoff as approval.

### Continuation Refresh And Output

After a released engine action or a recorded worker transition, re-observe with `get_change` and
acquire again for the same Change. Stop on the first yielding, unsupported, unavailable, or terminal
disposition, or when readiness offers no further action. Report the Change identity, each acquired
action and its exact disposition, forwarded transitions, preserved engine results and failure
envelopes, the retained custody statement when one applies, and the exact next user command when the
engine authored one.

## Step 1 - Acquire One Current Batch

Before using a target operation, call it directly when a callable binding is already present; a
deferred inventory listing does not override that binding. If a required target operation has no
direct callable binding, load the target tools once with `tool_search` using:

`OwlBear Delivery target portfolio list_changes acquire_actions delivery_health get_change transition_delivery recover_claim recover_integration_repair_claim`

Before calling `acquire_actions`, require callable bindings for `transition_delivery`,
`recover_claim`, `recover_integration_repair_claim`, and `delivery_health`. Invoke any directly bound
operation as granted; run one focused `tool_search` only for each operation with no direct callable
binding. If any binding remains unavailable or its focused search returns a tool error,
report the exact missing operation and end the session without acquisition. Transition and recovery
are required dispatch safety authority, not optional operations to discover after a claim has been
acquired.

Call `list_changes` only for bounded portfolio reporting. Call `acquire_actions` once for the
current cycle. Its `DeliveryAcquisitionResult` is the sole source of task launch order,
typed `integration_attention`, acquisition failures, and the optional `health_hint`. When
`health_hint` is non-empty, immediately call `delivery_health` with `{}` and report its bounded
diagnostics before dispatching any launch. Do not dispatch or recover a Change identified by those
diagnostics; quarantined Changes have no actionable launch authority. Active claims remain occupied until the
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
`recover_claim` request with `confirmed_lost=true`. Never forward this result to
`transition_delivery` or translate it into a worker lifecycle action.

If Planner or Builder dispatch otherwise fails before returning a structurally valid worker result,
use that same exact `recover_claim` request with `confirmed_lost=true`. Recovery attention remains runtime-owned evidence;
report it without interpreting Git, liveness, or custody. An acquisition failure carrying attempt
and claim IDs uses the same route. A failure without claim IDs is reported as bounded acquisition
attention and is not claim-recoverable by Orchestrator; it may still qualify for the Change repair
route in Step 4 when it has an exact `change_id`. Do not report a recovery operation as unavailable
unless its Step 1 focused search or an exact recovery call returned a recorded tool error.

When exact recovery returns `recovered`, discard the failed launch and continue with the next
acquisition cycle; do not inspect or classify the quarantined files. When it returns `attention`,
report the returned reason and retry condition as machine-owned evidence. Do not ask the user to
choose which dirty files to keep, discard, adopt, or commit.

## Step 3 - Forward One Worker Transition

Require the worker result to be one `DeliveryTransition` mapping or one `kind: submitted`
`DeliveryResultSubmissionResult` mapping. Validate only identity binding:

- `outcome_id` and `claim_id` equal the launch values;
- any transition `attempt_id` equals `launch.claim.attempt_id`;
- any nested output uses the launch claim ID.

For `kind: submitted`, require `change_id`, `outcome_id`, `claim_id`, and `result_id` to be present,
and require the returned binding to name the launch outcome. The Builder already called
`submit_result`, so record the submission and do not call `transition_delivery` again.

Do not select, rewrite, enrich, or reconstruct action, output, result, request, reason, evidence, or
commit fields. For a `DeliveryTransition`, call `transition_delivery` with outer
`change_id=launch.change_id` and the returned transition as `transition` byte-for-structure unchanged.
A worker-owned `block`, `retry`, or `return` is forwarded normally and must not be recovered. A
malformed submission result or identity mismatch follows the existing dispatch-failure recovery
route.

Immediately before forwarding, if no directly callable `transition_delivery` binding exists, run one focused
`tool_search` for that exact operation. If it remains unavailable or the search returns a tool
error, call `recover_claim` with `confirmed_lost=true` and the launch's exact change, outcome, attempt, and claim IDs, report
the routing failure and recovery result, and end the session after the current acquired batch. Do
not redispatch Planner, Builder, or another agent to echo, relay, reconstruct, or apply a transition.

An identity mismatch or malformed result is a failed dispatch result: publish no substitute and use
the exact Step 2 recovery route for the still-active claim. A rejected `transition_delivery` call
for worker-output schema validation is also a malformed dispatch result and requires that recovery
before session completion.

## Step 4 - Preserve Typed Integration Attention

Do not call a local Integration or completion operation from the orchestration loop. Acquisition
returns `integration_attention` as retained evidence for the owning attention or provider-acceptance
workflow. For each acquisition `failure` or health diagnostic with an exact `change_id`, call
`get_change` once. Dispatch the constrained `repairer` only when that view contains an
engine-authored repair proposal; pass the serialized view unchanged and treat its bounded result as
attention, never as a worker transition. A `stale` Repairer result is a clean re-entry requiring a
fresh view; never replay the old answer or proposal. Do not create a repair claim, dispatch Builder
for repair, or synthesize a repair result. A missing proposal, Integration attention, provider
waiting state, or authority gap remains reported evidence. Never infer completion from work-item
stages, worker prose, branch state, or cached results.

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
tool-layer error, or capability dispatch fails before a child result exists, record a non-blocking
housekeeping failure, report it separately, finish the current batch, and continue with the next
acquisition cycle; do not use Delivery recovery. If the invocation completes but returns no result,
a result without the curator's Channel A verdict, or a child report of its own internal failure,
record a malformed housekeeping result, do not retry it, and continue acquisition. A scheduled
attempt consumes its cadence slot regardless of its result.

## Step 6 - Refresh

Finish the current acquired batch, discard it, and call `acquire_actions` again. Continue
independent changes when one outcome returns or blocks. Stop when launch packages are empty, or when
a Delivery safety diagnostic requires user/operator action. A housekeeping failure is reported but
does not stop independent Delivery acquisition.
Non-empty `integration_attention` is bounded action, not quiescence.

Before reporting portfolio quiescence after an empty acquisition, call `list_changes`. Quiescence
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
