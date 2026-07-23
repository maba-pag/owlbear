---
id: 2008
title: 'P3-09: Persist native findings and list receipts'
status: verify
priority: high
created: 2026-07-23T02:23:31.452855+02:00
updated: 2026-07-23T10:41:52.297814+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - evidence
  - storage
  - security
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-009
parent: 2001
depends_on:
  - 2000
ac:
  - 'AC-1: Given schema-version-1 finding mappings, public parsers return frozen records
    preserving the fields defined in Scope. Unknown fields, malformed references,
    unsupported target or class literals, and missing required references return stable
    diagnostics.'
  - 'AC-2: Given public finding create, read, and list calls against an explicit work
    root, byte-equivalent replay returns the existing record; a differing occupied
    identity raises `FindingConflictError` with `code == "ERR_FINDING_CONFLICT"`.
    Traversal or symlink substitution returns a stable path diagnostic, listing sorts
    by finding ID, and failed writes leave no temporary or partial record.'
  - 'AC-3: Given `ReceiptStore` built from a loaded `ChangeRevision`, public list
    reads only `.owlbear/changes/<change-id>/receipts/`, returns entries sorted by
    receipt ID, and represents malformed or unsafe entries with `ReceiptDiagnostic`
    results. Existing create/read and `ReceiptConflictError` behavior remain unchanged,
    and no receipt bytes are written beneath the work root.'
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
- `packet_id`: `DN-003-PK-009`

## Outcome
Versioned immutable finding contracts and contained finding storage preserve corrective evidence; canonical change-plane receipts gain public deterministic listing without work-root duplication.

## Scope
In scope: public frozen `Finding` models, parsers, serializers, and stable diagnostics. A finding preserves finding, source-attempt, source-job, change, and digest references; one design-enumerated target kind and ID; one design-enumerated finding class; detail; and timestamp.

Also in scope: public finding create, read, and list operations against an explicit work root; byte-equivalent replay; conflict, path-containment, no-overwrite, failed-write cleanup, and deterministic finding-ID ordering; and public `ReceiptStore.list` on the existing `ChangeRevision`-bound canonical store.

Out of scope: all attempt contracts and attempt storage, claim and lifecycle predicates, job storage or OCC, finding routing or invalidation, receipt relocation or create/read redesign, multi-record transactions and recovery, MCP, and Cockpit. Task 2003 owns attempts and lifecycle.

## Current Foundation And Ownership
Deepen the native job and receipt contract boundary delivered by packet `DN-003-PK-001`. Add one cohesive finding owner under `owlbear_kanban`; extend the existing `ReceiptStore` rather than creating a second receipt store. Reuse descriptor-relative, no-follow, no-overwrite, fsync, and stable-diagnostic patterns from `receipt.py` and `storage_io.py` when current source supports them.

Public finding creation returns the existing record on byte-equivalent replay. A differing record at an occupied finding identity raises exported `FindingConflictError` with `code == "ERR_FINDING_CONFLICT"`.

## Authority
Resolve behavior from `REQ-008`, `REQ-016`, `IF-003`, `KEEP-007`, design sections 2, 3.5, 10, and 13, and packet `DN-003-PK-001` under `.owlbear/changes/replace-delivery-pipeline/`. Finding target kinds are requirements, interfaces, migrations, risks, workflows, delivery nodes, packets, proofs, receipts, and code revisions. Finding classes are `implementation-defect`, `unforeseeable-discovery`, `planning-omission`, and `scope-change`.

Proof guidance: exercise public finding parser and store APIs plus public receipt listing over temporary explicit change and work roots for replay, malformed-entry listing, containment, no-overwrite, deterministic order, durable readback, and work-root receipt absence; run the focused check plus a downstream-impact scan.

[[2026-07-23T02:34:43+02:00]]
## Builder Notes
- Change envelope: add a cohesive native evidence owner for immutable work-root attempt events/findings and a public `ReceiptStore.list` only; preserve canonical receipt storage under the loaded `ChangeRevision` and exclude job OCC, lifecycle predicates, MCP, and Cockpit.
- Files changed: none.
- Change Module Map deviations: none; source supports `receipt.py` as the canonical receipt owner and a new `owlbear_kanban` evidence owner for work-root storage.
- Rejection: the shaped authority requires an unsupported attempt-event literal to produce a stable diagnostic, but does not define the design-enumerated supported `event_kind` set. The named design sections/REQs are absent from the workspace: exact repository search found no admitted change artifact, only unrelated historical fixtures. Creating a literal set would invent a public versioned contract.
- Proof selected: no implementation proof because the acceptance contract is under-specified before any edit.
- Commands run: `rg -l -i 'attempt-event|implementation-defect|work-root|work root' . --glob '!**/.git/**'`; focused source reads of `receipt.py`, `jobs.py`, `test_change_receipts.py`, `change.py`, and the completed packet 2000 notes; `git status --short && git log --oneline -8`.
- Builder-challenger result: not run; a DONE verdict was not proposed.
- Follow-up required: shape must attach or restore the admitted design authority and enumerate allowed `event_kind` values (and any corresponding parser diagnostic codes), then return the task to build.

[[2026-07-23T02:48:09+02:00]]
Builder invocation stopped: task status is `shape`, not `build`. No implementation or task-content changes made; releasing claim for shaping.

[[2026-07-23T03:14:32+02:00]]
## Shape Notes
- Source and repair mode: user-approved connected material boundary repair for tasks 2001, 2003, and 2008 after this task's builder rejection.
- Rejection resolution: the builder's source premise was false. Admitted authority exists under `.owlbear/changes/replace-delivery-pipeline/`, including `intent.md`, `design.md`, `decisions.yaml`, `graph.yaml`, and `receipts/admission-9387dea789fb.yaml`. Design sections 2.2 and 2.3 classify attempts as operational work history and findings/receipts as durable evidence.
- User decision: all attempt contracts and attempt storage moved to task 2003. This task owns only immutable finding contracts/storage plus public deterministic `ReceiptStore.list` on the canonical `ChangeRevision`-bound receipt store.
- Planning artifacts: none revised. The task projection now matches existing admitted authority.
- Interrupted-layer adoption: retained the unstaged builder-stop note and claim layer from interrupted invocations; neither task record was staged and no hunk conflicted with this repair.

### Readiness And Authorities
- Authorities: `REQ-008`, `REQ-016`, `IF-003`, `KEEP-007`, design sections 2, 3.5, 10, and 13, packet `DN-003-PK-001`, and the admitted receipt.
- Readiness: completed task 2000 supplies native finding references and the canonical receipt contracts; task 2008 has no unresolved dependency or request.

### Change Module Map
| Owner | Responsibility | Interface impact |
|---|---|---|
| New finding owner under `owlbear_kanban` | Frozen Finding contract and contained create/read/list | New public finding parser/store |
| `receipt.py` | Canonical revision-bound receipt create/read/diagnostics | Add public deterministic list only |
| `storage_io.py` | Descriptor-relative containment and durable-write precedent | Reused internally |
| Task 2003 | Attempt contracts, attempt storage, and lifecycle | Explicitly outside this task |

### Product Invariant Map
| Invariant | Boundary |
|---|---|
| Findings are immutable, contained, parseable, and deterministically ordered | Public finding parser/store |
| Receipt bytes remain only in the loaded change revision | `ReceiptStore.list` plus work-root absence |
| Attempt history remains operational and lifecycle-owned | Task 2003 |
| Existing receipt create/read/conflict behavior is unchanged | Receipt regression proof |

### Product Promise Coverage Map
| Promise | Coverage |
|---|---|
| Typed corrective findings | This task under `REQ-008` |
| Inspectable canonical receipt history | `ReceiptStore.list` under `REQ-016` and `KEEP-007` |
| Immutable attempt history | Task 2003, not this task |

### Task And Dependency Changes
- Renamed the task to `P3-09: Persist native findings and list receipts` and replaced stale Outcome, Scope, ownership, Authority, proof guidance, and AC.
- Replaced generic evidence conflict semantics with task-local `FindingConflictError` and `ERR_FINDING_CONFLICT`; no current task, source, or authority references the superseded generic error.
- Kept parent 2001, dependency 2000, proof bundle, task count, and all unrelated edges unchanged.

### Challenge And Board Audit
- `shaper-challenger` decision: pass; authority, readiness, invariant ownership, boundary proof, error ownership, aggregate closure, and fidelity all met.
- Release audit: task 2008 advances to `build`, parent 2001, depends on completed task 2000, and is dependency-ready. Completed sibling 2009 remains archived under parent 2001.

[[2026-07-23T10:41:52+02:00]]
## Builder Notes
- Change envelope: add the public immutable `Finding` parser/store under `owlbear_kanban` and public deterministic `ReceiptStore.list`; preserve existing receipt create/read/conflict behavior, revision-root receipt storage, and all attempt/job/lifecycle ownership.
- Files changed: `serve/kanban/src/owlbear_kanban/finding.py`; `serve/kanban/src/owlbear_kanban/receipt.py`; `serve/kanban/src/owlbear_kanban/__init__.py`; `serve/kanban/tests/test_findings.py`.
- Change Module Map deviations: none. `finding.py` is the mapped new owner; `receipt.py` reuses its pinned-descriptor scanning boundary; no task 2003 ownership changed.
- Proof selected: durable public API regression coverage because immutable containment, replay/conflict, symlink resistance, failed-write cleanup, and canonical receipt inspection are shared evidence contracts.
- Commands run: `uv run pytest serve/kanban/tests/test_findings.py` (4 passed); `uv run ruff format --check` and `uv run ruff check` on all task-owned files (passed); `uv run pytest serve/kanban/tests/test_change_receipts.py serve/kanban/tests/test_findings.py` (36 passed); downstream receipt-list caller scan; `git diff --check`.
- Builder-challenger result: pass; no concrete DONE blocker in scope, API correctness, or test relevance.
- Follow-up risks: finding routing, invalidation, and attempt lifecycle remain intentionally owned by later tasks.
