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
