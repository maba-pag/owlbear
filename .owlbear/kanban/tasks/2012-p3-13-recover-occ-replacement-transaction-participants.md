---
id: 2012
title: 'P3-13: Recover OCC replacement transaction participants'
status: shape
priority: high
created: 2026-07-23T14:40:46.644783+02:00
updated: 2026-07-23T23:04:08.263257+02:00
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
  - 'AC-1: Given `storage_io.locked_roots` the root sequence `(root_b, root_a, root_a)`,
    it acquires one descriptor-backed `.storage.lock` for each canonical root in path
    order; a symlink root, symlink lock file, or failure while acquiring `root_b`
    raises before yielding and releases the lock and descriptor acquired for `root_a`.'
  - "AC-2: Given `JobStore.update` and `RuntimeTransaction.commit` start from the
    same stored job bytes on one work root, a two-phase subprocess proof holds one
    writer inside `storage_io.locked_roots`, observes the rival blocked, then releases
    the holder; the holder publishes, the rival returns `ERR_TRANSACTION_CONFLICT`
    or `ERR_JOB_OCC_STALE` according to its public boundary, and the holder's bytes
    remain stored."
  - 'AC-3: Given a replacement participant whose destination equals its expected bytes,
    `RuntimeTransaction.commit` publishes the replacement; when the destination already
    equals the replacement, replay returns the committed outcome; any other bytes
    return `ERR_TRANSACTION_CONFLICT` without mutation.'
  - 'AC-4: Given interruption before publication, after replacement publication, or
    before manifest cleanup, `RuntimeTransaction.recover_all` completes the replacement
    and removes the manifest; a second recovery leaves the replacement bytes unchanged.'
  - 'AC-5: Given a malformed replacement manifest, altered content digest, or participant
    root outside `recover_all(..., roots=...)`, `RuntimeTransaction.recover_all` raises
    `ERR_TRANSACTION_MANIFEST_INVALID` or `ERR_TRANSACTION_PATH_UNSAFE` and leaves
    the destination and outside paths unchanged.'
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

[[2026-07-23T15:20:46+02:00]]
## Builder Notes
- Change envelope: repair verifier-found cross-writer OCC safety for replacement participants in `RuntimeTransaction`, with only the transaction kernel and focused boundary proof eligible to change.
- Files changed: none. A targeted replacement-destination lock probe and its subprocess proof were applied, focused-validated, then removed when source inspection disproved the synchronization premise.
- Change Module Map deviations: none. The mapped kernel cannot independently serialize arbitrary participant writers.
- Rejection reason: `RuntimeTransaction._publish_replacement()` validates bytes then replaces the destination. The existing `JobStore` writer protocol serializes its writes with its private participant-root `.jobs.lock`; the kernel's manifest-root lock and a new generic replacement lock do not synchronize that writer. Therefore neither design proves REQ-016/RISK-002 cross-writer OCC, and adding an unrelated lock would only serialize replacement transactions, not prevent an intervening JobStore write from being overwritten.
- Required reshape: define one authoritative cross-writer compare-and-swap or locking contract and its owner. The implementation must make `JobStore` and replacement publication use that same authority, then add a focused intervening-writer proof. Do not weaken the requirement to replacement-transaction-only contention unless the named authorities explicitly allow it.
- Proof selected: `uv run pytest serve/kanban/tests/test_runtime_transaction.py` (11 passed), `uv run ruff check serve/kanban/src/owlbear_kanban/runtime_transaction.py serve/kanban/tests/test_runtime_transaction.py` (clean), and `git diff --check` (passed after probe removal). The temporary probe's focused run passed 12 tests before it was rejected as architecturally insufficient.
- Builder challenger: not called because no DONE verdict is proposed.
- Memory assessment: all applicable recalled entries were assessed. Two recall-payload entry identifiers were unavailable to the memory service during assessment; this did not affect task evidence.
- Follow-up risk: current committed replacement publication retains the verifier-identified TOCTOU gap until the shared OCC authority is shaped and implemented.

[[2026-07-23T22:55:31+02:00]]
## Operative Cross-Writer OCC Repair Amendment

This amendment supersedes narrower task text that limits ownership to `runtime_transaction.py` or treats replacement-only contention as sufficient proof.

### Shared Lock Authority

`serve/kanban/src/owlbear_kanban/storage_io.py` owns one root-lock context for storage mutation. It resolves and deduplicates supplied roots, acquires their advisory lock files in deterministic path order, and holds them until compare, publication, fsync, and cleanup complete. A one-root caller and a multi-root caller use the same lock identity for that root.

`JobStore.materialize`, `JobStore.update`, and `JobStore.archive` consume this shared root-lock authority for the job work root instead of the private `.jobs.lock` protocol. `RuntimeTransaction.commit` and recovery consume the same authority for the manifest root and participant roots. Replacement expected-byte comparison and publication occur while those locks are held, so an intervening `JobStore` writer cannot be overwritten.

### Change Module Map

- `serve/kanban/src/owlbear_kanban/storage_io.py`: owns resolved-root lock identity, deterministic multi-root acquisition, release, and partial-acquisition cleanup.
- `serve/kanban/src/owlbear_kanban/jobs.py`: consumes the shared lock without changing `JobStore` record/OCC ownership or stable `ERR_JOB_OCC_STALE` behavior.
- `serve/kanban/src/owlbear_kanban/runtime_transaction.py`: holds shared manifest/participant-root locks across prepare, replacement compare/publish, recovery, and cleanup; preserves `ERR_TRANSACTION_CONFLICT`, manifest validation, containment, and immutable participants.
- `serve/kanban/tests/test_runtime_transaction.py`: proves replacement/recovery behavior and an actual subprocess race through public `RuntimeTransaction` and `JobStore` boundaries.
- `serve/kanban/tests/test_jobs.py`: existing `JobStore` behavior remains the focused regression boundary; add durable coverage only if the shared-lock migration exposes a concrete unprotected behavior not exercised by the transaction race.

### Scope Boundary

This task owns the shared lock primitive and the `JobStore` versus replacement-transaction race required to close `AC-1/cross-writer-occ`. It does not own mixed job/attempt pair atomicity, rival attempt-event publication, or strict-subset visibility; task #2013 consumes this foundation for those outcomes.

[[2026-07-23T22:59:38+02:00]]
### Challenger Correction: Executable Lock Boundary

The shared callable is `storage_io.locked_roots(roots)`. It accepts existing root `Path` values, rejects symlink roots and symlink lock files through descriptor-backed no-follow opens, deduplicates roots by canonical identity, acquires one `.storage.lock` per root in canonical path order, and releases each previously acquired descriptor and lock when a later acquisition fails. Callers hold the returned context across their existing compare and mutation work; the helper does not move job serialization or transaction publication into `storage_io.py`.

The cross-writer proof uses a controlled two-phase subprocess harness rather than scheduler timing: one writer is held after acquiring the shared root lock, the rival is started and observed blocked, then the first writer is released and the rival's public result and final bytes are asserted.

Existing `atomic_write` consumers outside `JobStore` and `RuntimeTransaction` are not migrated by this task because they do not write the JobStore-owned destination exercised by `AC-2`. Task #2013 must consume the shared root lock when it assembles mixed job/attempt participants; pair atomicity and attempt-event visibility remain #2013 outcomes.

[[2026-07-23T23:04:08+02:00]]
## Shape Notes
- Repair classification: local OCC contract repair expanded into a connected parent-map repair after challenge; no product decision is pending.
- Source facts: accepted design section 13 assigns locks to `storage_io.py`; current `storage_io.py` lacks the lock helper; `JobStore` uses private `.jobs.lock`; `RuntimeTransaction` uses `.runtime-transactions.lock`, so replacement compare and publication are not serialized with `JobStore.update`.
- Task repair stored: exact `storage_io.locked_roots(roots)` contract, descriptor/no-follow safety, canonical deduplication/order, partial-acquisition cleanup, controlled two-phase JobStore versus RuntimeTransaction subprocess proof, and AC-1 through AC-5.
- Failure key `AC-1/cross-writer-occ`: task-local contract is resolved, but final route is intentionally withheld because parent #2003 still records `jobs.py` as consumed without ownership change and omits the shared-lock scenario axis.
- Challenger: first challenge required an executable shared-lock boundary and controlled writer ordering; both were added. Second challenge found stale parent maps. Live board check disproved concurrent sibling work: #2017 through #2019 are unclaimed and dependency-blocked through #2013, whose dependency on #2012 already supplies correct execution order.
- Lifecycle: release without status movement. Restart shaping as the explicit connected set #2003 and #2012, claimed in ID order, update only #2003 maps plus final #2012 route, then challenge the connected result.
