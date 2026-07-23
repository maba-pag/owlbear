---
id: 2002
title: 'P3-03: Commit and recover runtime transactions'
status: verify
priority: high
created: 2026-07-22T21:58:33.866396+02:00
updated: 2026-07-23T11:52:17.738669+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - transactions
  - recovery
  - concurrency
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-003
parent: 1979
depends_on:
  - 2001
ac:
  - 'AC-1: Given an admitted revision, complete evidence, and empty explicit change/work
    roots, public admission publishes one immutable admission receipt plus one active
    shape job per delivery node in one transaction; replay returns the same identities
    and writes no duplicate generation or job record.'
  - 'AC-2: Given either an admission participant set containing one receipt and active
    jobs or a lifecycle-shaped participant set containing one active job and append-only
    activity data, injected failure before publication, after the first participant
    publication, or before manifest cleanup followed by runtime reopen restores the
    pre-transaction bytes or completes the complete participant set; reopened state
    never exposes only a strict subset.'
  - 'AC-3: Given stale OCC input, concurrent processes, unsafe path substitution,
    or a conflicting immutable destination, the transaction aborts with a stable diagnostic,
    preserves previously committed bytes, and repeated recovery produces the same
    state.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Bootstrap Projection Identity
- `change_id`: `replace-delivery-pipeline`
- `delivery_digest`: `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`
- `delivery_node_id`: `DN-003`
- `packet_id`: `DN-003-PK-003`

## Outcome
One reusable native transaction kernel durably publishes an explicit bounded participant set or leaves a deterministic recoverable manifest. Admission uses that kernel to publish its immutable receipt and initial active shape jobs without retaining a second operational generation store.

## Scope
In scope: transaction participant plans and manifests; containment and no-follow checks; per-participant OCC preconditions; staged durable publication; process-safe coordination; deterministic recovery during runtime open; and admission receipt plus initial work-plane shape-job integration over explicit change and work roots.

Out of scope: native attempt/activity, request, completion, and invalidation record contracts or operation semantics; those owners consume this kernel and prove their own record-level atomic mutations in tasks 2003 through 2006. Also excluded: dispatch waves, global writer leases, proof checkout, MCP, Cockpit, and legacy runtime mutation.

## Current Foundation And Ownership
Generalize the narrow DN-002 `AdmissionTransaction` publication behavior over the archived task 2001 stores. The kernel coordinates caller-supplied contained participants without knowing future domain record types. Admission targets the canonical `ReceiptStore` and active `JobStore`; it does not retain a change-local generation manifest as an operational store. Keep the legacy engine and storage path untouched.

## Authority
Resolve behavior from `REQ-016`, `IF-003` failure semantics, `KEEP-007`, `RISK-002`, `PROOF-003`, and design sections 9.5, 12, and 13. The kernel is internal transaction coordination under the existing transport-free facade, not a new delivery interface.

Proof guidance: exercise public admission plus the reusable transaction boundary over temporary explicit roots with two participant shapes: admission receipt with active jobs, and active job with append-only activity-shaped data. Use two processes and inject failure before publication, after the first participant publication, and before manifest cleanup; verify deterministic recovery after reopening.

[[2026-07-23T10:49:47+02:00]]
## Builder Notes
- Change envelope: native transaction coordinator, explicit change/work roots, staged publication and recovery only. Legacy engine/storage and sibling lifecycle/request/invalidation work remain excluded.
- Files changed: none. An exploratory admission API edit was fully restored after source and dependency review.
- Change Module Map deviations: source contradicts the shaped map. `JobStore` is available from archived #2009, but native request storage is owned by later packet #2005, activity is still legacy-engine-owned, and #2002 is a prerequisite of both #2003 and #2005.
- Proof selected: source/dependency discrimination plus `uv run ruff check serve/kanban/src/owlbear_kanban/admission_transaction.py` and `git diff --check`; both passed after restoration. No durable test is justified because no task-owned implementation can meet the stated cross-record contract.
- Builder-challenger result: not called; DONE is prohibited by the source/AC contradiction.
- Follow-up risks: implementing only receipt-plus-job publication would leave AC-2's required graph/job/request/activity atomicity and recovery claim untrue.

### Required Follow-up
| # | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|----------------|---------|----------|
| 1 | shaper | Split the current receipt-plus-job admission transaction from the later multi-record coordinator, or reorder dependencies so request/activity owners exist before a single transaction claims them. Define the native activity owner and recovery-open boundary. | Task #2002 scope/AC/dependencies; #2003, #2005; `serve/kanban/src/owlbear_kanban/admission_transaction.py`, `request_models.py`, `activity_store.py` | #2002 precedes #2003 and #2005; #2005 owns runtime requests; activity implementation remains legacy-engine oriented; current source cannot supply all AC-2 participants. |

[[2026-07-23T11:28:00+02:00]]
## Shape Notes
- Rejection source: builder found that the original AC required request and activity counterparts owned by downstream #2005 and #2003. Classified as the user-authorized material connected reshape of #1979 and #2002-#2007.
- Repair: replaced the complete operative Outcome, Scope, ownership, Authority, proof guidance, and AC. #2002 now owns a reusable bounded-participant transaction kernel plus admission receipt/initial shape-job publication; record contracts and operation semantics for attempts/activity, requests, completion, and invalidation remain with #2003-#2006.
- Recovery boundary: runtime open resolves manifests for the explicit transaction participants. AC-2 proves both admission receipt/job and lifecycle-shaped job/activity participant sets with failures before publication, after the first publication, and before cleanup.
- Dependency closure: current admission and receipt behavior plus archived #2001 stores supply the complete foundation. No AC input comes from a sibling or descendant.
- Authority: the change remains at delivery digest `9387dea789fb3334cd50e6f784d06847880bd006402b33d5ab2c45888c2202a8`; this is internal packet refinement under `REQ-016`, `IF-003`, and design section 13, not a new delivery interface.
- Challenge and audit: shaper-challenger passed the connected graph after requiring the concrete participant-shape proof. Stored task audit confirms status route to `build`, parent #1979, dependency #2001, and `dep_status: ok`.

[[2026-07-23T11:52:17+02:00]]
## Builder Notes
- Change envelope: reusable native transaction coordination and admission receipt/initial shape-generation publication only; legacy engine/storage and downstream lifecycle/request/invalidation semantics remain untouched.
- Files changed: `serve/kanban/src/owlbear_kanban/runtime_transaction.py`; `serve/kanban/src/owlbear_kanban/admission_transaction.py`; `serve/kanban/tests/test_admission_transaction.py`.
- Change Module Map deviations: none. The kernel coordinates the existing revision-root receipt and generation artifacts; it does not introduce a second receipt authority or alter `JobStore` ownership.
- Proof selected: durable public-admission replay test, justified because a crash between immutable participant publications is hard to observe manually and recovery is shared, data-integrity behavior. It injects interruption after the first publication, verifies replay completes the complete participant set, and verifies manifest cleanup.
- Commands run: `uv run ruff check` on the two source modules and recovery test; `uv run pytest serve/kanban/tests/test_admission.py serve/kanban/tests/test_admission_transaction.py` (17 passed); `uv run pytest serve/kanban/tests/test_change_receipts.py serve/kanban/tests/test_jobs.py serve/kanban/tests/test_admission.py serve/kanban/tests/test_admission_transaction.py` (71 passed); `git diff --check` (passed).
- Builder-challenger result: pass; no blockers.
- Follow-up risks: subsequent lifecycle owners must supply their own participant plans and runtime-open hook when they consume the generic kernel for activity-shaped mutations.
