---
name: w-task-decomposition
description: "Workflow: Task decomposition — break features into atomic TDD-paired tasks with dependency graphs"
user-invocable: false
---

# Task Decomposition

Break complex features into atomic, test-driven kanban tasks with explicit dependency graphs and priority assignments.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

This skill does NOT claim a task — the planner creates tasks rather than processing one through the pipeline. If dispatched with a parent task ID, read the parent via `show_task` to understand scope and context.

**Execution mode:** When **dispatcher-dispatched** (parent task ID provided), execute `create_task` calls directly and report created IDs. When **user-invoked**, output planned tasks for review — do NOT execute them.

## Step 1 — Read the Plan

Read input (free-text, plan doc section, or requirements). Identify phase number, deliverables, and implicit ordering.

Announce: "Decomposing: {name}. Expected: {N} tasks in {M} layers."

## Step 2 — Check Board State

Read the current board via `list_tasks` to note: highest existing ID, existing dependencies, and current phase landscape.

> **MCP equivalent:** `list_tasks()` (with optional `status`, `tag`, or other filters)

## Step 3 — Decompose into Atomic Tasks

Each task must be:

- **Single responsibility:** one module, one function, one config
- **Domain scoped:** one primary domain per task (see `r-architecture-standards` domain taxonomy). Multi-domain tasks must be split.
- **Testable:** clear pass/fail criterion
- **Small:** ~2 hours of focused work max
- **TDD paired:** test task before implementation task

Ordering heuristic:

1. Model/schema tasks first (data structures)
2. Test tasks before their implementation counterparts
3. Integration tests after unit components
4. CLI/UI tasks last (depend on core logic)

## Step 4 — Build Dependency Graph

Build an explicit dependency graph:

- Test depends on nothing (or prior schema)
- Implementation depends on its test task
- Schema, CRUD, agent, CLI layers form a natural hierarchy
- Cross-phase dependencies only when strictly necessary
- Every dependency references a concrete task ID

## Step 5 — Assign Priority and Tags

- **Priority:** count dependents (critical if 3+, needed if 1-2, important otherwise)
- **Tags:** always `phase-{n}` + `scope:{domain}` + at least one category tag

See `r-project-standards` for the full priority scheme and tag taxonomy.

## Step 5a — Validate Planned Tasks

Before creating any task, validate every planned task:

- **Reject `TEMP-*` titles** — placeholder artifacts, not legitimate tasks.
- **Reject empty bodies** — no AC or scoped content means the task is invalid.

If a planned task fails: refine the title and body or stop. Never create a placeholder task.

## Step 6 — Create Tasks

**Naming convention:** `P{phase}-{nn}: {Title}` — phase inherited from plan, sequence `nn` zero-padded, unique within phase.

Create each task via `create_task` with title, priority, status `ideation`, tags, depends_on, and body containing AC.

> **MCP equivalent:** `create_task(title="...", priority="...", status="ideation", tags=[...], depends_on=[...], body="...")`

Group by dependency layer (independent first, then dependents). Record created task IDs for the report.

If dispatched with a parent task ID, append the planning summary to the parent body via `edit_task` (with `append_body` and `timestamp=True`).

## Step 7 — Visualize Dependencies

Produce a Mermaid diagram showing task relationships. Arrows: dependency toward dependent.

## Step 8 — Advance

If dispatched with a parent task ID, advance via `end_work` to release the claim and move status.

Return Channel A signal per `r-pipeline-protocol`.

## Output Template

Append to parent task body (if dispatched with parent ID):

```
## Planning
### Decomposition: {name}
- Tasks created: {N}
- Dependency layers: {M}
- Phase: {phase}

### Task List
| ID | Title | Priority | Depends On | Tags |
|----|-------|----------|------------|------|
| {id} | {title} | {priority} | {deps} | {tags} |

### Dependency Graph
{Mermaid diagram}
```

## Verification Checklist

- [ ] Announced decomposition plan and expected count
- [ ] Every impl task has a preceding test task with dependency
- [ ] No task has multiple responsibilities
- [ ] Sequence numbers unique and zero-padded
- [ ] Priority reflects blocking potential
- [ ] Tags include `phase-{n}` + category
- [ ] No cycles in dependency graph
- [ ] Mermaid diagram matches task list
- [ ] Total 20 tasks or fewer
- [ ] AC describes "done", not "how"
- [ ] No `TEMP-*` titles or empty bodies created

## Known Pitfalls

- **Forgetting TDD pairs:** Every implementation task needs a preceding test task. Missing these causes pipeline violations downstream.
- **Cross-phase dependencies:** These create long dependency chains that block parallelism. Use only when strictly necessary.
- **Placeholder tasks:** Never create tasks with vague titles or empty bodies — they accumulate as board noise.
- **Body content in `create_task`:** Keep AC concise. For complex multi-line AC, use the temp-file pattern (see `h-mcp-kanban`).
