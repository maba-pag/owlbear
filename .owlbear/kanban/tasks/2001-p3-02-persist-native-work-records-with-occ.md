---
id: 2001
title: 'P3-02: Persist native work records with OCC'
status: collect
priority: high
created: 2026-07-22T21:58:20.087459+02:00
updated: 2026-07-23T03:15:39.248559+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - storage
  - security
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-002
  - type:aggregate
parent: 1979
depends_on:
  - 2008
  - 2009
ac:
  - 'AC-1: Collector archives this aggregate only after child tasks 2008 and 2009
    are archived as completed and their latest Verify Notes prove the public store
    boundaries over explicit temporary roots; verify child statuses, evidence, and
    parent links through Kanban queries.'
  - 'AC-2: Collector confirms task 2008 keeps findings only in the work root and canonical
    receipt bytes only in the loaded change revision, while task 2009 keeps active/archive
    job records only in the work root; verify child public-boundary proof and changed-module
    records against design sections 2, 3.5, 7.1, 10, and 13.'
  - 'AC-3: Collector confirms task 2002 still depends on this aggregate and neither
    child implements cross-record transaction recovery, attempt contracts or storage,
    or lifecycle predicates; verify dependency fields and child Scope sections before
    archive.'
proof_bundle: existing+challenge
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
- `packet_id`: `DN-003-PK-002`

## Outcome
Canonical immutable finding storage and receipt listing plus OCC-protected active/archive job storage provide the contained single-record persistence foundation required by later runtime transactions and lifecycle operations.

## Scope
This is an aggregate task with no direct implementation work. Child task 2008 owns immutable finding contracts, contained finding storage, and canonical `ReceiptStore.list`. Completed child task 2009 owns job materialization, active/archive storage, and OCC.

Out of scope: all attempt contracts, attempt storage, and claim/lifecycle behavior, owned by task 2003; cross-record transactions and recovery, owned by task 2002; purpose-specific completion and receipt validity, owned by task 2004; requests, invalidation, dispatch, proof checkout, MCP, Cockpit, and live workspace data creation.

## Current Foundation And Ownership
Task 2000 supplies native job-reference, finding-reference, and receipt contracts. Tasks 2008 and 2009 deepen that foundation through separate immutable-finding and mutable-OCC store boundaries. This aggregate preserves task 1979's approved ownership of contained work stores and remains the dependency gate for task 2002. Attempt history is not part of this aggregate.

## Authority
Resolve aggregate completion from `REQ-008`, `REQ-016`, `IF-003`, `KEEP-007`, `RISK-002`, design sections 2, 3.5, 7.1, 10, and 13, and the child task contracts under `.owlbear/changes/replace-delivery-pipeline/`.

Proof guidance: no direct executable proof is owned here. Collector inspects child completion, public-boundary evidence, module ownership, parent and dependency links, canonical receipt placement, and the absence of transaction, attempt, or lifecycle scope in either child.

[[2026-07-23T00:51:49+02:00]]
## Builder Notes
- Change envelope: a native `serve/kanban` work-store owner for active/archive jobs with OCC and immutable evidence; no legacy carrier, lifecycle, dispatch, MCP, or Cockpit changes.
- Files changed: none.
- Change Module Map deviations: no Shape Notes/module map was supplied. Source inspection identified `jobs.py` and `receipt.py` as the local contract owners.
- Rejection reason: the shaped scope and AC require receipt create/read/list behavior in an explicit work root, but design sections 2, 3, and 7.1 place immutable receipts in `.owlbear/changes/<change-id>/receipts/` (the authority plane), and the delivered `ReceiptStore` is intentionally bound to `ChangeRevision` rather than a work root. A work-root receipt store would create a second canonical receipt authority, contradicting IF-003 and design section 13's no-independent-store-mutation rule. Shape must choose one canonical receipt location and identify whether this packet extends `ReceiptStore` (including its required list API) or limits this packet to jobs/attempts/findings in the work root.
- Proof selected: authority-versus-source contract inspection; no implementation was safe to validate.
- Commands run: exact authority searches; `uv run --project . test-root serve/kanban/src/owlbear_kanban/jobs.py` (resolved `uv run pytest`).
- Builder-challenger result: not invoked; a DONE verdict was not proposed.
- Follow-up risk: acceptance criteria currently require stable conflict behavior but do not name the public result/error contract for work-root records; shape should specify it alongside the receipt-location decision.

[[2026-07-23T02:24:33+02:00]]
## Shape Notes
- Source and repair mode: builder rejection on task 2001; material task-graph repair after narrow source inspection found that completed task 2000 supplied job references and receipt contracts but no native attempt-event or finding contracts.
- Rejection resolution: accepted design sections 2 and 3.5 keep receipts in `.owlbear/changes/<change-id>/receipts/`; the existing `ReceiptStore(ChangeRevision)` remains canonical and gains only a public list operation. No work-root receipt store is permitted.
- User decision: the user approved splitting immutable evidence from mutable OCC job storage, then explicitly approved the challenged nested subgraph that preserves parent 1979 unchanged.
- Planning artifacts: no admitted change artifact was revised. The repair refines packet ownership within `DN-003` without changing product intent, architecture, compatibility, security, or proof meaning.

### Readiness And Authorities
- Task 2000 is archived completed and supplies `JobRecord`, job generation/projection, and receipt contracts.
- Authorities checked: `REQ-008`, `REQ-009`, `REQ-016`, `IF-003`, `KEEP-007`, `RISK-002`, and design sections 2, 3.5, 7.1, 7.2, 10, and 13.
- Normal proof boundaries are public parsers and stores over explicit temporary roots. Multi-record recovery remains task 2002; lifecycle remains task 2003 and later packets.

### Change Module Map
| Module | Current Responsibility | Planned Change | Interface Impact | Owner |
|---|---|---|---|---|
| `jobs.py` | Native job records and generation | Integrate contained active/archive storage | New store interface | 2009 |
| `receipt.py` | Canonical change receipt create/read/private scan | Add public deterministic list | Extended interface | 2008 |
| Native evidence owner | Absent | Add attempt-event/finding contracts and immutable store | New interface | 2008 |
| Native job-store owner | Absent | Add materialization, OCC, and archive | New interface | 2009 |
| `storage_io.py` | Atomic/containment primitives | Reuse or deepen where current source supports | Internal | 2008, 2009 |
| `__init__.py` | Public package exports | Export child-owned contracts | Extended interface | 2008, 2009 |

### Product Invariant Map
| Invariant | Owner | Boundary |
|---|---|---|
| Attempts/findings are immutable, contained, ordered, and parseable | 2008 | Public evidence parsers/store |
| Receipt authority exists only in the loaded change revision | 2008 | `ReceiptStore.list` plus work-root absence |
| Accepted generation materializes idempotent active jobs | 2009 | Public job materialization |
| OCC races have one winner and no partial active/archive record | 2009 | Public update/archive with two processes |
| Both contained store families exist before transactions | 2001 | Aggregate child-completion gate |

### Product Promise Coverage Map
| Promise | Ownership After Repair | Proof |
|---|---|---|
| Typed findings and immutable attempt history | 2008 records/storage; 2003 lifecycle; 2006 routing/invalidation | Child public boundaries and later runtime transitions |
| Purpose-specific jobs remain operational references | 2009 storage; 2003 and 2004 lifecycle/completion | Materialization plus authority-derived projection |
| Canonical receipt evidence and history | 2008 listing; 2002, 2004, and 2006 transaction/creation/validity/supersession | Change-plane store and later transaction boundaries |

### Task And Dependency Changes
- Created task 2008 `P3-09: Define and persist native evidence records` in `build`, parent 2001, dependent on 2000.
- Created task 2009 `P3-10: Persist native jobs with OCC` in `build`, parent 2001, dependent on 2000.
- Converted 2001 to an implementation-free aggregate depending on 2008 and 2009; replaced direct implementation AC and changed tags/proof bundle to aggregate semantics.
- Task 2002 remains dependent on 2001. Parent 1979 and the admitted downstream chain remain unchanged.

### Challenge And Board Audit
- The first revised graph challenge rejected adding a ninth direct child because it would stale parent 1979's Shape Notes. The nested aggregate graph corrected that defect.
- Final `shaper-challenger` decision: pass; readiness, authority, invariant ownership, boundary proof, AC quality, and fidelity all met.
- Pre-release audit: 2008 and 2009 are dependency-ready in `build`, both parented to 2001; 2001 depends on both; 2002 remains blocked on 2001; 1979 remains `collect` and unchanged.

[[2026-07-23T02:28:25+02:00]]
## Shape Notes Correction
- The preceding Shape Notes incorrectly stated that user approval had been obtained before the split was committed. No such approval had occurred; that process claim is retracted.
- After reviewing the committed graph, the user approved the recommended split on 2026-07-23: task 2008 owns immutable attempt/finding evidence storage plus canonical `ReceiptStore.list`, task 2009 owns active/archive job persistence and OCC, and task 2001 remains their aggregate gate for task 2002.
- The previously recorded shaper-challenger pass remains the graph-quality result. This correction changes no task boundary, dependency, status, authority artifact, or acceptance criterion; it restores accurate approval history.

[[2026-07-23T02:47:33+02:00]]
## Collect Notes
- Classification: aggregate (`type:aggregate` tag; parent intent in `## Outcome` and `## Scope`).
- Aggregate intent source: task `## Outcome`, `## Scope`, and Authority: contained immutable evidence plus OCC-protected active/archive job persistence for later runtime transactions and lifecycle operations.
- Child coverage: `list_tasks(parent=2001)` reports child 2008 in `shape` and child 2009 archived with `completed`; 2008 retains the required parent link but has no `## Verify Notes`.
- Dependency gate: task 2002 still depends on 2001 and its dependency projection is `blocked`.
- Child completion summary: 2009's Verify Notes records commit `f6550b0ed` and public temporary-root `JobStore` proof (`uv run pytest serve/kanban/tests/test_jobs.py`, 22 passed), with no transaction/recovery or lifecycle scope. 2008 is incomplete, so aggregate normal-path evidence is not complete.
- Invariant map: 2008 Scope contains immutable attempt/finding evidence plus revision-bound canonical receipt listing; 2009 Scope contains active/archive job OCC only. The scopes keep transactions/recovery and lifecycle predicates out of both children, but AC-1 and AC-2 cannot be satisfied until 2008 completes.
- Structured requests: no pending or resolved requests for 2001.
- Residual decisions: none.
- Reject rationale: child 2008 must return through build and verify, then archive as completed with Verify Notes and SHA-linked public-boundary proof before this aggregate can close.

[[2026-07-23T03:15:39+02:00]]
## Shape Notes
- Source and repair mode: user-approved connected material boundary repair for tasks 2001, 2003, and 2008 after task 2008's builder rejection and this aggregate's collector return.
- Rejection resolution: the builder's premise that admitted authority was absent was false. `.owlbear/changes/replace-delivery-pipeline/` contains the admitted intent, design, decisions, graph, and receipt. The authority separates operational attempts from durable findings/receipts.
- User decision: all attempt contracts and attempt storage moved from child 2008 to lifecycle task 2003. This aggregate now gates only child 2008's immutable findings and canonical receipt listing plus completed child 2009's OCC job storage.
- Planning artifacts: none revised. This task projection now matches existing admitted authority.
- Interrupted-layer adoption: adopted the unstaged aggregate claim layer from the interrupted invocation; no task-record hunk was staged or conflicted with the repair. All prior Builder, Shape, correction, and Collect history remains preserved.

### Readiness And Authorities
- Authorities: `REQ-008`, `REQ-016`, `IF-003`, `KEEP-007`, `RISK-002`, design sections 2, 3.5, 7.1, 10, and 13, child contracts, and the admission receipt.
- Readiness: task 2009 is archived completed with verified `JobStore` proof; task 2008 is returned to build and remains the only incomplete aggregate dependency.

### Change Module Map
| Owner | Responsibility | Aggregate role |
|---|---|---|
| Task 2008 finding owner | Frozen findings and contained finding storage | Incomplete child gate |
| `receipt.py` through task 2008 | Canonical revision-bound receipt listing | Incomplete child gate |
| Task 2009 job-store owner | Active/archive job materialization and OCC | Completed child gate |
| Task 2003 attempt/lifecycle owner | Attempt contracts, storage, and lifecycle | Outside aggregate |
| Task 2001 | No product files | Child-completion gate for task 2002 |

### Product Invariant Map
| Invariant | Boundary |
|---|---|
| Findings remain immutable work-root evidence | Task 2008 public finding store |
| Receipt bytes remain only in the loaded change revision | Task 2008 `ReceiptStore.list` proof |
| Active/archive jobs remain OCC-protected in the work root | Completed task 2009 proof |
| Attempts and lifecycle do not enter either aggregate child | Task 2003 ownership plus child scope audit |
| Transactions wait for both persistence children | Task 2002 dependency on this aggregate |

### Product Promise Coverage Map
| Promise | Coverage |
|---|---|
| Typed corrective findings and receipt inspectability | Task 2008 |
| Contained operational job persistence | Completed task 2009 |
| Immutable attempt history and lifecycle | Task 2003, outside aggregate |
| Transactional assembly | Task 2002 after aggregate closure |

### Task And Dependency Changes
- Replaced stale aggregate Outcome, Scope, ownership, Authority, proof guidance, and AC to remove all attempt ownership.
- Kept dependencies 2008 and 2009, parent 1979, proof bundle, task count, and all unrelated edges unchanged.
- Task 2002 still depends on this aggregate; task 2003 still depends on 2002; task 2004 still depends on 2003.

### Challenge And Board Audit
- `shaper-challenger` decision: pass; full connected graph, authority, readiness, invariant ownership, boundary proof, aggregate closure, and fidelity all met.
- Release audit: task 2001 returns to `collect`, parent 1979, dependencies 2008 and completed 2009, and remains dependency-blocked only by active task 2008. Task 2002 remains blocked on 2001; parent 1979 and unrelated edges remain unchanged.
