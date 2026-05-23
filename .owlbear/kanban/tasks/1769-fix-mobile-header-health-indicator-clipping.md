---
id: 1769
title: Fix mobile header health indicator clipping
status: done
priority: important
created: 2026-05-23T17:19:35.025005+02:00
updated: 2026-05-23T17:56:12+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - mobile
  - visual-proof
parent:
depends_on:
  - 1768
ac:
  - At 320px and 390px mobile widths, the global health/status indicator is 
    fully visible and not clipped by the viewport edge.
  - The mobile header keeps OwlBear centered and does not overlap the nav 
    trigger, health indicator, or theme control.
  - Desktop header status layout remains unchanged in intent and keeps controls 
    reachable.
  - The fix uses existing Porsche Design System controls and Cockpit shell 
    patterns where possible.
  - Focused screenshots and geometry metrics prove the fix with no console 
    errors or failed requests.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Purpose
Fix the screenshot-visible mobile header issue found in the #1768 broad visual sweep: the green health/status indicator appears clipped against the right viewport edge on 320px and 390px mobile screenshots.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1768-current-state-visual-sweep-contact-sheet.png`
- Affected examples include `320-kanban-rest`, `320-decisions-rest`, `320-memory-rest`, `320-ideas-rest`, and corresponding 390px states.

## Finding
The health dot was geometrically inside the viewport; the screenshot-visible defect was the neighboring compact theme control being clipped by the PDS Canvas root on mobile. With the nav rail collapsed, the Canvas shadow `.root` is translated left by the 72px rail width and clipped at `x=248`, so the header-end slot painted only the health control even though the light-DOM status bar and theme button measured inside the viewport.

## Resolution
- Changed the Cockpit Canvas shadow override so `.root` remains viewport-sized but uses `overflow:visible`; `:host` and `.main` still bound the shell/workspace to the viewport.
- Restored the compact theme trigger to a Porsche Design System `PButton` with `icon="theme"`, `hideLabel`, and a 44px host touch target.
- Kept OwlBear centered and verified that the mobile status controls do not overlap the identity or viewport edge.

## Proof
- Focused checks: `npm test -- --run src/__tests__/ThemeToggle.test.tsx src/__tests__/Shell.test.tsx` passed, `npx eslint src/Shell.tsx src/__tests__/Shell.test.tsx src/components/ThemeToggle.tsx src/__tests__/ThemeToggle.test.tsx` passed, and `npm run build` passed with the existing large-chunk warning.
- Header proof metrics: `.owlbear/scratch/1716-wide-cockpit/1769-mobile-header-status-proof-metrics.json`
- Header proof contact sheet: `.owlbear/scratch/1716-wide-cockpit/1769-mobile-header-status-proof-contact-sheet.png`
- Regression metrics for the previous 320px Ideas dirty editor/preview shift: `.owlbear/scratch/1716-wide-cockpit/1769-ideas-320-regression-metrics.json`
- Regression screenshots: `.owlbear/scratch/1716-wide-cockpit/1769-ideas-320-dirty-editor-regression.png`, `.owlbear/scratch/1716-wide-cockpit/1769-ideas-320-dirty-preview-regression.png`