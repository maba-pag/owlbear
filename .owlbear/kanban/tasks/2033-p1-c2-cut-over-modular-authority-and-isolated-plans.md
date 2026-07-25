---
id: 2033
title: 'P1-C2: Cut over modular authority and isolated plan storage'
status: shape
priority: high
created: 2026-07-25T02:46:34.205290+02:00
updated: 2026-07-25T04:51:35.430457+02:00
tags:
  - change:replace-delivery-pipeline
  - node:DN-001
  - corrective
  - scope:core
  - migration
  - storage
  - type:build
  - rigor:thorough
parent: 1968
depends_on:
  - 2032
ac:
  - 'AC1: Given the admitted bootstrap package and its populated node plan, migration
    writes `delivery/obligations.yaml`, `delivery/contracts.yaml`, `delivery/nodes.yaml`,
    and `plans/DN-001.yaml`; public `load_change` returns digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`.'
  - 'AC2: Given the migrated package, absent `graph.yaml` loads successfully; adding
    `graph.yaml` returns `ERR_CHANGE_SCHEMA_INVALID` targeting `graph.yaml`, so the
    public loader accepts neither fallback nor dual authority.'
  - 'AC3: Given a modular `ChangeRevision`, `read_node_plan("DN-001")` returns the
    mapping from `plans/DN-001.yaml` and a missing declared-node plan returns `None`;
    the joined `DeliveryGraph` exposes no `execution` or `node_plans` field.'
  - 'AC4: Given `NodePlanStore.prepare` for `DN-001`, `RuntimeTransaction` interruption
    restores prior bytes or commits the complete YAML, replayed matching bytes is
    idempotent, and a stale observed token or differing existing bytes returns the
    declared conflict without changing the stored plan.'
  - 'AC5: Given maintained `test_change_revision.py` fixtures, package helpers write
    modular delivery documents and isolated plans; the logical parity scenario compares
    `compute_delivery_digest` over equivalent joined authority with public `load_change`
    output rather than loading `graph.yaml`, the focused module passes, and active
    scenarios create no `graph.yaml`, `ExecutionPlan`, or embedded `node_plans` authority.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Migrate the admitted bootstrap carrier and public loader to modular authority, preserve canonical semantic identity, and retain low-level isolated plan storage/OCC as the package primitive.

## Scope
In scope: physical package migration; public `load_change`; `ChangeRevision.read_node_plan`; `NodePlanStore` read/prepare including replay, OCC conflict, and `RuntimeTransaction` interruption recovery; `graph.yaml` rejection; and maintained loader/store fixtures including `serve/kanban/tests/test_change_revision.py`.

Out of scope: `NativeRuntime` `FinishPlanRequest` integration, receipt currentness/health integration, `shape` to `plan` identity, admission job generation, reconciliation, dispatch, and MCP.

## Authority
Admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; DEC-030; MIG-004; DN-001; IF-001; PROOF-001.

Package cutover and low-level `NodePlanStore` remain atomic because `ChangeRevision` source identity and contained plan paths define one package boundary. Assembled `NativeRuntime` publication and receipt integration are sequenced in #2034 after this primitive archives, avoiding dual authority without mixing public lifecycle identity into this task.

Proof guidance: load the migrated package through the public loader, compare its joined logical digest with the admitted digest, reject a reintroduced `graph.yaml`, and exercise isolated plan replay, conflict, and interruption recovery.

[[2026-07-25T04:05:40+02:00]]
## Builder Notes

### Change Envelope
- Intended owner map: `serve/kanban/src/owlbear_kanban/change.py` public loader and `ChangeRevision` plan access; `receipt.py` currentness and health; `native_runtime.py` isolated publication participant; admitted package `.owlbear/changes/replace-delivery-pipeline/`; focused change-revision and native-runtime tests.
- Contract availability was confirmed from task AC, admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`, the digest-named admission receipt, MIG-004, and predecessor #2032. No resolved structured requests existed.

### Source Findings
- `load_change` still reads `graph.yaml`; `load_modular_change` and `NodePlanStore` from #2032 provide the required modular authority and isolated-plan primitives.
- `native_runtime.py` reads and mutates `revision.graph.execution.node_plans` and `graph.yaml`; `receipt.py` derives plan digests and health authority paths from the same monolithic carrier.
- The public loader change, receipt digest/health change, and runtime participant migration were the intended minimal implementation. The shaped module map has no justified deviation.

### Partial Mutation And Containment
- The isolated package migration command completed before its terminal was interrupted: `.owlbear/changes/replace-delivery-pipeline/delivery/obligations.yaml`, `contracts.yaml`, `nodes.yaml`, and `plans/DN-001.yaml` now exist; `graph.yaml` is absent. The temporary migration helper was removed.
- Subsequent source inspection showed the attempted Python owner edits were not durably reflected, leaving the package and public loader inconsistent. Do not advance this task or commit this partial state.

### Proof Attempt
- Editor diagnostics were clean immediately after the attempted owner edits, but are not sufficient closure evidence after the source inconsistency.
- `uv run pytest serve/kanban/tests/test_change_revision.py -q` and `uv run pytest serve/kanban/tests/test_change_revision.py serve/kanban/tests/test_native_runtime.py -q` both exited `130` with no test output.
- Read-only terminal inspections and the scoped migration command also exited `130` without normal completion output. A read-only filesystem check confirmed the package migration effect, so the command was not retried.

### Builder-Challenger And Commit
- Not invoked: mandatory focused proof could not execute and the implementation is not coherent.
- No scoped commit was attempted. No task-owned commit SHA exists.

### Recovery
- Restore a coherent baseline or complete the modular owner cutover against the now-migrated package, then run the focused loader/runtime tests, builder challenger, and scoped `commit-owned` command before moving to verify.
- Follow-up risk: no asserted AC evidence; AC1 through AC5 remain unproved.

[[2026-07-25T04:27:22+02:00]]
## Builder Notes

### Change Envelope
- Expected owners: `serve/kanban/src/owlbear_kanban/change.py` public loader and `ChangeRevision` plan access, `receipt.py` currentness and health, `native_runtime.py` isolated publication participant, admitted `.owlbear/changes/replace-delivery-pipeline/`, and focused revision/runtime proof.
- Cheapest discriminating check: inspect the task-owned uncommitted diff and current owner declarations for scope compliance before completing the resumed partial implementation.

### Contract Classification
- Rejected to shape. The task's Scope explicitly excludes the `shape` to `plan` identity change, but the current uncommitted task-envelope diff renames `FinishShapeRequest` to `FinishPlanRequest`, `finish_shape` to `finish_plan`, and related internal branches in `native_runtime.py`.
- This is an externally visible authority/API choice not determined by AC1-AC5. Keeping it would violate the stated scope; reverting it would discard or alter pre-existing candidate work without authority. Shape must decide whether the rename is required by this migration, belongs to another task, or must be removed before this task is rebuilt.

### Files Inspected
- `serve/kanban/src/owlbear_kanban/change.py`
- `serve/kanban/src/owlbear_kanban/receipt.py`
- `serve/kanban/src/owlbear_kanban/native_runtime.py`
- `serve/kanban/tests/test_change_revision.py`
- `serve/kanban/tests/test_native_runtime.py`
- `.owlbear/changes/replace-delivery-pipeline/`

### Change Module Map Deviations
- Current partial diff introduces the forbidden `shape` to `plan` public identity migration in `native_runtime.py`; no implementation changes were made in this invocation.

### Proof Selected And Commands Run
- Read-only owner and diff inspection: scoped `git diff` plus searches for `load_change`, `ChangeRevision`, `graph.yaml`, `node_plans`, `ExecutionPlan`, `NodePlanStore`, and finish request identities.
- No focused test was run because the early routing gate failed on a named scope contradiction. Existing Builder Notes also record terminal exit 130 for the prior focused test attempts.

### AC And Follow-up Status
- AC1 through AC5 remain unproved. The prior required follow-up is unresolved pending shape's decision on the public API rename and coherent implementation boundary.

### Builder-Challenger
- Not invoked: mandatory only before a DONE verdict; this invocation rejects to shape.

### Follow-up Risk
- The admitted package is already modular while the uncommitted source diff is not an approved coherent cutover. Do not advance or commit this task until shaping assigns the `shape`/`plan` rename and reissues a scope-consistent module map.

[[2026-07-25T04:42:48+02:00]]
## Shape Notes

### Repair Classification
Connected local task repair with #2034. Builder rejection key `scope/public-api-rename` showed that the prior task boundary mixed modular storage with the separately admitted plan-only runtime identity. No product behavior or admitted architecture changed.

### Repair Closure Map
- `scope/public-api-rename`: production boundary is the public modular loader and low-level plan store. Current `change.py`, `node_plan.py`, `native_runtime.py`, the admitted package, and `test_change_revision.py` were checked. The filtered diff proves modular loading and plan-store access do not require lifecycle renames; a negative source scan keeps `FinishPlanRequest` changes out of this task.
- `AC3/modular-authority-fixtures`: focused `test_change_revision.py` reproduced 9 missing-delivery failures because its helper still wrote `graph.yaml`. AC5 now assigns that fixture migration and rewrites logical parity without a monolithic public-loader path.
- `low-level-storage`: AC4 now owns `NodePlanStore.prepare` replay, OCC conflict, and interruption recovery at the `RuntimeTransaction` boundary.

### Board Repair
- Narrowed ownership to DN-001 and removed the `node:DN-003` tag.
- Replaced stale scope and complexity-waiver prose with the modular package plus low-level storage boundary.
- Rewrote AC1 through AC5 to cover package migration, strict `graph.yaml` rejection, isolated plan reads, low-level transactional writes, and maintained modular fixtures.
- Sequenced assembled runtime and receipt integration in #2034.

### Challenge And Route
Shaper challenger first failed on four concrete contradictions; all four were corrected. Rechallenge passed with no findings. Task advances to `build`; #2034 depends on this task's archived modular baseline.

[[2026-07-25T04:47:33+02:00]]
## Builder Notes

### Change Envelope
- Migrated the admitted DN-001 package and public loader boundary to modular delivery authority with isolated plans; excluded runtime lifecycle identity and receipt integration per the repaired Shape Notes.
- Changed owners: `change.py`, the admitted package delivery/plan records, and `test_change_revision.py` fixtures and public-boundary proof.

### Change Module Map
- No deviation. `native_runtime.py` and `receipt.py` were not changed; the earlier `scope/public-api-rename` failure key is resolved by keeping those later-stage owners out of this task.

### Implementation
- Public modular loading now rejects any reintroduced `graph.yaml` as `ERR_CHANGE_SCHEMA_INVALID` targeting that legacy authority.
- Maintained package helpers create `delivery/obligations.yaml`, `delivery/contracts.yaml`, `delivery/nodes.yaml`, and isolated plans. Fixtures assert no embedded execution or node-plan authority, public digest parity, strict legacy rejection, and isolated plan reads.
- The admitted package contains modular delivery files and `plans/DN-001.yaml`; its legacy `graph.yaml` was removed.

### Proof
- `uv run pytest serve/kanban/tests/test_change_revision.py -q`: 27 passed. Exercises public loader behavior, malformed and identity diagnostics, isolated-plan interruption recovery, replay, stale conflict preservation, and `read_node_plan`.
- `uv run ruff check serve/kanban/src/owlbear_kanban/change.py serve/kanban/tests/test_change_revision.py`: all checks passed.
- Public admitted-package probe loaded `.owlbear/changes/replace-delivery-pipeline` through `load_change`, returned digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`, found no `graph.yaml`, and read the isolated DN-001 plan.

### AC Evidence
- AC1: admitted public load returned the required digest with modular documents and isolated DN-001 plan.
- AC2: focused public-loader test adds `graph.yaml` and receives the declared schema-invalid diagnostic targeting that file.
- AC3: focused tests prove absent plans return `None`, committed isolated plans are read through `ChangeRevision`, and `DeliveryGraph` has neither embedded execution nor node plans.
- AC4: focused transaction test proves interruption recovery, byte-identical replay, and conflict preservation.
- AC5: modular helpers and logical digest parity use public `load_change`; the focused module passes.

### Current Failure-Key Resolution
- `scope/public-api-rename`: no lifecycle API rename remains in this task.
- `AC3/modular-authority-fixtures`: legacy graph fixture writes and embedded-plan assertions were replaced with modular authority fixtures and isolated-plan proof.
- `low-level-storage`: replay, OCC conflict, and interruption recovery were exercised at `NodePlanStore` and `RuntimeTransaction` boundary.

### Durable Test Justification
- Updated existing maintained change-revision coverage for a public loader authority migration and its isolated transaction storage risk; no new standalone test file or speculative coverage was added.

### Builder Challenger
- `pass`: challenger independently ran the focused test suite and Ruff and confirmed the admitted package digest, legacy-file absence, and isolated plan.

### Follow-up Risks
- Runtime publication and receipt currentness remain intentionally sequenced to #2034. Unrelated dirty worktree files, the package storage lock, and shape receipt were not modified or included.

[[2026-07-25T04:51:35+02:00]]
## Verify Notes

### Evidence Reviewed
- Claimed task context and repaired Shape Notes. No resolved structured requests existed.
- Reviewed builder commit `837b76518` and its changed module list. The changed files match the repaired map: `change.py`, modular delivery and DN-001 plan records, and maintained `test_change_revision.py`; runtime and receipt owners remain excluded for #2034.
- Read `ChangeRevision.read_node_plan`, `load_modular_change`, `load_change`, and focused tests for public loading, strict legacy rejection, logical identity, and transactional plan storage.

### Named Authorities And Boundary
- Compared implementation and admitted package against the task authority, including digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`, MIG-004, and the digest-named admission receipt.
- Normal public boundary was exercised directly with `load_change(Path('.owlbear/changes'), 'replace-delivery-pipeline')`: it returned the required digest, found no `graph.yaml`, and returned an isolated DN-001 plan.
- The focused transaction proof uses real `NodePlanStore.prepare` and `RuntimeTransaction`; only the permitted interruption hook is replaced below that boundary.

### Checks Run
- `uv run pytest serve/kanban/tests/test_change_revision.py -q`: 27 passed.
- `uv run ruff check serve/kanban/src/owlbear_kanban/change.py serve/kanban/tests/test_change_revision.py`: all checks passed.
- Production public-loader probe returned the admitted digest, `graph.yaml` absent, and a non-null DN-001 plan.
- A first standalone probe used the wrong `load_change` argument shape and failed with `TypeError`; it was corrected and is not used as evidence.

### AC-To-Evidence Map
- AC1: corrected public probe returned the admitted digest from the modular package and isolated plan.
- AC2: `test_load_change_rejects_legacy_graph_authority` invokes public `load_change` after adding `graph.yaml` and asserts schema-invalid targeting that file.
- AC3: focused tests prove absent isolated plan returns `None`, stored plan is read through `ChangeRevision`, and graph serialization contains neither `execution` nor `node_plans`.
- AC4: `test_node_plan_store_recovers_replays_and_rejects_conflicting_bytes` proves interruption recovery, matching-byte replay, and byte-preserving conflict at the real transaction boundary.
- AC5: maintained modular helpers and logical public-loader parity are exercised by the focused suite.

### Finding
- Verification challenger returned `fail`: `delivery/nodes.yaml` still says `graph.yaml` remains the bootstrap carrier until MIG-004, while the committed public loader rejects it unconditionally.
- Direct source review confirms the statement was migrated from the prior graph authority. `delivery/contracts.yaml` defines MIG-004 as the broader migration of runtime, receipt, profile, transaction, dispatch, MCP, agent, test, and Cockpit vocabulary; the admitted receipt also still names `graph.yaml` as authority.
- This makes the admitted digest-bearing authority internally inconsistent with the cutover. Updating it changes admission semantics and likely the digest or receipt; that requires shaping and re-admission, not a verifier patch.

### Prior Failure-Key Check
- The earlier rejection key `scope/public-api-rename` was resolved by the current task boundary. No previous verifier rejection has this authority-consistency failure key.

### Verifier-Challenger Result
- `fail`: reconcile the admitted migration metadata and authority record with the strict modular-loader cutover before acceptance.

### Final Route
- Reshape. The focused behavior is passing, but the shaped and admitted authority premise is contradictory; Shape must decide the re-admission and migration-boundary correction before a build can be verified.
