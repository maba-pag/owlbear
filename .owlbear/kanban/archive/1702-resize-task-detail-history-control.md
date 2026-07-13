---
id: 1702
title: Resize task detail history control
status: archived
priority: medium
created: 2026-05-21T20:23:09.378280+02:00
updated: 2026-05-24T10:50:01.273248+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - visual-system
parent:
depends_on: []
ac:
  - Audit task detail History control size relative to Edit/Preview and Save.
  - Adjust History visual weight to match secondary action importance.
  - Preserve discoverability and accessible interaction.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
The History button in task detail is huge, especially compared to Edit/Preview and even bigger than Save.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current visual hierarchy issue.
- Value question: History is a secondary view/action and should not visually outrank Save or mode controls.
- Screenshot target: task detail header/action row with History, Edit/Preview, Save.

## Acceptance Criteria
- Audit task detail action sizing and hierarchy.
- Resize or reposition History so it matches its secondary importance.
- Preserve discoverability and keyboard accessibility.

## Implementation
- Replaced the full-width History row treatment with a compact secondary PDS button in the task detail lower section.
- Kept the control visible and keyboard/click accessible, but removed the oversized band-like visual weight that made History outrank the primary edit/save flow.
- Added unit and browser assertions that the History control is compact while preserving the existing history-dialog behavior.

## Evidence
- Browser screenshots reviewed in light and dark task detail states after the final Metadata change.
- History now appears as a small secondary action below Metadata, visually subordinate to `Edit details` and the edit/save controls.
- The compact control remains discoverable and no longer stretches across the modal.

## Validation
- `npx vitest run src/__tests__/DetailTab.test.tsx src/__tests__/DetailTab.information-architecture.test.tsx src/__tests__/TaskDetailModel.test.tsx src/__tests__/PdsMigration.test.tsx --reporter=dot` — 4 files passed, 157 passed, 4 skipped.
- `npx playwright test e2e/shell-sidecar-inspector.spec.ts -g "metadata|history control|task modal has identifiable actions|task detail opens in display mode" --project=chromium` — 4 passed.
- `npx playwright test e2e/lower-sections-screenshot-1701-1702.tmp.spec.ts --project=chromium` — 3 passed; screenshots reviewed before cleanup.
- `npx eslint src/components/DetailTab.tsx src/__tests__/DetailTab.test.tsx src/__tests__/DetailTab.information-architecture.test.tsx src/__tests__/TaskDetailModel.test.tsx e2e/shell-sidecar-inspector.spec.ts` — passed.
- `npm run build` — passed; existing Vite/Rolldown chunk-size warning remains.
- Editor diagnostics for touched files — no errors.