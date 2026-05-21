---
id: 1680
title: Unify workspace route headers
status: done
priority: important
created: 2026-05-21T19:51:31.249907+02:00
updated: 2026-05-21T21:30:30+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - route-chrome
parent:
depends_on: []
ac:
  - Compare route headers across Kanban, Decisions, Ideas, and Memory using 
    screenshots.
  - Define a shared route-header pattern, using Kanban as the preferred visual 
    reference.
  - Apply or document route-specific exceptions based on product value.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
When switching between pages with the left menu, pages look very different. Headlines have different sizes and positions, and headline-row icons use very different styles. The Kanban header look is preferred.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current product cohesion issue.
- Value question: what is the shared Cockpit route-header system, and which route-specific signals deserve exceptions?
- Screenshot target: Kanban, Decisions, Ideas, Memory at the same viewport, side-by-side comparison.

## Acceptance Criteria
- Define a shared route-header pattern using the Kanban header as the visual reference.
- Align title scale, position, icon style, and status affordances across main routes where appropriate.
- Explicitly document any route-specific exception and why it helps the intended tab functionality.

## Implementation Evidence
- Classification: observed current product cohesion issue, not theoretical.
- Impact: hurt the current cockpit now. Decisions, Ideas, and Memory used larger route headings and separate summary-chip styles while Kanban already had the preferred dense in-surface header.
- Decision: define a shared `WorkspaceHeader` pattern using Kanban as reference: compact title, same header height, same border rhythm, summary metrics on the right, and route actions kept route-owned.
- Route-specific exceptions: Kanban keeps Filters as header action; Ideas keeps Preview/Save in the editor shell because those commands act on the draft panel, not the route; Memory keeps filters below the header because they are the primary workspace controls.
- Evidence: desktop screenshots `.owlbear/scratch/1680-route-kanban-desktop.png`, `.owlbear/scratch/1680-route-decisions-desktop.png`, `.owlbear/scratch/1680-route-ideas-desktop.png`, `.owlbear/scratch/1680-route-memory-desktop.png`; mobile screenshots `.owlbear/scratch/1680-route-kanban-mobile.png`, `.owlbear/scratch/1680-route-decisions-mobile.png`, `.owlbear/scratch/1680-route-ideas-mobile.png`, `.owlbear/scratch/1680-route-memory-mobile.png`.
- Verification: `npm test -- --run src/__tests__/WorkspaceHeader.test.tsx src/__tests__/BoardVisualDesign.test.tsx src/__tests__/DecisionsTab.integration.test.tsx src/__tests__/IdeasPage.test.tsx src/__tests__/IdeasPage_1662.test.tsx src/__tests__/MemoryTab_1671.test.tsx src/__tests__/MemoryTab_1672.test.tsx --reporter=dot`; `npm run build`; `npm run test:e2e:all -- e2e/accessibility-dual-theme.spec.ts --reporter=line`; `npm run test:e2e:all -- e2e/shell-sidecar-inspector.spec.ts --reporter=line`.