---
id: 1728
title: Cockpit post-markdown visual sweep
status: archived
priority: medium
created: 2026-05-23T03:24:04+0200
updated: 2026-05-24T10:50:01.650125+02:00
tags:
  - cockpit
  - visual-audit
  - ux
parent:
depends_on: []
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
type: task
assignee: copilot
---

## Goal
Run another screenshot-backed pass over the current Cockpit tabs after the shared markdown preview polish, then identify the next real usability or visual issue before editing product code.

## Acceptance Criteria
- Capture current screenshots for the active Cockpit routes at a desktop viewport.
- Inspect the screenshots for visible regressions, cramped layouts, unreachable content, weak affordances, or mismatches with expected tab functionality.
- Record at least one concrete next action or explicitly state if no new issue is found.
- If a fix is needed, create a dedicated task before changing source code.

## Notes
- Use the running Cockpit instance on `http://127.0.0.1:8424` when available.
- Keep durable screenshots under `.owlbear/scratch/1716-wide-cockpit/`.

## Evidence
- Captured desktop screenshots for Kanban, Decisions, Memory, and Ideas after markdown code-block polish.
- Screenshot evidence:
  - `.owlbear/scratch/1716-wide-cockpit/1728-kanban-desktop.png`
  - `.owlbear/scratch/1716-wide-cockpit/1728-decisions-desktop.png`
  - `.owlbear/scratch/1716-wide-cockpit/1728-memory-desktop.png`
  - `.owlbear/scratch/1716-wide-cockpit/1728-ideas-desktop.png`
- Metrics evidence:
  - `.owlbear/scratch/1716-wide-cockpit/1728-desktop-sweep-metrics.json`
  - `.owlbear/scratch/1716-wide-cockpit/1728-layout-depth-metrics.json`
- Finding: Kanban and Memory expanded document height to roughly 10,168px and 8,375px at a 1440x1000 viewport, while Decisions and Ideas remained bounded.
- Follow-up fix task created: #1729 Bound Kanban and Memory workspace height.
