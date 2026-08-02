---
id: 1737
title: Cockpit interaction surface visual sweep
status: archived
priority: medium
created: 2026-05-23T04:49:00+0200
updated: 2026-05-24T10:50:01.775301+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - visual-sweep
  - interactions
parent:
depends_on: []
ac:
  - Capture current screenshots for key interactive Cockpit surfaces beyond the
    top-level route defaults.
  - Include at least task detail, decision resolver, Memory detail or edit, and
    Ideas edit/save state.
  - Record metrics or observations for viewport fit, control reachability,
    content clarity, and action affordance.
  - Classify any finding as observed/theoretical and current/future harm before
    creating a fix task.
  - Create a follow-up task before editing any newly discovered issue.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---

## Problem
The primary route surfaces now look stable, but Cockpit's intended functionality also lives in interaction states: task detail, decision resolving, Memory detail/edit flows, and Ideas editing. These need the same screenshot-backed scrutiny before calling the product experience polished.

## Evidence
- Captured interaction screenshots:
  - `.owlbear/scratch/1716-wide-cockpit/1737-task-detail.png`
  - `.owlbear/scratch/1716-wide-cockpit/1737-decision-resolver.png`
  - `.owlbear/scratch/1716-wide-cockpit/1737-memory-detail.png`
  - `.owlbear/scratch/1716-wide-cockpit/1737-memory-edit.png`
  - `.owlbear/scratch/1716-wide-cockpit/1737-ideas-editor.png`
  - `.owlbear/scratch/1716-wide-cockpit/1737-ideas-dirty.png`
- Metrics evidence: `.owlbear/scratch/1716-wide-cockpit/1737-interaction-sweep-metrics.json`.
- Stable surfaces: decision resolver, Memory detail, Ideas editor, and Ideas dirty state stayed within the document viewport with no document horizontal or vertical overflow.
- Finding: task detail window measured `bottom: 1010` at a 1000px viewport and the screenshot cuts into the metadata section at the bottom.
- Classification: observed current interaction usability issue. Current harm is clipped detail content in the primary task inspection/edit workflow. Product value of fixing is high because task detail is core to Cockpit's intended Kanban functionality.
- Follow-up fix task created: #1738 Bound task detail modal to viewport.
