---
id: 2012
title: 'P3-13: Recover OCC replacement transaction participants'
status: build
priority: high
created: 2026-07-23T14:40:46.644783+02:00
updated: 2026-07-23T15:13:06.665828+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - transactions
  - occ
  - recovery
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004-C
parent: 2003
depends_on:
  - 2002
ac:
  - 'AC-1: Given a replacement participant whose destination matches its expected
    bytes, commit publishes the replacement; when the destination already matches
    the replacement, replay returns the committed outcome; any other bytes return
    the stable conflict diagnostic without mutation.'
  - 'AC-2: Given interruption before publication, after replacement publication, or
    before manifest cleanup, `recover_all` completes the replacement and removes the
    manifest; repeated recovery is inert.'
  - 'AC-3: Given a malformed replacement manifest, altered content digest, or unsafe
    participant path, recovery raises the existing manifest or path diagnostic and
    leaves the destination and outside paths unchanged.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
`RuntimeTransaction` supports recoverable optimistic-concurrency replacement participants without weakening its existing immutable publication guarantees.

## Scope
In scope: expected-byte and replacement-byte participant metadata; contained mutable replacement; idempotent replay; conflict diagnostics; manifest schema and digest validation; interruption recovery before publication, after replacement publication, and before cleanup.

Out of scope: mixed job/event process races, attempt storage, lifecycle guards, receipt validity, and domain-specific transaction policy.

## Current Foundation And Ownership
Deepen the reusable transaction kernel delivered by archived task #2002. Preserve all existing immutable participant behavior and diagnostics. Consume `JobStore` byte/OCC semantics without moving job ownership into the kernel.

## Authority
Resolve behavior from `REQ-016`, `IF-003`, `KEEP-007`, `RISK-002`, `PROOF-003`, and design sections 9.5, 12, and 13. The user-approved architecture preserves persisted `JobRecord.claim_id` and `attempt_id` while adding reusable recoverable replacement participants.

## Proof Guidance
Use the transaction boundary directly. Cover expected, already-replaced, conflicting, malformed, unsafe, and all three interruption phases; do not add mixed process races to this task.

[[2026-07-23T15:09:56+02:00]]
## Builder Notes
- Change envelope: extend `RuntimeTransaction` with contained OCC replacement participants, preserving immutable participant behavior and diagnostics. The expected modules were the transaction kernel and its focused boundary tests; no Change Module Map deviation.
- Files changed: `serve/kanban/src/owlbear_kanban/runtime_transaction.py`; `serve/kanban/tests/test_runtime_transaction.py`.
- Implementation: added a schema-v2 replacement manifest entry carrying expected and replacement bytes plus SHA-256 digests; replacement publish accepts expected bytes, treats replacement bytes as an idempotent replay, and rejects all other states with `ERR_TRANSACTION_CONFLICT`. Recovery validates schema, digests, and containment before mutation.
- Proof selected: durable transaction-boundary regression coverage because crash recovery and OCC replacement are shared, data-integrity-sensitive behavior. Tests cover expected/replayed/conflicting destinations, all three interruption phases with repeat recovery, malformed manifests, altered digest, and unsafe root.
- Commands run: `uv run pytest serve/kanban/tests/test_runtime_transaction.py && uv run ruff check serve/kanban/src/owlbear_kanban/runtime_transaction.py serve/kanban/tests/test_runtime_transaction.py` (11 passed; Ruff clean). `git diff --check` passed. Editor diagnostics found no errors in touched files.
- Builder challenger: pass; no concrete blockers. It independently confirmed the focused test and lint results.
- Follow-up risks: no mixed job/event process races were added; those remain explicitly out of scope. One recalled memory identifier could not be resolved by the memory service during required assessment; the retry/replay memory was assessed outstanding.

[[2026-07-23T15:11:10+02:00]]
## Builder Notes
- No implementation performed: task was already in `verify` when claimed, outside the builder status boundary. Released unchanged for verifier ownership.

[[2026-07-23T15:13:06+02:00]]
## Verify Notes
- Evidence reviewed: task AC-1 through AC-3; Builder Notes; committed build `0db9122cb`; `runtime_transaction.py` and its focused boundary tests.
- Named authorities checked: `REQ-016`, `IF-003`, `KEEP-007`, `RISK-002`, and `PROOF-003` require bounded, containment-checked, crash-safe, concurrency-safe, recoverable transactions with stable failures. The implementation remains within the shaped kernel and focused-test module map; no module-map deviation.
- Normal-path boundary exercised: public `RuntimeTransaction.commit()` and `RuntimeTransaction.recover_all()` tests cover expected/replayed replacement states, three interruption phases, repeat recovery, malformed manifests, altered digests, and unsafe roots. Replacements below that boundary are only temporary filesystem roots.
- Checks run: `uv run pytest serve/kanban/tests/test_runtime_transaction.py` (11 passed); `uv run ruff check serve/kanban/src/owlbear_kanban/runtime_transaction.py serve/kanban/tests/test_runtime_transaction.py` (clean); `git diff --check HEAD -- serve/kanban/src/owlbear_kanban/runtime_transaction.py serve/kanban/tests/test_runtime_transaction.py` (passed).
- Prior same-AC rejection check: no earlier `## Verify Notes` or prior verifier rejection for this task.
- Finding: replacement OCC is not concurrency-safe. `_publish_replacement()` reads and validates expected bytes, then calls `replace()` with no lock or compare-and-swap mechanism protecting the participant root. A concurrent writer can change the destination after validation and before replacement, and its bytes will be overwritten. The manifest-root lock does not synchronize participant-root writers. This conflicts with `REQ-016` and `RISK-002`, and the existing immutable-participant process test does not prove replacement OCC.
- Patches applied: none; correcting this requires builder-owned synchronization or a compare-and-swap design plus a focused intervening-writer proof.
- Verifier challenger: fail; confirmed the replacement publication race and advised a transaction-layer correction.
- Final route: reject to build.
