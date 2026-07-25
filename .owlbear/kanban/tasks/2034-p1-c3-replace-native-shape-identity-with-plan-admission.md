---
id: 2034
title: 'P1-C3: Replace native shape identity with plan admission'
status: build
priority: high
created: 2026-07-25T02:46:39.499546+02:00
updated: 2026-07-25T04:42:48.845621+02:00
tags:
  - change:replace-delivery-pipeline
  - node:DN-002
  - node:DN-003
  - corrective
  - scope:core
  - admission
  - runtime
  - type:build
  - rigor:thorough
parent: 1968
depends_on:
  - 2032
  - 2033
ac:
  - 'AC1: Given one admitted 14-node revision, `AdmissionTransaction` publishes one
    admission receipt plus 14 plan jobs in authored node order; interrupted publication
    recovers both participants or exposes neither.'
  - 'AC2: Given active native job, receipt, request, corrective-route, and query parsing,
    `plan` is accepted where node planning applies and `shape` returns the existing
    kind or schema diagnostic; historical snapshot bytes remain inspectable without
    becoming current records.'
  - 'AC3: Public Python exports and runtime requests expose `PlanJob`, `FinishPlanRequest`,
    and plan-job generation; maintained active source and fixtures contain no `ShapeJob`,
    `FinishShapeRequest`, `plan_shape_jobs`, shape job kind, or shape receipt discriminator.'
  - 'AC4: Given replay of the same admission identity, the stored plan-job generation
    is returned without duplication; changed digest, evidence, or job identities return
    the stable admission conflict or validation result without mutation.'
  - 'AC5: Given `FinishPlanRequest` with a node plan, `NativeRuntime` commits `plans/<node-id>.yaml`
    with its plan receipt and transaction peers through `NodePlanStore`; `compute_node_plan_digest`,
    receipt currentness, and change health use modular authority plus isolated plan
    bytes, and an injected transaction interruption exposes prior bytes or the complete
    new YAML without `graph.yaml` mutation.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Make active native job, receipt, request, corrective-route, query, and admission contracts plan-only while preserving legacy bytes as inert history.

## Scope
In scope: `PlanJob`, job and receipt kinds, `FinishPlanRequest`, admission generation, corrective routes, request/query projections, exports, `NativeRuntime` plan-file publication through the #2033 `NodePlanStore` participant, receipt digest/currentness, modular change-health inventory, maintained fixtures, and focused MCP-facing contract tests.

Out of scope: low-level `NodePlanStore` storage semantics owned by #2033, acceptance-triggered reconciliation, engine-frontier dispatch, and final IF-015 MCP completion routing owned by #2037. MCP-facing models and tests required by the active plan-only contract remain in scope.

## Authority
Admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; DEC-033; MIG-004; DN-002; DN-003; IF-002; IF-003; PROOF-002; PROOF-003.

Proof guidance: start from #2033's archived modular fixture baseline, then run focused admission atomicity/replay, active-schema and legacy-history checks, and assembled `FinishPlanRequest` plan-file/receipt transaction recovery.

[[2026-07-25T04:17:25+02:00]]
## Builder Notes

### Change Envelope
- Intended active-contract scope: native plan job/admission/receipt/request/query/corrective-route contracts, exports, MCP finish endpoint, and maintained runtime fixtures.
- Controlling authority: admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`, confirmed by live `load_change`.
- Implemented local plan-only conversion in the declared runtime modules and focused fixtures; preserved the unowned legacy `receipts/shape-001.yaml` artifact.

### Change Module Map
- Followed active owners in `jobs.py`, `admission_transaction.py`, `native_runtime.py`, `dispatch.py`, `receipt.py`, `invalidation.py`, public exports, MCP models/server, and direct tests.
- Deviation discovered during final cross-check: `serve/kanban/tests/test_change_revision.py` remains an active monolithic `graph.yaml` fixture layer. It is the modular-authority migration boundary actively owned by concurrent task #2033, not a safe #2034 local repair.

### Proof Selected And Results
- Focused plan admission/runtime/query/dispatch/corrective/MCP scope: `174 passed`, with two Python 3.14 fork deprecation warnings.
- Ruff check on touched plan-runtime source and tests: passed.
- Active-source/fixture absence scan for retired plan-shape symbols, discriminators, and embedded-plan references: passed for the focused #2034 slice.
- Exact initial builder-challenger Kanban scope after receipt fixture correction: `170 passed`, two fork deprecation warnings.
- Builder-challenger final broad check reported 17 failures; direct `test_change_revision.py` reproduction reported 9 failures, all due to its monolithic fixture helper creating `graph.yaml` and no `delivery/` directory.

### AC-to-Evidence Map
- AC1: focused admission transaction and native runtime publication/replay tests passed.
- AC2: focused active schema scan and runtime/query/receipt tests passed; legacy history artifact was not changed.
- AC3: focused exports/MCP/runtime plan-only tests and absence scan passed.
- AC4: focused admission/native runtime replay and conflict tests passed.

### Builder Challenger
- First challenger `fail`: stale receipt-health fixture assumptions. Corrected `test_change_receipts.py` to modular authority and receipt health inventory; exact challenger scope then passed.
- Second challenger `fail`: broad suite exposes remaining monolithic `test_change_revision.py` fixture migration. This is a planning/dependency ownership issue, not safe to repair under #2034.

### Required Follow-up
| # | Failure Key | Target Agent | Action Required | File(s) | Evidence |
|---|-------------|--------------|-----------------|---------|----------|
| 1 | AC3/modular-authority-fixtures | shape | Reassign or explicitly add the remaining `test_change_revision.py` monolithic fixture migration to the modular-authority owner (#2033), then provide a clean broad Kanban/MCP fixture baseline before redispatching #2034. | `serve/kanban/tests/test_change_revision.py` | Broad challenger run: 17 failures; direct focused run: 9 failures, each `ERR_CHANGE_FILE_MISSING` for `delivery` caused by monolithic fixtures. |

### Follow-up Risk
- No scoped owned commit was made because broad validation is not clean and completing the missing fixture migration would cross into concurrent task #2033 ownership. Current unrelated dirty modular authority and legacy shape receipt artifacts were preserved.

[[2026-07-25T04:42:48+02:00]]
## Shape Notes

### Repair Classification
Connected local task repair with #2033. Builder rejection key `AC3/modular-authority-fixtures` showed that broad plan-runtime proof depended on a monolithic fixture owned by the modular loader task. No product behavior or admitted architecture changed.

### Repair Closure Map
- `AC3/modular-authority-fixtures`: #2033 now owns the `test_change_revision.py` helper and logical parity rewrite. This task is dependency-gated on #2033's archived modular fixture baseline.
- `runtime/storage-overlap`: current `native_runtime.py` and `receipt.py` place lifecycle identity, `FinishPlanRequest` publication, isolated-plan digest/currentness, and health inventory at one assembled runtime boundary. AC5 owns that integration through the lower `NodePlanStore` primitive from #2033.
- Negative control: #2033 can pass without lifecycle symbol edits; this task's broad proof must fail if runtime publication writes `graph.yaml` or bypasses isolated plan bytes.

### Board Repair
- Added dependency on #2033.
- Rewrote Scope so assembled `FinishPlanRequest` plan-file publication and receipt/health integration are in scope while low-level `NodePlanStore` semantics remain in #2033.
- Retained AC1 through AC4 and added AC5 for the assembled runtime transaction, isolated digest/currentness, modular health inventory, and interruption behavior.
- Kept final IF-015 engine completion routing in #2037 and acceptance-triggered reconciliation in #2035.

### Challenge And Route
Shaper challenger first failed on stale scope, waiver, fixture, and low-level storage ownership. Corrected rechallenge passed. Task advances to `build` but remains dependency-blocked until #2033 archives.
