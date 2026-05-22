---
id: 1698
title: Fix task detail field label layout loss
status: done
priority: important
created: 2026-05-21T20:22:11.464140+02:00
updated: 2026-05-22T12:29:00+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - behavior
parent:
depends_on: []
ac:
  - Reproduce task detail label disappearance after priority and mode changes.
  - Fix label/control stability and alignment across edit interactions.
  - Use browser evidence to confirm labels remain visible and aligned.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
When changing priority, text labels disappear and alignment gets messed up: `Title`, `Depends on`, and `Parent` vanish immediately. Same when switching preview/edit; the priority text field also disappears.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current behavior/layout defect.
- Value question: edit controls must keep stable labels and alignment, especially when a user is changing task metadata.
- Browser target: task detail priority change, preview/edit toggle, dependency/parent fields.

## Acceptance Criteria
- Reproduce label disappearance and alignment shift in task detail.
- Fix field label stability across priority changes and mode switches.
- Verify no text/control overlap or vanishing labels in light/dark if applicable.

## Implementation
- Removed the `hide-label` mutation path from task detail PDS form controls. The old helper forced `hide-label`/`hideLabel` onto `PInputText`, `PSelect`, and `PTextarea`, which matched the observed runtime failure after PDS re-synced fields during priority and mode changes.
- Updated the PDS migration test contract to protect visible task-detail labels instead of the obsolete hidden-label migration assumption.
- Added a Playwright regression guard that opens the task detail modal, changes priority via the PDS `change` event, toggles the body editor to edit and back to preview, and verifies `Title`, `Priority`, `Add tag`, `Depends on`, `Parent`, and `Body` controls keep labels and never receive `hide-label`.

## Evidence
- Browser screenshots reviewed for light and dark mode after priority change plus body edit toggle. Labels remained visible and aligned: `Title`, `Priority`, `Tags`, `Add tag`, `Brief`, `Body`, `Depends on`, and `Parent` were all present without overlap or vanishing fields.
- Focused runtime guard: `npx playwright test e2e/shell-sidecar-inspector.spec.ts -g "task editor labels remain visible" --project=chromium` passed.

## Validation
- `npx vitest run src/__tests__/PdsMigration.test.tsx src/__tests__/DetailTab.test.tsx src/__tests__/DetailTab.valid-edits.test.tsx --reporter=dot` — 3 files passed, 133 passed, 4 skipped.
- `npx playwright test e2e/shell-sidecar-inspector.spec.ts --project=chromium` — 19 passed.
- `npx eslint src/components/TaskFieldsEditor.tsx src/__tests__/PdsMigration.test.tsx e2e/shell-sidecar-inspector.spec.ts` — passed.
- `npm run build` — passed; existing Vite chunk-size warning remains.
- Editor diagnostics for touched files — no errors.