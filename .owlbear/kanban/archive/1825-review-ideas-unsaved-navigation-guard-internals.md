---
id: 1825
title: Review Ideas unsaved-navigation guard internals
status: archived
priority: important
created: 2026-05-24T11:03:07.492170+02:00
updated: 2026-05-24T11:26:04.366401+02:00
tags:
  - scope:cockpit-web
  - ux
  - api-boundary
  - ideas
  - discussion
parent: 1773
depends_on: []
ac:
  - Ideas unsaved-navigation behavior is reviewed against React Router public
    APIs and Cockpit navigation patterns.
  - The decision records whether UNSAFE_NavigationContext and navigator method
    mutation are acceptable or should be replaced.
  - Any approved change preserves the existing unsaved-change warning for route
    changes and browser/back navigation where supported.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
The Ideas tab implements its unsaved-navigation guard with React Router internals and direct navigator mutation. It imports `UNSAFE_NavigationContext`, reads `navigationContext.navigator`, uses an optional `.block()` method when present, and falls back to replacing `navigator.push`, `navigator.replace`, and `navigator.go` while the note is dirty.

## Evidence
- `serve/cockpit/web/src/pages/IdeasPage.tsx` imports `UNSAFE_NavigationContext` from `react-router` and reads it via `useContext`.
- The fallback guard stores `originalPush`, `originalReplace`, and `originalGo`, then assigns replacement functions to `navigator.push`, `navigator.replace`, and `navigator.go` until cleanup.
- `serve/cockpit/web/package.json` uses React Router `^7.15.1`, so the intended public navigation-blocking API should be verified before deciding the fix.

## Observed User Impact
This is not just implementation taste: unsaved-note protection is a core Ideas workflow. If the router internals change or another component expects the navigator methods to remain stable, the user may either lose an unsaved-change warning or see navigation behavior that differs from the rest of Cockpit.

## Boundary
Do not implement until the user decides whether this should be fixed now, refined with runtime proof, or accepted as current behavior.

## Approval
User approved the targeted fix for this task after review of the React Router public API boundary.

## Implementation
- Replaced the `UNSAFE_NavigationContext` and navigator method mutation in `IdeasPage` with React Router's public `useBlocker(isDirty)` API plus `useBeforeUnload` for hard reload/browser-close protection.
- Migrated the Cockpit app shell from `BrowserRouter` to `createBrowserRouter`/`RouterProvider` so `useBlocker` runs inside the required data-router context.
- Updated Ideas and App wiring test harnesses to render with data routers where they exercise route-bound behavior.
- Added explicit unsaved-dialog controls for the continue/cancel paths so the route transition behavior is testable without relying on private router internals.

## Verification
- `npm test -- IdeasPage.test.tsx IdeasPage_1662.test.tsx IdeasPage_1663.test.tsx IdeasPage_1664.test.tsx IdeasPage_1665.test.tsx`: 5 files, 146 tests passed.
- `npm test -- IdeasPage.test.tsx IdeasPage_1662.test.tsx IdeasPage_1663.test.tsx IdeasPage_1664.test.tsx IdeasPage_1665.test.tsx App.wiring.test.tsx src/App.wiring.test.tsx`: 7 files, 153 tests passed.
- `npm run build`: passed; Vite reported the existing large-chunk warning only.
- Runtime Playwright proof against `http://127.0.0.1:8421`: edited Ideas, attempted route navigation, verified Cancel stayed on `/ideas`, Leave continued to `/`, and captured the dirty-navigation dialog screenshot before task-scoped scratch cleanup.

## Follow-Up Records
Full frontend-suite verification no longer showed Ideas/App failures after this fix. Remaining unrelated failures were split into follow-up review tasks #1826, #1827, #1828, #1829, #1830, and #1831 for separate user approval before implementation.
