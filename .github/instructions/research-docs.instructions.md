---
applyTo: "docs/*.md"
description: "Guardrails for research/analysis documents — ensures findings become kanban tasks"
---

# Research Document Guardrails

Research and analysis documents (`docs/*.md`) are **supporting artifacts, never deliverables**. The deliverable is always kanban tasks and working code.

## Before writing a research doc

- Confirm the kanban task that owns this research (e.g., `#72 — Plan removal of GitHub Models API`).
- The task body should already describe what the research must produce (recommendations, migration steps, etc.).

## While writing

- Keep recommendations concrete and actionable. Vague findings ("consider doing X") are not useful.
- End the document with a **Follow-up Tasks** section listing every recommended action as a numbered task with: title, priority rationale, dependencies, and a one-line AC.

## After writing the research doc

**Move the owning task to `review`** (`kanban-md move <id> review`). The task is NOT done until:

1. Every recommended action from the doc exists as a kanban task (`kanban-md create ...`).
2. Each kanban task body links back to the research doc (e.g., `See docs/p7-research.md §4`).
3. You have verified the tasks exist on the board (`kanban-md list --compact`).
4. Move the owning task to `done` only after all follow-up tasks are on the board.

If the research doc recommends zero follow-up tasks, that's a red flag — explicitly state why no action is needed.

### Research task lifecycle

Tag research tasks with `research`. Flow: `backlog` → `todo` → `in-progress` (write doc) → `review` (create follow-up kanban tasks) → `done`.

## Common failure mode

Writing the doc, closing the kanban task, and moving on — without ever creating the follow-up tasks the doc recommends. This leaves actionable findings stranded in prose that nobody reads. **Don't do this.**
