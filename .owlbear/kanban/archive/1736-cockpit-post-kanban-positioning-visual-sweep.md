---
id: 1736
title: Cockpit post-Kanban positioning visual sweep
status: archived
priority: medium
created: 2026-05-23T04:42:00+0200
updated: 2026-05-24T10:50:01.759166+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - visual-sweep
parent:
depends_on: []
ac:
  - Capture fresh screenshots for the primary Cockpit workspaces after
  - Record route metrics for viewport fit, horizontal overflow, scroll surfaces,
    and visible work focus.
  - Classify any finding as observed/theoretical and current/future harm before
    creating a fix task.
  - Create a follow-up task before editing any newly discovered issue.
  - Do not modify unrelated files during the sweep.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## Problem
The Kanban active-work initial positioning fix is committed, so Cockpit needs another screenshot-backed pass across the main workspaces. The sweep should verify the board still feels useful and then find the next concrete usability or visual issue, if one is visible.

## Evidence
- Captured current desktop screenshots after #1735:
  - `.owlbear/scratch/1716-wide-cockpit/1736-kanban-desktop.png`
  - `.owlbear/scratch/1716-wide-cockpit/1736-decisions-desktop.png`
  - `.owlbear/scratch/1716-wide-cockpit/1736-memory-desktop.png`
  - `.owlbear/scratch/1716-wide-cockpit/1736-ideas-desktop.png`
- Metrics evidence: `.owlbear/scratch/1716-wide-cockpit/1736-desktop-sweep-metrics.json`.
- Route health: sampled routes report document height 1000px at a 1440x1000 viewport and no document horizontal overflow.
- Kanban health: In Progress is prominent with one Todo context lane, Done remains visible, and `leadingFragment: null`.
- Memory health: list remains vertically scrollable with `overflowX: hidden`, `overflowY: auto`, and continuation cue visible.
- Ideas health: preview remains bounded and current markdown rendering improvements are preserved.
- Finding: no new material top-level route defect was observed in this sweep.
- Follow-up task created: #1737 Cockpit interaction surface visual sweep.