---
id: 1680
title: Unify workspace route headers
status: archived
priority: important
created: 2026-05-21T19:51:31.249907+02:00
updated: 2026-05-24T10:50:00.989419+02:00
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
  - Remove the unnecessary leading separator before the first route-header
    metric group.
  - Tune right-side route-header metrics so numbers are informative without
    reading as giant display type.
  - Validate the shared header treatment on desktop screenshots at widths >=
    1200px.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
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


## Reopened User Feedback - 2026-05-22
- Route title bars show right-side numbers in overly large type.
- Metric text groups are separated by vertical lines, but the first group also has a leading line in front of it; that leading separator is unnecessary.
- Classification: user-observed route-header polish issue, not theoretical.
- Impact: hurts Cockpit now because repeated route chrome adds visual noise across every tab.

## Final Evidence - 2026-05-22
- Classification: observed route-header polish issue, not theoretical. The repeated metric treatment was visible in every route header and made the chrome louder than the route content.
- Impact: hurt Cockpit now because the shared header pattern repeated an unnecessary leading divider and overlarge metric value on Kanban, Decisions, Ideas, and Memory.
- Implementation: moved metric separator ownership from each `WorkspaceHeaderMetric` to the shared `WorkspaceHeader` summary container, so only a metric following another metric receives a left divider. Reduced metric value type from `text-lg` to `text-base` while leaving labels compact.
- Browser metric proof: desktop screenshot capture at 1440px for Kanban, Decisions, Ideas, and Memory, plus 2560px for Kanban. Computed CSS showed first metrics at `borderLeftWidth=0px`, `paddingLeft=0px`, `valueFontSize=16px`; Memory's second metric retained `borderLeftWidth=1px`, `paddingLeft=8px`, `valueFontSize=16px`.
- Screenshot review: inspected the route captures after waiting for the route transition to finish; Kanban/Decisions/Ideas now have no leading separator, and Memory has a divider only between `entries` and `shown`. Scratch captures/logs were removed after recording evidence.
- Validation: `npx vitest run src/__tests__/WorkspaceHeader.test.tsx src/__tests__/KanbanBoard.test.tsx src/__tests__/DecisionsPage_1688.test.tsx src/__tests__/IdeasPage.test.tsx src/__tests__/MemoryTab_1671.test.tsx --reporter=dot` passed 5 files / 123 tests. `npx playwright test e2e/shell-layout-1606.spec.ts --grep "Memory route keeps header metrics|direct Ideas route waits"` passed 2 tests. ESLint on touched files passed. `npm run build` passed with the existing Vite chunk-size warning. VS Code diagnostics found no errors in touched files.


## Reopened User Feedback - 2026-05-22 Later
- The latest metric treatment went too far: route header info such as `42 tasks` became small and ugly.
- User intent was to remove only the leading vertical separator before the first info group, not to shrink the metric value or remove useful visual rhythm.
- Classification: user-observed delivered-work regression, not theoretical.
- Impact: hurts Cockpit now because shared route headers are visible on every main tab and currently underplay important route summary information.
- Product direction: restore the bigger route-header metric value and existing multi-metric separators, while keeping no leading separator before the first metric.

## Final Evidence - 2026-05-22 Later
- Classification: observed delivered-work regression, not theoretical. The previous pass accidentally treated the metric value size as the problem, but the user intent was only to remove the leading separator before the first metric group.
- Impact: hurt Cockpit now because shared route headers are repeated across Kanban, Decisions, Ideas, and Memory, and the summary number needs to remain readable at a glance.
- Implementation: restored `WorkspaceHeaderMetric` values from `text-base` to `text-lg`, left the separator ownership on the shared summary container, and kept the browser guard that the first metric has no left divider while later metrics keep the divider.
- Browser metric proof: focused Playwright on Memory measured first metric `borderLeftWidth=0px`; second metric `borderLeftWidth=1px`; restored metric values share the same real app font size and are greater than 20px (`25.904px` in the browser run).
- Screenshot review: captured desktop screenshots for Kanban, Decisions, Ideas, and Memory at 1440px plus Kanban at 2560px. Review confirmed the first metric has no leading rule, Memory keeps the between-metric rule, and the metric values read prominently again. Scratch captures/logs were removed after recording evidence.
- Validation: `npx vitest run src/__tests__/WorkspaceHeader.test.tsx src/__tests__/KanbanBoard.test.tsx src/__tests__/DecisionsPage_1688.test.tsx src/__tests__/IdeasPage.test.tsx src/__tests__/MemoryTab_1671.test.tsx --reporter=dot` passed 5 files / 123 tests. `npx playwright test e2e/shell-layout-1606.spec.ts --grep "Memory route keeps restored header metrics|direct Ideas route waits"` passed 2 tests. ESLint on touched files passed. `npm run build` passed with the existing Vite chunk-size warning. VS Code diagnostics found no errors in touched files.

