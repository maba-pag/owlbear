---
id: 2011
title: 'P3-12: Persist immutable attempt event history'
status: verify
priority: high
created: 2026-07-23T14:40:36.839480+02:00
updated: 2026-07-23T15:33:51.097882+02:00
tags:
  - phase-3
  - scope:core
  - runtime
  - attempts
  - storage
  - path-safety
  - type:build
  - rigor:thorough
  - change:replace-delivery-pipeline
  - node:DN-003
  - packet:DN-003-PK-004-B
parent: 2003
depends_on:
  - 2010
ac:
  - 'AC-1: Given an explicit work root, public create, read, and list calls return
    the existing record for byte-equivalent replay and list records by attempt ID
    then positive sequence.'
  - 'AC-2: Given different bytes at an occupied event identity, creation raises exported
    `AttemptConflictError` with `code == "ERR_ATTEMPT_CONFLICT"` and preserves the
    existing record.'
  - 'AC-3: Given traversal, symlink substitution, or an injected write failure, the
    store returns the stable path or write diagnostic, leaves outside paths unchanged,
    and leaves no temporary or partial event.'
proof_bundle: critical+challenge
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
A contained `AttemptStore` creates, reads, and lists immutable attempt events with idempotent replay, deterministic ordering, and stable conflict and path-safety behavior.

## Scope
In scope: explicit work root; immutable event identity; byte-equivalent replay; conflict detection; attempt-ID then sequence ordering; traversal and symlink rejection; no-overwrite publication; failed-write cleanup.

Out of scope: mutable job replacement, multi-record transaction recovery, lifecycle guards, receipt validity, and successful completion.

## Current Foundation And Ownership
Consume the `AttemptEvent` contract from task #2010 and the contained storage conventions already used by the native stores. This task owns attempt history persistence only.

## Authority
Resolve behavior from `REQ-008`, `REQ-009`, `REQ-016`, `IF-003`, `KEEP-007`, `PROOF-003`, and design sections 2.3, 7.2, 12, 13, and 14.

## Proof Guidance
Exercise public create, read, and list operations against explicit temporary roots. Cover the finite destination classes absent, byte-equal, byte-different, unsafe, and failed-write.

[[2026-07-23T15:33:51+02:00]]
## Builder Notes
- Change envelope: implement only the explicit-root immutable attempt-event persistence boundary, including stable diagnostics and public exports; no lifecycle, jobs, receipts, transactions, or dispatch changes.
- Files changed: `serve/kanban/src/owlbear_kanban/attempts.py`, `serve/kanban/src/owlbear_kanban/__init__.py`, and `serve/kanban/tests/test_attempts.py`.
- Change Module Map: no deviation. The existing `attempts.py` contract owner now contains its matching store; package exports expose the public boundary.
- Proof selected: durable public-store tests were added because immutable event persistence, replay/conflict behavior, path containment, and partial-write cleanup are shared data-integrity and security boundaries. They cover ordered list/replay, conflict preservation, traversal, symlink substitution, and injected fsync failure with no partial output.
- Commands run: `uv run pytest serve/kanban/tests/test_attempts.py` (17 passed); `uv run ruff check serve/kanban/src/owlbear_kanban/attempts.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_attempts.py` (passed); `uv run ruff format --check serve/kanban/src/owlbear_kanban/attempts.py serve/kanban/src/owlbear_kanban/__init__.py serve/kanban/tests/test_attempts.py` (3 files already formatted); `git diff --check` (passed).
- Builder-challenger: pass; independently reran the same focused test, lint, and formatting checks with no concrete acceptance-criteria gap.
- Follow-up risks: full runtime transaction coordination and lifecycle guards remain deliberately owned by dependent tasks.
