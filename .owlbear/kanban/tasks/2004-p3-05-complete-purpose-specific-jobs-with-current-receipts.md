---
id: 2004
title: 'P3-05: Complete purpose-specific jobs with current receipts'
status: verify
priority: medium
created: 2026-07-22T21:58:55.620202+02:00
updated: 2026-07-24T14:12:29.270333+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - transitions
  - receipts
  - validity
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-005
parent: 1979
depends_on:
  - 2003
ac:
  - 'AC-1: Given a current shape attempt and a caller-supplied packet DAG contained
    by its delivery node with canonical packet impact closures, `finish_shape` atomically
    writes that node-plan namespace, its digest and shape receipt, packet build jobs,
    one dependency-gated accept job, one `succeeded` event for the owning attempt,
    and the archived shape-job disposition; out-of-bound reference, missing or malformed
    closure, or transaction failure publishes none of them.'
  - 'AC-2: Given a current build, accept, or audit attempt with kind-specific evidence
    and the canonical typed impact closure for that receipt kind, its finish operation
    requires current delivery and node-plan digests, predecessor result `CURRENT`,
    and required target, code, and proof fields, then atomically creates one immutable
    receipt, appends one `succeeded` event, and archives the same-kind job; replay
    writes no second receipt or event.'
  - 'AC-3: Given a stale delivery or node-plan digest, predecessor result other than
    `CURRENT`, explicit supersession `invalidated_receipt_ids` reference, or code-currency
    result other than `CURRENT`, receipt evaluation returns that stable reason and
    leaves dependent jobs unreleased; code-currency result `CURRENT` permits normal
    finish.'
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
- `packet_id`: `DN-003-PK-005`

## Outcome
Shape, build, accept, and audit completion validates current authority and predecessor closure, atomically records kind-specific evidence plus the owning attempt's `succeeded` activity event, and archives the immutable-purpose job without backward movement.

## Scope
In scope: node-plan digest computation; assembled receipt-validity consumption; public finish-shape, finish-build, finish-accept, and finish-audit transaction policies; successful attempt finalization; predecessor release; authority, node-plan, supersession, code-revision, and touched-boundary staleness.

Finish-shape atomically records one caller-supplied packet DAG contained by the target node, its digest and shape receipt, build jobs, one dependency-gated accept job, the owning attempt's `succeeded` event, and the archived shape-job disposition.

Out of scope: node-plan semantic review and agent contracts, corrective routing, dispatch and writer leases, proof-checkout creation, MCP, and UI.

## Current Foundation And Ownership
Use the contracts and stores from archived #2000/#2001, the transaction kernel from #2002, and the attempt/activity and receipt-currentness boundaries exported by #2003. #2003 owns and exports the reusable receipt-currentness evaluator produced by tasks #2014-#2016. #2004 owns assembled `finish_shape`/`finish_build`/`finish_accept`/`finish_audit` policy, invokes that evaluator, records `succeeded`, archives the job, and proves the evaluator through its public finish/validity boundary. DN-006 through DN-008 and DN-014 later provide the agents and semantic evidence that call these generic engine operations.

## Authority
Resolve behavior from `REQ-009`, `REQ-016`, `NEG-002`, `NEG-010`, `IF-003`, `RISK-003`, `PROOF-003`, and design sections 4.2, 4.3, 6, 7, and 13.

Proof guidance: exercise the public finish and receipt-validity boundaries with temporary Git revisions below the engine. For shape, build, accept, and audit, verify one transaction invokes the exported evaluator and publishes the kind-specific receipt, archived job disposition, and one `succeeded` activity event. Include stale authority, node-plan, predecessor, supersession, touched-boundary, replay, and transaction-failure cases.

[[2026-07-23T11:29:01+02:00]]
## Shape Notes
- Repair classification: local contract alignment inside the user-authorized connected reshape. Task #2003 already assigns successful completion's `succeeded` event to #2004, but #2004's operative AC omitted it.
- Repair: replaced the complete operative body and AC so `finish_shape`, `finish_build`, `finish_accept`, and `finish_audit` atomically publish the kind-specific receipt, archived job disposition, and one `succeeded` event for the owning attempt. Replay and transaction failure cannot leave a duplicate or partial success record.
- Dependency closure: #2004 consumes the transaction kernel through #2002 and attempt/activity contract through #2003. Node-plan, receipt-validity, and successful completion behavior are owned here; no request or invalidation producer is required.
- Board audit: remains `build`, parent #1979, depends on #2003, and is correctly dependency-blocked.

[[2026-07-23T14:54:49+02:00]]
## Ownership Clarification
- The earlier Shape Notes sentence assigning receipt-validity behavior to #2004 is superseded by the current operative contract. #2003 owns and exports the reusable receipt-currentness evaluator produced by #2014-#2016. #2004 consumes and proves that evaluator through its public finish/validity boundary while alone owning assembled `finish_shape`/`finish_build`/`finish_accept`/`finish_audit` policy, `succeeded` publication, receipt creation, and job archival.
- Outcome, AC-1 through AC-3, status `build`, parent #1979, and dependency #2003 remain unchanged.

## Operative Receipt Contract Amendment
This section supersedes earlier receipt-currentness ownership and `touched-boundary` wording.

Task #2003 exports the reusable evaluator produced by #2014, #2015, #2020, and #2016. Task #2004 remains the sole owner of assembled `finish_shape`, `finish_build`, `finish_accept`, and `finish_audit` policy, successful receipt issuance, one `succeeded` event, and job archival. Finish operations consume canonical typed impact closures required by the admitted packet contract and validated by #2015; they do not infer closure from changed paths or diffs.

Proof uses the public finish boundary and the exported result codes. Receipt ID order, `issued_at`, and prose boundary descriptions are not currentness authority.

[[2026-07-23T18:16:46+02:00]]
## Shape Notes
- Receipt consumer contract now names #2014, #2015, #2020, and #2016 and consumes canonical typed impact closures.
- AC-1 through AC-3 use stable currentness results and explicit `invalidated_receipt_ids`; receipt ID order, `issued_at`, changed-path inference, and prose `touched-boundary` wording are not authority.
- Task remains `build`, dependency-blocked behind #2003. Final concrete challenge passed.

[[2026-07-24T14:12:29+02:00]]
## Builder Notes
- Change envelope: completed purpose-specific native runtime finish policy in `native_runtime.py`, using transaction participants added to `runtime_transaction.py`, `jobs.py`, and `receipt.py`; exported the public request/result and node-plan digest contracts through `__init__.py`.
- AC-1: `finish_shape` validates a contained acyclic packet DAG and canonical typed packet impact closures, writes only its node-plan namespace, derives the node-plan digest, creates ordered build jobs plus one dependency-gated accept job, publishes one shape receipt and one `succeeded` event, and archives the shape job in one recoverable cross-root transaction. Invalid or out-of-bound plans publish nothing.
- AC-2: `finish_build`, `finish_accept`, and `finish_audit` share current authority, ownership, predecessor, purpose, evidence, code, and typed-closure validation before one immutable receipt, one `succeeded` event, and terminal archive publication. Exact archived replay returns the persisted outcome without another receipt or event.
- AC-3: finish operations consume exported complete receipt currentness for predecessors and return its stable lower code for stale digest, node plan, supersession, predecessor, or code currency; dependent jobs remain active and unreleased on refusal. Build consumes its canonical packet closure, accept derives the canonical packet union, and audit uses the complete repository plus active authority targets.
- Crash and concurrency behavior: added recoverable transformed move participants so job archive bytes and receipt/event/graph/job publications share one manifest; runtime construction recovers pending cross-root manifests before reading state.
- Durable proof admitted because completion is a shared crash and data-loss boundary. Added public runtime cases for atomic shape publication and replay, invalid closure and out-of-bound plan zero-publication, and stale predecessor refusal.
- Focused proof: `uv run pytest -n 0 serve/kanban/tests/test_native_runtime.py serve/kanban/tests/test_change_receipts.py serve/kanban/tests/test_jobs.py -q` returned 100 passed. Focused finish subset returned 4 passed. Ruff check and format check passed on all six task-owned source and proof files.
- Existing `test_runtime_transaction.py` result: 12 passed and 4 stale failures whose fixtures fabricate removed free-form `JobDisposition` values (`updated`, `transaction`, and `winner-*`); challenger confirmed these do not invalidate this task's public finish proof.
- Builder challenger: pass; no concrete DONE defect or scope drift.
- Files changed: `serve/kanban/src/owlbear_kanban/runtime_transaction.py`, `jobs.py`, `receipt.py`, `native_runtime.py`, `__init__.py`, and `serve/kanban/tests/test_native_runtime.py`.
