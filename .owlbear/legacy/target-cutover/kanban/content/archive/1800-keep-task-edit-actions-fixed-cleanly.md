---
id: 1800
title: Keep task edit actions fixed cleanly
status: archived
priority: medium
created: 2026-05-24T05:50:50.602184+02:00
updated: 2026-05-24T10:50:02.624763+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - kanban
  - task-detail
  - pds
  - discussion
parent: 1773
depends_on: []
ac:
  - Task detail edit Save/Cancel actions remain accessible during scrolling
    without covering form/detail content.
  - If PDS modal footer behavior can solve this, use it or align with its scroll
    model.
  - Do not replace the PDS modal solely for this issue.
  - Behavior is verified at the 1024px support floor.
  - Focused tests or screenshot proof cover the fixed action placement.
proof_bundle: behavioral+reader
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
User feedback from #1784 discussion: in Kanban task detail edit mode, Save/Cancel are not fixed as expected. They stay at the bottom end while scrolling and can move over detail content. User is fine with PDS modal footer behavior if that is the intended scroll model, and asked to fix only if possible with PDS tools; do not leave PDS behind for this.

## Current Interpretation
The current sticky action bar may be competing with the scrollable modal body instead of behaving like a stable modal footer.

## Value
Primary edit actions should remain available without visually covering content or breaking the PDS modal frame.

## User Direction
User asked to save and address this before starting other new work, with the constraint to keep PDS if possible and not replace it solely for this issue.

[[2026-05-24T06:33:00+02:00]]
## Implementation Proof
- Added a modal-level task detail action host inside the existing PDS modal, outside the scrollable content region.
- TaskFieldsEditor now portals real edit actions into that host when available, while retaining the inline top-sticky fallback for standalone renders.
- Save/Cancel remain available during scrolling without overlaying dependency or parent editors.
- Focused tests passed: `npm test -- --run src/__tests__/DetailTab.test.tsx src/__tests__/DetailTab.conflict-resolution.test.tsx src/__tests__/DetailTab.invalid-parent.test.tsx src/__tests__/DetailTab.task-switch.test.tsx src/__tests__/Shell.test.tsx src/__tests__/Shell.callbacks.test.tsx` -> 170 passed, 1 skipped.
- Lint passed: `npx eslint src/components/TaskFieldsEditor.tsx src/components/DetailTab.tsx src/Shell.tsx src/__tests__/DetailTab.test.tsx`.
- Build passed: `npm run build` (known Vite chunk-size warning only).
- Reader proof screenshot: `.owlbear/scratch/1716-wide-cockpit/1800-task-edit-actions-clean-1024.png` at the 1024 support floor. Metrics confirmed actions are hosted outside scroll content, no inline action duplicate exists, no overlap with reference editors, and the visible action rail reads `SaveCancel`.

[[2026-05-24T06:33:10+02:00]]
Completed the clean fixed task edit action placement with behavioral and reader proof.
