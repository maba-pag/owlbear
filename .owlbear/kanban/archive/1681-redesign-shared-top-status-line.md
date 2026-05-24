---
id: 1681
title: Redesign shared top status line
status: archived
priority: important
created: 2026-05-21T19:51:40.481282+02:00
updated: 2026-05-24T10:50:01.001573+02:00
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
archival_reason: completed
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

## Implementation Evidence
- Classification: observed current product issue, not theoretical.
- Impact: hurt the current cockpit now. The old `0 tasks / Health OK / DR 1` line looked like one optical control while mixing count, health, and decision actions.
- Decision: user selected route-owned decisions. The shared header now shows Workspace Status plus ThemeToggle; task count and global DR resolver were removed from the top bar.
- Evidence: desktop/mobile screenshots in `.owlbear/scratch/1672-status-route-owned-desktop-header.png` and `.owlbear/scratch/1672-status-route-owned-mobile-header.png`; browser checks show no `task-count`, no `dr-indicator`, and decisions badge remains in the left nav.
- Verification: `npm run build`; `npm run test:e2e:all -- e2e/shell-sidecar-inspector.spec.ts --reporter=line`; `npm run test:e2e:all -- e2e/overlay-behavior.spec.ts --reporter=line`.