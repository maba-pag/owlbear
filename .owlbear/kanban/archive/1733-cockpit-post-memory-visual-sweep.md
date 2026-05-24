---
id: 1733
title: Cockpit post-memory visual sweep
status: archived
priority: important
created: 2026-05-23T04:08:00+0200
updated: 2026-05-24T10:50:01.717738+02:00
tags:
  - cockpit
  - visual-sweep
  - ux-feedback
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
type: chore
assignee: copilot
---

## Problem
The Memory scroll affordance is fixed and committed, so Cockpit needs another screenshot-driven pass across the primary tabs. The goal is to find current, observed usability or visual defects rather than preserve speculative backlog noise.

## Acceptance Criteria
- Capture fresh screenshots for the primary Cockpit workspaces after #1732.
- Record metrics that distinguish observed current harm from theoretical or future concerns.
- Identify the next highest-value Cockpit polish issue, or explicitly record that no material issue was observed in the sampled routes.
- Create a follow-up task before editing any newly discovered issue.
- Do not modify unrelated files during the sweep.

## Evidence
- Captured current desktop screenshots against a fresh backend on `http://127.0.0.1:8426` after repairing task metadata visibility.
- Screenshot evidence:
  - `.owlbear/scratch/1716-wide-cockpit/1733-kanban-desktop.png`
  - `.owlbear/scratch/1716-wide-cockpit/1733-decisions-desktop.png`
  - `.owlbear/scratch/1716-wide-cockpit/1733-memory-desktop.png`
  - `.owlbear/scratch/1716-wide-cockpit/1733-ideas-desktop.png`
- Metrics evidence: `.owlbear/scratch/1716-wide-cockpit/1733-desktop-sweep-metrics.json`.
- Current route health: all sampled routes report document height 1000px at a 1440x1000 viewport and no document horizontal overflow.
- Board ledger check: Kanban now shows 58 tasks, including #1733 and #1734 in progress after #1734 repaired recent task metadata.
- Finding: Kanban initial positioning now anchors too far left when active work exists; the active In Progress lane is visible but sits as the fourth column, while the first screen spends most width on empty Research, Backlog, and Todo lanes.
- Classification: observed current usability issue. Current harm is a weak first-glance work focus on the primary task board. Product value of fixing is high because Kanban is the Cockpit's central task surface.
- Follow-up fix task created: #1735 Improve Kanban active-work initial positioning.