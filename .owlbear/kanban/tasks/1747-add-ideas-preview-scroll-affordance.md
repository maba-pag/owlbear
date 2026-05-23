---
id: 1747
title: Add Ideas preview scroll affordance
status: done
priority: important
created: 2026-05-23T11:03:43+0200
updated: 2026-05-23T11:09:40+0200
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - ideas
  - responsive
  - layout
parent:
depends_on: [1746]
ac:
  - Use the #1746 mobile Ideas screenshot and metrics as current evidence.
  - Show a subtle continuation affordance when the Ideas preview or editor has more vertical content below the visible surface.
  - Hide the affordance when the scroll surface reaches the bottom or has no vertical overflow.
  - Preserve the bounded Ideas workspace, mobile state panel, save/preview actions, and no document-level overflow.
  - Add or update focused tests for the Ideas scroll-affordance contract where practical.
  - Capture after-fix mobile screenshot or metrics evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## User Feedback Context
The #1746 mobile sweep shows the Ideas preview content cut off at the bottom of its internal scroll surface without an explicit continuation cue.

## Evidence Before Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1746-ideas-mobile.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1746-responsive-metrics.json` reports no document overflow and a bounded Ideas workspace.
- Detail probe: `.owlbear/scratch/1746-probe-mobile-detail.mjs` reports the Ideas preview at `scrollHeight: 571` and `clientHeight: 286` on a 390x844 viewport.

## Evaluation Notes
- Classification: observed current interaction usability issue.
- Current harm: mild but real. The preview is scrollable, but the clipped bottom edge makes long note content feel abruptly cut off.
- Product value: Ideas is a writing/review surface, so long markdown content should clearly communicate continuation without relying on native scrollbars.

## Implementation
- Added active Ideas scroll-surface tracking for the markdown preview and native editor textarea.
- Added a subtle bottom continuation cue inside the Ideas editor shell while the active surface has more vertical content below.
- Hid the cue when the active surface reaches the bottom or has no vertical overflow.
- Preserved the bounded Ideas workspace, mobile state panel, save/preview actions, and document-level overflow behavior.

## Evidence After Fix
- Screenshots:
  - `.owlbear/scratch/1716-wide-cockpit/1747-ideas-mobile-scroll-cue.png`
  - `.owlbear/scratch/1716-wide-cockpit/1747-ideas-mobile-scroll-cue-bottom.png`
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1747-ideas-scroll-cue-metrics.json`.
- Metrics flags: before bottom scroll, `previewHasVerticalOverflow: true`, `cueVisible: true`, `cueOverlapsPreviewBottom: true`, `actionsWithinViewport: true`, `horizontalOverflow: false`, and `verticalDocumentOverflow: false`; after bottom scroll, `cueVisible: false`.
- Browser proof reported no console, page, or request errors.
- Validation: `npx vitest run src/__tests__/IdeasPage.test.tsx src/__tests__/IdeasPage_1663.test.tsx --reporter=verbose` passed; `npx eslint src/pages/IdeasPage.tsx src/__tests__/IdeasPage.test.tsx` passed; `npm run build` passed with the existing Vite chunk-size warning.
