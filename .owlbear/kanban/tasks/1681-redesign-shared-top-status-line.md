---
id: 1681
title: Redesign shared top status line
status: research
priority: important
created: 2026-05-21T19:51:40.481282+02:00
updated: 2026-05-21T19:51:40.481282+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - ux-feedback
  - status-bar
  - decision-needed
parent:
depends_on: []
ac:
  - Inventory current top-status signals and menus across routes.
  - Classify each signal by value, duplication, and urgency.
  - Present a recommended shared status-line model for user decision before 
    implementation.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## User Feedback
Top bar feels very non-uniform: `o 0 tasks, Health OK, DR 1` reads like one optical button but is actually multiple things. The green light lacks explanation/hover, task count value is unclear, `Health OK` as full text is weird. Dropdown menus are the right choice, but the shared header status line needs a step-back decision.

## Framing
Use this task as a product/audit todo item, not an instruction to hand off to the pipeline automatically.

## Evaluation Notes
- Classification: user-observed current product/status architecture issue.
- Decision needed: what information belongs in the always-visible status line across all pages?
- Value questions: what is useful globally, what duplicates page content, and what should be hidden until there is a problem?
- Screenshot target: all routes with normal/empty/problem states if available.

## Acceptance Criteria
- Inventory every current top-status item and what action/menu it controls.
- Classify each item as global signal, page-specific duplicate, action launcher, or noise.
- Present a recommended status-line model to the user before implementation.