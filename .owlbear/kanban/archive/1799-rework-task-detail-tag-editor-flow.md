---
id: 1799
title: Rework task detail tag editor flow
status: archived
priority: important
created: 2026-05-24T05:50:41.289265+02:00
updated: 2026-05-24T10:50:02.613101+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - kanban
  - forms
  - task-detail
  - discussion
parent: 1773
depends_on: []
ac:
  - Task detail edit mode shows the tag add input row before the tag chip list.
  - Tag input has a `Tags` label, compact treatment where available, and an `Add
    tags` placeholder.
  - Add button is compact and aligned with the input.
  - Existing tags remain visible as dismissible compact chips below the add row.
  - Save payload, dirty state, validation, and conflict draft behavior remain
    correct.
  - Screenshot proof captures the revised tag editor flow.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
User feedback from #1784 discussion: task detail edit tags still do not feel logical. Current flow is `Tags` + chip list, then `Add tag` label, then full-height empty field and compact `+ Add` button.

## Desired Direction
User imagines a more logical flow:
- Compact add-tag text input first, with `Tags` label above and `add tags` placeholder.
- Compact `+ add tag` button aligned with the input.
- Existing dismissible compact tag list below the input row.

## Value
Tags are an editor control, not a read summary followed by a separate large form field. The add action should be primary in edit mode while current tags remain visible and removable.

## User Direction
User asked to save and address this before starting other new work.

[[2026-05-24T06:04:00+02:00]]
## Implementation Proof
- Reworked task detail edit tags so the compact add row comes before the existing tag chips.
- The add input is labeled `Tags`, uses placeholder `Add tags`, disables spellcheck for tag tokens, and uses PDS compact treatment.
- Existing tags remain visible as compact dismissible chips below the add row.
- Save payload and conflict behavior stayed covered by focused task-detail regression suites.
- Focused tests passed: `npm test -- --run src/__tests__/DetailTab.test.tsx src/__tests__/DetailTab.conflict-resolution.test.tsx src/__tests__/DetailTab.invalid-parent.test.tsx src/__tests__/DetailTab.task-switch.test.tsx` -> 122 passed, 1 skipped.
- Lint passed: `npx eslint src/components/TaskFieldsEditor.tsx src/__tests__/DetailTab.test.tsx`.
- Build passed: `npm run build` (known Vite chunk-size warning only).
- Reader proof screenshot: `.owlbear/scratch/1716-wide-cockpit/1799-task-detail-tag-editor-1024.png` at the 1024 support floor. Metrics confirmed input label `Tags`, placeholder `Add tags`, compact input/button, spellcheck false, chip labels `["bug", "frontend"]`, and order `["tag-editor-row", "tag-chip-list"]`.

[[2026-05-24T06:04:10+02:00]]
Completed the revised task-detail tag editor flow with behavioral and reader proof.
