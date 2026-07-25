---
id: 2065
title: 'P10-06: Prove audit rejection and minimum whole-change correction'
status: verify
priority: high
created: 2026-07-25T19:53:54.333878+02:00
updated: 2026-07-25T22:07:30.972357+02:00
tags:
  - phase-10
  - scope:test
  - auditor
  - rejection
  - corrective-work
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-014
  - packet:DN-014-PK-006
  - interface:IF-014
  - proof:PROOF-008
parent: 1986
depends_on:
  - 2064
ac:
  - 'AC-1: Real audit scenarios for cross-node integration and implemented migration
    absence make the shipped workflow emit strict `implementation-defect` findings
    and `whole-change-integration` routes whose `affected-node-correction` jobs identify
    only implicated nodes; an admitted authority or proof omission emits `planning-omission`,
    `design_reentry=true`, and zero jobs.'
  - 'AC-2: Public `reject_audit` publishes the finding, event, supersession, affected
    closure, and minimum jobs, cleans reader and checkout state, preserves unrelated
    receipt bytes, and replays without mutation; public queries expose the persisted
    correction chain.'
  - 'AC-3: A stale accept receipt and unresolved request are rejected before claim
    by `ERR_START_PREDECESSOR_INVALID` and `ERR_START_REQUEST_PENDING` without checkout
    or claim mutation; an auditor tracked edit produces `AuditBlocked`, write denial,
    unchanged-identity release, no finding, receipt, or job publication, and cleanup.'
  - 'AC-4: Malformed evidence or invalidation, cleanup failure, and injected transaction
    or OCC failures return stable public diagnostics; complete snapshots show no partial
    finding, event, receipt, job, coordination, or checkout publication.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Projection
`replace-delivery-pipeline` at `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; `DN-014-PK-006`. Resolve behavior from REQ-007, REQ-008, WF-005, IF-014, NEG-003, NEG-009, RISK-008, RISK-009, and PROOF-008.

## Outcome
Complete PROOF-008's rejection, minimum correction, dispatch gates, independence, failure atomicity, replay, and cleanup matrix.

## Envelope
In: real audit jobs, shipped dispositions, public reject/release, typed findings and routes, stale/request gates, snapshots, replay, and cleanup.

Out: new semantics, Cockpit, setup, cutover, and complete-system proof.

Proof guidance: extend the maintained assembled public audit scenario with the finite rejection and failure matrix plus native failure injection.

[[2026-07-25T22:07:30+02:00]]
## Builder Notes
DONE

Adopted and repaired the interrupted delegated test work within the shaped three-file envelope.

- AC-1: public real-Git route matrix covers cross-node integration, implemented migration absence, and admitted-authority omission; native assertions prove exact implicated-node jobs and zero-job design re-entry.
- AC-2: public `reject_audit` proves persisted finding queries, failed event, superseded audit job, affected closure, replay without mutation, reader/checkout cleanup, and preservation of every pre-existing receipt byte.
- AC-3: real superseded `accept-final` and real unresolved native request both fail public preclaim with the required stable diagnostics and no claim/checkout mutation; tracked auditor write denial maps to canonical `AuditBlocked`, then public release preserves publication state and cleans reader/checkout state.
- AC-4: invalid finding/invalidation/identity cases plus cleanup orphan/exception and injected transaction conflict preserve complete work/receipt snapshots and checkout authority; the maintained strict public schema test owns malformed-parameter pre-dispatch proof.

Changed files: `serve/kanban/tests/test_native_runtime.py`, `serve/kanban/tests/test_dispatch_runtime.py`, `serve/mcp-kanban/tests/test_mcp_acceptance_tools.py`.

Evidence: focused public matrix 7 passed; native/dispatch rejection matrix 12 passed; focused workspace lint passed; all three affected modules passed 86 tests; `git diff --check` passed. Builder challenger decision: pass and independently reran the 86-test module suite.
