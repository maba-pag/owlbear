---
id: 1697
title: Clarify task detail edit/display split
status: archived
priority: medium
created: 2026-05-21T20:21:57.574554+02:00
updated: 2026-05-24T10:50:01.203325+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - information-architecture
parent:
depends_on: []
ac:
  - Audit task detail duplicate summary and editable fields.
  - Ensure dropdown/edit controls are not presented as passive read-only
    content.
  - Simplify or rename the Details section based on actual value.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
Task detail top box is perfect: task number, task name, priority, status. But below it is another box with the same info in editable fields under the title `Details`; it feels redundant. If not in edit mode, why is priority a dropdown?

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current information-architecture/control-mode issue.
- Value question: display mode should read as a polished detail page; edit controls should appear only when editing or clearly be inline-edit affordances.
- Screenshot target: task detail modal in preview/display mode and edit mode.

## Acceptance Criteria
- Audit duplicate title/priority/status presentation in task detail.
- Separate read-only display from edit controls or make inline editing intentionally clear.
- Remove redundant `Details` heading if it adds no meaning.

## Implementation
- Changed the task detail modal to open in display mode. The summary remains the source of truth for task number, title, status, and priority; the body panel now shows tags, task body, and relation fields as read-only content.
- Added an explicit `Edit details` PDS button. Title, priority, tag editing, body editing, dependencies, parent, and save/cancel controls appear only after that action.
- Renamed the section heading from generic `Details` to `Task details`, which better describes the panel once the top summary owns task identity.
- Kept the existing editor machinery for save/conflict handling, but made the production modal start with `defaultEditing={false}`. Direct editor tests can still exercise the edit surface without reworking unrelated mutation coverage.
- Updated browser and unit tests for the display-first flow, including stale task-editor tag-chip assertions now that editable tags are `p-tag-dismissible` chips.

## Evidence
- Browser screenshots reviewed in light and dark themes for both display and edit states.
- Display mode shows no visible title input or priority dropdown, only read-only tags/body/relations and a clear `Edit details` action.
- Edit mode shows the full form with stable `Title`, `Priority`, `Tags`, `Add tag`, `Task body`, `Depends on`, and `Parent` labels. No disappearing labels or copy mismatch from #1698/#1700 regressed.

## Validation
- `npx vitest run src/__tests__/DetailTab.test.tsx src/__tests__/DetailTab.body-preview-toggle.test.tsx src/__tests__/PdsMigration.test.tsx --reporter=dot` — 3 files passed, 133 passed, 4 skipped.
- `npx playwright test e2e/shell-sidecar-inspector.spec.ts -g "display mode|task editor labels remain visible|task body uses consistent copy" --project=chromium` — 3 passed.
- `npx playwright test e2e/filter-controls.spec.ts -g "Task-editor PDS compliance" --project=chromium` — 12 passed.
- `npx eslint src/components/TaskFieldsEditor.tsx src/components/DetailTab.tsx src/__tests__/DetailTab.test.tsx src/__tests__/DetailTab.body-preview-toggle.test.tsx src/__tests__/PdsMigration.test.tsx e2e/shell-sidecar-inspector.spec.ts e2e/filter-controls.spec.ts` — passed.
- `npm run build` — passed; existing Vite chunk-size warning remains.
- Editor diagnostics for touched files — no errors.