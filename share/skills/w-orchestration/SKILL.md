---
name: w-orchestration
description: "Workflow: Acquire Delivery work, dispatch bounded workers, and forward their transitions"
user-invocable: false
---

# Delivery Orchestration

Run the portfolio until acquisition is quiescent or bounded attention requires
a user/operator. Delivery owns readiness, capacity, claims, identities, reviewer
policy, writer custody, transitions, provider-observed acceptance, and retained
Integration attention. Orchestrator performs only the mechanical dispatch loop
around that authority.

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
  obtain its own independent review. The shared `orchestrator` agent lists `finalizer` among its
  delegates, so the nested route exists; a host that cannot actually perform that dispatch still omits
  the capability.

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
| `finalization` | Dispatch `finalizer` with only the serialized `DeliveryFinalizationLaunch`; its `attempt` is the issued finalization identity and its `context` is the retained pre-acquisition context |
| `engine_action` | Call `execute_change_action` once with exactly `change_id` and `engine_action.operation_id` |

`execute_change_action` is the fixed executor for every engine action kind. Do not call the
underlying checkpoint, target-sync, mark-ready, or acceptance operation, do not dispatch an agent to
perform it, and do not author effect, target, receipt, success, or recovery arguments. Its returned
`DeliveryEngineActionResult` is the complete outcome: `completed`, `waiting`, and `stale` release the
action, while `blocked` retains custody and forbids a replacement operation.

A dispatched Builder that already called `submit_result` returns `kind: submitted`; record it and do
not call `transition_delivery` again for that result. A structurally valid, launch-bound
`DeliveryTransition` is validated and routed through Step 3 with its worker-selected payload unchanged.

A dispatched `finalizer` returns one `w-change-finalization` mapping, not a worker transition.
Require its `change_id` to equal the selected Change and any returned `operation_id` to equal
`finalization.attempt.writer.attempt_id`. Record `finalized` and `already_finalized` as successful
outcomes and re-observe with `get_change`; do not settle either result. For a normally returned
`proof_failed` or `review_failed`, require that exact `operation_id` and a lowercase 64-hex
`report_id` returned by `report_finalization_failure`. Construct `FinalizerSettlement` only from the
issued launch: copy `change_id`, `attempt.writer.attempt_id`, `attempt.writer.claim_id`,
`attempt.exact_head`, `context.reviewed_change_head`, `attempt.writer.actor_id`, and
`attempt.writer.process_id`; copy the actual `report_id`; set `disposition: normal-return` and map the
outcome to `proof-failed` or `review-failed`. Call the existing `settle_worker_invocation` once with
only `{"settlement": <FinalizerSettlement>}`. Record its exact receipt and retained attention;
preserve the report's code and `checks_state` (`not-run`, `failed`, or `unknown`) without presenting the report as
proof or as evidence that the Finalizer process is closed.

A missing or malformed report identity, missing or mismatched operation identity, malformed result,
`dispatch_failure`, or dispatch/transport that may still be running is unknown execution: do not settle,
recover, reacquire, or redispatch; report the issued attempt and retain custody. If the settlement call
errors or returns a malformed result, re-read `get_change` before any retry; retry only the identical
settlement when that view proves the same issued attempt is still active and unfinished. Otherwise
report the engine-observed state or unknown outcome without retrying. Never call a lower-level
settlement operation or forward a Finalizer result to
`transition_delivery`.

Continuation and finalization custody is engine-held; caller confirmation cannot release it through
`recover_claim`. For Planner or Builder, a returned dispatch error, empty or `no response` result,
malformed or schema-invalid output, identity mismatch, or `kind: dispatch_failure` uses the
`ended-without-result` settlement in Step 3 only after the dispatch call has returned and its owned
mutating terminals and asynchronous jobs are settled. Use the acquired launch identities, plus the
exact continuation `owner_id` and `process_id` as outer `host_id` and `session_id`; discard mismatched
returned identity values. After settlement, re-read `get_change`, report the exact receipt, and do not
dispatch a replacement in the same continuation cycle; a later fresh acquisition follows engine
backoff.

If the dispatch call has not returned (including Orchestrator or VS Code death/restart mid-run,
disconnected transport, or a cancelled wait), or any owned mutating terminal or asynchronous job may
still be running, retain custody: do not settle, call `recover_claim`, acquire a replacement action,
or redispatch. `confirmed_lost` is never evidence. Finalizer's no-report/malformed-result behavior
remains as stated above: retain custody without settlement or recovery.

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

When the selected Change's action is `resume-design`, report its complete engine-authored
`readiness.prompt` unchanged for that same Change. Do not replace it with a bare command, create
another Change identity, restate design content, or treat the handoff as approval.

### Continuation Refresh And Output

After a released engine action, recorded worker settlement, or recorded worker transition, re-observe
with `get_change` and acquire again for the same Change. Stop on the first yielding, unsupported, unavailable, or terminal
disposition, or when readiness offers no further action. Report the Change identity, each acquired
action and its exact disposition, forwarded transitions and worker settlement results, preserved
engine results and failure envelopes, the retained custody statement when one applies, and the exact
next user command when the engine authored one.

## Step 1 - Acquire One Current Batch

Before using a target operation, call it directly when a callable binding is already present; a
deferred inventory listing does not override that binding. If a required target operation has no
direct callable binding, load the target tools once with `tool_search` using:

`OwlBear Delivery target portfolio list_changes acquire_actions delivery_health get_change transition_delivery settle_worker_invocation recover_claim recover_integration_repair_claim`

Before calling `acquire_actions`, require callable bindings for `transition_delivery`,
`settle_worker_invocation`, `recover_claim`, `recover_integration_repair_claim`, and
`delivery_health`. Invoke any directly bound operation as granted; run one focused `tool_search` only
for each operation with no direct callable binding. If any binding remains unavailable or its
focused search returns a tool error, report the exact missing operation and end the session without
acquisition. Transition, settlement, and recovery are required dispatch safety authority, not
optional operations to discover after a claim has been acquired.

Call `list_changes` only for bounded portfolio reporting. Call `acquire_actions` once for the
current cycle. Its `DeliveryAcquisitionResult` is the sole source of task launch order,
typed `integration_attention`, acquisition failures, and the optional `health_hint`. When
`health_hint` is non-empty, immediately call `delivery_health` with `{}` and report its bounded
diagnostics before dispatching any launch. Do not dispatch or recover a Change identified by those
diagnostics; quarantined Changes have no actionable launch authority. Active claims remain occupied until the
exact verified recovery operation completes. `recover_claim` does not accept timeout or caller
confirmation as evidence. Without supported host-owned exclusion it returns
`ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED` with `retry_safe: false`, leaving custody and files unchanged.
Closure must cover the invocation, descendant writers and outstanding tool jobs with no ability to
resume, or enforce restart-durable exclusion from every managed filesystem, Git and mutation resource.
Report the typed result unchanged. Do not filter for capacity, infer readiness, create identities,
or reserve writer custody.

## Step 2 - Dispatch Or Recover Each Launch

Process `launch_packages` in returned order. For worker role `planner` or `builder`, dispatch exactly
`launch.policy.worker_agent` and pass only the serialized `DeliveryLaunchPackage`. The selected
agent's frontmatter owns its model. Do not substitute a role, agent, reviewer, worktree, branch, or
source head.

Treat `dispatch_failure` as a no-result outcome; settle it with `settle_worker_invocation` and
`disposition: ended-without-result`, using only the acquired launch identities. Never forward it to
`transition_delivery` or use returned identity values. Apply the same no-result route to a returned
Planner/Builder dispatch error, empty or `no response` result, malformed or schema-invalid output,
or identity-mismatched result. Preserve any available failure diagnostics for the report.

Only settle after Orchestrator observes that the dispatch call returned and all owned mutating
terminals and asynchronous jobs are settled. A dispatch call that has not returned (including
Orchestrator or VS Code death/restart mid-run, disconnected transport, or a cancelled wait), or any
owned mutating terminal or asynchronous job that may still be running, remains contained: do not
settle, call `recover_claim`, or dispatch a replacement. `confirmed_lost` is never evidence.

An acquisition failure carrying attempt and claim IDs is not a worker dispatch result and uses the
exact recovery route. Report recovery attention unchanged without interpreting Git, liveness, or
custody. A failure without claim IDs is bounded acquisition attention and is not claim-recoverable by
Orchestrator; it may still qualify for the Change repair route in Step 4 when it has an exact
`change_id`. Do not report a recovery operation as unavailable unless its Step 1 focused search or
an exact recovery call returned a recorded tool error.

Only a verified completed recovery receipt or settlement receipt permits a later fresh acquisition;
never interpret an error envelope as a completed operation. `ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED`
is non-retryable: report the missing supported host evidence and stop with custody intact.
Read-only diagnosis remains available. Do not inspect or classify private preservation contents or
ask the user to operate Git or kill processes.

## Step 3 - Route One Completed Worker Result

Require the worker result to be one `DeliveryTransition` mapping or one `kind: submitted`
`DeliveryResultSubmissionResult` mapping. Validate only identity binding:

- `outcome_id` and `claim_id` equal the launch values;
- any transition `attempt_id` equals `launch.claim.attempt_id`;
- any nested output uses the launch claim ID.

For `kind: submitted`, require `change_id`, `outcome_id`, `claim_id`, and `result_id` to be present,
and require the returned binding to name the launch outcome. The Builder already called
`submit_result`, so record the submission and do not call `transition_delivery` again.

Do not select, rewrite, enrich, or reconstruct action, output, result, request, reason, evidence, or
commit fields. Route normal completed returns and ended no-result outcomes as follows:

| Launch role | Worker outcome | Operation |
| --- | --- | --- |
| `planner` | `retry` | `settle_worker_invocation` with `DeliveryPlanningRetrySettlement` |
| `builder` | `retry`, `block`, or `return` to `planning` or `design` | `settle_worker_invocation` with `DeliveryBuilderInvocationSettlement` |
| `planner` | Ended without a valid result | `settle_worker_invocation` (`ended-without-result`) |
| `builder` | Ended without a valid result | `settle_worker_invocation` (`ended-without-result`) |
| Any task role | Any other supported transition | `transition_delivery` with the unchanged transition |

The real `settle_worker_invocation` MCP envelope has only these top-level fields:

```json
{
  "settlement": {},
  "host_id": "<optional exact claim owner>",
  "session_id": "<optional exact claim process>"
}
```

`settlement` is required and is one typed model. For a Planner retry, copy `change_id`, `outcome_id`,
`claim_id`, and `attempt_id` from the acquired launch, set `disposition: normal-return`, and copy the
returned `RetryDelivery` unchanged to `request`. For a Builder retry, block, or return to Planning or Design,
use the same launch identities plus `task_id=launch.task_id` and
`expected_last_reviewed_commit=launch.last_reviewed_commit`,
set `disposition: normal-return`, and copy the returned transition unchanged to `request`. When the
claim is a continuation, set the optional `host_id` and `session_id` from its exact `owner_id` and
`process_id`; never guess either value.

For `ended-without-result`, use the same top-level `settlement` envelope and typed identity fields as
completed-timeout, but set `disposition: ended-without-result` and omit `request` (or pass it as
`null`). A Planner settlement copies `change_id`, `outcome_id`, `claim_id`, and `attempt_id` only
from its launch. A Builder settlement also copies `task_id=launch.task_id` and
`expected_last_reviewed_commit=launch.last_reviewed_commit`. For a continuation, copy the exact
launch `owner_id` and `process_id` to outer `host_id` and `session_id`; never use returned identities.
The recorded failure code is the reserved `worker-ended-without-result`; workers must not return it
in their own `RetryDelivery`.

A completed-timeout settlement uses the matching typed identity, `disposition: completed-timeout`,
and no `request`. Orchestrator owns this completion report; the timed-out child need not return
a typed transition. Use it only after observing that the dispatched invocation has ended because
of timeout and its owned mutating terminals and asynchronous jobs are settled. Elapsed time,
a still-running tool, transport failure, cancelled wait or disconnect alone does not qualify.
An `ended-without-result` settlement is required for a Planner or Builder dispatch that returned an
error, empty or `no response` result, malformed or schema-invalid output, identity-mismatched
result, or `kind: dispatch_failure`. Use it only after Orchestrator observes that the dispatch call
returned and all owned mutating terminals and asynchronous jobs are settled. It counts as a failed
attempt in the same three-attempt episode and preserves worktree bytes, staging, commits, and refs.
Fresh acquisition may claim the same task after engine backoff; the next Builder triages preserved
work using fresh Build context and `prior_attempts`. Three total failures exhaust the episode with
failure history. After settlement, re-read `get_change`, report the exact receipt, and do not dispatch
a replacement in the same cycle.

An unreturned dispatch (Orchestrator or VS Code died/restarted mid-run, disconnected transport, or a
cancelled wait), or any owned mutating terminal or asynchronous job that may still be running, remains
contained: do not settle, call `recover_claim`, or dispatch a replacement. Elapsed time and
`confirmed_lost` are not evidence. Malformed Planner/Builder output is not a timeout; use
`ended-without-result` only when its observation precondition is met. Finalizer without a valid
report remains contained under the Finalizer rule above.

A normal Builder `return` to `design` is settled through the same typed envelope. Settlement clears
the exact active claim, records its failed attempt, and retains the task/results lineage and managed
workspace as a passive handoff. It does not revise or admit Design, grant Designer access to the
worktree, or make the Design route claimable by Planner or Builder. Re-read `get_change` and surface
its complete engine-authored `readiness.prompt` unchanged for the human-owned Design attention;
do not rebuild a bare `/design <change_id>` command or omit its recorded context. Do not fall back to
`transition_delivery` or synthesize a different transition.

For every other supported `DeliveryTransition`, call `transition_delivery` with outer
`change_id=launch.change_id` and the returned transition as `transition` byte-for-structure unchanged.
Immediately before either operation, if no directly callable binding exists, run one focused
`tool_search` for that exact operation. If it remains unavailable or the search returns a tool error,
retain the launch's exact change, outcome, attempt, and claim IDs, report the routing failure, and end
the session after the current acquired batch. Do not redispatch Planner, Builder, or another agent to
echo, relay, reconstruct, or apply a result. A failed settlement call must be reconciled with
`get_change` before any retry; it is not a reason to send its request through `transition_delivery`
or attempt recovery without the Step 2 evidence.

For an ended Planner/Builder dispatch, identity mismatch or malformed/schema-invalid output uses
`ended-without-result` under Step 2, with launch identities; publish no substitute. A dispatch that
has not returned or whose owned work may still run remains contained. A rejected `transition_delivery`
call for worker-output schema validation after the invocation ended and its owned work settled also
uses this settlement; report the exact failure instead of forwarding or retrying the invalid transition.

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
a non-empty acquisition batch whose launches have been handled and whose worker transitions, exact
settlements, or recovery results have been recorded. Do not count an empty acquisition, an acquisition failure, or
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

Report forwarded transition and settlement identities, typed Integration attention, periodic
housekeeping results,
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
