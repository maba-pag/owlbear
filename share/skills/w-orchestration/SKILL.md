---
name: w-orchestration
description: "Workflow: Continue one Delivery Change, dispatch bounded workers, and forward their transitions"
user-invocable: false
---

# Delivery Orchestration

Continue one selected Change until its acquisition yields or bounded attention
requires the user. Delivery owns readiness, capacity, claims, identities, reviewer
policy, writer custody, transitions, provider-observed acceptance, and retained
Integration attention. Orchestrator performs only the mechanical dispatch loop
around that authority.

Run the session-start claim check before the first acquisition. A pre-existing running claim was not
dispatched by this session and may belong to a prior run or another live chat; only the user can
identify whether that exact run stopped.

**Session-start stale-claim check.** For `/continue-change <change_id>`, call `get_change(change_id)` and
inspect only that Change's running claims, revalidating them in the same coherent view. Do not call
`list_changes` or inspect sibling Changes on this route. For every Planner, Builder, or Finalizer card
with `readiness.status == "running"`, revalidate that exact claim and its running readiness in that
coherent view. Outcome claims are in `unresolved_outcomes[].active_claim`, with
readiness on the outcome's card; an active Finalizer is an unfinished `finalization_attempt.writer` with
`kind: finalize`.
Use the outcome claim's `worker_role` and `started_at`, or the Finalizer's `claimed_at`, to label
the question with role, Change ID, outcome (or Finalizer), and start time. Copy `change_id`,
`outcome_id`, `attempt_id`, and `claim_id` only from that same `get_change` view; use
`outcome_id: null` for Finalizer. If the exact claim is no longer active or running, do not ask or
release it.

Ask once per revalidated running claim through `vscode/askQuestions`: was this exact run stopped or
closed? Offer `stopped/closed`, `still running`, and `unsure`. For `stopped/closed`, call
`release_stuck_worker` exactly once with the copied identity and report its result unchanged. If it
returns `ERR_DELIVERY_WORKER_ACTIVE`, preserve the returned retry time or process details and do
not retry or dispatch a replacement in this cycle. For `still running` or `unsure`, leave the claim
and its files unchanged. Never edit its worktree or dispatch a
replacement for that claim while it remains unresolved. A `worker-stall-wait` readiness needs no question
or manual settlement; report its retry time or bounded process details and let a later acquisition
settle it when the guard passes.

Subagents run inside the issuing VS Code window and have no separate OS process identity.
Delivery automatically records `worker-host-lost` on a later acquisition only after the issuing
VS Code window identified by its recorded PID and process start time is gone, the worktree has had
no writes for 30 seconds, and no live same-user process has a cwd or open file beneath the managed
worktree or Git admin directory. An MCP-server restart while the issuing window remains alive does
not trigger host loss. The process guard ignores a terminal-attached idle shell whose only link is its
worktree cwd and which has no live children; open files still block. While the guard is unmet, `worker-stall-wait`
with `next_eligible_at` indicates the write guard; without a time, report the process names in the
prompt (or its bounded scan detail) and yield. Do not inspect the managed worktree meanwhile: Git
commands such as `git status` and `git diff` can update Git metadata and restart the quiet period.

## Change Continuation Entry

`/continue-change <change_id>` is the only execution entry. A continuation session carries exactly one
Change: never acquire, dispatch, recover, or report a sibling Change from it. Several Changes run in
separate continuation chats; Delivery enforces capacity and dependencies across them, and Cockpit
shows the portfolio.

### Continuation Bindings

Before the first acquisition, require callable `get_change`, `acquire_change_action`, and
`execute_change_action` bindings. Invoke any directly bound operation as granted; for each operation
with no direct callable binding, follow MCP Tool Bootstrap in `owlbear-system.instructions.md`: one
`tool_search` whose query is exactly that operation name. Never combine several names in one query.

If a required binding remains unavailable or that search returns a tool error, report the
exact missing operation and end the session without acquiring. A missing continuation operation is
never a reason to call the underlying checkpoint, target-sync, mark-ready, acceptance, finalization,
or transition operation directly. When Delivery MCP is unavailable or refuses to start, report that
and name `/repair-delivery` as the user's next step.

### Continuation Observation

Call `get_change(change_id)` once per continuation cycle. Pass its returned `readiness.basis`
unchanged as `expected_basis`. Do not edit, complete, reorder, recompute, or infer basis fields; the
engine compares the observed basis exactly and answers `stale` when it no longer matches.

When the host writes any tool or worker response to a file and returns only its path, copy that
path verbatim into the read; never retype it. If the read reports that the file does not exist,
compare the attempted path with the returned path character by character and retry once with the
exact returned path. If that read also fails, report the exact path and error and yield without
acquiring or settling. Never substitute an earlier, inferred, or reconstructed response.

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
| `launch` | Dispatch `launch.policy.worker_agent` with only the launch reference defined in Step 2, then apply Steps 2 and 3 unchanged |
| `finalization` | Dispatch `finalizer` with only the serialized `DeliveryFinalizationLaunch`; its `attempt` is the issued finalization identity and its `context` is the retained pre-acquisition context |
| `engine_action` | Call `execute_change_action` once with exactly `change_id` and `engine_action.operation_id` |

`execute_change_action` is the fixed executor for every engine action kind. Do not call the
underlying checkpoint, target-sync, mark-ready, or acceptance operation, do not dispatch an agent to
perform it, and do not author effect, target, receipt, success, or recovery arguments. Its returned
`DeliveryEngineActionResult` is the complete outcome: `completed`, `waiting`, and `stale` release the
action, while `blocked` retains custody and forbids a replacement operation. After `blocked`, re-read
`get_change` once and report its engine-authored `readiness.prompt` unchanged as the user's next
command. `failure.detail` is bounded text: never derive paths, commands, or a paraphrased next step
from it.

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
`dispatch_failure`, or a dispatch/transport that may still be running is unknown execution: do not call
`settle_worker_invocation`, `recover_claim`, reacquire, or redispatch. Such a Finalizer is known ended
only after this session's dispatch call has returned and its owned mutating terminals and asynchronous
jobs are settled; then call `release_stuck_worker` once with the issued launch identity and
`outcome_id: null` (Step 2), even without a user statement. Delivery records a counted
`finalizer-ended-without-report` and refuses with `ERR_DELIVERY_WORKER_ACTIVE` while the worktree is in
use. If the user explicitly states that this exact Finalizer chat was stopped, use the same route once;
otherwise report the issued attempt and retain custody. A Delivery-authored
`finalizer-ended-without-report` has `checks_state: unknown` and is not proof. If the settlement call
errors or returns a malformed result, re-read `get_change` before retrying the identical settlement;
otherwise report the engine-observed or unknown outcome. Never call a lower-level settlement operation
or forward a Finalizer result to `transition_delivery`.

Continuation and finalization custody is engine-held; caller confirmation cannot release it through
`recover_claim`. For Planner or Builder, a returned dispatch error, empty or `no response` result,
malformed or schema-invalid output, identity mismatch, or `kind: dispatch_failure` uses the
`ended-without-result` settlement in Step 3 only after the dispatch call has returned and its owned
mutating terminals and asynchronous jobs are settled. Use the acquired launch identities, plus the
exact continuation `owner_id` and `process_id` as outer `host_id` and `session_id`; discard mismatched
returned identity values. After settlement, re-read `get_change`, report the exact receipt, and do not
dispatch a replacement in the same continuation cycle; a later fresh acquisition follows engine
backoff.
A dispatch that never returned in a previous session is handled by the session-start check and, when
its issuing window is gone, by a later acquisition after Delivery's write/process guard passes. When
Delivery reports `worker-stall-wait`, report its `next_eligible_at` when present or its bounded
process details when absent, then yield; do not settle, recover, release, or dispatch a replacement.
Within the current session, an unreturned dispatch or any owned mutating terminal or asynchronous
job that may still be running is not settled by Orchestrator.
If the user explicitly states that the specific worker chat was stopped, use the separate one-shot
`release_stuck_worker` route in Step 2. `confirmed_lost`, elapsed time, disconnection, and a cancelled
wait are never evidence for `settle_worker_invocation` or `recover_claim`.

### Continuation Dispositions

A non-acquired result carries no launch. Respond to its `kind` exactly:

| `kind` | Required response |
| --- | --- |
| `busy` | Yield. Report the in-progress operation; do not poll in a loop, revoke custody, or recover a claim |
| `waiting` | Yield with reason; report `next_eligible_at` for `worker-stall-wait`. No dispatch or capability upgrade |
| `human` | Yield to the user with the reason code and readiness, reporting the returned `readiness.prompt` unchanged when present; the next actor is not this loop |
| `stale` | Refresh once: re-read `get_change` and re-acquire once with the fresh basis. If the second attempt is stale again, report both observations and stop |
| `reconciled` | Report the preserved `engine_result` unchanged; continue only from a fresh observation |
| `unsupported` | Report the exact reason. There is no raw-operation fallback and no invented repair; `repair-required` uses the Step 4 Change repair route |
| `unavailable` | Custody is retained. Report `failure` and its retry condition unchanged; never redispatch, replay the effect, acquire a replacement operation, or reconstruct journals |
| `terminal` | Report completion or abandonment. Never merge, clean up, remove a worktree, or transition anything implicitly |

When the selected Change's action is `resume-design`, report its complete engine-authored
`readiness.prompt` unchanged for that same Change. Do not replace it with a bare command, create
another Change identity, restate design content, or treat the handoff as approval.

### Merge Offer And Unknown Merge

No agent tool approves a merge; only the user approves, in Cockpit.

- Reason `merge-approval-required`: show `readiness.merge_offer` (repository and PR, exact head, target
  branch and head, required-check and proof summary, merge method), tell the user to approve it with
  **Approve merge** in Cockpit or merge the PR in GitHub, and stop. Never ask for the approval in chat
  or claim one.
- Reason `merge-response-unknown` (`human`): show "GitHub has not confirmed this merge. It may still
  run." with `readiness.merge_attempt.pr_url`, then ask one question with the options **Check again**
  and **Not now**. Each Check again answer makes exactly one `observe_acceptance(change_id)` call;
  report its result, re-observe with `get_change`, and ask again only while the reason stays
  `merge-response-unknown`. Not now stops. Never call it without an answer, never loop on it, and never
  request a merge.

### Continuation Refresh And Output

After a `release_stuck_worker` result, report it and stop the current cycle; do not reacquire or
dispatch a replacement in that cycle. After a host-tool `dispatch_failure` (Step 2), report it and end
the session without reacquiring or dispatching. After a released engine action, ordinary worker
settlement, or worker transition, re-observe with `get_change` and acquire again for the same Change. Stop on the
first yielding, unsupported, unavailable, or terminal disposition, or when readiness offers no
further action. Report the Change identity, each acquired action and its exact disposition, forwarded
transitions and worker settlement results, preserved engine results and failure envelopes, the
retained custody statement when one applies, and the exact next user command when the engine authored
one.

## Step 2 - Dispatch Or Recover Each Launch

For an acquired launch with worker role `planner` or `builder`, dispatch exactly
`launch.policy.worker_agent` and pass only this launch reference, copied verbatim from the acquired
launch:

```yaml
change_id: <launch.change_id>
outcome_id: <launch.outcome_id>
attempt_id: <launch.claim.attempt_id>
claim_id: <launch.claim.claim_id>
worker_role: <launch.claim.worker_role>
task_id: <launch.task_id or null>
```

Never retype or serialize the full `DeliveryLaunchPackage`; the worker loads the authoritative launch
from its Delivery context operation, which refuses a reference that does not name the active claim.
The selected agent's frontmatter owns its model. Do not substitute a role, agent, reviewer, worktree,
branch, or source head. Settlement still uses the acquired launch held by Orchestrator.

Treat `dispatch_failure` as a no-result outcome; settle it with `settle_worker_invocation` and
`disposition: ended-without-result`, using only the acquired launch identities. Never forward it to
`transition_delivery` or use returned identity values. Apply the same no-result route to a returned
Planner/Builder dispatch error, empty or `no response` result, malformed or schema-invalid output,
or identity-mismatched result. Preserve any available failure diagnostics for the report.

When a returned `dispatch_failure` reports that the worker's terminal or other host tools returned no
output or were unavailable, this chat's host is suspect: settle it as above, then end the session
without reacquiring or dispatching, and tell the user to continue the Change from a new chat.

Only settle after Orchestrator observes that the dispatch call returned and all owned mutating
terminals and asynchronous jobs are settled. A dispatch call that has not returned, or any owned
mutating terminal or asynchronous job that may still be running, is not settled by Orchestrator. For a
previous-session dispatch, rely on the session-start check and Delivery's recorded-window and
write/process guard at acquisition; report `worker-stall-wait` with its retry time or process details
and yield when the guard is not yet eligible.

### Release A User-Stopped Worker

Use `release_stuck_worker` only when the user explicitly states that the specific worker chat/window
was stopped, or for a known-ended Finalizer whose dispatch returned in this session without a valid
report (Step 2). If a user statement is ambiguous, ask which exact worker was stopped before mutating. Take
`change_id`, `outcome_id`, `attempt_id`, and `claim_id` unchanged from the acquisition result or one
fresh `get_change` view; for a Finalizer attempt, pass `outcome_id: null`. Never infer identity from
conversation, elapsed time, or a worker's missing response. Require a callable `release_stuck_worker`
binding at this point of use; if it is not directly bound, run one `tool_search` whose query is
exactly `release_stuck_worker`. A missing release binding is never a reason to use `settle_worker_invocation` or
`recover_claim` instead. Call the tool once and report its result
unchanged. If it returns `ERR_DELIVERY_WORKER_ACTIVE`, report the returned retry time or process details
unchanged and leave custody and files unchanged; do not retry or dispatch a replacement in the same
cycle. This is a user decision consumed by Delivery's 30-second write and process guard, not a
process-control operation.

`worker-host-lost` and `worker-released-stuck` are engine-only dispositions; never send either through
`settle_worker_invocation`. Each records the same failed-attempt semantics as `ended-without-result`,
preserves worktree bytes, staging, commits, and refs, and counts in the same three-attempt episode.
After backoff, a fresh Builder receives `prior_attempts` and triages the preserved same-task work; a
Planner retries under the same bounded episode. Three failures exhaust the episode. When a lost or
released Finalizer has no report, Delivery authors a `worker-ended` report with code
`finalizer-ended-without-report` and `checks_state: unknown`; it is diagnostic history, not proof.

Orchestrator does not recover claims. Report claim-recovery attention unchanged without interpreting
Git, liveness, or custody; the user recovers a claim through Cockpit **Recover claim** or
`/resolve-delivery-attention`. `recover_claim` accepts neither timeout nor caller confirmation as
evidence: without supported host-owned exclusion it returns `ERR_DELIVERY_WORKER_EXCLUSION_REQUIRED`
with `retry_safe: false`, leaving custody and files unchanged.

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
cancelled wait), or any owned mutating terminal or asynchronous job that may still be running, is not
settled by Orchestrator. The separate user-stopped route above may call `release_stuck_worker` once;
previous-session loss is handled by Delivery at acquisition. Elapsed time and `confirmed_lost` are not
evidence for normal settlement or `recover_claim`. Malformed Planner/Builder output is not a timeout;
use `ended-without-result` only when its observation precondition is met. Finalizer without a valid
report remains unknown unless Delivery settles a lost, known-ended (Step 2), or explicitly released
attempt, in which case its engine-authored `finalizer-ended-without-report` remains non-proof.

A normal Builder `return` to `design` is settled through the same typed envelope. Settlement clears
the exact active claim, records its failed attempt, and retains the task/results lineage and managed
workspace as a passive handoff. It does not revise or admit Design, grant Designer access to the
worktree, or make the Design route claimable by Planner or Builder. Re-read `get_change` and surface
its complete engine-authored `readiness.prompt` unchanged for the human-owned Design attention;
do not rebuild a bare `/design <change_id>` command or omit its recorded context. Do not fall back to
`transition_delivery` or synthesize a different transition.

For every other supported `DeliveryTransition`, call `transition_delivery` with outer
`change_id=launch.change_id` and the returned transition as `transition` byte-for-structure unchanged.
Immediately before either operation, if no directly callable binding exists, run one `tool_search`
whose query is exactly that operation name. If it remains unavailable or the search returns a tool error,
retain the launch's exact change, outcome, attempt, and claim IDs, report the routing failure, and end
the session. Do not redispatch Planner, Builder, or another agent to
echo, relay, reconstruct, or apply a result. A failed settlement call must be reconciled with
`get_change` before any retry; it is not a reason to send its request through `transition_delivery`
or attempt recovery without the Step 2 evidence.

For an ended Planner/Builder dispatch, identity mismatch or malformed/schema-invalid output uses
`ended-without-result` under Step 2, with launch identities; publish no substitute. A dispatch that
has not returned during the current session is not settled by Orchestrator. Step 2 permits one
`release_stuck_worker` call after an explicit user stop; previous-session loss is handled by Delivery
at acquisition. A rejected `transition_delivery`
call for worker-output schema validation after the invocation ended and its owned work settled also
uses this settlement; report the exact failure instead of forwarding or retrying the invalid transition.

## Step 4 - Preserve Typed Integration Attention

Do not call a local Integration or completion operation from the continuation loop. Integration
attention is retained evidence for the owning attention or provider-acceptance workflow. For a
`repair-required` result or a health diagnostic of the selected Change, call `get_change` once.
Dispatch the constrained `repairer` only when that view contains an
engine-authored repair proposal; pass the serialized view unchanged and treat its bounded result as
attention, never as a worker transition. A `stale` Repairer result is a clean re-entry requiring a
fresh view; never replay the old answer or proposal. Do not create a repair claim, dispatch Builder
for repair, or synthesize a repair result. A missing proposal, Integration attention, provider
waiting state, or authority gap remains reported evidence. Never infer completion from work-item
stages, worker prose, branch state, or cached results.

## Known Pitfalls

- **Local scheduling:** acquisition already owns stable readiness and capacity.
- **Identity generation:** launch claims and role policies are runtime output, not Orchestrator input.
- **Transition interpretation:** worker action and payload remain unchanged.
- **Completion inference:** orchestration never synthesizes local completion; provider acceptance
 must be observed through its receipt-backed Delivery operation.
