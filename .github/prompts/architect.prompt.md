---
agent: architect
description: "Review researched tasks in backlog, refine AC, ensure architectural soundness, approve for development"
---

Architect Review: ${input:task_or_scope:Task ID or scope — e.g. 'task #40', 'all backlog', 'tag:phase-4'}

**Context for this run:**

- Read the board: `kanban\kanban-md.exe list --compact --status backlog`
- For each task in scope, read full details: `kanban\kanban-md.exe show {id}`
- If the task references a research doc, read it with `read_file`
- **Search existing codebase** — find related modules, patterns, interfaces
- For each task, decide: approve / refine AC / split / merge / block
- When refining: `kanban\kanban-md.exe edit {id} --body "updated AC"`
- When splitting: `kanban\kanban-md.exe create ...` for subtasks + update deps
- When approving: `kanban\kanban-md.exe move {id} todo`
- Produce an ArchitectReview report for each task
- **Never write code.** Your output is refined tasks, not implementations.
