---
id: 2032
title: 'P1-C1: Establish modular change-package primitives'
status: archived
priority: high
created: 2026-07-25T02:46:24.792896+02:00
updated: 2026-07-25T03:58:16.298758+02:00
tags:
  - change:replace-delivery-pipeline
  - node:DN-001
  - corrective
  - scope:core
  - authority
  - storage
  - type:build
  - rigor:thorough
parent: 1968
depends_on: []
ac:
  - 'AC1: Given equivalent monolithic and modular fixture content, the modular parser
    returns the same delivery digest, stable identities, authored sequence order,
    and accepted-decision projection; the focused parity check compares both results.'
  - 'AC2: Given a missing, duplicate, malformed, symlinked, or escaping delivery participant,
    the parser returns the declared `ERR_CHANGE_*` diagnostic and no `ChangeRevision`;
    focused checks exercise the five classes.'
  - 'AC3: Given a loaded digest and receipts directory, admission discovery selects
    `receipts/admission-<digest-prefix>.yaml`; absent or ambiguous current receipts
    produce a health finding, while older-digest receipts remain inspectable stale
    history.'
  - 'AC4: Given a node ID and plan mapping, `NodePlanStore` prepares one contained
    OCC participant for `plans/<node-id>.yaml`; replayed bytes are idempotent and
    conflicting bytes leave the stored plan unchanged.'
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Objective
Provide the typed modular authority and isolated-plan storage primitives required by MIG-004 without registering a compatibility fallback.

## Scope
In scope: joined delivery parser/model, canonical digest parity, current-admission discovery from the digest-named receipt, contained `NodePlanStore` OCC participants, and path/schema/identity diagnostics.

Out of scope: live package cutover, runtime plan completion, lifecycle vocabulary, reconciliation, dispatch, and MCP.

## Authority
Admitted digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990`; DEC-030; MIG-004; DN-001; IF-001; PROOF-001.

Proof guidance: run focused modular parity/path checks plus isolated-plan transaction replay, conflict, and recovery checks.

[[2026-07-25T03:45:58+02:00]]
## Builder Notes

### Implementation
- Added typed modular authority documents and `load_modular_change`, joining `delivery/obligations.yaml`, `delivery/contracts.yaml`, and `delivery/nodes.yaml` into the existing immutable `DeliveryGraph` while loading isolated node plans outside the delivery digest.
- Added `NodePlanStore` with pinned change-directory identity, declared-node/path validation, deterministic YAML serialization, create/replay behavior, and token-guarded replacement participants backed by `RuntimeTransaction`.
- Added digest-named `discover_admission`; strict `ReceiptStore` reads remain current-revision-bound, while discovery retains older admission receipts as stale history and reports absent, ambiguous, malformed, unsafe, or wrong-change evidence.
- Exported the new public primitives and added focused durable behavior coverage.

### AC Evidence
- AC1: `test_modular_loader_preserves_logical_revision_identity` compares canonical digest, authored entity order, and accepted decisions across equivalent physical layouts.
- AC2: `test_modular_loader_rejects_invalid_participants` covers missing, duplicate, malformed, symlinked, and escaping participants with stable `ERR_CHANGE_*` outcomes and no revision.
- AC3: admission discovery tests cover exact digest path, stale-history inspection, absence, and ambiguity.
- AC4: `test_node_plan_store_recovers_replays_and_rejects_conflicting_bytes` proves interrupted recovery, exact replay, and unchanged stored bytes after conflict.

### Validation
- Owning suites: `85 passed` for change revision and receipt modules.
- Ruff check and format check: clean on all six touched source/test files.
- Editor diagnostics and `git diff --check`: clean.
- Builder challenger: `pass`, no findings.
- Mapped regression: `1101 passed`, four pre-existing fixture failures in `finish_shape`. The admitted bootstrap graph already embeds DN-001's plan, and untracked legacy `receipts/shape-001.yaml` is copied by those tests. This task does not modify `NativeRuntime`, shape completion, or those fixtures; #2034 owns lifecycle replacement.

### Files
- `serve/kanban/src/owlbear_kanban/change.py`
- `serve/kanban/src/owlbear_kanban/node_plan.py`
- `serve/kanban/src/owlbear_kanban/receipt.py`
- `serve/kanban/src/owlbear_kanban/__init__.py`
- `serve/kanban/tests/test_change_revision.py`
- `serve/kanban/tests/test_change_receipts.py`

[[2026-07-25T03:56:42+02:00]]
## Verify Notes

### Verdict
PASS. No verification patch was required.

### Independent Evidence
- AC1: the focused parity scenario passed, and an independent temporary split of the real admitted `graph.yaml` into `delivery/obligations.yaml`, `delivery/contracts.yaml`, and `delivery/nodes.yaml` loaded at exact digest `3f6c656289911320bb5e7faf37b5e86ffa8511e729ade201a03a19913e33d990` with identical authored entity order.
- AC2: all five modular participant failures passed: missing, duplicate identity, malformed YAML, symlinked file, and escaping delivery directory; each returned no revision and the expected stable `ERR_CHANGE_*` class.
- AC3: exact digest-named current admission, stale-history retention, absent current receipt, and ambiguous current receipt scenarios passed.
- AC4: interrupted publication recovery, exact replay, observed-token replacement semantics, conflicting publication, and unchanged stored bytes passed.
- Exact AC run: 10 passed. Owning loader/receipt modules: 85 passed.
- Ruff check, format check, editor diagnostics, and whitespace checks were clean.
- Verifier challenger: `pass`, with no findings.

### Scope And Regression Boundary
- Current source/tests match builder commit `c0d73675`; the three files flagged between turns contain no post-commit diff.
- Broader mapped run previously had 1101 passes and four `finish_shape` fixture failures. They are causally outside this task: #2032 changes neither `native_runtime.py`, `test_native_runtime.py`, nor bootstrap fixtures. The admitted graph already embeds DN-001's plan and a local legacy `shape-001.yaml` fixture is copied by those tests. Runtime lifecycle replacement remains owned by #2034.

### Commit Verified
- Builder implementation commit: `c0d73675ce0fb71c75508aae3880140fb37043b5`.

[[2026-07-25T03:58:16+02:00]]
## Collect Notes

### Classification
leaf

### Latest Verification Evidence
The latest `## Verify Notes` records PASS at 2026-07-25T03:56:42+02:00. Exact AC validation reported 10 passed; owning loader/receipt modules reported 85 passed. The verifier recorded clean Ruff, format, diagnostics, and whitespace checks, plus a passing verifier challenger.

### Invariant Map Coverage
AC1 covers modular/monolithic digest, identity, sequence, and decision parity. AC2 covers all five invalid participant classes with declared diagnostics and no revision. AC3 covers digest-named current admission plus stale, absent, and ambiguous receipt states. AC4 covers recovery, replay, observed-token replacement, conflict, and unchanged bytes.

### Aggregate And Dependency Check
No child tasks, aggregate intent, or dependency gate apply; this is a leaf task. Parent assignment to #1968 is organizational only.

### Commit And Normal-Path Proof
Verifier ties the focused normal-path proof to builder commit `c0d73675ce0fb71c75508aae3880140fb37043b5`, confirmed current with no post-commit diff. The exact AC run was 10 passed.

### Residual Decisions
No pending or resolved structured requests exist for this task. The documented broader `finish_shape` fixture failures are outside this task's modules and remain owned by #2034.

### Archive Rationale
Archived mechanically: current verifier PASS, complete AC evidence, SHA-linked proof, and no unresolved follow-up or request state.
