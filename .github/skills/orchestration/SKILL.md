---
name: orchestration
description: "Orchestration workflow: plan → track → dispatch → evaluate → execute → pipeline → loop → curate. Mechanical dispatch loop for the orchestrator agent."
---

# Orchestration Workflow

Step-by-step process for dispatching subagents based on a planner-generated WAVE_PLAN,
forwarding results for evaluation, and executing verdicts mechanically.

## Context budget

The orchestrator maintains constant-size context. These invariants prevent context
window bloat from killing long sessions:

- **No board state.** The planner reads the board each cycle. You never call `kanban-md list` or `kanban-md show`.
- **Raw signal passthrough.** Subagent Channel A signals are forwarded verbatim to the planner (evaluate mode). You do not accumulate, summarize, or interpret them.
- **Only `retry_count` persists.** Per task, per pipeline stage. An integer. Nothing else survives across retries.
- **Prior wave results discarded.** After the planner processes a wave's results, those results are gone. The next wave starts with only the WAVE_PLAN and fresh retry counters for new tasks.

## Signal contracts

### Planner → Orchestrator: WAVE_PLAN

```
WAVE_PLAN
WAVE 1:
  #{id} {agent_name} "{one-line AC summary}"
  #{id} {agent_name} "{one-line AC summary}"
WAVE 2:
  #{id} {agent_name} "{one-line AC summary}"
BLOCKED:
  #{id} "{reason}"
SKIPPED:
  #{id} gate:{gate_name} "{reason}"
END_PLAN
```

Parse rules:

- Extract waves as ordered groups of `(task_id, agent_name, summary)` tuples
- BLOCKED and SKIPPED sections are informational — report to user but do not act on them
- If WAVE_PLAN contains zero waves, report "nothing dispatchable" and stop

### Subagent → Orchestrator: Channel A signal

```
{VERDICT} #{id} -> {target_status} | {one-line evidence}
```

Do NOT parse, interpret, or act on this. Forward it verbatim to the planner (evaluate mode).

### Planner (evaluate mode) → Orchestrator: Verdict block

```
- task_id: {id}
- verdict: ADVANCE | RETRY | BLOCK | ESCALATE
- target_status: {status string}
- confidence: {0.0-1.0}
- reason: {one-line, evidence-backed}
- notes_for_next_agent: {context for downstream agent}
- retry_hint: {text, present only when verdict=RETRY}
```

Execute mechanically per Step 5 rules. No second-guessing.

## Step 1 — Plan

Dispatch the planner with the user's scope filter:

```
runSubagent("planner", "Plan: {scope_filter}", "Plan wave")
```

Receive the WAVE_PLAN. If the plan has zero waves (only BLOCKED/SKIPPED), report the
blocked/skipped tasks to the user and stop.

If the plan contains BLOCKED or SKIPPED tasks, summarize them once for the user (e.g.,
"3 tasks blocked, 2 skipped — see planner output for details").

**Ideation handling:** If the SKIPPED section contains tasks with `gate:status "ideation"`,
these are pre-pipeline tasks that need research. Dispatch the researcher for up to 2
ideation tasks per session:

```
runSubagent("researcher", "Research: #{id}", "Researcher #{id}")
```

After researchers return, re-plan (repeat Step 1) to pick up newly backlog'd tasks.

## Step 2 — Track

Create a `manage_todo_list` checklist from the WAVE_PLAN:

```
- [ ] Wave 1: #{id1} ({agent}), #{id2} ({agent})
- [ ] Wave 2: #{id3} ({agent})
- [ ] Pipeline stages for ADVANCE tasks
- [ ] Curate if any tasks completed
```

Initialize `retry_count = 0` for each task at each pipeline stage.

## Step 3 — Dispatch

For the current wave:

Issue ALL `runSubagent` calls for the wave in a **single parallel tool-call block** —
one task per call, never sequential.

**Dispatch prompt contains ONLY the task ID.** Subagents read their own AC via
`kanban\kanban-md.exe show {id}` in their skill Step 1. Never include AC text, file paths,
shell commands, pytest flags, or step-by-step procedures in the dispatch prompt.

Example — 3 tasks in parallel:

```
runSubagent("test-writer", "Write tests: #45", "Test-writer #45")
runSubagent("builder", "Build: #46", "Builder #46")
runSubagent("architect", "Architect Review: #47", "Architect #47")
```

For RETRY with hint from planner:

```
runSubagent("builder", "Build: #45 — Retry hint: fix TypeError in parse_section", "Builder #45 retry")
```

All calls run concurrently. You receive all results at once.

## Step 4 — Evaluate

Collect all Channel A signals from the completed wave. Dispatch the planner in
**evaluate mode**:

```
runSubagent("planner", "Evaluate wave:
Stage: {pipeline_stage}

Results:
{raw Channel A signal for task #id1}
{raw Channel A signal for task #id2}

Retry counts:
#id1: {retry_count}
#id2: {retry_count}", "Evaluate wave N")
```

Forward signals **verbatim**. Do not summarize, parse, or filter them.

## Step 5 — Execute

Apply each planner verdict mechanically:

| Verdict      | Action                                                                                                                                                     |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **ADVANCE**  | Proceed to next pipeline stage (Step 6). The agent that just completed already moved the task.                                                             |
| **RETRY**    | Re-dispatch the same agent with planner's `retry_hint` appended to the prompt. Increment `retry_count` for this task+stage. Go to Step 4 after completion. |
| **BLOCK**    | Report to user. The agent already blocked the task via `kanban-md edit --block`.                                                                           |
| **ESCALATE** | Present to user via `askQuestions`: task ID, failure history, planner's reason. Pause the task until user responds.                                         |

**Safety check:** If `retry_count >= 2` for any task and the planner did not ESCALATE,
override to ESCALATE. The max-2-retry rule is enforced here.

After executing all verdicts, update `manage_todo_list`.

## Step 6 — Pipeline

For each ADVANCE task, determine the next pipeline stage and repeat Steps 3–5:

| Just completed | Next stage | Next agent                                                       |
| -------------- | ---------- | ---------------------------------------------------------------- |
| test-writer    | —          | Re-plan (task is now in in-progress, planner dispatches builder) |
| builder        | review     | reviewer                                                         |
| reviewer       | docs       | writer                                                           |
| writer         | —          | Re-plan picks up for auditor in next cycle                       |
| architect      | —          | done for this cycle (task moves to todo)                         |
| researcher     | —          | done for this cycle (task moves to backlog)                      |

Each pipeline stage is a separate dispatch→evaluate→execute cycle. Do not batch
stages together — complete one stage's evaluation before starting the next.

Group tasks at the same pipeline stage for parallel dispatch (e.g., all tasks
needing review get dispatched to reviewers in one parallel block, then evaluated
together).

## Step 7 — Loop

After all tasks in the current wave have completed their pipeline stages (or been
BLOCKED/ESCALATED):

- **Next wave exists in WAVE_PLAN?** → Go to Step 3 with the next wave.
- **Board changed significantly?** → Go to Step 1 (re-plan). "Significantly" means: a BLOCKED task's dependency was resolved by this wave, or 3+ tasks changed status outside the current plan.
- **No work remains?** → Go to Step 8.

Discard all Channel A signals and planner verdicts from the completed wave.
Only `retry_count` for tasks still in-progress survives.

## Step 8 — Curate

If any tasks reached `done` during this session, dispatch the curator:

```
runSubagent("curator", "Curate: session complete, tasks #{ids} reached done", "Curation")
```

This is fire-and-forget — do not wait for the curator to finish before reporting.

Report final status to the user: tasks completed, tasks blocked, tasks escalated.

## Self-critique checklist

Before reporting session complete:

- [ ] Planner was dispatched with the user's scope filter (not a hardcoded filter)
- [ ] Every task in the WAVE_PLAN was dispatched (none silently dropped)
- [ ] ONE task per subagent call — no batching
- [ ] Dispatch prompts contained ONLY task IDs — no AC text, no commands, no procedures
- [ ] All Channel A signals forwarded verbatim to planner (evaluate mode) — no interpretation
- [ ] Planner verdicts executed mechanically — no second-guessing
- [ ] `retry_count` tracked per task per stage — no resets within a stage
- [ ] Max-2-retry safety check applied — ESCALATE overrides planner if needed
- [ ] Prior wave results discarded after processing — no accumulation
- [ ] `manage_todo_list` updated at every step transition
- [ ] Session summary reports all done/blocked/escalated tasks
