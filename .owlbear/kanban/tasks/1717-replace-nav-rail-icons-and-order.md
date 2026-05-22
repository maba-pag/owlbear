---
id: 1717
title: Replace nav rail icons and order
status: done
priority: important
created: 2026-05-22T01:01:09.630391+02:00
updated: 2026-05-22T14:32:49+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - navigation
  - icons
parent:
depends_on: []
ac:
  - Replace nav rail icon mapping with Kanban steering-wheel, Decisions route,
    Memory brain, Ideas user-manual when supported by PDS.
  - Reorder route navigation so Memory appears before Ideas.
  - Preserve accessible labels, active-page state, pending badges, keyboard
    order, and route URLs.
  - Validate with desktop screenshots at widths >= 1200px.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
The menu bar icons are not ideal. Suggested Porsche icon mapping: Kanban `steering-wheel`, Decisions `route`, Memory `brain`, Ideas `user-manual`. Memory should appear above Ideas instead of after it.

## Evaluation Notes
- Classification: user-observed navigation clarity issue, not theoretical.
- Impact: hurts Cockpit now because icon-only navigation depends on recognizable destination symbols and predictable ordering.

## Acceptance Criteria
- Replace nav rail icon mapping with Kanban `steering-wheel`, Decisions `route`, Memory `brain`, Ideas `user-manual` when supported by PDS.
- Reorder route navigation so Memory appears before Ideas.
- Preserve accessible labels, active-page state, pending badges, keyboard order, and route URLs.
- Validate with desktop screenshots at widths >= 1200px.

## Builder Evidence
- Reordered `routeConfig` to render Kanban, Decisions, Memory, then Ideas while preserving route URLs and labels.
- Updated Shell's semantic nav-surface icon mapping to PDS v4 icons: `steering-wheel`, `route`, `brain`, and `user-manual`.
- Added a regression assertion covering #1717 nav order and rendered `p-icon` names.
- Focused proof: `npx vitest run src/__tests__/BoardVisualDesign.test.tsx --testNamePattern="#1717" --reporter=json --outputFile=/Users/markus/Projects/owlbear-dev/.owlbear/scratch/1717-vitest-nav-focused.json` -> 1 passed, 0 failed.
- Regression proof: `npx vitest run src/__tests__/NavRailButtons_1642.test.tsx src/__tests__/NavBadge_1646.test.tsx src/__tests__/MemoryTab_1672.test.tsx src/__tests__/routes_1639.test.tsx --reporter=json --outputFile=/Users/markus/Projects/owlbear-dev/.owlbear/scratch/1717-vitest-nav-regression.json` -> 130 passed, 0 failed.
- Lint: `npx eslint src/Shell.tsx src/routes.ts src/__tests__/BoardVisualDesign.test.tsx` -> pass.
- Build: `npm run build` -> pass; existing Vite chunk-size warning only.
- Editor diagnostics clean for Shell, routes, and the touched test file.
- Desktop screenshot validation at 2560x1440: `.owlbear/scratch/1716-wide-cockpit/kanban-viewport.png`. Capture reported 0 console errors, 0 page errors, and 0 response errors.