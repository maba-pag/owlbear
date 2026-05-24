---
id: 1796
title: Reduce Memory filter control density
status: research
priority: important
created: 2026-05-24T03:13:48.718875+02:00
updated: 2026-05-24T03:27:28.695837+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux
  - memory
  - filters
  - discussion
parent: 1773
depends_on: []
ac:
  - Memory filter controls use compact sizing where PDS supports it.
  - The filter bar preserves readability and accessible labels while reducing 
    vertical bulk.
  - The memory list gains useful visible space at supported desktop widths.
  - No implementation begins until the user approves this task.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
While discussing #1791, user noted the Memory filter bar controls are huge and may be the only input/buttons that are not compact. They asked whether Memory filters can be reduced to compact text/input/select fields.

## Current Interpretation
Observed density/ergonomics issue on a repeated filtering surface. Memory is filter-heavy, but the controls may consume too much vertical space relative to list content.

## Value
Memory triage depends on scanning many entries. Compact filters would free more room for results while keeping filters available.

## Discussion Questions
- Should all Memory filter controls use compact PDS variants where available?
- Should filter labels remain visible, or can some become placeholders/tooltips?
- Should Memory filter layout keep full-width always-visible controls or move toward a collapsible/compact pattern?

[[2026-05-24T03:27:28+02:00]]

## Discussion Decision
Keep Memory filters always visible, but reduce their vertical bulk with compact sizing and tighter spacing. Use PDS compact variants where available while preserving accessible labels and the ability to scan/filter quickly.

