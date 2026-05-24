---
id: 1773
title: Cockpit evidence-led interaction critique sweep
status: research
priority: important
created: 2026-05-24T00:33:26.614960+02:00
updated: 2026-05-24T01:57:30.041901+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - visual-proof
  - interaction-states
  - discussion
parent:
depends_on:
  - 1772
ac:
  - 'Fresh screenshots cover representative Cockpit tab interactions across mobile
    and desktop widths after #1772.'
  - Every observed potential improvement is immediately captured as its own
    kanban task, then refined or closed if later evidence clears it.
  - Findings distinguish observed current harm from theoretical risk and record
    value, context, and uncertainty.
  - No implementation changes are made until the user explicitly approves a
    selected finding.
  - The sweep ends by presenting one candidate improvement at a time through
    askQuestions for discussion.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Purpose
Run an analysis-only, evidence-led Cockpit interaction sweep after #1772. The goal is to find real, observed UI/UX improvement candidates for discussion, not to implement fixes.

## Rules
- Capture current screenshots/metrics before proposing changes.
- Create a task immediately for every potential issue worth discussing.
- Refine the task if more evidence changes the interpretation.
- Close or mark as not-current-harm if the evidence clears the concern.
- Do not implement without explicit user approval.

## Candidate Areas
Kanban, Decisions, Memory, Ideas, global header/status controls, task detail/edit states, modal/dialog states, mobile and desktop interaction paths.

[[2026-05-24T00:54:34+02:00]]
## Desktop Evidence Rerun
After #1779, the sweep was rerun at 1024, 1200, 1440, and 2000px. Outputs:
- `.owlbear/scratch/1716-wide-cockpit/1773-desktop-interaction-sweep-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1773-desktop-interaction-sweep-metrics.json`

Result: no horizontal document overflow, no console messages, and no request failures. The previous sub-1024 findings (#1774, #1775, #1776, #1778) were closed as stress notes. New supported-width candidate #1780 was created for modal surfaces clipping slightly at 1024px and task detail clipping at 1200px. Long edit-form height flags were not treated as bugs because primary controls remain visible and content is scrollable.

[[2026-05-24T01:08:20+02:00]]
## #1780 Follow-Through
User approved implementing #1780 after the effort estimate. The modal containment fix is complete and #1780 is done. Post-fix proof at 1024/1200 shows task detail and Decision resolver modal surfaces and primary actions fully inside the viewport. Remaining desktop sweep flags are long edit-form height metrics with primary controls visible and are not current #1780 bugs.

[[2026-05-24T01:15:04+02:00]]
## Reframe After #1780
User challenged the width focus. Corrected interpretation: viewport containment is only a guardrail. The next #1773 pass should prioritize general Cockpit UX quality: task selection, information hierarchy, repeated workflows, edit confidence, decision resolution clarity, memory triage, ideas capture, keyboard/focus affordance, loading/error/empty states, and whether each tab's intended job is obvious and efficient at supported desktop widths.

[[2026-05-24T01:57:30+02:00]]
## User Feedback Capture
User provided general UX feedback and clarified priorities. Created/refined tasks:
- #1781: proof-readiness / route transition fade artifact.
- #1782: closed as loading/capture artifact, not product issue.
- #1783: closed; horizontal Kanban scrolling is acceptable.
- #1784: broadened to task and decision detail modal frame/content overhang.
- #1785: Kanban cards should vertically expand or otherwise show all tags intentionally.
- #1786: theme switcher should be round and transparent at rest.
- #1787: task detail should clarify move/archive actions.
- #1788: task detail hierarchy/labels need discussion.
- #1789: task tag/dependency editors need clearer structured input.
- #1790: dependency status data contract must be verified; no direct filesystem interaction.
- #1791: Kanban filters should align with trigger and expose clear filters.
- #1792: Decisions need metadata and reduced agent prominence.
- #1793: Ideas header status pill may be redundant; consider saved recency.

All are discussion tasks only. No implementation is approved by this feedback alone.
