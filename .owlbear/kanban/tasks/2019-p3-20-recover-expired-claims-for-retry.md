---
id: 2019
title: 'P3-20: Recover expired claims for retry'
status: build
priority: high
created: 2026-07-23T14:42:08.799937+02:00
updated: 2026-07-24T13:15:32.665080+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - claims
  - attempts
  - recovery
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004-J
parent: 2003
depends_on:
  - 2017
  - 2018
ac:
  - 'AC-1: Given positive `claim_expiry`, `NativeRuntime` constructs; zero or negative
    duration raises `ValueError`. `RecoverExpiredClaimsRequest` accepts a timezone-aware
    ISO `recovered_at` and rejects malformed or naive timestamps.'
  - 'AC-2: Given an active job whose started timestamp plus `claim_expiry` is after
    or equal to `recovered_at`, `recover_expired_claims` returns no outcome and changes
    no bytes. A strictly later `recovered_at` clears matching pointers and appends
    one sequence-2 `crashed` event.'
  - 'AC-3: The recovered job remains `pending` and uses `recovered_at` as `updated_at`.
    Its crashed event carries the active job, attempt, and claim; request actor, process,
    and timestamp; detail `claim expired`; and no evidence IDs.'
  - 'AC-4: Given active jobs stored out of job-ID order, recovery evaluates ascending
    job IDs and returns expired outcomes in ascending job-ID order; non-expired and
    release/fail-resolved jobs produce no outcome or diagnostic.'
  - 'AC-5: Given inconsistent active pointers, missing or mismatched started identity,
    or invalid started timestamp, recovery returns `ERR_RECOVERY_IDENTITY_INVALID`
    for that job. A transaction destination conflict returns `ERR_RECOVERY_CONFLICT`;
    either leaves that job unchanged and does not prevent a later eligible job from
    recovery.'
  - 'AC-6: Given an exact repeated request after recovery, `recover_expired_claims`
    returns the existing job/crashed-event pair and `AttemptStore.list` retains one
    crashed event. A newly assembled `NativeRuntime` with the same policy and request
    returns the same result.'
  - 'AC-7: Given a recovered job that starts a later attempt, repeating the older
    recovery request does not return the prior crash outcome or mutate the later active
    claim.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
The native runtime deterministically converts an expired active claim into immutable crash evidence and an open retryable job.

## Scope
In scope: supplied recovery time; configured positive expiry duration; strict expiry boundary; crashed event; atomic matching-claim clear; retryability; reopen-driven recovery; idempotent repeated sweep; non-expired and already-resolved no-op behavior.

Out of scope: process liveness probing, successful completion, dispatch policy, global writer leases, receipt creation, MCP, and Cockpit.

## Current Foundation And Ownership
Compose start identity from task #2017 with owner-finalization behavior from task #2018. Deepen the same native runtime facade; preserve its mixed transaction and immutable event semantics.

## Authority
Resolve behavior from `REQ-008`, `REQ-009`, `REQ-016`, `IF-003`, `KEEP-007`, design sections 2.2, 2.3, 7.2, 8.6, 13, and 14, and accepted `DEC-007` and `DEC-009`.

## Proof Guidance
Exercise public recovery at just before, exactly at, and just after expiry; then reopen and repeat recovery. Keep process-race and transaction interruption matrices in tasks #2013 and #2012.

[[2026-07-24T12:59:45+02:00]]
## Builder Notes
- Change envelope: deepen the native `NativeRuntime` facade with expiry recovery only, preserving its `JobStore`, `AttemptStore`, and mixed transaction ownership. Expected files, if contract-ready: `serve/kanban/src/owlbear_kanban/native_runtime.py`, package exports, and focused native-runtime behavior coverage.
- Files changed: none; task metadata only.
- Change Module Map deviations: source confirms `NativeRuntime` is the lifecycle owner, but the shaped task does not identify the owner or representation of the required configured positive expiry duration, nor a public recovery request/result interface.
- Preflight routing: rejected to shape. The admitted design requires claims to be recoverable and preserves crashed attempts as operational events; its native start/finalization sections do not specify recovery parameters, diagnostics, configuration source, or result projection. The existing legacy `KanbanEngine.sweep()` uses implicit wall-clock time and a legacy config timeout, which cannot establish the required native contract with supplied recovery time.
- Proof selected: source comparison of native runtime, its public tests, admitted design, and the legacy sweep. No durable test added because there is no approved interface to exercise.
- Commands run: `rg` authority/runtime search; `uv run --project . test-root serve/kanban/src/owlbear_kanban/native_runtime.py serve/kanban/tests/test_native_runtime.py`; focused source reads of `native_runtime.py`, `test_native_runtime.py`, admitted design, and legacy `engine.py` sweep.
- AC-to-evidence map: AC-1 through AC-3 cannot be proved or safely implemented until shape defines (1) the expiry-duration configuration owner and validation, (2) the public recovery operation’s request/result and per-job versus sweep scope, (3) crash-event actor/process/timestamp/detail identity, and (4) reopen integration point. Current source only establishes that existing release/fail finalization and legacy sweeping differ from the requested native behavior.
- Current failure-key resolutions: none.
- Builder-challenger result: not called; challenger is required only before a DONE verdict.
- Follow-up risks: implementing either a constructor config, a recovery request field, or a return projection without those decisions would create a second lifecycle contract and violate the task’s supplied-time requirement.

[[2026-07-24T13:12:13+02:00]]
## Shape Notes
- Material repair source: builder found no approved native expiry-policy owner, request/result/diagnostic contract, sweep scope, crash identity, or reopen integration point.
- User decisions: inject required positive `timedelta` expiry policy into `NativeRuntime`; recover through a deterministic ascending job-ID sweep rather than caller-selected single-job recovery.
- Authority reconciliation: accepted DEC-024, added design section 7.5, and extended IF-003. Recovery uses supplied aware time and executor identity, strict greater-than expiry, one job/event transaction per expired claim, ordered recovered outcomes and diagnostics, exact persisted replay, and no legacy BoardConfig dependency.
- Public contract draft: `RecoverExpiredClaimsRequest`, `RecoveredClaim`, `RecoveryDiagnosticCode`, `RecoveryDiagnostic`, and `RecoverExpiredClaimsResult`; stable diagnostics are `ERR_RECOVERY_IDENTITY_INVALID` and `ERR_RECOVERY_CONFLICT`.
- Validation: public `load_change` returns a revision with no diagnostics at digest `eaab0f2e46780f38b5df541d248fc54cb8a0483da1464f60f4d507c0f3cad617`; authority diffs pass `git diff --check`. Global re-admission remains DN-013/DN-014 bootstrap debt.
- Approved graph: connected set #2003/#2019, no edge changes. #2019 owns native recovery models, constructor policy, ordered sweep, strict boundary, per-job diagnostics, crash transaction, exact reopen replay, exports, and focused public tests. Existing jobs/attempts/transaction owners are reused unchanged.
- Seven AC cover policy/request validation, before/equal/after boundary, crash record fields, deterministic multi-job behavior, diagnostic isolation, exact same-instance/reopened replay, and later-retry separation.
- Complete shaper challenge passed with readiness, authority, ownership, dependency, scenario, proof, and fidelity coverage.
- User graph approval: approved the hardened #2003/#2019 recovery delta.
- Lifecycle: release #2019 without movement. Commit reconciled authority and this review history, then restart the connected mutation set by claiming #2003 and #2019 in ID order.

[[2026-07-24T13:13:34+02:00]]
## Operative Native Expired-Claim Recovery Contract

This amendment supersedes earlier Scope, Authority, ownership, and proof wording where they conflict with the contract below.

### Scope And Authority Amendment

In scope: required positive runtime expiry policy; aware supplied recovery time; deterministic native job sweep; active identity validation; strict expiry boundary; per-job crash transaction; ordered mixed results; exact persisted replay after reassembly; and later-retry separation. Process liveness, successful completion, dispatch policy, global writer leases, receipts, MCP, and Cockpit remain outside this task.

Controlling authority is `REQ-008`, `REQ-009`, `REQ-016`, `REQ-022`, `IF-003`, `KEEP-007`, design sections 2.2, 2.3, 7.2, 7.5, 8.6, 13, and 14, and accepted `DEC-007`, `DEC-009`, `DEC-023`, and `DEC-024`. `DEC-024` and design section 7.5 control expiry policy ownership, sweep scope, boundary semantics, diagnostics, and replay.

### Public Contract

- `NativeRuntime(revision, work_root, history, claim_expiry)` requires a positive `timedelta`; zero or negative values raise `ValueError`. It does not load legacy `BoardConfig` and requests cannot override policy.
- `RecoverExpiredClaimsRequest` contains timezone-aware ISO `recovered_at`, `actor_id`, and `process_id`; malformed or naive time fails request validation.
- `RecoveryDiagnosticCode` contains `ERR_RECOVERY_IDENTITY_INVALID` and `ERR_RECOVERY_CONFLICT`.
- `RecoveryDiagnostic` contains code, job ID, detail, and optional lower-layer code.
- `RecoveredClaim` contains one `StoredJob` and one `AttemptEvent`.
- `RecoverExpiredClaimsResult` contains recovered outcomes and diagnostics, each ordered by job ID; mixed success and diagnostics are valid.

### Sweep, Mutation, And Replay

`recover_expired_claims` first completes pending transactions rooted at the work root, reads active jobs in ascending job-ID order, and scans immutable attempt history once for replay. Active identity requires both job pointers and a sequence-one started event matching job, attempt, and claim with an aware timestamp. Missing or inconsistent identity returns `ERR_RECOVERY_IDENTITY_INVALID` for only that job.

A claim expires only when `recovered_at` is strictly later than the started timestamp plus `claim_expiry`; before and equality are no-ops. Recovery uses one `RuntimeTransaction` per expired job. It clears only matching claim and attempt pointers, keeps disposition `pending`, sets `updated_at` to `recovered_at`, and appends sequence-two `crashed` with active job/attempt/claim identity, request actor/process/time, detail `claim expired`, and no evidence. `TransactionConflictError` maps to `ERR_RECOVERY_CONFLICT` for that job; later jobs continue.

Non-expired and release/fail-resolved jobs produce no result entry. An exact repeated request returns a pointer-clear job whose `updated_at` equals `recovered_at` plus its matching persisted crash event, without duplication. A new runtime instance returns the same result. Starting a later attempt changes job identity and timestamp, so an older request cannot replay or mutate it.

### Change Module Map

- `serve/kanban/src/owlbear_kanban/native_runtime.py`: own recovery models, constructor policy, time validation, transaction completion, ordered sweep, identity checks, strict expiry, crash transaction, diagnostics, and persisted replay.
- `serve/kanban/src/owlbear_kanban/__init__.py`: export the recovery public contract.
- `serve/kanban/tests/test_native_runtime.py`: update existing constructor calls with positive policy and prove all recovery scenarios through the public facade over real stores and transactions.
- `serve/kanban/src/owlbear_kanban/jobs.py`, `attempts.py`, and `runtime_transaction.py`: reuse existing inventory, immutable history, participant, conflict, and recovery behavior unchanged.

### Validation And Bootstrap Admission

The revised authority loads without diagnostics at digest `eaab0f2e46780f38b5df541d248fc54cb8a0483da1464f60f4d507c0f3cad617`. Global re-admission remains delegated to DN-013/DN-014 and is not a local #2019 acceptance branch.

[[2026-07-24T13:15:32+02:00]]
## Shape Completion Notes
- User-approved DEC-024 implementation contract applied: required positive constructor expiry, aware supplied recovery time, ascending native job sweep, strict-after boundary, per-job atomic crash transaction, stable identity/conflict diagnostics, exact persisted replay after reassembly, and later-retry separation.
- Public models and export ownership are explicit; jobs, attempts, and RuntimeTransaction are reused unchanged.
- Seven bounded AC cover policy/time validation, boundary and mutation bytes, event/job payload, ordering/no-ops, identity/conflict isolation, exact reopen replay, and later retry.
- Authority loads without diagnostics at eaab0f2e46780f38b5df541d248fc54cb8a0483da1464f60f4d507c0f3cad617. Global admission remains DN-013/DN-014 debt.
- Dependency audit: unchanged depends_on [2017, 2018], both archived.
- Validation: uv run pytest -q tests/test_edit_task_contract.py passed 2; task diff check passed; one operative amendment and exactly seven AC confirmed.
- Builder route: implement only native_runtime.py, __init__.py, and test_native_runtime.py; preserve unrelated dirty changes and use public facade proof over real stores.
