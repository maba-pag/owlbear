---
id: 2032
title: 'P1-C1: Establish modular change-package primitives'
status: verify
priority: high
created: 2026-07-25T02:46:24.792896+02:00
updated: 2026-07-25T03:45:58.272985+02:00
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
archival_reason:
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
