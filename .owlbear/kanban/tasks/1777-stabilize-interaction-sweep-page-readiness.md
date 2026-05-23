---
id: 1777
title: Stabilize interaction sweep page readiness
status: done
priority: important
created: 2026-05-24T00:36:40.855465+02:00
updated: 2026-05-24T00:54:39.281852+02:00
tags:
  - cockpit-perfect-ui
  - scope:cockpit-web
  - visual-proof
  - tooling
  - discussion
parent: 1773
depends_on:
  - 1773
ac:
  - Future Cockpit interaction sweeps wait for route-specific loaded content
    rather than capturing transient Preparing states.
  - Evidence scripts avoid false findings caused by early screenshots.
  - The task remains tooling-only unless user approves implementation of
    script/test harness changes.
proof_bundle: smoke
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
#1773 screenshots `320-header-rest`, `320-kanban-rest`, `768-kanban-rest`, and similar early captures show `Preparing board...` even though later screenshots in the same run show loaded Kanban content. This is a proof-quality issue, not a product UI finding.

## Value Question
The sweep is supposed to decide product improvements. If screenshots catch transient loading states by accident, we could create noisy or misleading findings.

## Current Interpretation
Observed tooling harm now. It does not imply Cockpit itself is wrong; it means the sweep script should wait for loaded route content before rest captures.

## Evidence
- `.owlbear/scratch/1716-wide-cockpit/1773-evidence-interaction-sweep-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1773-320-header-rest.png`
- `.owlbear/scratch/1716-wide-cockpit/1773-320-kanban-rest.png`
- `.owlbear/scratch/1716-wide-cockpit/1773-768-kanban-rest.png`

[[2026-05-24T00:54:34+02:00]]
## Resolution Evidence
The #1773 sweep script now waits for Kanban task cards before header/Kanban captures and uses the desktop support-width viewport set: 1024, 1200, 1440, 2000. The rerun produced 52 screenshots without transient `Preparing board...` captures, console errors, or request failures.

Outputs:
- `.owlbear/scratch/1716-wide-cockpit/1773-desktop-interaction-sweep-contact-sheet.png`
- `.owlbear/scratch/1716-wide-cockpit/1773-desktop-interaction-sweep-metrics.json`
