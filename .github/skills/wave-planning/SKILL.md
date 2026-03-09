---
name: wave-planning
description: "Wave planning workflow: read board → build DAG → gate checks → produce DISPATCH_LIST. Used by the planner agent."
---

# Wave Planning

Step-by-step process for producing a dispatch list from a kanban board. The planner
reads the board, classifies tasks, checks gates, and outputs a flat list of tasks the
orchestrator should dispatch in parallel.

## Agent dispatch mapping

The planner assigns agents based on task status:

| Task status   | Dispatch agent | Pipeline action                                           |
| ------------- | -------------- | --------------------------------------------------------- |
| `backlog`     | `architect`    | Architecture review → move to `todo`                      |
| `todo`        | `test-writer`  | Write failing tests (RED phase) → move to `in-progress`   |
| `in-progress` | `builder`      | GREEN phase → move to `review`                            |
| `review`      | `reviewer`     | Quality verification → move to `docs`                     |
| `docs`        | `writer`       | Documentation gate → move to `done`                       |
| `done`        | `auditor`      | Exit gate verification → archive                          |

Tasks in `ideation` are never dispatched directly. `ideation` tasks need
research first (orchestrator routes to `researcher`).

**Non-implementation tasks:** Tasks tagged `research`, `docs`, `type:config`, or
`type:docs` still flow through the standard pipeline (`todo → test-writer → in-progress
→ builder`). The test-writer recognizes them and passes them through without writing
tests (see tdd-red skill, Step 1a). This keeps the dispatch table simple and avoids
special-case routing. The architect is responsible for tagging tasks correctly during
backlog → todo approval.

---

## Step 1 — Receive scope

The orchestrator passes a scope filter and optional failure context from the previous
cycle.

Apply the filter to `kanban\kanban-md.exe list --compact`. Examples:

- Tag filter: `kanban\kanban-md.exe list --compact --tag phase-3`
- Status filter: `kanban\kanban-md.exe list --compact --status todo,review`
- All: `kanban\kanban-md.exe list --compact`

If the scope returns 0 tasks, output an empty DISPATCH_LIST and stop.

**Failure context:** If the orchestrator reports tasks that failed in the previous cycle,
note them. If a task appears at the same status it was dispatched from last cycle (it
hasn't moved), flag it as STALE in the BLOCKED section — the agent ran but nothing
changed, which indicates a structural problem that a retry won't fix.

## Step 2 — Read board

For each candidate task from Step 1, run:

```
kanban\kanban-md.exe show {id}
```

Extract from each task: title, status, priority, tags, `depends_on` list, blocked
state, and acceptance criteria.

Use `manage_todo_list` to track progress through the remaining steps.

**Context budget:** If the scope contains more than 20 tasks, prioritize by: (1) critical
and needed priority first, (2) tasks closest to `done` in the pipeline (docs > review >
todo > backlog). Read details for the top 20 only — report the rest as SKIPPED with
gate: `scope_overflow`.

## Step 3 — Build DAG

Construct a dependency graph from task metadata:

- **Nodes** = in-scope tasks
- **Edges** = `depends_on` relationships (directed: dependency → dependent)

Classify each task:

| Classification | Condition                                                                        |
| -------------- | -------------------------------------------------------------------------------- |
| **Ready**      | All `depends_on` tasks are in `done` status AND task is not blocked              |
| **Blocked**    | At least one `depends_on` task is NOT `done`, or task has `--block` set          |
| **External**   | Has `depends_on` pointing to tasks outside the current scope that are not `done` |

External-blocked tasks go to the BLOCKED section with the out-of-scope dependency noted.

## Step 4 — Gate checks

For each **ready** task (not blocked, not external), run all 5 gate checks. A task must
pass ALL gates to be dispatched. Any failure → SKIPPED with the gate name and reason.

**Gate 1 — Status gate:**
Task status must match a dispatchable status in the agent dispatch mapping above.
Tasks in `ideation` fail this gate. Tasks in `in-progress` are dispatched to the builder.

**Gate 2 — Dependency gate:**
ALL tasks in `depends_on` must be in `done` status. No exceptions.

**Gate 3 — Atomicity gate:**
Title describes a single responsibility. Red flag: the word "and" joining unrelated
concerns (e.g., "Implement parser and update config"). Related concerns joined by "and"
are fine (e.g., "Read board and build DAG" — both are planning sub-steps).

**Gate 4 — TDD gate (safety net):**
For `in-progress` tasks, verify that the task body contains `## Test-Writer Notes`
(written by the test-writer during RED phase or pass-through). If present → gate passes.
If absent → something went wrong (task reached `in-progress` without the test-writer
running). Block the task and flag the anomaly.
As a fallback, a linked test task in `done` status also satisfies this gate.

This gate catches tasks that reached `in-progress` without proper test-writer processing
(e.g., manually moved tasks). Non-implementation tasks will have a pass-through note
instead of test details — both satisfy this gate. When the pipeline works correctly,
this gate is redundant — which is by design (belt-and-suspenders).

**Gate 5 — Clarity gate:**
Task body contains non-empty acceptance criteria with at least one bullet point
(`- ` or `- [ ]`) describing a verifiable criterion.
Tasks with empty or missing AC fail this gate.

## Step 5 — Filter, deconflict, prioritize

From the gate-passing tasks, build the dispatch list:

1. **Dependency filter:** Only include tasks whose ALL `depends_on` are `done`. Tasks
   that depend on other gate-passing tasks go to later cycles naturally — the orchestrator
   will re-plan after this batch completes, and those tasks will then be dispatchable.

2. **Builder domain deconfliction:** At most **one builder task per domain** in a single
   dispatch list. Builders modify existing code — two builders in the same domain risk
   file conflicts. All other agent types (reviewer, auditor, writer, architect,
   test-writer, researcher) are safe to parallelize within a domain because they either
   read only or create new files.

   Domain is determined by the task's `scope:{domain}` tag (see kanban-planner domain
   table). Tasks without a `scope:` tag are treated as unique domains (no conflict).

3. **Priority ordering:** Sort by: (1) `critical` > `needed` > `important` >
   `nice-to-have` > `someday`, (2) pipeline proximity — tasks closer to `done` first
   (docs > review > in-progress > todo > backlog), (3) tasks that unblock the most
   downstream dependents.

4. **Batch size cap:** Max 8 tasks per dispatch list. If more qualify, take the top 8
   by priority. The rest will be picked up in the next planning cycle.

## Step 6 — Output DISPATCH_LIST

Produce the structured output as the final response. Format:

```
DISPATCH_LIST
  #{id} {agent_name} "{one-line AC summary}"
  #{id} {agent_name} "{one-line AC summary}"
  #{id} {agent_name} "{one-line AC summary}"
BLOCKED:
  #{id} "{reason — which dependency is unmet or why blocked}"
SKIPPED:
  #{id} gate:{gate_name} "{reason — what failed}"
END_PLAN
```

**Rules:**

- `DISPATCH_LIST` and `END_PLAN` are the opening and closing delimiters
- Task lines: `#{id} {agent_name} "{one-line summary}"` — agent name from the dispatch mapping
- `BLOCKED:` section lists tasks with unmet dependencies, explicit blocks, or stale tasks
- `SKIPPED:` section lists tasks that failed gate checks, with the gate name
- If no tasks are dispatchable, output `DISPATCH_LIST` / `END_PLAN` with only BLOCKED/SKIPPED sections
- Gate names in SKIPPED: `status`, `dependency`, `atomicity`, `tdd`, `clarity`, `scope_overflow`

---

## Self-critique checklist

Before outputting:

- [ ] Scope filter was applied — not reading the entire board unfiltered (unless scope is "all")
- [ ] Every candidate task was read with `kanban\kanban-md.exe show {id}` (not just list output)
- [ ] DAG was built — tasks classified as ready, blocked, or external
- [ ] All 5 gate checks were run on every ready task
- [ ] No task in the DISPATCH_LIST failed any gate check
- [ ] At most one builder per `scope:{domain}` in the list
- [ ] Batch does not exceed 8 tasks
- [ ] Agent names match the dispatch mapping
- [ ] BLOCKED section includes all tasks with unmet dependencies, blocks, and stale flags
- [ ] SKIPPED section includes all gate-failed tasks with gate name and reason
- [ ] Failure context from orchestrator was checked for stale tasks
- [ ] Output uses DISPATCH_LIST format, not prose or markdown tables
- [ ] No `kanban-md move` commands were run
- [ ] No subagents were dispatched
- [ ] No source/test files were edited
