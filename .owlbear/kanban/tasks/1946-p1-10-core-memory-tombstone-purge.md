---
id: 1946
title: 'P1-10: Core memory tombstone purge'
status: collect
priority: medium
created: 2026-07-17T03:04:09.242165+02:00
updated: 2026-07-17T06:08:36.651805+02:00
tags:
  - phase-1
  - scope:memory
  - maintenance
  - data-safety
parent: 1951
depends_on: []
ac:
  - 'AC-1: Given deleted entries at the cutoff and newer than the cutoff plus a non-deleted
    entry, the public preview operation counts the at-cutoff entry as eligible, counts
    the newer deleted entry as too_recent, reports deleted_total for those two tombstones,
    and leaves the filesystem unchanged.'
  - 'AC-2: Given min_age_days=0, the public purge operation removes the deleted entries,
    preserves the non-deleted entry, and returns purged, skipped, and failed counts
    that reconcile with the classified deleted set.'
  - 'AC-3: Given one eligible unlink failure and one eligible file already absent,
    purge continues, reports the unlink failure as failed, reports the absent desired
    state as purged, and leaves failed entry state available for retry.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
MemoryEngine previews and performs age-based best-effort tombstone purge through one eligibility authority.

## Scope
In scope: core eligibility, one UTC cutoff per request, protected physical deletion, and reconciled outcome counts.

Out of scope: cache synchronization, HTTP routes, Cockpit UI, and changes to ordinary memory deletion behavior.

## Contract Authorities
- OpenSpec capability: `memory-tombstone-purge`.
- Memory state, timestamp, path, and mutation authority: `MemoryEngine`.
- Physical deletion safety authority: `owlbear_memory.storage.delete_entry`.

Proof guidance: run focused pytest at the public MemoryEngine boundary; control clock and selected storage outcomes below the engine, then scan existing memory deletion checks for downstream impact.

[[2026-07-17T06:06:58+02:00]]
## Builder Notes
Change envelope: Core memory tombstone purge only; eligibility, one UTC cutoff per request, protected physical deletion, reconciled counts, and local engine synchronization. No routes, UI, cache synchronization beyond engine indexes, or ordinary deletion behavior changes.

Files changed: `serve/memory/src/owlbear_memory/models.py`, `serve/memory/src/owlbear_memory/engine.py`.

Change Module Map deviations: none. Added typed `PurgePreview` and `PurgeResult`; added `MemoryEngine.preview_purge()` and `purge()` using one deleted-entry eligibility helper, UTC cutoff arithmetic, `storage.delete_entry`, absent-file reconciliation, continued per-entry failure handling, and an instance `RLock` around cache/index loading and access.

Proof selected: focused existing memory engine behavior suite plus direct public-boundary filesystem smoke proof.

Commands run:
- `uv run pytest tests/test_memory_engine.py tests/test_memory_engine_lifecycle.py tests/test_memory_state_machine.py -q` -> 96 passed.
- `uv run ruff check serve/memory/src/owlbear_memory/models.py serve/memory/src/owlbear_memory/engine.py` -> passed.
- `uv run ruff format --check serve/memory/src/owlbear_memory/models.py serve/memory/src/owlbear_memory/engine.py` -> passed.
- Direct `uv run python` smoke test -> `memory purge smoke passed`; covered exact cutoff preview, newer tombstone classification, non-deleted preservation, and zero-day purge.

Durable-test justification: no durable tests added. Existing tests and focused executable smoke proof adequately protect this core slice; the task's broader task-specific failure injection remains a verifier concern.

Builder-challenger result: `builder-challenger` returned `decision: pass` with no concrete blockers.

Follow-up risks: the existing repository has an unrelated pre-existing task-file modification in the worktree; it was not changed or reverted. Failure injection and already-absent-file continuation should receive verifier-level focused coverage for AC-3.

[[2026-07-17T06:08:36+02:00]]
## Verify Notes
Evidence reviewed: builder diff for `serve/memory/src/owlbear_memory/models.py` and `serve/memory/src/owlbear_memory/engine.py`; builder command records; and the delta authority `openspec/changes/purge-deleted-memories/specs/memory-tombstone-purge/spec.md`.

Named authorities checked: the OpenSpec requirement defines exact-cutoff, zero-day, protected deletion, already-absent reconciliation, and count requirements; `MemoryEngine` remains the eligibility/state/index owner; `owlbear_memory.storage.delete_entry` remains the physical deletion safety owner.

Change Module Map: no deviations. The implementation is limited to the shaped core models and engine slice. No routes, Cockpit UI, cache sidecar, or ordinary deletion contract changes are present.

Normal-path boundary exercised: an independent temporary public-`MemoryEngine` smoke proof seeded exact-cutoff deleted, newer deleted, non-deleted, injected-unlink-failure, and already-absent-after-classification entries. Clock and `storage.delete_entry` were controlled below the engine boundary. Preview returned deleted_total=4, eligible=3, too_recent=1 without filesystem mutation. Purge returned purged=2, skipped=1, failed=1; exact and absent tombstones were reconciled and removed, recent/non-deleted/failed entries remained, and the failed entry stayed available for retry.

Replacements used below boundary: frozen `owlbear_memory.engine.datetime` and selected `owlbear_memory.engine.storage.delete_entry` outcomes only; the public engine operations, eligibility, index updates, and storage safety delegation remained real.

Checks run:
- `uv run python .owlbear/scratch/1946-verify-purge.py` passed.
- `uv run pytest tests/test_memory_engine.py tests/test_memory_engine_lifecycle.py tests/test_memory_state_machine.py -q` passed: 96 tests.
- `uv run ruff check serve/memory/src/owlbear_memory/models.py serve/memory/src/owlbear_memory/engine.py` passed.
- `uv run ruff format --check serve/memory/src/owlbear_memory/models.py serve/memory/src/owlbear_memory/engine.py` passed.
- VS Code diagnostics for both changed source files: no errors.

Findings: no acceptance-criterion gap or local defect found. The temporary smoke proof was removed after execution; no verifier product patch was applied.

Verifier-challenger result: `decision: pass`; no concrete concerns, scope drift, or unresolved acceptance criterion.

Final route: PASS to collect.
