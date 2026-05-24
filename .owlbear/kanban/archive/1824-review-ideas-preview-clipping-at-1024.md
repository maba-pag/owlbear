---
id: 1824
title: Review Ideas preview clipping at 1024
status: archived
priority: important
created: 2026-05-24T10:56:15.436214+02:00
updated: 2026-05-24T11:01:12.714108+02:00
tags:
  - scope:cockpit-web
  - ux
  - screenshot
  - discussion
parent: 1773
depends_on: []
ac:
  - The 1024px Ideas screenshot is reviewed for whether preview clipping/fade
    harms notebook usability.
  - If a layout change is needed, the preview/notebook stacking tradeoff is
    decided before implementation.
  - Any approved change is verified with a 1024px screenshot and a desktop
    comparison screenshot.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
At the 1024px support-floor screenshot for Ideas, the markdown preview panel visibly fades/clips the lower preview content while the Notebook panel begins immediately below. The underlying text exists in the DOM and appears fully at 1440px, so this is a layout/scroll affordance question rather than data loss.

## Evidence
- Screenshot: `.owlbear/scratch/1773-current-sweep/floor-ideas.png`
- Comparison screenshot: `.owlbear/scratch/1773-current-sweep/desktop-ideas.png`
- Metrics: `.owlbear/scratch/1773-current-sweep/report.json` shows no document overflow, but the 1024 viewport only visually exposes the top portion of the preview.

## Boundary
Do not implement until the user decides whether the 1024 preview clipping/fade is harmful enough to fix.

## Decision
User rejected this as a poorly framed finding because it over-centered the 1024px support floor instead of broader Cockpit product quality. Closed as no-op.

Future #1773 sweep work should treat small viewport checks as occasional guardrails only, and should instead focus on workflows, information required for action, action affordances, cross-tab standardization, compactness, font hierarchy, and whether the frontend uses the intended API/data boundaries.
