---
id: 1731
title: Cockpit post-layout visual sweep
status: done
priority: important
type: task
created: 2026-05-23T03:45:25+0200
updated: 2026-05-23T03:54:38+0200
assignee: copilot
tags:
  - cockpit
  - visual-audit
  - ux
---

## Goal
Run a fresh screenshot-backed pass after the bounded workspace and Kanban initial-scroll fixes, then identify the next concrete Cockpit usability or visual polish issue before editing product code.

## Acceptance Criteria
- Capture current desktop screenshots for the top-level Cockpit routes.
- Record viewport/document metrics for the route surfaces.
- Inspect visible content for cramped controls, clipped text, scroll affordance problems, weak hierarchy, or mismatches with tab functionality.
- Create a dedicated follow-up task before any source changes if a fix is needed.

## Notes
- Use the running Cockpit instance on `http://127.0.0.1:8424` when available.
- Keep durable screenshots under `.owlbear/scratch/1716-wide-cockpit/`.

## Evidence
- Captured desktop screenshots for Kanban, Decisions, Memory, and Ideas after bounded workspace and Kanban initial-scroll fixes.
- Screenshot evidence:
  - `.owlbear/scratch/1716-wide-cockpit/1731-kanban-desktop.png`
  - `.owlbear/scratch/1716-wide-cockpit/1731-decisions-desktop.png`
  - `.owlbear/scratch/1716-wide-cockpit/1731-memory-desktop.png`
  - `.owlbear/scratch/1716-wide-cockpit/1731-ideas-desktop.png`
- Metrics evidence: `.owlbear/scratch/1716-wide-cockpit/1731-desktop-sweep-metrics.json`.
- Viewport containment held on all four routes: document scroll height remained 1000px at a 1440x1000 viewport.
- Finding: Memory list correctly scrolled internally, but exposed unnecessary horizontal overflow and lacked a visual continuation cue for 94 visible entries.
- Follow-up fix task created: #1732 Improve Memory scroll affordance.
