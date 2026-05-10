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
- **`cycle_count`** (integer, starts at 1): Incremented each cycle. Used to trigger the memory-curator every 5th cycle.
- **No board state.** `pick_tasks` reads the board each cycle via MCP tool call.
- **Channel A reading.** Read agent return values for outcome detection: `FAIL` (task failed), `TOOL_UNAVAILABLE` (tool degraded), or success. Do not parse signals for task routing — re-plan from board state each cycle.
- **Brief context:** Available to pipeline agents via parent task lookup — the orchestrator does not use Brief context directly.

## Signal Contracts

See `r-pipeline-protocol` → Communication for Channel A/B spec.

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

**Pipeline subagent output:** Channel A diagnostic line. Read for outcome detection: `FAIL` signals a task failure, `TOOL_UNAVAILABLE` signals tool degradation, any other return is success. Do not parse for routing.

## Step 1 — Housekeeping

At the **start of every cycle**, perform lightweight housekeeping. `pick_tasks` handles decision/action request resolution internally before it returns dispatchable work, so the orchestrator does not call a separate decision-resolver tool.

**Every cycle — decision/action request resolution:**

No separate tool call. The Step 2 `pick_tasks` call scans `.owlbear/decisions/pending/`, resolves responded DR/AR files, writes summaries to task bodies, unblocks resolved tasks, moves resolved files, and then returns fresh dispatch waves.

The orchestrator does not parse decision housekeeping output separately — `pick_tasks` reads fresh board state and filters blocked tasks.

**Every 5th cycle — memory-curator** (`cycle_count % 5 == 0`):

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

1. **Filter** — exclude claimed, archived, blocked, and dependency-blocked tasks.
2. **Sort** — deterministic order by priority rank, then age (oldest first), then task ID.
3. **Greedy wave assembly** — place each task into the first wave that satisfies all constraints.
4. **Return** — `PickTasksResponse(waves, guidance)`; tasks that cannot fit within `max_waves` are dropped for that cycle and reported in guidance.

Wave constraints enforced during greedy assembly:

- **Size cap**: wave length cannot exceed effective wave size (`wave_size` override or `BoardConfig.wave_size`).
- **Dep-disjointness**: no intra-wave dependency edges.
- **Agent-compatibility (D62+D63)**: agent buckets must be mutually compatible via `BoardConfig.agent_types` and `BoardConfig.agent_compatibility`.

Orchestrator dispatches waves in returned order. No local re-bucketing or re-assembly.

### Dispatch Mechanics

**Dispatch prompt contains ONLY the task ID.** Subagents claim and read their own AC via `start_work` in their own Step 0.

**Error handling — unified model:**

Classify agent returns top-to-bottom. First match wins.

**Structured vs crash classification:** A return that starts with a recognized verdict keyword (`DONE`, `FAIL`, `PASS`, `REJECT`, `REJECTED`, `ARCHIVED`, `APPROVED`, `REFINE`, `SPLIT`, `MERGE`, `BLOCK`) is a *structured return* — the agent completed its lifecycle and called `end_work`. Any other return (error, empty, unrecognized) is a *crash* — the agent did NOT call `end_work`.

1. **TOOL_UNAVAILABLE** (return contains `TOOL_UNAVAILABLE`):
   - Re-dispatch the same agent on the same task immediately.
   - If the retry also returns `TOOL_UNAVAILABLE`: **halt orchestration** — "Tool availability degraded: {agent} cannot reach {tool_name}. Restart VS Code or check extension status."
   - If the retry succeeds: tools recovered. Continue normally.
   - Note: TOOL_UNAVAILABLE returns are always structured (agent called `end_work`). The orchestrator does not block or edit the task — the agent already handled its own state.
2. **Rate-limit** (message contains "rate-limited", "rate_limited", or "rate limits"):
   - Set `rate_limited = True`. Retry the dispatch once.
   - All subsequent `pick_tasks` calls use `wave_size=1` (one-way transition — no resume to parallel).
3. **Structured return** (verdict keyword present — including `FAIL`):
   - The agent called `end_work` and managed its own task state (status, block, release). **Do not override** — no `edit_task(block=...)`, no `move_task`. The task is in the correct state.
   - Proceed to the next task in the wave.
4. **Crash** (no structured return — agent error, timeout, or unrecognized output):
   - Retry the dispatch once.
   - If the retry also crashes: **block the task** via `edit_task(block="{agent} crashed twice: {reason}")`.
   - After blocking, proceed to the next task in the wave.

## Step 4 — Loop

After all dispatches:

1. Increment `cycle_count`.
2. **Re-plan:** Go to **Step 1**. The decision resolver processes any DRs that were responded during this cycle, then `pick_tasks` reads fresh board state.

Loop continues until `pick_tasks` returns `waves=[]`. **Do not stop for any other reason.**

## Output Format

During execution:

```
Cycle 1 (Plan): Running pick_tasks(wave_size=None, max_waves=3)...
Cycle 1 (Wave 1/3): #101 (architect), #103 (builder), #105 (reviewer)
Cycle 1 (Done): 4/5 succeeded, 1 crashed (#112)
```

At end of session:

```
Session complete:
  Completed: #101, #103, #105
  Failed: #112 (crashed twice)
  Cycles: 2
```

## Verification Checklist

- [ ] If an agent crashed twice (no structured verdict), the task is blocked on the board with a reason note
- [ ] If an agent returned a structured verdict (including FAIL), the orchestrator did NOT edit or block the task
- [ ] If rate-limited at any point, all subsequent `pick_tasks` calls use `wave_size=1`
- [ ] Loop not stopped early — only empty waves or user intervention

## Known Pitfalls

- **Structured return ≠ needs orchestrator cleanup.** When an agent returns a structured verdict (`DONE`, `FAIL`, `BLOCK`, etc.), it called `end_work` and managed its own task state. Never `edit_task(block=...)` or `move_task` on a task whose agent returned a structured signal — that overwrites the agent's intentional state transition.
- **No dispatch decisions from housekeeping agents.** The orchestrator does not use decision-resolver or curator output for dispatch planning. They modify board state directly; `pick_tasks` reads fresh state each cycle. Informational signals (deferred count, pending DRs) are surfaced to the user only.
- **Legacy wave planner drift:** Do not reintroduce manual bucket planning in this skill. `pick_tasks` is the single wave-assembly authority.
