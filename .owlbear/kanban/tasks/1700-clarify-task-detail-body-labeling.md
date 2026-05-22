---
id: 1700
title: Clarify task detail body labeling
status: done
priority: important
created: 2026-05-21T20:22:45.699635+02:00
updated: 2026-05-22T12:55:00+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - copy
parent:
depends_on: []
ac:
  - Audit `Brief` and `Body` labels in task detail preview/edit modes.
  - Choose consistent wording that matches the actual task content.
  - Remove or align labels so mode changes do not introduce contradictory copy.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Why does task detail say `Brief` above the task body? In edit mode a text `Body` suddenly appears below it.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current copy/labeling confusion.
- Value question: labels should match the underlying task artifact and user mental model; preview/edit labels should not contradict each other.
- Screenshot target: task detail body preview and edit mode.

## Acceptance Criteria
- Audit task body labels in preview and edit modes.
- Choose consistent wording for task body/brief content.
- Remove duplicate or contradictory labels across mode switches.

## Implementation
- Replaced the task body section copy from `Brief` with `Task body` so the label matches the persisted task field and user mental model.
- In edit mode, removed the separate section label and let the PDS textarea expose the same `Task body` label. This avoids the old preview/edit contradiction where the section said `Brief` and the control suddenly said `Body`.
- Added unit and browser regression coverage that verifies `Brief` is absent and the PDS textarea label remains `Task body` after switching modes.

## Evidence
- Browser screenshots reviewed in light and dark modes for both preview and edit states. Preview shows a single `Task body` label above rendered markdown; edit mode shows the PDS textarea labeled `Task body`. No `Brief`/`Body` mismatch remains, and the #1698 label-stability behavior still holds.

## Validation
- `npx vitest run src/__tests__/DetailTab.test.tsx --reporter=dot` — 1 file passed, 52 passed, 1 skipped.
- `npx playwright test e2e/shell-sidecar-inspector.spec.ts -g "task body uses consistent copy|task editor labels remain visible" --project=chromium` — 2 passed.
- `npx eslint src/components/TaskFieldsEditor.tsx src/__tests__/DetailTab.test.tsx e2e/shell-sidecar-inspector.spec.ts` — passed.
- `npm run build` — passed; existing Vite chunk-size warning remains.
- Editor diagnostics for touched files — no errors.