---
id: 1746
title: Cockpit responsive visual sweep
status: archived
priority: important
created: 2026-05-23T10:59:05+0200
updated: 2026-05-24T10:50:01.903384+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - visual-sweep
  - responsive
parent:
depends_on:
  - 1745
ac:
  - Capture current narrow-viewport screenshots for Kanban, Decisions, Memory,
    and Ideas.
  - Record geometry metrics for workspace bounds, document overflow, horizontal
    overflow, scroll surfaces, and obvious action reachability.
  - Classify each finding as observed/theoretical and current/future harm with
    product value.
  - Create a follow-up fix task before editing any newly discovered issue.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## Problem
Desktop Cockpit states are now mostly bounded and action-reachable. Responsive behavior still needs current runtime evidence so small-view usability work is driven by screenshots and measured overflow rather than assumptions.

## Evidence Plan
- Capture Kanban, Decisions, Memory, and Ideas at a narrow mobile viewport.
- Record whether each workspace fits the viewport, creates document overflow, or hides primary actions.
- Classify findings before creating any fix task.

## Evidence
- Screenshots:
  - `.owlbear/scratch/1716-wide-cockpit/1746-kanban-mobile.png`
  - `.owlbear/scratch/1716-wide-cockpit/1746-decisions-mobile.png`
  - `.owlbear/scratch/1716-wide-cockpit/1746-memory-mobile.png`
  - `.owlbear/scratch/1716-wide-cockpit/1746-ideas-mobile.png`
- Metrics: `.owlbear/scratch/1716-wide-cockpit/1746-responsive-metrics.json`.
- Detail probe: `.owlbear/scratch/1746-probe-mobile-detail.mjs` confirms Memory filter controls and the Ideas state panel are bounded without internal horizontal overflow.
- Stable surfaces: all four mobile routes reported no document-level horizontal or vertical overflow, and each workspace bottom stayed within the 390x844 viewport.

## Findings
- Kanban: observed expected horizontal lane strip. Current harm: low; horizontal board navigation is intentional and bounded. Product value: no immediate fix from this sweep.
- Decisions: observed healthy narrow layout. Current harm: none found; the decision card is readable and action text remains visible.
- Memory: observed healthy bounded filter panel and list shell. Current harm: no fix-worthy clipping found after detail probing; long entries below the viewport are inside the list scroll surface.
- Ideas: observed current interaction usability issue. The mobile preview is an internal scroll surface with `scrollHeight: 571` and `clientHeight: 286`, and the screenshot shows content cut off at the bottom without a continuation affordance. Current harm is mild but real: users can scroll, but the preview reads as abruptly clipped. Product value is high enough to fix because Ideas is a writing surface and long notes are normal.

## Follow-up
- Created #1747 Add Ideas preview scroll affordance before editing.
