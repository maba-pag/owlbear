---
id: 1701
title: Handle empty task detail sections
status: archived
priority: medium
created: 2026-05-21T20:22:56.770746+02:00
updated: 2026-05-24T10:50:01.258525+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - task-detail
  - information-architecture
parent:
depends_on: []
ac:
  - Audit empty Actions and Metadata sections in task detail.
  - Eliminate clickable no-op affordances and misleading empty boxes.
  - Provide useful empty states or hide sections until they have value.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
Task detail has an Actions box and a Metadata box that are empty. Metadata is clickable but does nothing. This may be because tasks are new, but it still feels weird.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current empty-state/affordance issue.
- Value question: empty sections should either be hidden, explain their value, or show disabled/coming context; clickable non-actions erode trust.
- Screenshot target: new task detail with empty actions/metadata; populated task if available.

## Acceptance Criteria
- Audit Actions and Metadata sections in empty and populated task states.
- Remove, collapse, or provide meaningful empty states for empty sections.
- Ensure clickable affordances have visible effects or are not interactive.

## Implementation
- Added a task-action availability check in the detail modal. Tasks with no backward move, no claim action, and no block action now show `No direct actions available.` instead of an empty action box.
- Replaced the task-detail Metadata accordion with a static Metadata section so it no longer looks clickable when there is no interactive behavior.
- Kept Metadata visible because the fields are useful audit context, but made absent values explicit: `Claimed` renders `Yes`/`No`, `Claimed at` renders `Not claimed` when absent, and `Dependency status` renders `None` when absent.
- Updated unit, browser, and information-architecture coverage for actionless tasks and the static metadata contract.

## Evidence
- Browser screenshots reviewed for populated light/dark task detail states and an actionless task state.
- The actionless state now has a readable empty-state sentence instead of a visually empty controls area.
- Metadata reads as plain task properties, contains no accordion/no-op affordance, and no longer has blank values.

## Validation
- `npx vitest run src/__tests__/DetailTab.test.tsx src/__tests__/DetailTab.information-architecture.test.tsx src/__tests__/TaskDetailModel.test.tsx src/__tests__/PdsMigration.test.tsx --reporter=dot` — 4 files passed, 157 passed, 4 skipped.
- `npx playwright test e2e/shell-sidecar-inspector.spec.ts -g "metadata|history control|task modal has identifiable actions|task detail opens in display mode" --project=chromium` — 4 passed.
- `npx playwright test e2e/lower-sections-screenshot-1701-1702.tmp.spec.ts --project=chromium` — 3 passed; screenshots reviewed before cleanup.
- `npx eslint src/components/DetailTab.tsx src/__tests__/DetailTab.test.tsx src/__tests__/DetailTab.information-architecture.test.tsx src/__tests__/TaskDetailModel.test.tsx e2e/shell-sidecar-inspector.spec.ts` — passed.
- `npm run build` — passed; existing Vite/Rolldown chunk-size warning remains.
- Editor diagnostics for touched files — no errors.