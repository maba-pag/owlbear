---
name: w-orchestration
description: "Workflow: Orchestration — plan, dispatch, and verify agent execution cycles"
user-invocable: false
---

# Orchestration

Plan-dispatch-loop cycle for the orchestrator. The orchestrator maintains minimal context, dispatches agents in parallel waves, and loops until the board is clear.

## Context Budget

The orchestrator maintains constant-size context:

- **No board state.** `pick_tasks` reads the board each cycle via MCP tool call; no board state held in context between cycles.
- **No signal interpretation.** Pipeline subagents return a Channel A diagnostic line. Only check: did the agent return normally or crash? After scribe returns, read `resolve-summary.json` for structured dispatch data (see Step 1).
- **No retry tracking state — except:** `stale_retried` (task IDs dispatched with retry_hint), `last_dispatched` (dict[int, str] — task_id → status from previous pick_tasks result, max 20 entries), `sequential_remaining` (rate-limit sequential counter), `needs_info_dispatches` (list of {task_id, agent} pairs from scribe `resolve-summary.json`, cleared each cycle).
- **Prior cycle results discarded.** Each cycle starts fresh with scope filter, crash IDs, and `stale_retried`.

## Signal Contracts

See `r-pipeline-protocol` → Communication for Channel A/B spec.

**pick_tasks output:** Array of task objects (id, status, priority, title, tags). Empty array = nothing dispatchable, stop.

**Pipeline subagent output:** Channel A diagnostic line. Do NOT parse for routing. Only check: normal return vs crash. After scribe returns, read `resolve-summary.json` for structured dispatch data (see Step 1).

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

Call `pick_tasks` with the user's scope tag and a limit of 25:

```
pick_tasks(limit=25, tag="{scope_tag}")
```

Where `{scope_tag}` is the tag from the user's scope filter (e.g., `"phase-2"` from `"Orchestrate: tag:phase-2"`). Pass `tag=None` when scope is `"all"` or omitted.

If `pick_tasks` returns an empty array, report to user and stop.

**Crash failure exclusion:** Apply a set-difference filter — exclude any task_ids present in the current cycle's `crash_failures` set from the pick_tasks result.

**NEEDS-INFO injection:** Append `needs_info_dispatches` (from Step 1) to the dispatch list. Each entry uses the originating agent from the DR, not the status-to-agent mapping. Skip any that are already in the pick_tasks result or in `crash_failures`.

**Status-to-agent mapping:**

| Task status   | Dispatch agent |
| ------------- | -------------- |
| `research`    | researcher     |
| `backlog`     | architect      |
| `todo`        | test-writer    |
| `in-progress` | builder        |
| `review`      | reviewer       |
| `docs`        | doc-writer     |
| `done`        | auditor        |

**Non-Status-Triggered Agents:**

| Agent   | Trigger condition |
| ------- | ----------------- |
| curator | Every 5th cycle (handled in Step 3) |


**Stale detection:** Compare each pick_tasks result task against `last_dispatched`. If a task appears at the same status as its last_dispatched entry and is NOT in `stale_retried`:

1. Call `show_task(task_id)` to read the task body.
2. Extract a single-line retry_hint (120 chars max) from the last agent note section.
3. Include the `retry_hint` in the dispatch prompt for this task.
4. Add the task ID to `stale_retried`.

After processing, update `last_dispatched` with the current cycle's pick_tasks result (max 20 entries; evict oldest if over limit).

Track `stale_retried`: add task IDs when dispatched with `retry_hint`; clear an ID when the task appears at a *different* status in the next cycle's pick_tasks result (task has moved).

If the processed dispatch list is empty, report to user and stop.

## Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| **Wave size** | 4 | Max parallel dispatches per wave |

## Step 3 — Dispatch

Dispatch the `dispatch` array in parallel waves. Take tasks in priority order.

### Wave Assembly

**Agent-type compatibility:**

| Agent type | Category | May share wave with | Never with |
|------------|----------|---------------------|------------|
| auditor | restricted | light flex | builders, heavy flex, other auditors |
| builder | restricted | light flex, heavy flex | auditors, other builders |
| researcher, doc-writer, architect, planner, curator | light flex | any | — |
| reviewer, test-writer | heavy flex | builders, other flex | auditors |

**Assembly algorithm (four-bucket, minimize wave count):**

**Phase 1 — Draft the wave plan:**

1. Separate into four buckets: **auditors**, **builders**, **light flex**, **heavy flex**. Keep priority order.
2. **Auditor waves.** One auditor per wave. Fill remaining slots with light flex.
3. **Builder waves.** One builder per wave. Fill with light flex first, then heavy flex.
4. **Overflow waves.** Remaining light + heavy flex in new waves.
5. **Periodic curator.** Every 5th cycle, add curator to a wave with a remaining slot.
6. **Consolidation.** DEACTIVATED. Skip this step.
7. **Drop rule.** Solo non-auditor waves get dropped. Exception: keep the first if dropping would eliminate all non-auditor waves.

**Phase 2 — Execute the plan:**

8. Dispatch waves in order. No reordering.

### Dispatch Mechanics

**Dispatch prompt contains ONLY the task ID.** Subagents claim and read their own AC via `start_work` in their own Step 0.

**Exception — retry_hint:** Append to dispatch prompt:

```
runSubagent("builder", "Build: #103\nRetry context: {hint}", "Builder #103")
```

**Exception — curator:** No task ID:

```
runSubagent("curator", "Curate: Periodic curation", "Curation")
```

**Error handling:**

1. Check for rate-limit errors first (message contains "rate-limited", "rate_limited", or "rate limits"). Follow rate-limit sequential fallback.
2. For non-rate-limit errors: retry once.
3. If it errors again: record as failure.

### Rate-Limit Sequential Fallback

When a rate-limit crash occurs:

1. Switch to sequential mode. No more parallel calls in this wave.
2. Retry rate-limited agent(s) one at a time.
3. Continue dispatching sequentially until 3 sequential dispatches complete.
4. Resume parallel dispatch.

## Step 4 — Loop

After all dispatches:

1. **Failures exist?** Note as failure context for next cycle.
2. **Re-plan:** Go to **Step 1**. The scribe processes any DRs that were responded during this cycle, then `pick_tasks` reads fresh board state.

Loop continues until `pick_tasks` returns an empty list. **Do not stop for any other reason.**

## Output Format

During execution:

```
Cycle 1 (Plan): Running pick_tasks with tag='{scope_tag}'...
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

- [ ] Scribe called at start of **every** cycle (Step 4 loops to Step 1)
- [ ] Pending DRs reported to user in cycle 1 output
- [ ] `pick_tasks` called with the user's scope tag (not hardcoded)
- [ ] Every task in the dispatch list was dispatched (none silently dropped)
- [ ] Waves respect wave-size limit (unless in sequential mode)
- [ ] Wave assembly uses agent-type compatibility rules
- [ ] Crash failures excluded from dispatch list (set-difference applied)
- [ ] `resolve-summary.json` read via `readFile` after scribe returns, deleted after reading (Step 1)
- [ ] `needs_info_dispatches` from `resolve-summary.json` injected into dispatch list (Step 2)
- [ ] `last_dispatched` updated with current cycle's pick_tasks result
- [ ] Loop not stopped early — only empty dispatch list ends the session

## Known Pitfalls

- **File-based dispatch injection:** The orchestrator does NOT parse pipeline agents' Channel A for routing. Only check: normal return vs crash. After scribe returns, read `.owlbear/decisions/resolve-summary.json` for structured dispatch data — reading deposited state is infrastructure, not signal parsing.
- **NEEDS-INFO dispatch injection:** If the scribe signals NEEDS-INFO and the orchestrator does NOT inject those tasks into the dispatch plan, the task stays blocked forever. The user will repeatedly set `response: needs-info`, and the scribe will append duplicate `## Clarification Requested` sections each cycle.
- **Stale_retried tracking:** Clear an ID when the task appears at a *different* status in the next cycle's pick_tasks result (task has moved). Forgetting to clear causes permanent stale marking.
- **last_dispatched cap:** Maintain max 20 entries; evict oldest when over limit to prevent context growth.
- **Wave consolidation:** Currently DEACTIVATED. Do not attempt to merge solo waves of the same restricted type.
- **Rate-limit cascade:** After entering sequential mode, complete 3 sequential dispatches before resuming parallel. Premature resumption triggers repeated rate limits.
- **Stopping the loop early:** The orchestrator's ONLY stop condition is an empty dispatch list. Subagent errors and partial completions do NOT stop the loop.
