---
id: 2090
title: 'P16-02: Expose the fail-closed bootstrap finalizer'
status: archived
priority: high
created: 2026-07-27T08:39:49.070496+02:00
updated: 2026-07-27T10:51:57.213251+02:00
tags:
  - phase-16
  - scope:core
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - digest:6c95c70c81a1
  - node:DN-012
  - packet:T2
  - module:MOD-001
  - module:MOD-006
  - interface:IF-016
parent: 1989
depends_on:
  - 2087
ac:
  - "AC-1: Given a released terminal board with zero active claims, writers, and pending
    requests; a verified #2087 inventory; expected authority and code revisions; and
    explicit finalization approval, the public finalizer writes an immutable snapshot
    and finalization receipt, removes the supplied active board and sibling carrier,
    verifies their absence, and returns the tracked paths required for the caller's
    commit."
  - 'AC-2: Given missing or stale proof, a nonterminal projection, an active claim,
    writer, or request, a changed source, an existing destination, a hash mismatch,
    or an unsafe path, the finalizer returns a typed failure, preserves a recoverable
    source, and writes no completed finalization receipt.'
  - 'AC-3: Given an interruption during publication or absence verification, recovery
    exposes no partial-success receipt; a replay after correction completes once and
    returns the same committed artifact identities.'
proof_bundle: existing+challenge
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Outcome
A public fixture-proved finalizer applies the native snapshot contract only after terminal-readiness, currentness, approval, claim, writer, request, and path checks, then publishes immutable finalization evidence and returns the tracked paths for the caller's scoped commit.

## Scope
In scope: reusable MOD-001 finalization transaction, typed request/result/finalization-receipt declarations, and MOD-006 public command/script adapter.

Out of scope: invoking the command against the live self-hosting board, native job dispatch for DN-015, consumer setup, and broad legacy-surface removal.

## Authority
DN-012 at delivery digest `6c95c70c81a13ef7a59206ac63bfd9b7338ccb87520d22d90517bf67d50167e9`; IF-016, MIG-005's consumed handoff contract, DEC-036, RISK-001, KEEP-007, MOD-001 internal ownership, and MOD-006 public interface ownership.

Proof guidance: invoke the public command against temporary populated repositories and exercise the finite approval/currentness/readiness/path/publication/absence matrix; never point it at the live board.

[[2026-07-27T10:48:55+02:00]]
## Builder Notes

Implemented IF-016 as a fixture-proved fail-closed bootstrap finalizer without invoking the live carrier.

- Added typed readiness/request/error/receipt/result contracts and a replayable core transaction in `serve/kanban`.
- Added public source-inventory and published-snapshot verification helpers that recompute every content hash.
- Added `setup/finalize.py`, a thin JSON command returning machine-readable success or typed failure.
- Finalization validates proof/terminal declarations, zero claims/writers/requests/unclassified records, authority/code/source currentness, explicit approval, and workspace-relative non-overlapping paths before mutation. It publishes a verified snapshot, removes source and sibling carrier, verifies absence, publishes an exclusive deterministic receipt, and returns the exact four commit paths.
- A deterministic pending fingerprint supports same-request replay after interruption. Receipt-link interruption rolls back the visible receipt; corruption rolls back the snapshot while the source remains; completed replay verifies and returns identical artifact identities.

Proof:
- Complete `serve/kanban` suite plus command contract: 338 passed, with 4 existing Python multiprocessing fork deprecation warnings.
- Setup/export regressions: 18 passed.
- Root test collection succeeds.
- Ruff check and format pass across all affected package/setup/test paths; direct command help and package imports succeed; editor diagnostics and scoped `git diff --check` are clean.
- Builder challenger APPROVE with no follow-up; independent finalizer/snapshot/command run: 34 passed.

All destructive tests used temporary workspaces. The live `.owlbear/kanban` carrier was not supplied to the finalizer.

[[2026-07-27T10:51:30+02:00]]
## Verifier Notes

PASS against builder commit `f8c6d6cbbac2007f6ca25a7f5ef52610e3cda070`.

- `git show --check` passed; the committed finalizer/snapshot/public-command matrix passed 34 tests.
- A first challenger incorrectly classified Python 3.14 PEP 758 syntax (`except A, B:`) as invalid. This was disproved under the repository contract: Python 3.14.6 imported the module, `py_compile` passed, Ruff 0.16 reported the file already formatted, and all committed tests executed successfully. No compatibility edit was made.
- The fresh verifier challenger returned PASS with no findings. AC-1 is covered by fixture finalization, content-hash verification, both-carrier absence, deterministic receipt validation, exact tracked paths, exports, and CLI output. AC-2 covers readiness, stale identities, source mutation, unsafe/overlapping/symlink paths, existing destination, verification/publication/receipt failure, and recovery state. AC-3 covers interruption after snapshot/source removal, absence verification, before/after receipt publication, correction/replay, and stable receipt/manifest identities.
- No proof invoked the live `.owlbear/kanban` carrier.

[[2026-07-27T10:51:57+02:00]]
## Collect Notes

ARCHIVED. Builder commit `f8c6d6cbbac2007f6ca25a7f5ef52610e3cda070` and verifier commit `efedb36094fdb2b370131d8e0643edbfd24207e6` are reachable from `dev`; no task-owned implementation/test path is uncommitted. Direct evidence closes AC-1 through AC-3, both challengers' final decisions approve/pass with no follow-up, and the one initial syntax objection was conclusively disproved against the pinned Python 3.14.6/Ruff contract. The live external carrier remains untouched for DN-015.
