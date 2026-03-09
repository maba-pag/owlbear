---
name: orchestration
description: "Orchestration workflow: plan → dispatch → loop. Mechanical dispatch loop for the orchestrator agent."
---

# Orchestration Workflow

The orchestrator is a mechanical dispatch loop. It asks the planner for a dispatch list,
runs all tasks in parallel, then re-plans from fresh board state. The board is the state
machine — subagents move their own tasks, and the planner reads reality each cycle.

## Context budget

The orchestrator maintains constant-size context:

- **No board state.** The planner reads the board each cycle. You never call `kanban-md list` or `kanban-md show`.
- **No signal interpretation.** Subagents return a short Channel A diagnostic line. You check only: did the agent return normally, or did it error/crash? You do not parse verdicts or route based on signals.
- **No retry tracking state.** If an agent crashes, you retry once immediately. If it crashes again, you note the failure and pass it to the planner in the next cycle. The planner sees the task hasn't moved and handles it.
- **Prior cycle results discarded.** After each plan→dispatch cycle, all results are gone. The next cycle starts fresh with only the scope filter and any failure context from the current cycle.

## Signal contracts

### Planner → Orchestrator: JSON dispatch plan

```json
{"dispatch":[{"id":101,"agent":"architect"},{"id":103,"agent":"builder"}],"blocked":[{"id":102,"reason":"dep #99 (review)"}]}
```

Parse rules:

- `dispatch` array: extract `(id, agent)` tuples. Priority-sorted by the planner.
- `blocked` array: informational — report to user but do not act on them.
- If `dispatch` is empty, report blocked tasks and stop.

### Subagent → Orchestrator: Channel A signal (diagnostic)

```
{VERDICT} #{id} -> {target_status} | {one-line evidence}
```

This is a **diagnostic convention** for transparency and logging. The orchestrator does
NOT parse this for routing decisions. The only thing you check: did the subagent return
normally (any response = success) or error out (crash/timeout = failure)?

Subagents move their own tasks on the board. The planner reads the board next cycle and
sees the updated state.

## Step 1 — Plan

Dispatch the planner with the user's scope filter and any failure context from
the previous cycle:

```
runSubagent("planner", "Plan: {scope_filter}", "Plan dispatch")
```

If there were failures from the previous cycle (agents that crashed twice):

```
runSubagent("planner", "Plan: {scope_filter}\n\nPrevious cycle failures:\n#{id}: agent crashed twice\n#{id}: agent crashed twice", "Plan dispatch")
```

Receive the JSON plan. If `dispatch` is empty (only blocked tasks), report the blocked
tasks to the user and stop.

If `blocked` mentions stale tasks (dispatched last cycle but unchanged), report
those to the user as potential issues.

## Step 2 — Dispatch

Dispatch the `dispatch` array in **waves of 4**. Take tasks in the order the planner
provided (priority order). For each wave:

1. Issue up to 4 `runSubagent` calls in a **single parallel tool-call block** —
   one task per call.
2. Wait for all calls in the wave to complete.
3. Handle errors (see below).
4. Move to the next wave of 4 (or fewer if remaining tasks < 4).

After all waves from this plan complete, proceed to Step 3.

**Dispatch prompt contains ONLY the task ID.** Subagents read their own AC via
`kanban\kanban-md.exe show {id}` in their skill Step 1. Never include AC text, file paths,
shell commands, pytest flags, or step-by-step procedures in the dispatch prompt.

Example — 6 tasks across 2 waves:

Wave 1:
```
runSubagent("architect", "Architect Review: #101", "Architect #101")
runSubagent("builder", "Build: #103", "Builder #103")
runSubagent("reviewer", "Review: #105", "Reviewer #105")
runSubagent("auditor", "Audit: #108", "Auditor #108")
```
[parallel — all return at once]

Wave 2:
```
runSubagent("test-writer", "Write tests: #110", "Test-writer #110")
runSubagent("researcher", "Research: #112", "Researcher #112")
```
[parallel — both return]

**Error handling:** If a subagent errors (crash, timeout, no response):

1. Retry the same dispatch **once** immediately.
2. If it errors again, record the task ID as a failure. Do NOT retry a third time.

After all dispatches complete (including any single retries), collect:

- **Successes:** tasks where the agent returned normally (regardless of what it said)
- **Failures:** tasks where the agent crashed twice

Update `manage_todo_list` with results.

## Step 3 — Loop

After all dispatches from Step 2 complete:

1. **Failures exist?** → Note them as failure context for the next planning cycle.
2. **Re-plan:** Go to Step 1. The planner reads fresh board state. Tasks that
   advanced are in their new status. Tasks that failed are unchanged (planner flags
   them as stale). Dependencies resolved by this cycle's successes unlock new tasks.
3. **Empty plan?** — If the planner returns an empty `dispatch` array:
   - If any tasks reached `done` during this session, dispatch the curator:
     ```
     runSubagent("curator", "Curate: session complete", "Curation")
     ```
   - Report final status to the user and stop.

The loop continues until the planner has nothing to dispatch.

## Self-critique checklist

Before reporting session complete:

- [ ] Planner was dispatched with the user's scope filter (not a hardcoded filter)
- [ ] Every task in `dispatch` was dispatched (none silently dropped)
- [ ] Waves of at most 4 parallel calls each
- [ ] ONE task per subagent call — no batching multiple tasks into one call
- [ ] Dispatch prompts contained ONLY task IDs — no AC text, commands, or procedures
- [ ] Errors retried exactly once — no infinite retry loops
- [ ] Failure context passed to planner on next cycle — failures not silently dropped
- [ ] `manage_todo_list` updated at every step transition
- [ ] Session summary reports all completed/blocked/failed tasks
