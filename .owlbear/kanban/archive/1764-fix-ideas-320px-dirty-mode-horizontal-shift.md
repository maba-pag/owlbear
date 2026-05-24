---
id: 1764
title: Fix Ideas 320px dirty mode horizontal shift
status: archived
priority: important
created: 2026-05-23T16:56:48.679163+02:00
updated: 2026-05-24T10:50:02.151086+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - mobile
  - visual-proof
parent: 1763
depends_on:
  - 1763
ac:
  - At 320px, Ideas dirty editor and dirty preview states keep the workspace and
    route surface inside the viewport left edge.
  - Dirty badge, Preview/Edit toggle, and Save remain visible and reachable
    without clipping.
  - Notebook state panel and editor/preview content remain horizontally bounded
    on 320px mobile.
  - The 390px mobile and desktop Ideas layouts keep their current intent and
    control hierarchy.
  - Focused screenshot and geometry evidence proves the fix, with no console
    errors or failed requests.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Purpose
Fix the screenshot-confirmed 320px Ideas dirty-mode layout shift found by #1763.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1763-320px-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1763-320px-mobile-sweep-metrics.json`
- `.owlbear/scratch/1716-wide-cockpit/1763-320-ideas-dirty-editor.png`
- `.owlbear/scratch/1716-wide-cockpit/1763-320-ideas-dirty-preview.png`

## Finding
The dirty editor and dirty preview states keep document-level horizontal overflow false, and the Ideas toolbar controls fit within their local shell. The visible route surface still shifts left (`workspace.left = -97`) at 320px, clipping the workspace from the left. Fix the root cause locally in the Ideas route unless a shared shell cause is proven.

## Initial Hypothesis
Interaction with the focused editor/preview toggle is leaving horizontal scroll state on the page or a shell ancestor. Verify scroll state before patching, then make the route reset or prevent horizontal displacement without changing notebook save/dirty behavior.

## Fix
The shift was caused by the Porsche Design System `p-canvas` shadow `.root` becoming a horizontal scroll container after focus returned to PDS toolbar buttons. Page-level scroll stayed at zero, so document overflow metrics were false-green while slotted workspace content rendered left of the viewport.

Changed the Cockpit canvas shadow override from horizontal `overflow:hidden` to `overflow:clip` on `:host`, `.root`, and `.main`, and reset any stale `.root` scroll when the override is installed.

## Proof
- Focused proof metrics: `.owlbear/scratch/1716-wide-cockpit/1764-ideas-320-shift-proof-metrics.json`
- Contact sheet: `.owlbear/scratch/1716-wide-cockpit/1764-ideas-320-shift-proof-contact-sheet.png`
- 320px dirty editor: `.owlbear/scratch/1716-wide-cockpit/1764-320-dirty-editor.png`
- 320px dirty preview: `.owlbear/scratch/1716-wide-cockpit/1764-320-dirty-preview.png`
- 390px dirty preview: `.owlbear/scratch/1716-wide-cockpit/1764-390-dirty-preview.png`
- 1440px dirty preview: `.owlbear/scratch/1716-wide-cockpit/1764-1440-dirty-preview.png`
- Sequence probe after patch: `ideas-after-preview` keeps `workspace.left = 16`, `ideas.left = 16`, `canvasScrollLeft = 0`.

## Validation
- `npm test -- --run src/__tests__/Shell.test.tsx` passed: 22 tests.
- `npx eslint src/Shell.tsx src/__tests__/Shell.test.tsx` passed.
- `npm run build` passed; Vite reported only existing chunk-size warnings.