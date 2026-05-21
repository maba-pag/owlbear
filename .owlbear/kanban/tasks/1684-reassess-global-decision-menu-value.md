---
id: 1684
title: Reassess global decision menu value
status: research
priority: important
created: 2026-05-21T19:52:10.714317+02:00
updated: 2026-05-21T19:52:10.714317+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - decisions
  - decision-needed
parent:
depends_on: []
ac:
  - Map current decision signals and action entry points across Cockpit.
  - Evaluate whether global decision resolution duplicates or helps the intended
    workflow.
  - Present a recommendation before changing the global decision menu behavior.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Why is there a decision menu with the ability to decide on the kanban board? The information that decisions are open may be helpful, but the left-menu counter plus orange task background might be enough to alert.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed product workflow concern; needs design decision.
- Value question: should decision resolution be globally available from every page, or only visible as a notification that routes users to the Decisions workspace/task context?
- Screenshot target: top status DR menu, left nav badge, orange task state, Decisions route.

## Acceptance Criteria
- Map all current decision entry points and what each lets the user do.
- Compare global resolve menu vs route-only decision workflow for morning cockpit usage.
- Present recommendation before removing or demoting the global decision menu.