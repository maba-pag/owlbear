---
name: w-task-decomposition
description: "Workflow: Task decomposition — break features into atomic TDD-paired tasks with dependency graphs"
user-invocable: false
---

# Task Decomposition

Break complex features into atomic, test-driven kanban tasks with explicit dependency graphs and priority assignments.

**Kanban operations:** See `h-mcp-kanban` skill — section `## Agent Lifecycle Pattern`.

## Step 0 — Setup

Read `r-pipeline-protocol` skill if not already loaded.

**Claiming:** When **orchestrator-dispatched** (parent task ID provided), claim the parent task via `start_work` — it returns the task body, making a separate `show_task` call redundant. When **user-invoked**, read the task via `show_task` without claiming.

**Execution mode:** Determined by the caller's prompt prefix (mirrors `planner.agent.md` three-tier convention):
- **`Plan and create: #{id} — ...`** → dispatch mode: execute `create_task` calls directly and report created IDs.
- **`Plan: ...`** → user mode: present planned breakdown → `askQuestions` approval → create on approve. See Step 5b.
- **No prefix detected** → fallback: if pipeline markers are present, abort with an error asking the caller to use `Plan and create:` prefix; otherwise default to user mode.

## Step 1 — Read the Plan

Read input (free-text, plan doc section, or requirements). Identify phase number, deliverables, and implicit ordering.

If the parent task body contains a `## Brief` or `## Problem` section (Brief artifact, produced by ideation), use it to derive scope, investment tier, and approach constraints for decomposition. Include `Brief: see parent #{id}` reference in each child task body.

Announce: "Decomposing: {name}. Expected: {N} tasks in {M} layers."

## Step 2 — Check Board State

Read the current board via `list_tasks` to note: highest existing ID, existing dependencies, and current phase landscape.

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

## Step 5b — Approval (user mode only)

Skip this step if invoked in dispatch mode (`Plan and create:` prefix) — proceed directly to Step 6.

Present the planned breakdown inline in the chat:
- Task list table (title, priority, dependencies, tags)
- Dependency graph (Mermaid)
- Summary: total count, dependency layers, phase

Call `askQuestions` with two options:
- "Approve — create all {N} tasks"
- "Reject — cancel without creating tasks"

**On approve:** proceed to Step 6.  
**On reject:** stop, report cancellation to the user. Do NOT call `create_task`.

## Step 6 — Create Tasks

**Naming convention:** `P{phase}-{nn}: {Title}` — phase inherited from plan, sequence `nn` zero-padded, unique within phase.

Create each task via `create_task` with title, priority, status `research`, tags, depends_on, and body containing AC.

Group by dependency layer (independent first, then dependents). Record created task IDs for the report.

If dispatched with a parent task ID, include the planning summary in your `end_work` note.

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
