---
id: 2033
title: 'P1-C2: Cut over modular authority and isolated plans'
status: shape
priority: high
created: 2026-07-25T02:46:34.205290+02:00
updated: 2026-07-25T04:27:22.571363+02:00
tags:
  - change:replace-delivery-pipeline
  - node:DN-001
  - node:DN-003
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
  - 'AC1: Given the admitted bootstrap package and embedded node plans, migration
    writes the three `delivery/*.yaml` files and one plan file per populated node;
    public `load_change` returns digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`.'
  - 'AC2: Given `load_change` after migration, `graph.yaml` absence succeeds; restoring
    `graph.yaml` returns `ERR_CHANGE_SCHEMA_INVALID` targeting that file, so no fallback
    or dual authority is accepted.'
  - 'AC3: Given a plan read or node-plan digest request, `ChangeRevision` and receipt
    currentness use `plans/<node-id>.yaml`; a missing plan yields the declared unavailable
    or stale result rather than embedded execution data.'
  - 'AC4: Given a runtime plan-publication participant from #2032, commit changes
    only the target plan and its transaction peers; injected interruption recovers
    prior bytes or the complete new plan, never a partial YAML document.'
  - 'AC5: Source and maintained-fixture inspection finds no active `ExecutionPlan`
    or `node_plans` graph field, `graph.yaml` plan mutation, or dual modular/monolithic
    registration.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Objective
Migrate the admitted bootstrap carrier and active consumers to modular authority and isolated plans with no `graph.yaml` fallback.

## Scope
In scope: physical package migration, public `load_change`, `ChangeRevision` plan access, receipt digest/currentness, native plan persistence, and change health.

Out of scope: `shape` to `plan` identity, reconciliation, dispatch, and MCP.

## Authority
Admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; DEC-030; MIG-004; DN-001; IF-001; PROOF-001.

Complexity waiver: five AC share one atomic migrated-package boundary; splitting carrier removal from plan persistence would expose a forbidden dual authority.

Proof guidance: migrate a package copy through the public loader, compare semantic identity, and interrupt isolated plan publication.

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
- Read-only owner and diff inspection: `git diff` scoped to the mapped owners/package plus exact `rg` searches for `load_change`, `ChangeRevision`, `graph.yaml`, `node_plans`, `ExecutionPlan`, `NodePlanStore`, and finish request identities.
- No focused test was run because the early routing gate failed on a named scope contradiction. Existing Builder Notes also record terminal exit 130 for the prior focused test attempts.

### AC And Follow-up Status
- AC1 through AC5 remain unproved. The prior required follow-up is unresolved pending shape's decision on the public API rename and coherent implementation boundary.

### Builder-Challenger
- Not invoked: mandatory only before a DONE verdict; this invocation rejects to shape.

### Follow-up Risk
- The admitted package is already modular while the uncommitted source diff is not an approved coherent cutover. Do not advance or commit this task until shaping assigns the `shape`/`plan` rename and reissues a scope-consistent module map.
