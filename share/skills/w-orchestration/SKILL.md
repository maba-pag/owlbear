---
name: w-orchestration
description: "Workflow: Orchestration — plan, dispatch, and verify agent execution cycles"
user-invocable: false
---

# Orchestration

Plan-dispatch-loop cycle for the orchestrator. The orchestrator maintains minimal context, dispatches agents in parallel waves, and loops until the board is clear.

## Context Budget

The orchestrator maintains minimal session state:

- **`rate_limited`** (boolean, default `False`): Set to `True` on any rate-limit error. Once set, all subsequent `pick_tasks` calls use `wave_size=1`. Never reset within a session.
- **`cycle_count`** (integer, starts at 1): Incremented each cycle. Used to trigger the memory-curator every 10th cycle.
- **No board state.** `pick_tasks` reads the board each cycle via MCP tool call.
- **Brief context:** Available to pipeline agents via parent task lookup — the orchestrator does not use Brief context directly.

## Signal Contracts

**pick_tasks tool:** `pick_tasks(wave_size=None, max_waves=3)` delegates to `AgentView.pick_tasks`.

**pick_tasks output shape:** `PickTasksResponse`

- `waves: list[Wave]`
- `guidance: list[str]`

`Wave` shape:

- `index: int` (zero-based)
- `tasks: list[DispatchEntry]`

`DispatchEntry` shape:

- `id: int`
- `status: str`
- `priority: str`
- `title: str`
- `tags: list[str]`
- `agent: str` (computed from `BoardConfig.agent_map` for task status)

Empty `waves` means nothing dispatchable for this cycle.

**Pipeline subagent output:** Use the Channel A vocabulary defined by `r-pipeline-protocol`. Channel A
reports lifecycle completion; it never authorizes orchestration to route the task. Re-plan from the
board after each wave.

`shape` tasks are excluded from routine dispatch. They require the user-facing `/shape` prompt because shaper may ask product, architecture, scope, or action-request questions through `askQuestions`.

## Step 1 — Housekeeping

At the **start of every cycle**, perform lightweight housekeeping. Decision/action request resolution is a Cockpit/user operation, not part of orchestration.

**Every cycle — dispatch planning:**

The Step 2 `pick_tasks` call is read-only. It reads the current board state, excludes blocked tasks, and returns fresh dispatch waves. If a DR/AR was resolved before this cycle, that resolution has already appended the task summary, unblocked the task when appropriate, and moved the file to resolved.

Dispatch planning uses the fresh board state returned by `pick_tasks`.

**Every 10th cycle — memory-curator** (`cycle_count % 10 == 0`):

```
runSubagent("memory-curator", "Curate: Periodic curation", "Curation")
```

Dispatch before or alongside the next planning cycle. The curator does not affect board state.

If the curator errors, note it but proceed to Step 2.

## Step 2 — Plan

Call `pick_tasks`:

```
pick_tasks(wave_size=1 if rate_limited else None, max_waves=3)
```

Default behavior:

- `wave_size=None` means the engine resolves the effective size from `BoardConfig.wave_size`.
- If `rate_limited` is `True`, pass `wave_size=1` to enforce sequential dispatch.
- `max_waves` defaults to `3`.

If `pick_tasks` returns `waves=[]`, report to user and stop.

`pick_tasks` already applies the engine-native four-step dispatch pipeline:

1. Filter
2. Sort
3. Greedy wave assembly
4. Return `PickTasksResponse`

## Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| **Wave size** | `BoardConfig.wave_size` | Effective cap when `pick_tasks(wave_size=None, ...)` |
| **Max waves** | `3` | Default `pick_tasks` ceiling per cycle |

## Step 3 — Dispatch

Dispatch `pick_tasks` return waves in order.

### Wave Assembly

Wave assembly is engine-native and must be sourced from the `pick_tasks` MCP tool (which delegates to `AgentView.pick_tasks`). Do not implement local four-bucket wave logic in the orchestrator skill.

`pick_tasks` wave assembly uses this four-step pipeline:

1. **Filter** — exclude claimed, archived, blocked, and dependency-blocked tasks, including tasks whose dependencies are still active.
2. **Sort** — deterministic order by priority rank, then age (oldest first), then task ID.
3. **Greedy wave assembly** — place each task into the first wave that satisfies all constraints.
4. **Return** — `PickTasksResponse(waves, guidance)`; tasks that cannot fit within `max_waves` are dropped for that cycle and reported in guidance.

Wave constraints enforced during greedy assembly:

- **Size cap**: wave length cannot exceed effective wave size (`wave_size` override or `BoardConfig.wave_size`).
- **Dep-disjointness**: no intra-wave dependency edges.
- **Agent-compatibility (D62+D63)**: agent buckets must be mutually compatible via `BoardConfig.agent_types` and `BoardConfig.agent_compatibility`.

Orchestrator dispatches waves in returned order. No local re-bucketing or re-assembly.

Treat each `pick_tasks` response as a consumable dispatch plan. A normal dispatch must match one
exact `(task_id, agent)` pair in the latest response, and that pair is consumed when dispatched.
Never derive or dispatch a new pair from task state, a lifecycle return, a task lookup, or agent
prose. In particular, if a dispatched task advances to another stage, its next agent cannot run
until the current plan is exhausted and a fresh `pick_tasks` response returns that new pair. The
only same-plan redispatches are the explicit `TOOL_UNAVAILABLE`, rate-limit, and crash retries below.

### Dispatch Mechanics

**Dispatch prompt contains ONLY the task ID.** Subagents claim and read their own AC via `start_work` in their own Step 0.

**Error handling:** Classify agent returns top-to-bottom. First match wins.

1. **`TOOL_UNAVAILABLE`** (return starts with the token):
   - Re-dispatch the same agent on the same task immediately.
   - If the retry also returns `TOOL_UNAVAILABLE`: **halt orchestration** — "Tool availability degraded: {agent} cannot reach {tool_name}. Restart VS Code or check extension status."
   - If the retry succeeds: tools recovered. Continue normally.
   - The agent already called `end_work(outcome="fail")`; do not release or block the task.
2. **Structured lifecycle return** (starts with `DONE`, `PASS`, `ARCHIVED`, `REJECT`, `RESHAPE`,
   `BLOCK`, or `COMMIT_FAILED`):
   - The agent already managed task state. Do not call `end_work`, `edit_task`, or `move_task`.
   - Mark the dispatched pair consumed and proceed only to the next unconsumed pair from the current
     plan. Routing for any changed task state comes from the next `pick_tasks` call.
3. **Raw rate-limit error** (unstructured message contains "rate-limited", "rate_limited", or "rate limits"):
   - Set `rate_limited = True`. Retry the dispatch once.
   - All subsequent `pick_tasks` calls use `wave_size=1` (one-way transition — no resume to parallel).
4. **Crash** (empty, unrecognized, timeout, or other unstructured error):
   - Release any claim before retry: `end_work(id={task_id}, outcome="release", note="{agent} crashed once; releasing claim before retry: {reason}")`.
   - If release reports `ERR_NOT_CLAIMED`, the agent crashed before claiming; continue to the retry.
   - Re-dispatch the same agent on the same task once.
   - If the retry also crashes: **block the task** via `end_work(id={task_id}, outcome="block", block_reason="{agent} crashed twice: {reason}", note="{agent} crashed twice: {reason}")` so any claim is released.
   - If `end_work` reports `ERR_NOT_CLAIMED`, the agent crashed before claiming; block the unclaimed task via `edit_task(id={task_id}, block_reason="{agent} crashed twice before claiming: {reason}")`.
   - After blocking, proceed to the next task in the wave.

## Step 4 — Loop

After all dispatches:

1. Increment `cycle_count`.
2. **Re-plan:** Go to **Step 1**. The next `pick_tasks` call sees any DR/AR resolutions already applied before the cycle and returns fresh dispatch waves.

Loop continues until `pick_tasks` returns `waves=[]`. **Do not stop for any other reason.**

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

## Verification Checklist

- [ ] If an agent crashed once (no structured verdict), any claim was released before retry
- [ ] If an agent crashed twice (no structured verdict), the task is blocked on the board with a reason note
- [ ] If an agent returned a structured lifecycle signal, the orchestrator did NOT edit or block the task
- [ ] Every normal dispatch matched one unconsumed pair in the latest `pick_tasks` response
- [ ] No task's next-stage agent ran before a fresh `pick_tasks` response returned that pair
- [ ] If rate-limited at any point, all subsequent `pick_tasks` calls use `wave_size=1`
- [ ] Loop not stopped early — only empty waves or user intervention

## Known Pitfalls

- **Structured return ≠ needs orchestrator cleanup.** Never mutate a task after a structured signal;
   this includes `BLOCK` and `COMMIT_FAILED` containment states.
- **Lifecycle return ≠ dispatch plan.** A task advancing from build to verify does not authorize an
   immediate verifier call. Finish the current plan, then require `pick_tasks` to return the verifier pair.
- **Crash retry requires claim release.** A crashed agent may have claimed the task before failing. Release with `end_work(outcome="release")` before retrying, otherwise the retry can hit `ERR_ALREADY_CLAIMED`.
- **No dispatch decisions from housekeeping output.** Curator output is informational only; `pick_tasks` reads fresh board state each cycle.
- **Legacy wave assembly drift:** Do not reintroduce manual bucket planning in this skill. `pick_tasks` is the single wave-assembly authority.
