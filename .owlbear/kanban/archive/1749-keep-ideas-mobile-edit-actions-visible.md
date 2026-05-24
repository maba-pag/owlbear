---
id: 1749
title: Keep Ideas mobile edit actions visible
status: archived
priority: needed
created: 2026-05-23T11:14:09+0200
updated: 2026-05-24T10:50:01.943467+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - ideas
  - responsive
  - edit-mode
parent:
depends_on:
  - 1748
ac:
  - Use the
  - Keep the Ideas editor toolbar actions visible and reachable on a 390x844
    mobile viewport after entering dirty edit mode.
  - Prevent the native textarea from forcing its hidden editor shell to scroll
    or clip the toolbar on narrow viewports.
  - Preserve desktop Ideas editor sizing, dirty-state behavior, save/preview
    actions, and the
  - Add or update focused tests for the mobile editor sizing/action visibility
    contract where practical.
  - Capture after-fix mobile screenshot or metrics evidence.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## User Feedback Context
The #1748 mobile dirty-editor capture shows the Ideas editor content but not the editor toolbar. Raw metrics still put the toolbar controls in the viewport, so the screenshot is the decisive evidence: the editor shell itself has been scrolled/clipped after textarea focus.

## Evidence Before Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1748-mobile-ideas-dirty-editor.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1748-mobile-interaction-metrics.json`.
- Key metrics: `ideasEditorShell.clientHeight: 368`, `ideasEditorShell.scrollHeight: 543`, `ideasEditorShell.scrollTop: 174`; `ideasTextarea.clientHeight: 420`, `ideasTextarea.scrollHeight: 968`; document overflow is still false.

## Evaluation Notes
- Classification: observed current usability issue.
- Current harm: real. Mobile users editing Ideas can lose the visible Save/Preview toolbar because the textarea is taller than the bounded shell.
- Product value: high. Ideas is an editing surface, and dirty-state actions must remain visibly reachable while writing.

## Implementation
- Replaced the mobile-hostile textarea minimum height with `min-h-0`, allowing the native editor to shrink inside the bounded editor shell.
- Kept the editor shell overflow hidden and let the textarea own vertical scrolling.
- Preserved dirty state, Save/Preview actions, and the #1747 scroll cue on the active textarea surface.
- Added a focused static contract test that prevents the fixed `min-h-[420px]` sizing from returning.

## Evidence After Fix
- Screenshot: `.owlbear/scratch/1716-wide-cockpit/1749-ideas-mobile-edit-fit.png`.
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1749-ideas-mobile-edit-fit-metrics.json`.
- Metrics flags: `editorShellNotProgrammaticallyScrolled: true`, `editorShellContentFitsVisibleShell: true`, `textareaHasVerticalOverflow: true`, `scrollCueVisible: true`, `dirtyVisibleWithinClips: true`, `previewToggleVisibleWithinClips: true`, `saveVisibleWithinClips: true`, `horizontalOverflow: false`, `verticalDocumentOverflow: false`.
- Browser proof reported no console, page, or request errors.
- Validation: `npx vitest run src/__tests__/IdeasPage.test.tsx src/__tests__/IdeasPage_1663.test.tsx --reporter=dot` passed with 54 tests; `npx eslint src/pages/IdeasPage.tsx src/__tests__/IdeasPage.test.tsx` passed; `npm run build` passed with the existing Vite chunk-size warning.
