---
id: 1778
title: Improve Decision resolver responsive fit
status: done
priority: important
created: 2026-05-24T00:37:24.558145+02:00
updated: 2026-05-24T00:51:53+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - visual-proof
  - responsive
  - decisions
  - discussion
  - stress-note
parent: 1773
depends_on:
  - 1773
ac:
  - At 320px, the Decision resolver presents summary, options, response choices,
    and primary actions with a clear scroll/flow path rather than hiding
    important decision content below an ambiguous clipped panel.
  - At 768px, the Decision resolver surface and footer actions stay inside the
    viewport horizontally.
  - The resolver keeps enough density for desktop decision work if this is
    approved for implementation.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
#1773 fresh sweep shows the Decision resolver has responsive fit issues. At 320px, the summary panel consumes the visible content area and the Options/response area begins below the fold with weak affordance. At 768px, the resolver surface visibly extends past the right viewport and the footer actions are clipped. Screenshots: `.owlbear/scratch/1716-wide-cockpit/1773-320-decisions-resolver.png`, `.owlbear/scratch/1716-wide-cockpit/1773-390-decisions-resolver.png`, `.owlbear/scratch/1716-wide-cockpit/1773-768-decisions-resolver.png`.

## Value Question
The Decisions tab exists to resolve pending decisions. If the resolver hides options or clips the action footer at common widths, the tab's central workflow feels fragile.

## Current Interpretation
Reclassified after #1779: observed stress evidence below the 1024px Cockpit support floor, not current product harm. No implementation is approved from this task.

## Decision
Closed as a stress note. The Decision resolver should be re-evaluated at 1024px+ before any implementation decision.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1773-evidence-interaction-sweep-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1773-evidence-interaction-sweep-metrics.json`
- `.owlbear/scratch/1716-wide-cockpit/1773-320-decisions-resolver.png`
- `.owlbear/scratch/1716-wide-cockpit/1773-390-decisions-resolver.png`
- `.owlbear/scratch/1716-wide-cockpit/1773-768-decisions-resolver.png`