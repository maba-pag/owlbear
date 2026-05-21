---
id: 1714
title: Reconsider top bar product identity
status: done
priority: important
created: 2026-05-21T23:24:05.487044+02:00
updated: 2026-05-22T00:07:46+02:00
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