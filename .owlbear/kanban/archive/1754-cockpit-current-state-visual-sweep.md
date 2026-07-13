---
id: 1754
title: Cockpit current state visual sweep
status: archived
priority: medium
created: 2026-05-23T15:31:40+0200
updated: 2026-05-24T10:50:02.015616+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - visual-proof
  - sweep
parent:
depends_on:
  - 1753
ac:
  - Capture current desktop and mobile Cockpit states after
  - Include route-level and key interaction states without mutating persisted
    project data.
  - Use screenshots and geometry metrics to classify observed current issues
    versus theoretical issues.
  - Create a follow-up task before any source-code fix if a material issue is
    found.
  - Record evidence under `.owlbear/scratch/1716-wide-cockpit/`.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Purpose
Run the next evidence pass after the mobile Kanban active-lane fix. The goal is to decide the next highest-value Cockpit polish item from current UI evidence, not from stale screenshots or test expectations.

## Evaluation Frame
- Cockpit should feel like a bounded, high-density Porsche Design System work surface.
- Findings must be classified as observed current harm, plan risk, or theoretical.
- Prefer small, route-owned fixes when the problem is local; prefer shared components only when multiple surfaces benefit.

## Evidence
- Fresh server check on `http://127.0.0.1:8426`: health OK, task IDs #1753 and #1754 present.
- Screenshots captured under `.owlbear/scratch/1716-wide-cockpit/1754-*.png` for desktop/mobile routes and key interaction states.
- Metrics captured in `.owlbear/scratch/1716-wide-cockpit/1754-current-state-sweep-metrics.json` with 18 records.
- Summary: no document-level horizontal or vertical overflow, no console messages, no request failures.

## Finding
- Observed current harm: mobile Ideas notebook/status panel clips right-side values inside the bounded route surface. Follow-up created as #1755.
- Non-issue: the mobile memory edit form extends below the first viewport, but its actions are visible and the list shell owns vertical scrolling; this is acceptable for a long form.
