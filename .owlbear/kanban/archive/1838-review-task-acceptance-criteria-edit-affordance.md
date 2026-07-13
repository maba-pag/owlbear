---
id: 1838
title: Review task acceptance criteria edit affordance
status: archived
priority: medium
created: 2026-05-24T12:39:41.796906+02:00
updated: 2026-05-24T23:32:21.768933+02:00
tags:
  - scope:cockpit-web
  - detail-tab
  - ux
  - editing
  - discussion
parent: 1773
depends_on: []
ac:
  - Evaluate whether task acceptance criteria should be editable from Cockpit 
    task detail.
  - Any approved change preserves existing body/tags/dependency/parent edit 
    behavior.
  - Any approved change treats AC as structured task contract data rather than 
    ad hoc body text unless explicitly approved otherwise.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
Task detail displays Acceptance Criteria as a first-class section, but entering task edit mode does not provide any control to add, remove, or edit those criteria. The edit form supports title, priority, tags, body, dependencies, parent, and block reason, while Acceptance Criteria remains a static read-only section below the form.

## Evidence
- Acceptance Criteria display screenshot: `.owlbear/scratch/1773-audit-continue/task-detail-ac-section.png`
- Acceptance Criteria in edit mode screenshot: `.owlbear/scratch/1773-audit-continue/task-detail-ac-section-in-edit-mode.png`
- Focused runtime report: `.owlbear/scratch/1773-audit-continue/task-detail-ac-edit-static-report.json`
- Runtime facts: in edit mode, `[data-region="task-acceptance-criteria"]` contains 3 `task-ac-item`s and 0 controls; the edit form exposes controls for title, tags, body edit, dependencies, and parent, but no AC/criterion control.
- Code surface: `serve/cockpit/web/src/components/DetailTab.tsx` renders `acceptanceCriteria` as a separate list section after `TaskFieldsEditor`; `serve/cockpit/web/src/components/TaskFieldsEditor.tsx` has no AC field in `TaskEditPayload` or form controls.
- API surface: `serve/cockpit/web/src/api/tasks.ts` and `serve/cockpit/src/owlbear_cockpit/routes/mutation.py` `EditRequest` models do not include an `ac` field.

## Observed User Impact
Acceptance criteria are the task contract users and agents use to decide whether work is complete. Cockpit lets users edit surrounding task metadata and body, but not the displayed criteria themselves. When AC need correction, addition, or cleanup, the UI offers no obvious path, which can push users back to raw task files or leave stale criteria visible in the primary task-detail surface.

## Boundary
This is an audit finding only. Do not implement without explicit user approval. The review should decide whether AC editing belongs in Cockpit task edit mode, whether body-only editing is intentional, or whether the API should expose a structured acceptance-criteria mutation.

## User Decision
Approved direction: implement structured acceptance-criteria editing in Cockpit task detail.

Implementation should treat AC as structured task contract data, not ad hoc body text, and must preserve existing title, priority, body, tag, dependency, parent, block-reason, and save/conflict behavior.

## Implementation Outcome
Completed with structured acceptance-criteria editing in task detail edit mode. The frontend sends `ac` as a structured array, the Cockpit mutation route accepts it, and the view passes it through to the kanban engine rather than treating criteria as body text.

Evidence: backend Cockpit ideas/mutation tests passed with 184 passed, including AC edit coverage; full Cockpit frontend Vitest suite passed with 2390 passed, 0 failed, 11 skipped; frontend build passed.

## Screenshot Follow-Up
Post-implementation screenshot capture showed the AC editor portal leaking into display mode and duplicating the criteria surface. Fixed by rendering the portal-backed AC editor only while task edit mode is active, while preserving the hidden edit form structure used by existing jsdom coverage.

Additional evidence: focused DetailTab/Shell Vitest proof passed with 77 passed, 1 skipped; refreshed screenshot `.owlbear/scratch/1773-task-detail-ac-edit.png` shows only the edit-mode AC editor, and `.owlbear/scratch/1773-decisions-open-task.png` shows display-mode AC without duplicate edit controls.
