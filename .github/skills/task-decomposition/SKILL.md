---
name: task-decomposition
description: "Task decomposition workflow: read plan → check board → decompose into atomic TDD-paired tasks → build dependency graph → assign priority/tags → generate kanban-md commands. Used by the kanban-planner agent."
---

# Task Decomposition

Step-by-step process for breaking complex features into atomic, test-driven kanban tasks.

## kanban-md Commands

| Action | Command |
|--------|---------|
| Board overview | `kanban\kanban-md.exe board --compact` |
| List existing tasks | `kanban\kanban-md.exe list --compact` |
| List by status | `kanban\kanban-md.exe list --compact --status S` |
| List by tag | `kanban\kanban-md.exe list --compact --tag T` |
| Read parent task | `kanban\kanban-md.exe show {id}` |
| Append plan to parent | `kanban\kanban-md.exe edit {id} -a "## Planning\n{content}" -t` |
| OUTPUT (not executed) | `kanban\kanban-md.exe create "P{n}-{nn}: TITLE" --priority P --tags T --depends-on ID --body "AC"` |

**Important:** The kanban-planner outputs `create` commands for user review — it does NOT execute them. Only `list`, `show`, `board`, and `edit` (for appending to a parent task) are executed directly.

See kanban-md skill for claiming protocol and pitfalls.

## Step 1 — Read the plan

Read input (free-text, plan doc section, or requirements). Identify phase number,
deliverables, implicit ordering.

Announce: "Decomposing: {name}. Expected: {N} tasks in {M} layers."

## Step 2 — Check board state

```powershell
kanban\kanban-md.exe list --compact
```

Note: highest existing ID, existing dependencies, current phase landscape.

## Step 3 — Decompose into atomic tasks

- **Single responsibility:** one module, one function, one config per task
- **Domain scoping:** classify each task against the domain table (see agent critical_rules). If a task touches modules from two domains, split it so each task has exactly one primary domain.
- **Testable:** clear pass/fail criterion
- **Small:** ≤ 2 hours of focused work
- **TDD pairs:** test task before implementation task

Ordering heuristic:

1. Model/schema tasks first (data structures)
2. Test tasks before their implementation counterparts
3. Integration tests after unit components are done
4. CLI/UI tasks last (they depend on core logic)

## Step 4 — Identify dependencies

Build explicit graph:

- Test → impl (impl depends on test)
- Schema → CRUD → agent → CLI (layered architecture)
- Cross-phase only when strictly necessary
- Every `--depends-on` references a concrete task ID

## Step 5 — Assign priority and tags

- **Priority:** count dependents (critical ≥ 3, needed 1–2, important otherwise)
- **Tags:** always `phase-{n}` + `scope:{domain}` from the domain table + at least one category tag

## Step 6 — Generate commands

**Naming convention:** `P{phase}-{nn}: {Title}` — phase inherited from plan,
sequence `nn` zero-padded, unique within phase.

One command per task:

```
kanban\kanban-md.exe create "P{phase}-{nn}: {Title}" --priority {p} --tags "{tags}" --depends-on {id} --body "{AC}"
```

Group by dependency layer (independent first, then dependents).

## Step 7 — Visualize dependencies

Mermaid diagram showing task relationships. Arrows: dependency → dependent.

## Self-critique checklist

Before submitting:

- [ ] Announced decomposition plan and expected count
- [ ] Every impl task has preceding test task with `--depends-on`
- [ ] No task has multiple responsibilities
- [ ] Sequence numbers unique and zero-padded
- [ ] Priority reflects blocking potential
- [ ] Tags include `phase-{n}` + category
- [ ] No cycles in dependency graph
- [ ] Mermaid diagram matches command list
- [ ] Total ≤ 20 tasks
- [ ] AC describes "done", not "how"
