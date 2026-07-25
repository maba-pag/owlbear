---
id: 2055
title: 'P9-01: Atomically reject accept attempts into corrective work'
status: build
priority: high
created: 2026-07-25T17:19:27.594283+02:00
updated: 2026-07-25T17:19:27.594283+02:00
tags:
  - phase-9
  - scope:kanban
  - acceptance
  - invalidation
  - transaction
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-008
  - packet:DN-008-PK-001
  - interface:IF-009
parent: 1985
depends_on: []
ac:
  - 'AC-1: Given a current owned accept attempt, typed findings and corrective routes,
    affected receipts, stable output IDs, evidence replacements, and code revision,
    public `DispatchRuntime.reject_accept` atomically publishes the findings, failed
    terminal attempt, supersession receipt, minimum corrective jobs, superseded affected
    jobs, reader release, and proof-checkout cleanup; returned and persisted state
    match.'
  - 'AC-2: Replaying the same rejection identity returns the persisted outcome without
    duplicate finding, event, receipt, or job; changing one immutable identity returns
    the stable conflict diagnostic and complete artifact snapshots remain unchanged.'
  - 'AC-3: Missing or stale claim, digest, receipt, finding target, route, job identity,
    checkout cleanup failure, or injected transaction failure returns a stable diagnostic;
    finding, attempt, receipt, job, coordination, and checkout snapshots prove no
    partial publication.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-008-PK-001`. Resolve behavior from WF-004, IF-009, REQ-008, DEC-009, and PROOF-007.

## Outcome
Add one purpose-specific core rejection transaction for an active accept attempt.

## Envelope
In: finding transaction participation, composable invalidation preparation, terminal attempt state, minimum corrective jobs, reader release, checkout cleanup, replay, and stable diagnostics.

Out: MCP exposure, agent workflow, new finding taxonomy, accept success, Cockpit, setup, and seed work.