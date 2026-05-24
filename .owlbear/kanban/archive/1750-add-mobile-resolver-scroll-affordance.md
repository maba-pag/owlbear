---
id: 1750
title: Add mobile resolver scroll affordance
status: archived
priority: important
created: 2026-05-23T11:19:40+0200
updated: 2026-05-24T10:50:01.957934+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - decisions
  - responsive
  - layout
parent:
depends_on:
  - 1748
ac:
  - Use the
  - Show a subtle continuation affordance when the resolver body has more
    vertical content below the visible area.
  - Hide the affordance when the resolver body reaches the bottom or has no
    vertical overflow.
  - Preserve visible modal footer actions, focus handling, response selection,
    notes input, and no document-level overflow.
  - Add or update focused tests for the resolver scroll-affordance contract
    where practical.
  - Capture after-fix mobile screenshot or metrics evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## User Feedback Context
The #1748 mobile resolver capture shows the modal footer buttons visible while the response section and notes continue below/behind the visible modal body without an explicit continuation cue.

## Evidence Before Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1748-mobile-decisions-resolver.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1748-mobile-interaction-metrics.json`.
- Key metrics: resolver surface is bounded (`top: 101`, `bottom: 810`) with document overflow false, but the response selector extends to `bottom: 974` and notes start at `top: 1042` inside the scrollable body while footer actions remain visible.

## Evaluation Notes
- Classification: observed current mobile usability issue.
- Current harm: mild-to-moderate. Users can scroll the modal body, but the hidden response/notes continuation is not visually communicated while the disabled Submit button is already visible.
- Product value: high. Decision resolution is a primary workflow, and mobile users need a clear signal that more resolver inputs are below.

## Implementation
- Added a dedicated resolver scroll body wrapper with `data-testid="resolve-scroll-body"`.
- Added scroll/resize/ResizeObserver tracking for whether resolver inputs continue below the visible body.
- Added a subtle bottom continuation cue inside the resolver body when more content remains below.
- Hid the cue at the bottom of the scroll body.
- Normalized a nullable resolver body before decision brief parsing so the existing null-body fallback path does not crash.

## Evidence After Fix
- Screenshots:
  - `.owlbear/scratch/1716-wide-cockpit/1750-mobile-resolver-cue.png`
  - `.owlbear/scratch/1716-wide-cockpit/1750-mobile-resolver-cue-bottom.png`
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1750-mobile-resolver-cue-metrics.json`.
- Metrics flags: before bottom scroll, `scrollBodyHasVerticalOverflow: true`, `cueVisible: true`, `cueOverlapsScrollBodyBottom: true`, `footerActionsWithinViewport: true`, `horizontalOverflow: false`, `verticalDocumentOverflow: false`; after bottom scroll, `cueVisible: false`.
- Browser proof reported no console, page, or request errors.
- Validation: `npx vitest run src/__tests__/ResolveModalUX.test.tsx src/__tests__/PModal.coverage.test.tsx --reporter=dot` passed with 72 tests; `npx eslint src/components/ResolveModal.tsx src/__tests__/ResolveModalUX.test.tsx` passed; `npm run build` passed with the existing Vite chunk-size warning.
