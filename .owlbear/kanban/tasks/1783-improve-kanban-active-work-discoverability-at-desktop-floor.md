---
id: 1783
title: Improve Kanban active work discoverability at desktop floor
status: done
priority: important
created: 2026-05-24T01:20:30.722675+02:00
updated: 2026-05-24T01:56:07.104431+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - visual-proof
  - ux
  - discussion
parent: 1773
depends_on:
  - 1779
ac:
  - At supported desktop widths, the Kanban first viewport makes current active 
    work and distribution obvious.
  - Empty lanes do not dominate the primary scan when most useful work sits 
    elsewhere.
  - Any horizontal board navigation has clear affordance or summary context.
  - No implementation begins until the user approves this task.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
At the 1024px desktop floor, the Kanban tab reports 104 tasks but the first viewport mostly shows two Research tasks plus empty Backlog/Todo lanes and a clipped In Progress lane. The rest of the board is available only through horizontal scrolling, with little immediate evidence of where active work actually lives.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1773-desktop-1024-kanban-rest.png`
- Screenshot shows `104 tasks` in the header, `Research 2`, `Backlog 0`, `Todo 0`, and partial `In Progress`, while the user's primary question is likely what needs attention now.

## Current Interpretation
Observed supported-width UX candidate, not a layout clipping bug. The board is functional, but at the support floor it may spend prime viewport space on empty lanes and make active work/distribution hard to scan.

## Value
Kanban is the Cockpit's main work-selection surface. A user should quickly understand where work is, what is blocked/important, and what deserves attention without hunting across a horizontal strip.

## Decision Needed
Discuss whether to improve active-work discoverability with stronger lane summary, active-lane jump/overview, smarter initial alignment, or another desktop-focused board scan pattern.

[[2026-05-24T01:56:07+02:00]]
## Reclassification
User clarified horizontal scrolling itself is fine. The valuable Kanban board issue is different: task cards do not vertically expand to show all tags, especially visible on the full-width board in Done. This original discoverability concern is not the current target; follow-up task created for card tag expansion.
