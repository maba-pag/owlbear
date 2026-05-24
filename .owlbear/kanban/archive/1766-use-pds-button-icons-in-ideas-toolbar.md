---
id: 1766
title: Use PDS button icons in Ideas toolbar
status: archived
priority: nice-to-have
created: 2026-05-23T17:09:20.023658+02:00
updated: 2026-05-24T10:50:02.176593+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - mobile
  - pds
parent: 1765
depends_on:
  - 1765
ac:
  - Ideas Preview/Edit and Save controls use the Porsche Design System `PButton`
    icon API instead of nested `PIcon` children.
  - At 320px, the dirty editor toolbar shows the Preview icon and label without
    clipping.
  - At 320px, dirty preview still shows Edit and Save controls without clipping.
  - Existing Ideas toolbar behavior, dirty state, save disabled state, and
    preview toggling remain unchanged.
  - Focused screenshot evidence and Ideas tests prove the change.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Purpose
Polish the remaining screenshot-visible Ideas toolbar inconsistency from #1765: in the 320px dirty editor screenshot, the `Preview` control appears text-only while the preview state shows the Edit icon.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1765-320-ideas-dirty-editor.png`
- `.owlbear/scratch/1716-wide-cockpit/1765-320-ideas-dirty-preview.png`

## Finding
`IdeasPage` currently nests `PIcon` inside `PButton`. PDS v4 exposes a first-class `icon` prop on `PButton`; using that API should make button icon rendering and spacing more robust on compact custom-element buttons.

## Fix
Ideas toolbar controls now use `PButton`'s `icon` prop directly:
- Preview/Edit toggle: `icon={previewMode ? 'edit' : 'view'}`
- Save: `icon="save"`

The nested `PIcon` children were removed, keeping the controls aligned with the PDS v4 button API.

## Proof
- Focused metrics: `.owlbear/scratch/1716-wide-cockpit/1766-ideas-pds-button-icon-proof-metrics.json`
- Contact sheet: `.owlbear/scratch/1716-wide-cockpit/1766-ideas-pds-button-icon-proof-contact-sheet.png`
- 320px dirty editor: `.owlbear/scratch/1716-wide-cockpit/1766-320-ideas-dirty-editor.png`
- 320px dirty preview: `.owlbear/scratch/1716-wide-cockpit/1766-320-ideas-dirty-preview.png`

## Validation
- `npm test -- --run src/__tests__/IdeasPage.test.tsx` passed: 39 tests.
- `npx eslint src/pages/IdeasPage.tsx src/__tests__/IdeasPage.test.tsx` passed.
- `npm run build` passed; Vite reported only existing chunk-size warnings.