---
id: 2057
title: 'P9-03: Install the independent node acceptor workflow'
status: build
priority: high
created: 2026-07-25T17:19:45.152185+02:00
updated: 2026-07-25T17:19:45.152185+02:00
tags:
  - phase-9
  - scope:agent
  - acceptor
  - orchestrator
  - read-only
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-008
  - packet:DN-008-PK-002
  - interface:IF-009
parent: 1985
depends_on:
  - 2056
ac:
  - 'AC-1: `w-node-acceptance` rehydrates only successful `start_job` identity, engine
    checkout, admitted node authority, current plan, packet receipts, and exact-SHA
    proof; it requires replacements and before/after tracked state, then returns one
    complete `AcceptorSuccess | AcceptanceRejected | AcceptanceBlocked` disposition.'
  - 'AC-2: The `acceptor` agent has no edit or lifecycle tools, uses the read-only
    write guard and tracked-diff check, executes proof only in the engine checkout
    or scratch, and cannot pick, start, finish, release, or approve authored tracked
    changes; agent validation and WIRING inspection prove the boundary.'
  - 'AC-3: `w-orchestration` maps `AcceptorSuccess` fields unchanged to `finish_accept`,
    `AcceptanceRejected` fields unchanged to `reject_accept`, and `AcceptanceBlocked`
    with unchanged identity to `release_job`; orchestrator exposes the acceptor and
    rejection tool, halts after one job, and does not classify findings or assemble
    evidence.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-008-PK-002`. Resolve behavior from REQ-006, WF-004, IF-009, NEG-003, NEG-009, RISK-008, and PROOF-007.

## Outcome
Install one hard-read-only acceptor role, its exact-commit workflow, and deterministic orchestrator routing.

## Envelope
In: workflow, agent declaration, write guard, orchestrator mapping, agent validation, and WIRING.

Out: runtime/MCP semantics, auditor work, setup/seed propagation, and Cockpit.