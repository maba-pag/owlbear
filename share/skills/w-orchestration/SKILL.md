---
name: w-orchestration
description: "Workflow: Orchestration — plan, dispatch, and verify agent execution cycles"
user-invocable: false
---

# Orchestration

Plan-dispatch-loop cycle for the orchestrator. The orchestrator maintains minimal context, dispatches agents in parallel waves, and loops until the board is clear.

## Context Budget

The orchestrator maintains constant-size context:

- **No board state.** The dispatcher reads the board each cycle.
- **No signal interpretation.** Subagents return a Channel A diagnostic line. Only check: did the agent return normally or crash?
- **No retry tracking state — except:** `stale_retried` (task IDs dispatched with retry_hint), `gate_warned` (task ID to count), `sequential_remaining` (rate-limit sequential counter).
- **Prior cycle results discarded.** Each cycle starts fresh with scope filter, crash IDs, and `stale_retried`.

## Signal Contracts

See `r-pipeline-protocol` → Communication for Channel A/B spec.

**Dispatcher output:** JSON with `dispatch` array (extract `(id, agent)` tuples, priority-sorted). Empty `dispatch` = nothing dispatchable, stop.

**Subagent output:** Channel A diagnostic line. Do NOT parse for routing. Only check: normal return vs crash.

## Step 0 — Resolve Pending Decision Requests

Before planning, call the **scribe** agent to process any resolved decision/action requests:

```
runSubagent("scribe", "Scribe: task_id=all, mode=resolve, agent=orchestrator", "Resolve pending DRs")
```

The scribe scans `docs/decisions/pending/`, processes files where `approved: true` or `completed: true`, writes summaries to task bodies, unblocks tasks, moves files to resolved, and handles 5-day auto-resolution.

If the scribe reports errors, note them but proceed. If zero resolved, proceed.

## Step 1 — Plan

Dispatch the dispatcher with the user's scope filter and any failure context:

```
runSubagent("dispatcher", "Plan: {scope_filter}", "Plan dispatch")
```

With failure context:

```
runSubagent("dispatcher", "Plan: {scope_filter}\n\nPrevious cycle: #{id} crashed twice; #{id2} stale, retried with hint", "Plan dispatch")
```

Failure context categories:

- **Crash failures:** `#{id} crashed twice`
- **Stale-retried IDs:** `#{id} stale, retried with hint`

Track `stale_retried`: add task IDs when dispatcher includes `retry_hint`; clear when dispatcher dispatches the task without `retry_hint` (task has moved).

If `dispatch` is empty, report to user and stop.

After receiving the plan, process `gate_warnings`:

1. Increment count in `gate_warned` for each ID in `gate_warnings`.
2. Remove IDs no longer in `gate_warnings`.

## Configuration

| Setting | Value | Notes |
|---------|-------|-------|
| **Wave size** | 4 | Max parallel dispatches per wave |

## Step 2 — Dispatch

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

**Dispatch prompt contains ONLY the task ID.** Subagents claim and read their own AC via `start_work` in their Step 0.

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

## Step 3 — Loop

After all dispatches:

1. **Failures exist?** Note as failure context for next cycle.
2. **Re-plan:** Go to Step 1. The dispatcher reads fresh board state.

Loop continues until the dispatcher returns empty `dispatch`. **Do not stop for any other reason.**

## Output Format

During execution:

```
Cycle 1 (Plan): Dispatching dispatcher with scope '{filter}'...
Cycle 1 (Wave 1/3): #101 (architect), #103 (builder), #105 (reviewer)
Cycle 1 (Done): 4/5 succeeded, 1 crashed (#112)
Cycle 1 (Gate Warning): #205 stuck at review gate for 2 cycles
```

Gate warning lines appear only when a task in `gate_warned` has count >= 2.

At end of session:

```
Session complete:
  Completed: #101, #103, #105
  Failed: #112 (crashed twice)
  Cycles: 2
```

## Verification Checklist

- [ ] Dispatcher was dispatched with the user's scope filter (not hardcoded)
- [ ] Every task in `dispatch` was dispatched (none silently dropped)
- [ ] Waves respect wave-size limit (unless in sequential mode)
- [ ] Wave assembly uses agent-type compatibility rules
- [ ] Failure context passed to dispatcher on next cycle
- [ ] `gate_warned` counts updated each cycle; IDs cleared when task exits gate_warnings
- [ ] Gate warnings logged when any task count >= 2
- [ ] Loop not stopped early — only empty plan ends the session

## Known Pitfalls

- **Parsing subagent signals:** The orchestrator does NOT parse Channel A for routing. Only check: normal return vs crash.
- **Stale_retried tracking:** Clear an ID when the dispatcher dispatches it without `retry_hint`. Forgetting to clear causes permanent stale marking.
- **Gate_warned accumulation:** Clear IDs no longer in `gate_warnings`. Otherwise counts grow indefinitely for resolved issues.
- **Wave consolidation:** Currently DEACTIVATED. Do not attempt to merge solo waves of the same restricted type.
- **Rate-limit cascade:** After entering sequential mode, complete 3 sequential dispatches before resuming parallel. Premature resumption triggers repeated rate limits.
- **Stopping the loop early:** The orchestrator's ONLY stop condition is an empty dispatch plan. Subagent errors, partial completions, and gate warnings do NOT stop the loop.
