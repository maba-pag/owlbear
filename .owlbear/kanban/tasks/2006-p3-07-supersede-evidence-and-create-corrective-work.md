---
id: 2006
title: 'P3-07: Supersede evidence and create corrective work'
status: verify
priority: medium
created: 2026-07-22T21:59:17.003316+02:00
updated: 2026-07-24T15:14:07.001806+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - invalidation
  - supersession
  - corrective-work
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-007
parent: 1979
depends_on:
  - 2004
  - 2005
ac:
  - 'AC-1: Given a finding against packet implementation/local proof, packet plan/dependency/proof,
    admitted design authority, node integration, or whole-change integration, the
    public planner returns respectively a build repair, node shape revision, design
    re-entry with no local job, build-owned node repair through shape correction,
    or affected-node shape/build correction route; the late-work class is `implementation-defect`,
    `unforeseeable-discovery`, `planning-omission`, or `scope-change`.'
  - 'AC-2: Given one or more invalidated receipts, the public closure includes only
    receipt and job descendants whose computed validity depends on them; applying
    it atomically appends one supersession receipt, cancels or supersedes stale open
    jobs, and creates the planned corrective jobs without rewriting prior receipts,
    attempts, findings, or jobs.'
  - 'AC-3: Replaying the same finding set and invalidation identity returns the same
    supersession and corrective identities; a conflicting set or injected write failure
    returns a stable conflict or abort and leaves the prior current chain observable
    without partial corrective work.'
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
- `packet_id`: `DN-003-PK-007`

## Outcome
Typed findings invalidate the minimum affected receipt closure, append immutable supersession evidence, dispose stale open jobs, and create exact corrective jobs while preserving prior chains.

## Scope
In scope: finding targets and late-work classes; receipt/job dependency indexes; affected-descendant closure; supersession transaction; stale-job disposition; corrective-route matrix; deterministic identities, replay, and conflict behavior.

Out of scope: global designer workflow, agent execution, dispatch waves, proof checkout, MCP, Cockpit, and mutation of prior evidence.

## Current Foundation And Ownership
Build over purpose-specific receipt validity and native request disposition from packets `DN-003-PK-005` and `DN-003-PK-006`. The runtime returns typed design re-entry when authority expansion is required; it does not perform that design work.

## Authority
Resolve behavior from `REQ-008`, `NEG-010`, `IF-003`, `RISK-003`, `PROOF-003`, and design section 10. Preserve `implementation-defect`, `unforeseeable-discovery`, `planning-omission`, and `scope-change` as distinct late-work classes.

Proof guidance: use a table-driven corrective-route matrix plus generic receipt/job DAG closure and transaction failure injection through the public invalidation operation.

[[2026-07-23T11:29:39+02:00]]
## Shape Notes
- Repair classification: connected dependency-closure audit; no operative contract change required.
- Dependency closure: #2006 consumes purpose-specific receipt validity/completion from #2004 and native request disposition from #2005. It introduces its own supersession and corrective identities, computes affected closure, and uses the transitive #2002 transaction kernel for atomic publication. No sibling or descendant producer is required.
- Atomicity boundary: AC-2 and AC-3 already couple supersession evidence, stale-job disposition, and corrective jobs while preserving prior attempts/findings/receipts/jobs and rejecting partial publication.
- Board audit: remains `build`, parent #1979, dependencies #2004 and #2005, and is correctly dependency-blocked.

[[2026-07-24T15:14:07+02:00]]
## Builder Notes
- Change envelope: implemented the design-owned invalidation planner/runtime, package exports, handled transaction rollback, and durable proof in the owning kanban runtime modules. Updated four stale transaction fixtures to current typed job dispositions after challenger review; no compatibility path was added.
- Files changed: `serve/kanban/src/owlbear_kanban/invalidation.py`, `serve/kanban/src/owlbear_kanban/runtime_transaction.py`, `serve/kanban/src/owlbear_kanban/__init__.py`, `serve/kanban/tests/test_invalidation.py`, and `serve/kanban/tests/test_runtime_transaction.py`.
- AC-1: `plan_corrective_route` preserves all four late-work classes and returns typed build repair, node shape revision, design re-entry without a local job, node integration repair through shape correction, or affected-node correction. Immediate shape jobs use the established `finish_shape` boundary to generate later build jobs.
- AC-2: `InvalidationRuntime.apply` computes reverse receipt-predecessor and job-predecessor closures, publishes one immutable supersession receipt, OCC-supersedes only affected active jobs, creates exact caller-identified corrective jobs, and leaves findings, receipts, archived jobs, and unrelated active jobs byte-identical.
- AC-3: supersession evidence binds the durable invalidation/finding/job identity. Exact replay returns the stored outcome; conflicting identity returns `ERR_INVALIDATION_CONFLICT`. Handled injected failure returns `ERR_INVALIDATION_ABORTED` and restores exact pre-publication state at all three transaction stages. Process interruption still retains manifest-driven recovery-to-completion.
- Durable-test justification: supersession and mixed-participant rollback are shared state-machine and data-loss boundaries named by PROOF-003. Public filesystem tests protect route semantics, minimum DAG closure, immutable history, replay/conflict, all failure stages, and immutable/replacement/move rollback.
- Evidence: focused invalidation module passed 36 tests; final owning aggregate passed 159 tests across transaction, receipts, jobs, findings, native runtime, and invalidation. Ruff check and format check passed for all owned files; diff whitespace check and VS Code diagnostics were clean.
- Builder challenger: final decision `pass`; no concrete defects, no scope drift, durable proof rent accepted, and no auto-fixes.
- Memory: all 10 recalled entries were assessed; refined artifact-to-scope, replay-after-failure, and atomic rollback guidance directly shaped the proof. One scoped pending lesson recorded for handled abort versus crash recovery.
- Follow-up risks: none identified within the shaped scope.
