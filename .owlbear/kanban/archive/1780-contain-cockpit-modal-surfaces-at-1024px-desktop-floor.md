---
id: 1780
title: Contain Cockpit modal surfaces at 1024px desktop floor
status: archived
priority: important
created: 2026-05-24T00:54:16.614690+02:00
updated: 2026-05-24T10:50:02.357907+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - visual-proof
  - discussion
  - desktop-floor
parent: 1773
depends_on:
  - 1779
ac:
  - At 1024px, task detail modal content and all primary actions are fully
    inside the viewport without horizontal clipping.
  - At 1200px, task detail modal content is fully inside the viewport without
    horizontal clipping.
  - At 1024px, the Decision resolver surface and Close/Submit actions are fully
    inside the viewport without horizontal clipping.
  - No product implementation begins until the user approves this task.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
#1773 desktop evidence rerun after #1779 shows supported-width modal surfaces can sit slightly beyond the right viewport edge at the 1024px floor and, for task detail, also at 1200px.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1773-desktop-interaction-sweep-contact-sheet.png`
- `1773-desktop-1024-kanban-task-detail.png`: task detail window right edge at 1044 on a 1024px viewport; Edit details button right edge at 1031.
- `1773-desktop-1200-kanban-task-detail.png`: task detail window right edge at 1212 on a 1200px viewport.
- `1773-desktop-1024-decisions-resolver.png`: resolver surface and Close Modal button right edge at 1044 on a 1024px viewport.

## Current Interpretation
Observed supported-width product harm, not a sub-1024 stress note. The visual effect is modest but real: modal content is horizontally clipped at the product support floor, and the issue appears shared across PDS modal surfaces rather than isolated task content.

## Decision Needed
Discuss whether to fix this now by constraining modal child width/centering at 1024-1200, or defer if the team accepts slight edge clipping at the floor.

## Non-Issue Boundary
Long edit forms extending below the viewport were not filed as bugs from this sweep because primary controls remain visible and the form is naturally scrollable.

[[2026-05-24T01:00:46+02:00]]
## Effort Estimate
Likely small: 2 product files (`Shell.tsx`, `ResolveModal.tsx`) and roughly 2-8 product LOC if the fix is just modal width/centering classes. Add focused coverage at the 1024px floor, likely 20-40 test LOC. Budget 30-60 minutes mainly for PDS modal geometry verification with screenshots, not implementation complexity.

## Risk
Low-to-moderate. The source change is small, but PDS Modal centering/slot geometry has surprised us before, so screenshot proof at 1024, 1200, 1440, and 2000px is required.

[[2026-05-24T01:08:07+02:00]]
## Implementation
Approved by user and implemented. Tightened the task detail and Decision resolver modal surface width budgets at the desktop floor so PDS modal offset no longer clips the right edge.

Changed files:
- `serve/cockpit/web/src/Shell.tsx`
- `serve/cockpit/web/src/components/ResolveModal.tsx`
- `serve/cockpit/web/src/__tests__/Shell.callbacks.test.tsx`
- `serve/cockpit/web/e2e/shell-layout-1606.spec.ts`

## Verification
- `npm test -- --run src/__tests__/Shell.callbacks.test.tsx src/__tests__/ResolveModal.test.tsx`: passed, 32 tests.
- `npx eslint src/Shell.tsx src/components/ResolveModal.tsx src/__tests__/Shell.callbacks.test.tsx e2e/shell-layout-1606.spec.ts`: passed.
- `npx playwright test e2e/shell-layout-1606.spec.ts`: passed, 15 tests including 1024px modal containment coverage.
- `npm run build`: passed; existing Vite large chunk warning remains.
- Post-fix desktop screenshot sweep: passed for #1780 modal containment. Remaining metrics flags are long edit forms extending below viewport with primary actions visible; not part of #1780.

## Post-Fix Geometry
- 1024 task detail window: left=148, right=980; Edit details button right=967.
- 1200 task detail window: left=172, right=1180; Edit details button right=1167.
- 1024 Decision resolver surface: left=148, right=980; Submit right=838; Close right=980.
- 1200 Decision resolver surface: left=172, right=1092; Submit right=950; Close right=1092.

## Proof Artifacts
- `.owlbear/scratch/1716-wide-cockpit/1773-desktop-interaction-sweep-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1773-desktop-interaction-sweep-metrics.json`
- `.owlbear/scratch/1716-wide-cockpit/1780-postfix-desktop-sweep-run.log`
