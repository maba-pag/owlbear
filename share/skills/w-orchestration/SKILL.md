---
name: w-orchestration
description: "Workflow: Orchestration — plan, dispatch, and verify agent execution cycles"
user-invocable: false
---

# Orchestration

Dispatch fresh engine plans until no work remains.

## Context Budget

- `rate_limited` starts `False`. After one rate-limit error, use `wave_size=1` for the rest of the session.
- `cycle_count` starts at 1 and increments after each cycle.
- Keep no board state between plans.

## Native Bootstrap Contract

`pick_tasks` is the default procedure below. IF-015 permits an explicit, non-default native procedure
for an admitted `change_id`: call `pick_jobs` for the current candidate revision, call `start_job` for
one returned entry, dispatch only its assigned profile, and pattern-match its structured disposition.
The profile-specific success object selects the matching `finish_plan`, `finish_build`,
`finish_accept`, or `finish_audit`;
`RateLimited` selects `release_job`; `Crash` selects strict-expiry `recover_expired_claims`. Then obtain
a fresh plan. Do not route by prose or bridge native jobs to task lifecycle state.

For an engine-selected `planner`, dispatch `runSubagent(agentName="planner")` with only the complete
successful `start_job` result serialized as its prompt. Pattern-match one exact disposition:

- `PlannerSuccess`: call `finish_plan` with the unchanged change, job, attempt, claim, actor, and
   process identity from the started job, an orchestrator-owned completion timestamp, and the
   returned `receipt_id`, `code_revision`, `evidence`, `evidence_ids`, `impact_closure`, `node_plan`,
   `build_job_ids`, and `accept_job_id`. Do not inspect, complete, or reconstruct `node_plan`.
- `RequestCreated`: call `release_job` with the unchanged active identity, then obtain a fresh
   `pick_jobs` result. The pending request is an engine dispatch gate.
- `SpecificationReentry`: call `release_job`, halt native mode, and report the returned target,
   finding, and evidence for user-facing `/design` re-entry. Do not edit Specification or legacy task
   state.
- `PlanBlocked`: call `release_job`, halt native mode, and report the returned target and finding.

Malformed planner output is an unstructured return and follows crash recovery. The orchestrator
never creates a planner Decision Request or node plan itself.

For an engine-selected `builder`, dispatch `runSubagent(agentName="builder")` with only the complete
successful `start_job` result serialized as its prompt. Pattern-match one exact disposition:

- `BuilderSuccess`: call `finish_build` with the unchanged change, job, attempt, claim, actor, and
   process identity from the started job, an orchestrator-owned completion timestamp, and the
   returned `receipt_id`, `code_revision`, `evidence`, `evidence_ids`, and `impact_closure`. Do not
   inspect, reconstruct, or supplement those returned fields.
- `SpecificationReentry`: call `release_job` with the unchanged active identity, halt native mode,
   and report the returned finding class, target, finding, and evidence for user-facing `/design`
   re-entry. Do not create a corrective job, request, receipt, or authority edit.
- `CommitFailed`: call `release_job` with the unchanged active identity, halt native mode, and report
   the returned command, error, and changed paths. Do not broaden or retry the commit from the
   orchestrator and do not issue a receipt.
- `BuildBlocked`: call `release_job` with the unchanged active identity, halt native mode, and report
   the returned target and finding. Do not create corrective work or issue a receipt.

Malformed builder output is an unstructured return and follows crash recovery. The orchestrator
never reviews, repairs, commits, classifies findings, or assembles build evidence itself.

Before `start_job`, resolve the selected profile against the installed subagent allowlist. If it is unavailable,
report the profile and halt native mode without claiming, running, releasing, or mutating legacy task state.
The native `planner` profile is valid only in this explicit mode; routine `pick_tasks` shape work remains
user-facing through `/shape`. Do not add acceptor or auditor role bodies here.

For `accept` and `audit`, `start_job` returns the engine-owned exact-commit checkout context. The orchestrator
does not materialize or clean it independently; finish, release, and recovery own checkout cleanup.

## Signal Contracts

`pick_tasks(wave_size=None, max_waves=3)` returns ordered waves of `(task, agent)` entries. Empty
waves end the session.

**Pipeline subagent output:** Use the Channel A vocabulary defined by `r-pipeline-protocol`. Channel A
reports lifecycle completion; it never authorizes orchestration to route the task. Re-plan from the
board after each wave.

`shape` work stays user-facing through `/shape`.

## Step 1 — Housekeeping

Every 10th cycle (`cycle_count % 10 == 0`), dispatch:

```
runSubagent(agentName="memory-curator", prompt="Curate: Periodic curation", description="Curation")
```

Curator failure does not stop dispatch.

## Step 2 — Plan

Call:

```
pick_tasks(wave_size=1 if rate_limited else None, max_waves=3)
```

If `waves=[]`, report completion and stop.

## Step 3 — Dispatch

Dispatch waves in returned order without re-bucketing. Dispatch each returned `(task_id, agent)` pair
once. A lifecycle result never authorizes the task's next agent; only a fresh plan does. Same-plan
redispatch is limited to the recovery cases below.

### Dispatch Mechanics

For each returned pair, use the `agent` capability's
`runSubagent(agentName=agent, prompt=str(task_id), description=description)` operation. The prompt
contains only the task ID; the description is display-only. The subagent claims and reads its task.

**Error handling:** Classify agent returns top-to-bottom. First match wins.

1. **Return starts with `TOOL_UNAVAILABLE`:** retry the same pair once. A second occurrence halts
   orchestration. Do not release or block; the agent already recorded failure.
2. **Return starts with `DONE | PASS | ARCHIVED | REJECT | RESHAPE | BLOCK | COMMIT_FAILED`:**
   consume the pair. The agent owns task state; make no task mutation.
3. **Unstructured return contains `rate-limited | rate_limited | rate limits`:** set
   `rate_limited=True`, retry the same pair once, and keep later plans sequential.
4. **Crash or unstructured return:** call
   `end_work(id={task_id}, outcome="release", note="{agent} crashed once: {reason}")`, then retry
   once. Continue when release returns `ERR_NOT_CLAIMED`. After a second crash, call
   `end_work(id={task_id}, outcome="block", block_reason="{agent} crashed twice: {reason}",
   note="{agent} crashed twice: {reason}")`. If that returns `ERR_NOT_CLAIMED`, call
   `edit_task(id={task_id}, block_reason="{agent} crashed twice before claiming: {reason}")`.

## Step 4 — Loop

After all waves, increment `cycle_count` and re-plan. Normal completion requires empty waves; user
intervention or a halting error above may stop earlier.

## Output Format

During execution:

```
Cycle 1 (Plan): Running pick_tasks(wave_size=None, max_waves=3)...
Cycle 1 (Wave 1/3): #103 (builder), #105 (verifier)
Cycle 1 (Done): 3/4 succeeded, 1 crashed (#112)
```

At end of session:

```
Session complete:
  Completed: #101, #103, #105
  Failed: #112 (crashed twice)
  Cycles: 2
```
