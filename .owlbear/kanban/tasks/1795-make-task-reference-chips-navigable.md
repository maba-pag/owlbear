---
id: 1795
title: Make task reference chips navigable
status: research
priority: important
created: 2026-05-24T03:09:50.740084+02:00
updated: 2026-05-24T03:26:45.789478+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - kanban
  - references
  - discussion
parent: 1773
depends_on: []
ac:
  - Parent and dependency references in task detail are rendered as intentional 
    chips/tags, not inert plain text.
  - Clicking a valid task reference opens the referenced task detail through 
    Cockpit navigation/API, not direct filesystem access.
  - Missing or archived references are represented safely and clearly.
  - No implementation begins until the user approves this task.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
While discussing #1789, user noted that dependencies and parent are both task references and should probably be clickable PTags/bubbles that open the respective task details. This is related but broader than edit-input structure because it affects read-mode navigation too.

## Current Interpretation
Observed workflow improvement candidate. Task references should behave like references, not inert numbers/text, especially inside task detail where jumping between related tasks is a natural workflow.

## Value
Clickable parent/dependency chips let users inspect related tasks without copying IDs or going back to the board/search. This improves dependency tracing and task navigation.

## Discussion Questions
- Should reference chips open the referenced task in the same modal, preserving a back stack?
- Should broken/missing references render differently and explain the issue?
- Should chips show only `#id`, or also title/status when available?

[[2026-05-24T03:26:45+02:00]]

## Discussion Decision
Use same-modal navigation with a local back stack for task reference chips. Valid parent/dependency chips should open the referenced task detail in place, and the user should be able to return to the previously viewed task. Prefer chips that include `#id`, title, and status when available; missing or inaccessible references should render safely.

