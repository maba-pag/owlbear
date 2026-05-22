---
id: 1714
title: Reconsider top bar product identity
status: done
priority: important
created: 2026-05-21T23:24:05.487044+02:00
updated: 2026-05-22T11:42:16+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - top-bar
  - identity
parent:
depends_on: []
ac:
  - Audit whether the Porsche logo is required for Cockpit or incidental visual
    treatment.
  - Compare top-bar identity alternatives such as OwlBear Dashboard/Cockpit.
  - Decide and implement an identity treatment that fits the product and
    constraints.
  - Make the visible product identity read as the intended OwlBear
    dashboard/cockpit name on desktop.
  - Keep workspace status and theme controls in a deliberate utility area
    instead of visually drifting into the center of the title bar.
  - Validate identity and control placement with desktop screenshots at widths
    >= 1200px.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Is the Porsche logo a requirement on the top bar? Can it be replaced with `OwlBear dashboard` or something more fitting?

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically. This likely needs a product/brand decision before implementation.

## Evaluation Notes
- Classification: user-observed brand/product-fit question.
- Value question: top identity should clarify the tool and feel fitting; Porsche Design System usage does not automatically mean the Porsche logo is the right product identity.
- Impact: could hurt Cockpit now by making the app feel like a Porsche-branded demo rather than OwlBear cockpit; brand requirements are unknown and should be verified before removal.
- Screenshot target: top bar desktop/mobile with Porsche logo, possible OwlBear/dashboard identity alternatives.

## Acceptance Criteria
- Determine whether Porsche logo is a requirement or only inherited from PDS styling.
- Compare product identity alternatives for clarity and fit.
- Choose top-bar identity treatment that supports OwlBear Cockpit without violating brand constraints.

## Evidence - 2026-05-22
- Classification: observed current UX issue. Screenshots showed the inherited Porsche crest/wordmark as the top-bar identity, making Cockpit read like a Porsche-branded demo rather than an OwlBear operations surface.
- Impact: hurts us now by confusing product identity and visual ownership; not merely theoretical. No repo requirement was found that the Porsche logo must remain visible when using PDS.
- Source audit: `PCanvas` renders `p-crest`/`p-wordmark` internally by default and exposes no React prop to replace or hide them. Existing Cockpit code only supplied a hidden `slot="title"` label, so the Porsche mark was incidental PDS chrome rather than an OwlBear requirement.
- Decision: keep `PCanvas` and PDS layout, add visible `OwlBear Cockpit` identity in `slot="header-start"`, and hide the inherited PDS crest/wordmark through a focused shadow-root style override. Desktop keeps `OwlBear Cockpit`; mobile shows `OwlBear` to avoid crowding the compact status/theme controls.
- Browser proof: refreshed `.owlbear/scratch/1680-route-kanban-desktop.png` and `.owlbear/scratch/1680-route-kanban-mobile.png`; both show OwlBear identity, compact controls, and no visible Porsche mark.
- Validation: `npx vitest run src/__tests__/Shell.test.tsx src/__tests__/PdsSimpleSwaps.test.tsx --reporter=dot` passed 2 files / 49 tests. `npm run build` passed with the existing Vite chunk-size warning. Focused Playwright identity checks passed 2 tests. `npx eslint src/Shell.tsx src/__tests__/Shell.test.tsx e2e/shell-layout-1606.spec.ts e2e/shell-sidecar-inspector.spec.ts` passed. VS Code diagnostics found no errors in touched files.


## Reopened User Feedback - 2026-05-22
- The delivered identity change did not satisfy the intended result: the Porsche logo was removed, but the top bar still does not read as the requested OwlBear dashboard identity strongly enough.
- The status light and theme switcher are visually centered in the title bar; they should sit in the appropriate utility/control area without weakening the product name.
- Classification: user-observed delivered-work gap, not theoretical.
- Impact: hurts Cockpit now by making the app identity and utility-control placement feel unfinished.

## Final Evidence - 2026-05-22
- Classification: observed delivered-work gap, not theoretical. The previous pass removed the inherited Porsche mark, but the visible app identity was still too weak and the status/theme utilities visually sat around the title-bar center.
- Impact: hurt Cockpit now by making the shell feel unfinished and visually ambiguous; it was not only a future/edge-case risk.
- Source audit: `PCanvas` uses a three-column header grid (`minmax(0,1fr) auto minmax(0,1fr)`) and renders crest/wordmark in the middle. Hiding those elements left the start/end areas subject to normal grid auto-placement, which allowed the `header-end` controls to occupy the center column.
- Implementation: renamed the visible product identity to `OwlBear Dashboard`, increased it to the next local type size, kept the hidden title/accessible label aligned to the same name, and pinned the PDS header start/end slots to explicit columns while keeping the hidden crest/wordmark in the center column.
- Desktop screenshot proof: captured and inspected 1440px light, 1440px dark, and 2560px light screenshots. Metrics after the fix: identity x=96/right=230; utility group x=1320/right=1416 at 1440px, and x=2440/right=2536 at 2560px. That places controls in the right utility area rather than the visual center.
- Test contract update: replaced the stale E2E expectation that the status bar be wider than 200px with a compact right-anchored utility-area assertion.
- Validation: `npx vitest run src/__tests__/Shell.test.tsx src/__tests__/Shell.theme-toggle.test.tsx --reporter=dot` passed 2 files / 23 tests. `npx playwright test e2e/shell-layout-1606.spec.ts` passed 11 tests. `npx playwright test e2e/shell-sidecar-inspector.spec.ts --grep "StatusBarNavHierarchy"` passed 5 tests. ESLint on touched shell/test files passed. `npm run build` passed with the existing Vite chunk-size warning. VS Code diagnostics found no errors in touched files. Task scratch artifacts were cleaned after screenshot review.


## Reopened User Feedback - 2026-05-22 Later
- The current `OwlBear Dashboard` identity is too boring and small after the last fix.
- User preferred the earlier prettier treatment with stronger logo-line presence, a slightly gray secondary word, and more central visual balance; suggested `text-lg` scale and contrast treatment as directional input, not exact spec.
- Classification: user-observed delivered-work regression, not theoretical.
- Impact: hurts Cockpit now because the global product identity is the first-frame orientation point for the whole cockpit and currently feels under-designed.
- Product direction: make the logo/title line larger and more intentional while keeping utility controls in the correct right-side area and avoiding the inherited Porsche mark.

## Final Evidence - 2026-05-22 Later
- Classification: observed delivered-work regression, not theoretical. The previous `OwlBear Dashboard` line was functional but read like a small label, not a polished product identity.
- Impact: hurt Cockpit now because every route opens under this top chrome; weak identity made the whole workspace feel unfinished.
- Implementation: changed the visible and accessible product name to `OwlBear Cockpit`, centered the identity over the PCanvas workspace/header area, restored a larger `text-lg` scale, and split the wordmark treatment so `OwlBear` stays primary while `Cockpit` uses the PDS contrast-medium token at lighter weight. Kept the PDS crest/wordmark hidden and the utility controls pinned to the right header slot.
- Browser geometry proof: Playwright screenshot run captured 1440px light, 1440px dark, and 2560px light views. Metrics showed identity center equals workspace/header center (`756` at 1440px, `1316` at 2560px), utility controls remain at the far right (`statusRight=1416` at 1440px, `2536` at 2560px), and the real app identity font size is larger (`25.904px` at 1440px, `28.48px` at 2560px).
- Screenshot review: inspected the light/dark 1440px and light 2560px captures. The result reads as a centered product wordmark, `Cockpit` is visibly secondary, and the status/theme controls do not compete with the brand line. Scratch captures/logs were removed after recording evidence.
- Validation: `npx vitest run src/__tests__/Shell.test.tsx src/__tests__/Shell.theme-toggle.test.tsx src/__tests__/PdsSimpleSwaps.test.tsx --reporter=dot` passed 3 files / 52 tests. Focused Playwright shell checks passed 3 tests. ESLint on touched shell/test files passed. `npm run build` passed with the existing Vite chunk-size warning. VS Code diagnostics found no errors in touched files.

