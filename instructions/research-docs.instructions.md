---
applyTo: "docs/research/*.md"
description: "Guardrails for research/analysis documents — ensures findings become kanban tasks"
---

# Research Document Guardrails

For the complete research procedure and task lifecycle, see the `research-workflow` skill.

## Document requirements

- Keep recommendations concrete and actionable. Vague findings ("consider doing X") are not useful.
- End the document with a **Follow-up Tasks** section listing every recommended action as a numbered task with: title, priority rationale, dependencies, and a one-line AC.
- Include a concrete `kanban-md create` command for each follow-up task and record the created task IDs after execution.
- Ensure each created task body links back to the research doc (for example, `See docs/research/p7.md §4`).
- If the research doc recommends zero follow-up tasks, explicitly state why no action is needed.

### When a finding requires a user decision

If a research finding recommends a feature, architectural direction, or approach that the user hasn't approved — and there is no clear winner among options — **do not create follow-up tasks**. Instead, use the **scribe** agent to check/create a decision request:

```
runSubagent("scribe", "Scribe: task_id={id}, mode=check-or-create, request_type=decision, agent=researcher, concern={description}", "Check/create DR for #{id}")
```

The scribe checks for duplicates, creates the DR if needed, and blocks the task automatically.

If no other unblocked tasks are available on the board, create the decision request, proceed with the recommended option, create the follow-up tasks, and mark the request `urgency: advisory` with `approved: auto`. The user can override later.
