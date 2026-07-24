---
id: 2007
title: 'P3-08: Expose indexed runtime health and history'
status: verify
priority: low
created: 2026-07-22T22:07:25.462842+02:00
updated: 2026-07-24T15:59:51.690271+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - health
  - history
  - indexes
  - scale
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-008
parent: 1979
depends_on:
  - 2006
ac:
  - 'AC-1: Given current, blocked, stale, cancelled, superseded, failed-attempt, and
    completed jobs, public projections preserve immutable job kind and expose dependency
    readiness, claim, request, block, attempt, finding, receipt, validity, and disposition
    separately while authority-derived fields come from the current graph and node
    plan.'
  - 'AC-2: Given cursor/limit queries over 500 nodes and at least 2,000 combined jobs,
    attempts, findings, and receipts, list and history operations return deterministic
    bounded pages and current-validity/dependency indexes update only the affected
    closure after supersession; repeated unchanged queries return identical identities
    and order.'
  - 'AC-3: Given dangling references, stale digests, broken predecessor or supersession
    chains, orphan records, unsafe entries, unresolved transaction manifests, or index
    disagreement, `work_health` returns stable findings and checked paths or cursors
    without mutation; healthy stores return no findings.'
proof_bundle: behavioral+challenge
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
- `packet_id`: `DN-003-PK-008`

## Outcome
Deterministic native runtime projections, validity indexes, paginated history, and bounded health scans make hundreds of graph, work, and evidence records inspectable without treating stale records as current.

## Scope
In scope: public job, evidence, request, and history projections; current-validity and dependency indexes with explicit invalidation; deterministic pagination; work health and recovery-manifest findings.

Out of scope: dispatch selection, MCP, HTTP, UI, and automated repair.

## Current Foundation And Ownership
Build over the native runtime facade, stores, receipt validity, requests, and invalidation closure delivered by preceding packets. This packet owns the integrated public health and projection proof for `REQ-023`, `KEEP-006`, `RISK-006`, and the remaining `PROOF-003` read boundary; lower store instrumentation is test evidence only.

## Authority
Resolve behavior from `REQ-009`, `REQ-023`, `KEEP-006`, `KEEP-007`, `IF-003`, `RISK-006`, `PROOF-003`, and design sections 7.3, 8.5, 9.7, and 13.

Proof guidance: exercise public projection and health operations over scale and corruption fixtures; instrument lower store reads only to prove index-bounded behavior.

[[2026-07-23T11:29:56+02:00]]
## Shape Notes
- Repair classification: connected dependency-closure audit; no operative contract change required.
- Dependency closure: #2007 consumes the assembled job, attempt/activity, finding, receipt, request, validity, and invalidation runtime through #2006's transitive closure. It introduces only read projections, indexes, pagination, and health diagnostics.
- Integrated boundary: AC-1 exposes orthogonal runtime state, AC-2 proves bounded indexed history, and AC-3 reports unresolved transaction manifests and cross-store corruption without mutation. This remains the assembled read/health portion of `PROOF-003`.
- Board audit: remains `build`, parent #1979, dependency #2006, and is correctly dependency-blocked.

[[2026-07-24T15:59:51+02:00]]
## Builder Notes
- Verdict: DONE. Change envelope stayed within one native runtime read owner, facade delegation/cache coherence, public exports, and focused durable proof. No MCP, HTTP, UI, dispatch, or unrelated runtime refactor was added.
- Files changed: `serve/kanban/src/owlbear_kanban/runtime_query.py`, `serve/kanban/src/owlbear_kanban/native_runtime.py`, `serve/kanban/src/owlbear_kanban/__init__.py`, `serve/kanban/tests/test_native_runtime.py`, and `serve/kanban/tests/test_runtime_query.py`.
- AC-1: `RuntimeJobProjection` preserves immutable job kind and separately projects dependency readiness, claim, persisted typed requests, block, latest attempt, finding, receipt, candidate-revision validity, and disposition. Normative title, outcome, acceptance, modules, interfaces, and proof are resolved through `project_job` from current authority.
- AC-2: lazy indexes back stable cursor pages for jobs, attempts, findings, receipts, requests, and combined history. The scale proof uses 500 authority nodes, 500 jobs, and 2,000 attempts; unchanged repeated queries preserve identities/order and lower-store instrumentation proves no rescan after initial index construction. `NativeRuntime.invalidate` refreshes only the explicit affected receipt/job closure returned by supersession and preserves the unrelated projection exactly.
- AC-3: `work_health` checks only one requested path page and returns stable findings plus checked paths/cursor without recovery or mutation. Proof covers healthy zero findings, dangling predecessor, orphan finding, unsafe entry, unresolved transaction manifest, primed-index disagreement, stable repeated pages, bounded two-path scans, and byte-identical stores.
- Durable-test justification: indexed scale behavior and non-mutating cross-store corruption diagnosis are shared control-plane, stale-authority, and data-integrity boundaries named by REQ-023, RISK-006, and PROOF-003; regressions would be difficult to detect manually.
- Evidence: final Ruff check and format check passed; diff whitespace check passed; owning aggregate passed 185 tests across native runtime, query, invalidation, requests, receipts, jobs, attempts, findings, and transaction recovery. Two existing multiprocessing fork deprecation warnings remain.
- Builder challenger: final decision `pass`; no problem, no further action, durable tests accepted, no auto-fixed files. Challenger independently ran 28 targeted tests plus Ruff and format checks.
- Memory: all 10 recalled entries were assessed; refined artifact-to-scope and live public-callable proof guidance directly shaped the final proof.
- Follow-up risks: none identified within shaped scope.
