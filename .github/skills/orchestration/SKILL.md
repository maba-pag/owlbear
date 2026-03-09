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

### Planner → Orchestrator: DISPATCH_LIST

```
DISPATCH_LIST
  #{id} {agent_name} "{one-line AC summary}"
  #{id} {agent_name} "{one-line AC summary}"
BLOCKED:
  #{id} "{reason}"
SKIPPED:
  #{id} gate:{gate_name} "{reason}"
END_PLAN
```

Parse rules:

- Extract task lines as `(task_id, agent_name, summary)` tuples
- BLOCKED and SKIPPED sections are informational — report to user but do not act on them
- If DISPATCH_LIST contains zero task lines, report "nothing dispatchable" and stop

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

Receive the DISPATCH_LIST. If the list has zero tasks (only BLOCKED/SKIPPED), report the
blocked/skipped tasks to the user and stop.

If the BLOCKED section mentions stale tasks (dispatched last cycle but unchanged), report
those to the user as potential issues.

**Ideation handling:** If the SKIPPED section contains tasks with `gate:status "ideation"`,
these are pre-pipeline tasks that need research. Dispatch the researcher for up to 2
ideation tasks per session:

```
runSubagent("researcher", "Research: #{id}", "Researcher #{id}")
```

After researchers return, re-plan (repeat Step 1) to pick up newly backlog'd tasks.

## Step 2 — Dispatch

Issue ALL `runSubagent` calls from the dispatch list in a **single parallel tool-call
block** — one task per call, never sequential.

**Dispatch prompt contains ONLY the task ID.** Subagents read their own AC via
`kanban\kanban-md.exe show {id}` in their skill Step 1. Never include AC text, file paths,
shell commands, pytest flags, or step-by-step procedures in the dispatch prompt.

Example — 4 tasks in parallel:

```
runSubagent("test-writer", "Write tests: #45", "Test-writer #45")
runSubagent("builder", "Build: #46", "Builder #46")
runSubagent("reviewer", "Review: #47", "Reviewer #47")
runSubagent("auditor", "Audit: #48", "Auditor #48")
```

All calls run concurrently. You receive all results at once.

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
3. **Empty plan?** → If the planner returns an empty DISPATCH_LIST:
   - If any tasks reached `done` during this session, dispatch the curator:
     ```
     runSubagent("curator", "Curate: session complete", "Curation")
     ```
   - Report final status to the user and stop.

The loop continues until the planner has nothing to dispatch.

## Self-critique checklist

Before reporting session complete:

- [ ] Planner was dispatched with the user's scope filter (not a hardcoded filter)
- [ ] Every task in the DISPATCH_LIST was dispatched (none silently dropped)
- [ ] ONE task per subagent call — no batching
- [ ] Dispatch prompts contained ONLY task IDs — no AC text, commands, or procedures
- [ ] Errors retried exactly once — no infinite retry loops
- [ ] Failure context passed to planner on next cycle — failures not silently dropped
- [ ] `manage_todo_list` updated at every step transition
- [ ] Session summary reports all completed/blocked/failed tasks
