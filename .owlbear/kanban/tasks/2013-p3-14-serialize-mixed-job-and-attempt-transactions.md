---
id: 2013
title: 'P3-14: Serialize mixed job and attempt transactions'
status: verify
priority: high
created: 2026-07-23T14:40:53.788290+02:00
updated: 2026-07-23T23:42:12.115289+02:00
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
  - 'AC-1: Given a stored job and its current token, `JobStore.replacement_participant(replacement,
    expected_token)` returns a `ReplacementTransactionParticipant` for `jobs/{job_id}.yaml`
    without changing stored bytes; a stale token raises `ERR_JOB_OCC_STALE` and returns
    no participant.'
  - 'AC-2: Given an `AttemptEvent` with a safe attempt ID and positive sequence, `AttemptStore.create_participant(event)`
    returns a `TransactionParticipant` for `attempts/{attempt_id}/{sequence}.json`
    without creating the event; committing that participant makes `AttemptStore.read`
    return the input event.'
  - 'AC-3: Given a `RuntimeTransaction` containing one planned job replacement followed
    by one planned attempt event, interruption after the first publication followed
    by `RuntimeTransaction.recover_all` makes `JobStore.read` return the replacement
    and `AttemptStore.read` return the event, removes the manifest, and leaves no
    temporary participant file.'
  - "AC-4: Given two processes with participant tuples planned from the same job token
    but different replacement records and attempt IDs, one `RuntimeTransaction.commit`
    succeeds and the rival returns `ERR_TRANSACTION_CONFLICT`; store reads return
    the successful process's matching job/event pair and the rival attempt ID remains
    missing."
  - 'AC-5: Given a committed mixed participant tuple, committing a byte-equivalent
    tuple again leaves `JobStore.read` and `AttemptStore.read` equal to the committed
    pair, `AttemptStore.list` contains one matching event, and no transaction manifest
    remains.'
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

[[2026-07-23T23:29:53+02:00]]
## Operative Mixed Participant Planning Amendment

This amendment supersedes earlier terms that refer only to a `mixed plan`, `runtime reopen`, `stable outcome`, or `the operation` without naming callable boundaries.

### Public Planning Boundaries

- `JobStore.replacement_participant(replacement, expected_token)` reads the current canonical job bytes for `replacement.job_id`, verifies `expected_token` through existing `JobStore` OCC authority, and returns a `ReplacementTransactionParticipant` rooted at the store work root and `jobs/{job_id}.yaml`. A stale token raises existing `ERR_JOB_OCC_STALE`; planning does not mutate the job.
- `AttemptStore.create_participant(event)` validates the event identity through the store's existing safe location rule and returns a `TransactionParticipant` rooted at the store work root and `attempts/{attempt_id}/{sequence}.json` with the same canonical bytes consumed by `AttemptStore.create`. Planning does not create the event.
- `RuntimeTransaction` remains the generic mixed commit and `recover_all` boundary. Task #2013 does not add lifecycle policy or a native-runtime facade.

### Change Module Map

- `serve/kanban/src/owlbear_kanban/jobs.py`: owns job replacement participant planning, canonical stored/replacement bytes, job path, and existing stale-token result.
- `serve/kanban/src/owlbear_kanban/attempts.py`: owns immutable attempt participant planning, canonical bytes, and safe event path.
- `serve/kanban/src/owlbear_kanban/runtime_transaction.py`: existing mixed participant commit, shared-lock serialization, manifest recovery, conflict, and cleanup authority; change only if a small generic correction is exposed by the mixed proof.
- `serve/kanban/tests/test_runtime_transaction.py`: public-boundary proof using real `JobStore`, `AttemptStore`, participant factories, `RuntimeTransaction.commit`, `recover_all`, and store reads.
- `serve/kanban/tests/test_jobs.py` and `test_attempts.py`: existing store behavior remains regression proof; add durable cases only for concrete factory behavior not exercised by the mixed boundary.

### Scope Boundary

Task #2013 owns participant planning and mixed transaction evidence. Task #2012 retains shared locks and replacement recovery primitives. Tasks #2017 through #2019 consume the resulting mixed boundary for start/finalization/retry policy.

[[2026-07-23T23:35:31+02:00]]
## Shape Notes
- Rejection source: the earlier builder stopped because #2012 was in shape. That dependency is now archived completed, but live-source validation exposed a second local gap: canonical job and attempt participant construction was private and the old AC did not name an assembled callable boundary.
- Repair classification: connected local task repair with parent #2003; no product, architecture, or graph decision changed.
- Public planning contract: `JobStore.replacement_participant(replacement, expected_token)` creates a non-mutating replacement participant from canonical current/replacement bytes and raises existing `ERR_JOB_OCC_STALE` for a stale token. `AttemptStore.create_participant(event)` creates a non-mutating immutable participant using the store's canonical safe path and bytes. `RuntimeTransaction` remains the generic commit/recover boundary.
- AC repair: AC-1 proves current/stale job planning and no mutation; AC-2 proves attempt planning plus commit/read; AC-3 proves after-first-publication recovery to both store records with cleanup; AC-4 proves a two-process same-token rival pair yields one success, one `ERR_TRANSACTION_CONFLICT`, and no rival event; AC-5 proves byte-equivalent replay leaves one matching event and no manifest.
- Change Module Map: `jobs.py` owns job participant planning, `attempts.py` owns attempt participant planning, `runtime_transaction.py` retains generic mixed publication/recovery, and `test_runtime_transaction.py` proves the real assembled boundary. Existing store suites remain regression boundaries.
- Scope: #2012 retains lock/replacement primitives. #2017 through #2019 retain lifecycle policy and consume this result through existing dependencies.
- Parent repair: #2003 maps and scenario axes now include participant planning; parent correction committed as `872e95991a834f457ab701766c5c0e8c203147e5`.
- Challenger: pass. It confirmed existing canonical helpers make both factories buildable, dependency direction creates no cycle, AC use real public boundaries and exact stable codes, and no strict-subset overclaim remains.
- Route: advance #2013 from shape to build; dependencies #2011 and #2012 are archived completed.

[[2026-07-23T23:42:12+02:00]]
## Builder Notes
- Change envelope: add store-owned public planning for one OCC job replacement and one immutable attempt creation; compose them through the existing `RuntimeTransaction` commit/recovery boundary. No runtime engine or lifecycle-policy change.
- Files changed: `serve/kanban/src/owlbear_kanban/jobs.py`, `serve/kanban/src/owlbear_kanban/attempts.py`, and `serve/kanban/tests/test_runtime_transaction.py`.
- Change Module Map deviations: none. `runtime_transaction.py` required no generic correction.
- Proof selected: durable public-boundary regression tests. They protect atomic cross-store publication, replay, recovery, and process serialization, which are hard to detect manually and materially risky to regress.
- Commands run:
  - `uv run pytest -o addopts='--import-mode=importlib -m "not e2e" -p no:logfire -p no:pytest_logfire' serve/kanban/tests/test_jobs.py serve/kanban/tests/test_attempts.py serve/kanban/tests/test_runtime_transaction.py` -> 55 passed.
  - `uv run ruff check serve/kanban/src/owlbear_kanban/jobs.py serve/kanban/src/owlbear_kanban/attempts.py serve/kanban/tests/test_runtime_transaction.py` -> passed.
  - `uv run ruff format --check serve/kanban/src/owlbear_kanban/jobs.py serve/kanban/src/owlbear_kanban/attempts.py serve/kanban/tests/test_runtime_transaction.py` -> passed.
- AC-to-evidence map:
  - AC-1: `JobStore.replacement_participant` reuses canonical job serialization and OCC authority; the mixed recovery test proves no planning mutation and `ERR_JOB_OCC_STALE` behavior.
  - AC-2: `AttemptStore.create_participant` reuses safe location validation and canonical event content; the mixed recovery test proves planning does not create the event and commit makes it readable.
  - AC-3: the mixed recovery test interrupts after first publication, invokes `recover_all`, and asserts both records, no manifest, and no temporary files.
  - AC-4: the coordinated forked process-race test proves one success, `ERR_TRANSACTION_CONFLICT` for the rival, matching winner records, and no rival event.
  - AC-5: the mixed recovery test commits a byte-equivalent replay and asserts one matching event plus no manifest.
- Current failure-key resolutions: none returned from verify.
- Builder-challenger result: pass; no concrete blockers.
- Follow-up risks: process-race proof uses `fork`, available on the supported macOS/Linux environment.
