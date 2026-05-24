---
id: 1791
title: Align Kanban filters with trigger and clear action
status: research
priority: important
created: 2026-05-24T01:57:03.822491+02:00
updated: 2026-05-24T03:13:48.686029+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - kanban
  - filters
  - discussion
parent: 1773
depends_on: []
ac:
  - Opening Kanban filters visually relates the filter UI to the right-side 
    Filter trigger.
  - When filters are active, users can clear them without reopening the filter 
    popup/panel.
  - The active-filter indicator remains readable at supported desktop widths.
  - No implementation begins until the user approves this task.
  - Kanban filter UI uses an anchored popover/menu pattern rather than a 
    left-aligned full-width panel, unless proof shows the popover cannot hold 
    the controls well.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
User feedback on Kanban filters:
1. When opened, the filter popup/panel is left-aligned even though the Filter button and current-filter indicator are on the right side of the board.
2. The active-filter bar should probably include a Clear filters button so filters can be reset easily even when the filter popup is closed.

## Current Interpretation
Observed workflow polish issue. Filter controls and active filter feedback are spatially disconnected, and clearing filters may be less discoverable than setting them.

## Value
Filters are a repeated board workflow. Users should understand which controls belong together and be able to recover quickly from a filtered board.

## Discussion Questions
- Should the filter UI be a right-aligned popover under the Filter button, or a full-width panel with stronger right-side anchoring?
- Should Clear filters appear only when filters are active?
- Should active filter chips live in the header row, inside the panel, or both?

[[2026-05-24T03:13:48+02:00]]
## Decision
User prefers trying a popover pattern for Kanban filters, similar in interaction feel to the workspace status/health menu: anchored to the Filter trigger, dismissible, and spatially connected to the right-side header controls. Active filters should still have an accessible Clear filters action outside the popover.
