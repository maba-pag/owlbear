---
applyTo: "docs/research/*.md"
description: "Guardrails for research/analysis documents — ensures findings become kanban tasks"
---

# Research Document Guardrails

Research and analysis documents (`docs/research/*.md`) are **supporting artifacts, never deliverables**. The deliverable is always kanban tasks and working code.

For the complete research procedure and task lifecycle, see the `research-workflow` skill.

## Before writing a research doc

- Confirm the kanban task that owns this research (e.g., `#72 — Plan removal of GitHub Models API`).
- The task body should already describe what the research must produce (recommendations, migration steps, etc.).

## While writing

- Keep recommendations concrete and actionable. Vague findings ("consider doing X") are not useful.
- End the document with a **Follow-up Tasks** section listing every recommended action as a numbered task with: title, priority rationale, dependencies, and a one-line AC.

## After writing the research doc

The task is NOT done until:

1. Every recommended action from the doc has a concrete `kanban-md create` command in the Follow-up Tasks section **and the researcher executes them**, creating tasks at `ideation` status. This is safe — the architect still gates tasks before they become `todo`.
2. Each created task body links back to the research doc (e.g., `See docs/research/p7.md §4`).
3. The Follow-up Tasks section is complete and reflects which tasks were created (include the IDs after creation).

If the research doc recommends zero follow-up tasks, that's a red flag — explicitly state why no action is needed.

### When a finding requires a user decision

If a research finding recommends a feature, architectural direction, or approach that the user hasn't approved — and there is no clear winner among options — **do not create follow-up tasks**. Instead, create a **decision request** file in `docs/decisions/pending/`. See `decision-requests.instructions.md` for the format and workflow.

Block the current task with a reference to the decision request:

```powershell
kanban\kanban-md.exe edit {ID} --block "Decision pending: docs/decisions/pending/{id}-{slug}.md"
```

If no other unblocked tasks are available on the board, proceed with the recommended option, mark the decision as `auto-resolved`, and create the follow-up tasks. The user can override later.

## Common failure mode

Closing the kanban task without executing follow-up task creation commands. **Always
create all recommended follow-up tasks at `ideation` status before closing.** The
architect still gates them before `todo`.
