---
id: 1944
title: 'P1-08: Module-aware Workspace Status and repair feedback'
status: build
priority: medium
created: 2026-07-17T02:32:30.849128+02:00
updated: 2026-07-17T02:33:38.587603+02:00
tags:
  - phase-1
  - scope:cockpit-web
  - ui
  - health
parent: 1945
depends_on:
  - 1943
ac:
  - Given checking, healthy, attention, unhealthy, and check-failed module 
    states, Workspace Status renders an overall light plus 
    task/request/memory/ideas lights and labels; repair remains available when 
    task repairable_count is positive even if unresolved findings make the task 
    row red.
  - Given a completed or partially failed task repair, closing 
    confirmation/popover leaves a dismissible receipt showing completion time 
    and removed/moved/quarantined/skipped/failed/unresolved counts; only 
    unresolved/failed item details are shown, and polling does not erase the 
    receipt.
  - The assembled Cockpit Workspace Status has no generic Cleanup control or 
    task-only scan path, and VS Code integrated-browser observation shows gray 
    initial state followed by module results without overlap or lost feedback.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Replace the task-only status and generic Cleanup experience with a four-module Workspace Status, one task-repair action, and a dismissible repair receipt that survives overlay closure and polling.

## Scope
In scope: Cockpit Workspace Status components and Shell assembly, module and overall indicators, repair availability, confirmation/result presentation, receipt dismissal, generic Cleanup removal, and integrated-browser visual/workflow proof. Out of scope: backend contracts, provider ordering internals, memory purge, and broad keyboard/accessibility expansion.

## Planning Authority
OpenSpec change: `redesign-workspace-health`, including the accepted module rows, status colors, unresolved-only detail rule, and repair receipt lifetime. Ordered frontend state is supplied by dependency #1943.

## Complexity Waiver
Package-local behavior checks and the VS Code integrated browser are both required: component checks protect state/interaction behavior, while the assembled browser proves overlay lifetime, layout, and visible state transitions. They cover one UI failure domain and should finish in one frontend pass.

## Proof Guidance
Run package-local frontend checks and use the VS Code integrated browser for the assembled workflow. Capture screenshots where they materially prove initial gray state, module layout, or retained feedback; avoid adding durable visual tests unless they protect a recurring product risk.