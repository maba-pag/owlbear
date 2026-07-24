---
id: 2017
title: 'P3-18: Start only eligible job attempts'
status: shape
priority: high
created: 2026-07-23T14:41:39.975443+02:00
updated: 2026-07-24T03:01:51.869841+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - claims
  - attempts
  - lifecycle
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004-H
parent: 2003
depends_on:
  - 2013
  - 2016
ac:
  - 'AC-1: Given an open job matching loaded authority, current predecessor validity,
    no pending request, and no terminal disposition or active claim, `start_job` atomically
    writes `claim_id` and `attempt_id` on the job plus one `started` event at the
    supplied claim timestamp.'
  - 'AC-2: Given an active claim, stale authority, invalid predecessor projection,
    pending request, or terminal disposition, `start_job` returns the stable reason
    for that class and leaves the job and attempt history unchanged.'
  - 'AC-3: Given replay with the same caller-supplied attempt identity that matches
    the active claim, `start_job` returns the existing outcome; a different identity
    is rejected without an additional event.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
A transport-free native runtime starts one eligible job attempt by atomically persisting the active claim pointers and one immutable `started` event.

## Scope
In scope: loaded-authority match; complete predecessor validity; pending-request and terminal-disposition guards; active-claim exclusion; caller-supplied attempt identity; claim and process identity; supplied claim timestamp on the started event; idempotent same-identity replay; stable rejection reasons.

Out of scope: transaction failure matrices, receipt evaluator internals, release/failure, expiry recovery, successful completion, dispatch waves, global writer leases, MCP, and Cockpit.

## Current Foundation And Ownership
Compose the mixed job/event transaction from task #2013 with complete receipt currentness from task #2016. Add the `start_job` operation to the transport-free native runtime facade; callers do not mutate `JobStore` directly.

## Authority
Resolve behavior from `REQ-008`, `REQ-009`, `REQ-016`, `IF-003`, `KEEP-007`, `PROOF-003`, design sections 4.3, 7.2, 8.6, 13, and 14, and accepted `DEC-007` and `DEC-009`.

## Proof Guidance
Exercise public `start_job` with the finite readiness classes eligible, active claim, stale authority, invalid predecessor, pending request, terminal disposition, same-identity replay, and different identity. Lower transaction and validity failure matrices remain in their owners.

[[2026-07-23T23:49:54+02:00]]
## Builder Notes
- Change envelope: add the transport-free native runtime facade and its public `start_job` contract, composing `JobStore`, `AttemptStore`, `RuntimeTransaction`, and complete receipt currentness. The contract must define constructor inputs, request/result models, stable reason codes, loaded-authority source, terminal dispositions, and claim/process identity semantics.
- Files changed: none; task metadata only.
- Change Module Map deviations: source confirms no existing runtime facade or state/request projection owner. The shaped map names the facade outcome but does not name its module or contract boundary.
- Proof selected: source inspection plus exact searches for `start_job`, native runtime facade, active-claim/terminal-disposition contract, and tests. This disproved the availability of a local owner and a public callable to exercise.
- Durable-test justification: no test added because no stable public contract exists to protect.
- Commands run: `git status --short && git diff -- .owlbear/kanban/tasks/2017-p3-18-start-only-eligible-job-attempts.md` (only expected claim metadata on this task; unrelated worktree changes preserved).
- AC-to-evidence map: AC-1 cannot be implemented without an authoritative `start_job` request/result and authority-loading contract. AC-2 cannot select stable reasons without a terminal-disposition vocabulary and readiness projection. AC-3 cannot define same-identity replay without the caller identity and outcome shape.
- Current failure-key resolutions: none; no Verify Notes or Required Follow-up section.
- Builder-challenger result: not invoked; no DONE verdict is proposed.
- Follow-up risk: shape must define the facade module, public callable signature/models, loaded-authority and candidate-revision inputs, request/terminal state ownership, exact stable rejection codes, and same-identity outcome semantics. Implementing these choices here would invent an unadmitted cross-module interface.

[[2026-07-24T03:01:51+02:00]]
## Shape Notes
- Material repair review completed. The builder correctly found that the original task lacked a public facade, request/result models, exact diagnostics, terminal vocabulary, and replay contract.
- User decision: approved Option A, strict `JobDisposition = pending | cancelled | superseded` plus a dedicated `NativeRuntime.start_job` result. Unknown dispositions fail schema validation; lower-layer code/target remain optional diagnostic evidence rather than public control flow.
- Authority reconciliation: added accepted DEC-022, design section 7.3, and extended IF-003 with strict disposition, six stable `ERR_START_*` diagnostics, ordered eligibility checks, atomic start, and exact replay identity including claimed_at.
- Validation: revised package loads. Standard focused authority tests produced 31 passes and four existing DV-010 failures because global admission metadata is null/old. With an in-memory current-digest admission marker, admission evaluation returned no findings at digest `ce87d37e9935c7dfbb07a52ad485a8ce4b3641d3b054ba72417b0d80577f1a82`. Archived #2021 records this live-change admission limitation as delegated to DN-013/DN-014 rather than a leaf blocker.
- Draft graph: #2017 owns jobs.py strict disposition migration, new native_runtime.py start facade/models, package exports, and public start tests. Dependencies remain #2017 after archived #2013/#2016, then #2018 and #2019.
- Draft AC: eight independently verifiable cases cover schema literals, eligible atomic start, stale authority, predecessor invalidity, pending request, terminal states, exact/conflicting replay identity, and different/inconsistent active claims.
- Challenger: final complete graph challenge passed after adding explicit DEC-022/design 7.3 task authority, schema-migration ownership, and complete eligible preconditions.
- User graph approval: approved the presented #2003/#2017 graph delta.
- Lifecycle: release #2017 without movement. Commit reconciled authority and this task history, then restart the approved connected mutation set by claiming #2003 and #2017 in ID order.
