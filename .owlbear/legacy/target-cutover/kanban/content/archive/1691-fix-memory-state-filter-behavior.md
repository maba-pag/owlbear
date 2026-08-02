---
id: 1691
title: Fix memory state filter behavior
status: archived
priority: medium
created: 2026-05-21T19:53:12.805354+02:00
updated: 2026-05-24T10:50:01.129289+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - memory
  - filters
  - behavior
parent:
depends_on: []
ac:
  - Reproduce the Memory state filter behavior with realistic mixed-state
    entries.
  - Fix confirmed state-filter failures so visible rows match selected states.
  - Update shown counts and empty states consistently with the active filter.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## User Feedback
Memory page: the state filter does not work.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current behavior defect.
- Value question: state filtering is central to memory review; if it fails, the filter panel loses trust and should be fixed before visual polish.
- Browser target: state filter with realistic entries across pending/curated/approved/deleted.

## Acceptance Criteria
- Reproduce the state filter failure in browser with realistic memory data.
- Fix confirmed behavior so selected states control visible entries.
- Ensure the shown count and empty states update with the active filter.

## Builder Evidence
- Reproduced the defect in Playwright with realistic pending/curated/approved/deleted memory entries: dispatching the PDS multi-select `change` event to select only `deleted` left the default pending/curated/approved rows visible.
- Root cause: `MemoryTab` listened for `update` events on `p-multi-select`, but PDS v4's React wrapper documents selection changes as `change` events. The state and category multi-selects now listen to both `update` and `change`.
- Added browser regression coverage in `e2e/memory-state-filter.spec.ts` proving the state filter controls visible rows and the `shown` count.
- Added jsdom regression coverage proving a PDS `change` event on the state filter yields only selected states and updates the header shown metric.
- Focused proof: `npx vitest run src/__tests__/MemoryTab_1671.test.tsx --testNamePattern="state filter|PDS change" --reporter=dot` -> 4 passed, 0 failed.
- Browser proof: `npx playwright test e2e/memory-state-filter.spec.ts --project=chromium` -> 1 passed, 0 failed.
- Memory suite proof: `npx vitest run src/__tests__/MemoryTab_1671.test.tsx src/__tests__/MemoryTab_1672.test.tsx --reporter=json --outputFile=/Users/markus/Projects/owlbear-dev/.owlbear/scratch/1691-vitest-memory-filter.json` -> 123 passed, 0 failed.
- Lint: `npx eslint src/pages/MemoryTab.tsx src/__tests__/MemoryTab_1671.test.tsx e2e/memory-state-filter.spec.ts` -> pass.
- Build: `npm run build` -> pass; existing Vite chunk-size warning only.
- Editor diagnostics clean for touched source, unit test, and e2e files.
- Desktop screenshot validation at 2560x1440: `.owlbear/scratch/1716-wide-cockpit/memory-state-filter-deleted.png` shows `deleted` selected, `4 entries`, `1 shown`, and only `Deleted Memory` visible. Capture reported 0 console errors, 0 page errors, and 0 request failures.