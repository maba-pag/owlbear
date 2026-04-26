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
- **`needs_info_dispatches`** (list of `{task_id, agent}` pairs, cleared each cycle): Populated from scribe's `resolve-summary.json` in Step 1. Injected into dispatch plan in Step 2.
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

**Pipeline subagent output:** Channel A diagnostic line. Read for outcome detection: `FAIL` signals a task failure, `TOOL_UNAVAILABLE` signals tool degradation, any other return is success. Do not parse for routing. After scribe returns, read `resolve-summary.json` for structured dispatch data (see Step 1).

## Step 1 — Resolve Pending Decision Requests

At the **start of every cycle**, call the **scribe** agent to process any responded decision/action requests:

```
runSubagent("scribe", "Scribe: task_id=all, mode=resolve, agent=orchestrator", "Resolve pending DRs")
```

The scribe scans `.owlbear/decisions/pending/`, classifies each file by its `response` field (`pending`, `approved`, `completed`, `needs-info`, `rejected`). It writes summaries to task bodies, unblocks approved/rejected/completed tasks, keeps `needs-info` tasks blocked and signals for re-dispatch, moves resolved files, and handles 5-day auto-resolution.

**NEEDS-INFO dispatch injection:** After the scribe returns, read `.owlbear/decisions/resolve-summary.json` via `readFile`. Extract the `needs_info` array — each entry is `{task_id, agent}`. Store as `needs_info_dispatches`. Delete the file after reading (stale-file mitigation). If the file is missing, treat as empty (graceful degradation). These are **injected into the dispatch plan in Step 2** after `pick_tasks` returns, bypassing the blocked-task filter. The originating agent is dispatched for the task, regardless of the task's current status.

If the scribe reports `PENDING` DRs awaiting user action, surface them in the cycle output (once per session, cycle 1 only):

```
Cycle 1 (DRs): Pending user response: #616 (616-scope-params-approval.md), ...
```

If the scribe reports errors, note them but proceed. If zero resolved, proceed.

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

**NEEDS-INFO injection:** Append `needs_info_dispatches` (from Step 1) to the dispatch list. Each entry uses the originating agent from the DR, not the status-to-agent mapping. Skip any that are already in the pick_tasks result.

**Non-Status-Triggered Agents:**

| Agent   | Trigger condition |
| ------- | ----------------- |
| memory-curator | Every 5th cycle (`cycle_count % 5 == 0`) |

If the processed dispatch list is empty, report to user and stop.

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

**Exception — memory-curator:** No task ID (dispatched every 5th cycle):

```
runSubagent("memory-curator", "Curate: Periodic curation", "Curation")
```

**Error handling — unified failure model:**

1. Check for rate-limit errors first (message contains "rate-limited", "rate_limited", or "rate limits"). Set `rate_limited = True`. Retry the dispatch once.
2. If the agent's return contains `FAIL`: retry the dispatch once.
3. If the agent crashes (non-rate-limit error): retry the dispatch once.
4. If the retry also fails (any of the above): **block the task** on the board via `edit_task(block="{agent} failed twice: {reason}")`. Include the error or FAIL reason in the block note.
5. After blocking, proceed to the next task in the wave.

### Tool-Failure Verification

When an agent's return contains `TOOL_UNAVAILABLE`, the agent could not reach a required tool or subagent (see `r-pipeline-protocol` → Tool Availability). This may be transient (one-off dispatch glitch) or systemic (VS Code extension degraded).

1. Re-dispatch the same agent on the same task immediately.
2. If the retry also returns `TOOL_UNAVAILABLE`: halt orchestration — "Tool availability degraded: {agent} cannot reach {tool_name}. Restart VS Code or check extension status."
3. If the retry succeeds: tools recovered. Continue the loop normally.

### Rate-Limit Handling

When a rate-limit error occurs:

1. Set `rate_limited = True`.
2. Retry the rate-limited dispatch once.
3. All subsequent `pick_tasks` calls use `wave_size=1` (one-way transition — no resume to parallel).

## Step 4 — Loop

After all dispatches:

1. Increment `cycle_count`.
2. **Re-plan:** Go to **Step 1**. The scribe processes any DRs that were responded during this cycle, then `pick_tasks` reads fresh board state.

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

- [ ] If a dispatch failed twice, the task is blocked on the board with a reason note
- [ ] If rate-limited at any point, all subsequent `pick_tasks` calls use `wave_size=1`
- [ ] Loop not stopped early — only empty waves or user intervention

## Known Pitfalls

- **File-based dispatch injection:** The orchestrator reads agent return values for outcome detection (FAIL, TOOL_UNAVAILABLE, success) but does NOT parse Channel A for routing decisions. After scribe returns, read `.owlbear/decisions/resolve-summary.json` for structured dispatch data — reading deposited state is infrastructure, not signal parsing.
- **NEEDS-INFO dispatch injection:** If the scribe signals NEEDS-INFO and the orchestrator does NOT inject those tasks into the dispatch plan, the task stays blocked forever. The user will repeatedly set `response: needs-info`, and the scribe will append duplicate `## Clarification Requested` sections each cycle.
- **Legacy wave planner drift:** Do not reintroduce manual bucket planning in this skill. `pick_tasks` is the single wave-assembly authority.
