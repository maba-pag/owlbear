---
id: 1832
title: Review task edit action bar hierarchy
status: done
priority: important
created: 2026-05-24T11:55:10.047697+02:00
updated: 2026-05-24T23:25:36.635362+02:00
tags:
  - scope:cockpit-web
  - ux
  - detail-tab
  - interaction
  - discussion
parent: 1773
depends_on: []
ac:
  - Re-evaluate task detail edit action hierarchy against current Memory and 
    Ideas edit states.
  - Any approved change keeps Save and Cancel visible/reachable while reducing 
    their visual dominance.
  - Any approved change preserves task edit dirty-state, unsaved navigation 
    guard, and save behavior.
blocked: false
block_reason:
claimed_at: 2026-05-24T23:25:36.635362+02:00
archival_reason:
archival_refs: []
---
## Observation
The current task detail edit state promotes Save and Cancel into a large standalone bar between the task summary and editable fields. In the captured 1440x1000 workflow, the bar reads as a separate modal section: a black primary Save button and large secondary Cancel sit in a bordered/shadowed strip before the user reaches Title, Priority, Tags, body, dependencies, or parent.

## Evidence
- Screenshot: `.owlbear/scratch/1773-audit-continue/workflow-task-edit.png`
- Comparison screenshots: `.owlbear/scratch/1773-audit-continue/workflow-memory-edit.png`, `.owlbear/scratch/1773-audit-continue/workflow-ideas-dirty-edit.png`, `.owlbear/scratch/1773-audit-continue/workflow-task-detail.png`
- Runtime report: `.owlbear/scratch/1773-audit-continue/workflow-audit-report.json`
- Code surface: `serve/cockpit/web/src/components/TaskFieldsEditor.tsx` renders `task-detail-edit-actions`; `serve/cockpit/web/src/Shell.tsx` portals it into `task-detail-action-host` above the scrollable edit form.

## Observed User Impact
Task editing is a primary Cockpit workflow, but this state gives the save controls more visual weight than the task fields and breaks the otherwise compact action pattern used by Memory and Ideas. A user trying to edit the task has to visually step around an extra action block before the form begins, and the hierarchy suggests the action strip is the main content rather than a supporting toolbar.

## Boundary
This is an audit finding only. Do not implement without explicit user approval. The task should evaluate whether task edit actions should be normalized toward the compact toolbar/header treatment used elsewhere, while preserving the existing unsaved-change and save/cancel behavior.

## User Decision
Approved direction: implement a compact toolbar/header action area for the task edit state. Save and Cancel should remain visible and reachable, but the current standalone action strip should stop dominating the field hierarchy.

Implementation must preserve dirty-state signaling, unsaved-navigation protection, save/cancel behavior, and the existing task edit payload semantics.

## Implementation Outcome
Completed by compacting the task edit action area into a lighter toolbar/header treatment while keeping Save and Cancel visible. Dirty-state signaling, save/cancel behavior, unsaved-change plumbing, and existing payload semantics were preserved.

Evidence: DetailTab focused suite passed; affected bundle passed; full Cockpit frontend Vitest suite passed with 2390 passed, 0 failed, 11 skipped; frontend build passed.
