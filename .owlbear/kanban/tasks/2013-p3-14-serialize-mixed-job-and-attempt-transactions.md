---
id: 2013
title: 'P3-14: Serialize mixed job and attempt transactions'
status: shape
priority: high
created: 2026-07-23T14:40:53.788290+02:00
updated: 2026-07-23T23:28:20.147724+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - transactions
  - attempts
  - concurrency
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004-D
parent: 2003
depends_on:
  - 2011
  - 2012
ac:
  - 'AC-1: Given a mixed plan containing one replacement `JobRecord` and one immutable
    attempt event, interruption followed by runtime reopen yields the complete pair
    or the pre-transaction state, never a strict subset.'
  - 'AC-2: Given two processes using the same expected job bytes with different attempt
    events, exactly one process commits its matching job/event pair; the rival receives
    the stable OCC or conflict outcome and publishes no rival event.'
  - 'AC-3: Given byte-equivalent replay of a committed mixed plan, the operation returns
    the existing pair and creates no duplicate event.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
A mixed transaction atomically couples one OCC `JobRecord` replacement with one immutable attempt event and serializes competing processes.

## Scope
In scope: mixed replacement/create participant plans; reopen recovery; same-expected-bytes process races; stable loser outcome; byte-equivalent replay; no strict-subset visibility.

Out of scope: replacement-manifest primitives, attempt model/store behavior, readiness guards, receipt validity, and lifecycle policy.

## Current Foundation And Ownership
Compose the immutable attempt store from task #2011 with the recoverable replacement primitive from task #2012. This task owns only mixed participant serialization and process-race proof.

## Authority
Resolve behavior from `REQ-016`, `IF-003`, `KEEP-007`, `RISK-002`, `PROOF-003`, and design sections 7.2, 9.5, 12, and 13.

## Proof Guidance
Exercise a mixed job/event plan over explicit temporary roots. Inject one mixed interruption and run a two-process same-expected-job race; lower primitive failure matrices remain in their owning tasks.

[[2026-07-23T15:37:50+02:00]]
## Builder Notes
- Change envelope: compose task #2011's immutable attempt store with task #2012's recoverable OCC replacement primitive, then prove mixed-plan interruption, process races, and byte-equivalent replay.
- Files changed: none.
- Change Module Map deviations: no source inspection or implementation occurred because the required #2012 foundation is not build-ready.
- Proof selected: none; its required owner is unavailable.
- Durable-test justification: no tests added.
- Commands run: none.
- Builder-challenger result: not invoked; a DONE verdict was not proposed.
- Follow-up risk: task #2012 is in `shape`, but this task's scope requires its replacement/reopen primitive. Reshape or complete #2012 before redispatching #2013.

[[2026-07-23T23:28:20+02:00]]
## Shape Notes
- Initial classification changed from mechanical reroute to connected local contract repair after live-source validation.
- Dependency check: #2011 and #2012 are archived completed; no pending or resolved requests exist. The original builder dependency blocker is gone.
- New source fact: `RuntimeTransaction` accepts byte participants, but canonical job replacement bytes/path and immutable attempt bytes/path remain private (`jobs._serialized_job`, `attempts._event_content`, and their private path helpers). The current AC terms `runtime reopen`, `stable outcome`, and `the operation` do not name a public mixed-plan construction or observation boundary.
- Repair needed: define store-owned public participant planning for `JobStore` and `AttemptStore`, keep generic publication/recovery in `RuntimeTransaction`, replace AC with exact commit/recover/read/race/replay observations, and update parent #2003's module/scenario maps.
- Lifecycle: released unchanged in shape. Restart as connected set #2003 and #2013, claimed in ID order, before the first mutation.
