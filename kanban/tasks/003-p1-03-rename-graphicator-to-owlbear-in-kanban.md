---
id: 3
title: 'P1-03: Rename Graphicator to OwlBear in kanban-planner.agent.md'
status: archived
priority: high
created: 2026-02-24T15:03:14.8567693+01:00
updated: 2026-02-27T09:59:53.6320806+01:00
started: 2026-02-24T15:16:56.397089+01:00
completed: 2026-02-27T09:59:53.6320806+01:00
tags:
    - phase-1
    - config
    - rename
class: standard
---

## Acceptance Criteria
- Replace ALL references to 'graphicator' in .github/agents/kanban-planner.agent.md with 'owlbear'
- This includes the good_example section referencing src/graphicator/models.py -> src/owlbear/models.py
- Preserve the agent structure, persona, workflow, boundaries, and examples exactly as-is otherwise

## Files to Edit
- .github/agents/kanban-planner.agent.md

## Verification
- grep -i 'graphicator' .github/agents/kanban-planner.agent.md returns zero results
- Agent file structure remains valid (YAML frontmatter + content)
