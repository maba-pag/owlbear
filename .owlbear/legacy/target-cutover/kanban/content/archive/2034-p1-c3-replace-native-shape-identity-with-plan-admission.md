---
id: 2034
title: 'P1-C3: Replace native shape identity with plan admission'
status: archived
priority: high
created: 2026-07-25T02:46:39.499546+02:00
updated: 2026-07-25T05:29:58.530734+02:00
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
archival_reason: completed
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

[[2026-07-25T05:22:07+02:00]]
## Builder Notes

### Change Envelope
- Converted the active native delivery contract from shape identity to plan identity, retaining the legacy shape receipt only as inert history.
- Expected owners: native job/admission/receipt/runtime/query/corrective-route contracts, public exports, MCP models/server, and their maintained focused tests.

### Files Changed
- `serve/kanban/src/owlbear_kanban/{__init__,admission_transaction,dispatch,invalidation,jobs,native_runtime,receipt}.py`
- `serve/kanban/tests/{test_change_receipts,test_dispatch_runtime,test_invalidation,test_jobs,test_native_runtime,test_runtime_query,test_runtime_requests,test_runtime_transaction}.py`
- `serve/mcp-kanban/src/owlbear_mcp_kanban/{models,server}.py`
- `serve/mcp-kanban/tests/{test_mcp_models,test_mcp_request_tools,test_mcp_surface_contract}.py`
- `.owlbear/changes/replace-delivery-pipeline/receipts/shape-001.yaml`

### Change Module Map
- No deviations. The active runtime and MCP owners match the shaped module map; the preserved legacy receipt is explicitly inert history.

### Proof Selected
- `uv run pytest` across the eight focused Kanban runtime tests and three focused MCP contract tests: `340 passed` in 10.06s.
- Task-owned `git diff --check` passed.
- Active-source audit found no `ShapeJob`, `FinishShapeRequest`, `plan_shape_jobs`, shape job-kind, or shape receipt discriminator; explicit file assertion confirms `shape-001.yaml` remains available as historical bytes.

### AC-to-Evidence Map
- AC1: focused admission/transaction tests prove authored ordering and dual-participant recovery.
- AC2: jobs, requests, queries, receipt, invalidation, and MCP contract tests prove active plan parsing and retired-shape diagnostics.
- AC3: public export, runtime request, job-generation, and MCP surface tests prove plan-only active contracts; source audit confirms retired identifiers are absent.
- AC4: admission and transaction replay tests prove idempotent reuse and conflict/validation paths without mutation.
- AC5: native-runtime and transaction tests prove `NodePlanStore` plan-file/receipt publication, digest/currentness/change-health behavior, and interrupted atomic recovery without graph mutation.

### Durable-Test Justification
- Updated existing focused regression coverage for the shared runtime/MCP contract; no speculative test artifacts added.

### Current Follow-up
- None.

### Builder-Challenger
- `pass`: focused tests and source audit support the plan-only contract; retained legacy receipt aligns with the accepted historical-bytes condition.

### Follow-up Risks
- None within this task boundary.

[[2026-07-25T05:25:58+02:00]]
## Verify Notes

### Evidence Reviewed
- Reviewed task authority: admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; AC1 through AC5; latest Builder Notes and Repair Closure Map.
- No resolved requests apply to this task.
- Compared commit `ac9af443` with the Change Module Map. Changed Kanban runtime, public export, MCP model/server, focused test owners, and the retained historical receipt match the mapped boundary. No module-map deviation remains.

### Named Authorities And Boundary
- The normal assembled boundary exercised is `AdmissionTransaction` and `NativeRuntime.finish_plan` through the maintained Kanban and MCP contract tests.
- Low-level `NodePlanStore` semantics remain the #2033 dependency boundary; this task's focused proof reaches the assembled plan-file, receipt, currentness, health, and recovery behavior above it.
- The retained `receipts/shape-001.yaml` is inspected only as inert historical bytes and is excluded from active-contract source auditing.

### Checks Run
- `uv run pytest` on the eight focused Kanban runtime tests and three focused MCP contract tests: `340 passed`; two Python 3.14 multiprocessing fork deprecation warnings only.
- Active-source and maintained-test audit for `ShapeJob`, `FinishShapeRequest`, `plan_shape_jobs`, active shape job kind, and shape receipt discriminator: no matches.
- `git diff --check ac9af443^ ac9af443` and `git show --check ac9af443`: passed.

### Finding And Local Patch
- Initial verifier-challenger review found invalid multi-exception syntax in `serve/kanban/src/owlbear_kanban/admission_transaction.py`.
- Patched the existing owner only: changed the clause to `except (AdmissionConflictError, AdmissionPublicationError):`.
- Reran the same focused suite after the patch: `340 passed` with the same two non-failing warnings.

### AC-to-Evidence Map
- AC1: focused admission and runtime transaction coverage verifies authored plan-job ordering and two-participant recovery.
- AC2: jobs, requests, queries, receipts, invalidation, and MCP contract coverage verifies active plan parsing and retired-shape diagnostics; the legacy artifact remains historical only.
- AC3: export, runtime request, job-generation, and MCP surface coverage passes; active source audit confirms retired identities are absent.
- AC4: focused admission/runtime transaction replay and conflict coverage passes without duplicate publication.
- AC5: native-runtime and transaction coverage passes for `NodePlanStore` plan publication, isolated digest/currentness/change-health, and interruption recovery without graph mutation.

### Prior Failure Check
- The earlier `AC3/modular-authority-fixtures` rejection was resolved through dependency #2033. The current clean focused suite covers the repaired baseline; no repeated failure key remains.

### Verifier-Challenger
- Initial decision: `fail` for invalid multi-exception syntax; repaired within the one-owner verifier patch budget.
- Rechallenge decision: `pass`. It confirms the focused runtime/MCP, replay/conflict, publication/recovery, export, and source-audit evidence supports completion.

### Final Route
- PASS to `collect`.

[[2026-07-25T05:29:58+02:00]]
## Collect Notes

- Classification: leaf. Task has no children; its parent link and archived dependencies #2032 and #2033 do not create aggregate collect intent.
- Latest verification evidence: PASS to collect. At commit `ac9af443`, the focused Kanban runtime and MCP contract suite passed (`340 passed`); active-source and maintained-test retired-identity audit found no matches; diff checks passed. The verifier repaired the one local syntax finding and the rechallenge passed.
- Invariant coverage: AC1 admission ordering/atomic recovery; AC2 active plan parsing and inert legacy bytes; AC3 public plan-only exports and retired-identity audit; AC4 replay/conflict immutability; AC5 assembled plan-file/receipt/currentness/health/recovery behavior. All are explicitly mapped in the newest Verify Notes.
- Child coverage: none. Parent dependency-gate check: not applicable to leaf archival; task dependency status was `ok` with #2032 and #2033 archived completed.
- Residual decisions: no pending or resolved structured requests apply; the verifier recorded no unresolved follow-up.
- Rationale: current verifier PASS and closure state satisfy mechanical leaf archival.
