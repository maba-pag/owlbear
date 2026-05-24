---
id: 1838
title: Review task acceptance criteria edit affordance
status: research
priority: important
created: 2026-05-24T12:39:41.796906+02:00
updated: 2026-05-24T12:39:41.796906+02:00
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
archival_reason:
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
