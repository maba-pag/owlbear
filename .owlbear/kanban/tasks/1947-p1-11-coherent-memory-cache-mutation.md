---
id: 1947
title: 'P1-11: Coherent memory cache mutation'
status: collect
priority: medium
created: 2026-07-17T03:04:14.374374+02:00
updated: 2026-07-17T06:38:00.683802+02:00
tags:
  - phase-1
  - scope:memory
  - concurrency
  - integrity
parent: 1951
depends_on:
  - 1946
ac:
  - 'AC-1: Given purge interleaved with an mtime-triggered public get_entries reload,
    both calls complete and the returned entries and ID lookups correspond to files
    remaining in the memory directory.'
  - 'AC-2: Given an ordinary mutation interleaved with reload, both calls complete
    and subsequent public reads expose the persisted post-mutation entry without index
    loss or duplication.'
  - 'AC-3: Given pending and non-pending delete requests after synchronization is
    introduced, pending deletion removes its file while non-pending deletion persists
    a deleted tombstone.'
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Outcome
Shared memory cache and ID-to-path state remains coherent across reload, purge, and ordinary mutation threads.

## Scope
In scope: serialization of the mtime check, reload, index reads/replacement, and mutation paths.

Out of scope: purge eligibility, Cockpit API behavior, and frontend behavior.

## Contract Authorities
- Shared cache and index owner: `MemoryEngine`.
- Concurrency design: OpenSpec Design decision 2.

Proof guidance: run focused public-engine concurrency checks with scheduling controlled below the calls, plus an existing memory-engine downstream-impact scan.

[[2026-07-17T06:36:23+02:00]]
## Builder Notes

Change envelope: serialize all MemoryEngine paths that read, reload, replace, or mutate `_entries`, `_id_to_path`, and the mtime cache with the existing instance-level re-entrant lock. Preserve purge eligibility, API, and frontend behavior.

Files changed: `serve/memory/src/owlbear_memory/engine.py`.

Change Module Map deviations: none. The implementation stayed within the shaped MemoryEngine owner and reused its existing `RLock`; no new abstraction or dependency was introduced.

Proof selected: existing memory-engine lifecycle and downstream-impact suites, plus Ruff. No durable tests added: the maintained suites exercise the shared public boundary and the task required synchronization of existing mutation paths; adding timing-sensitive thread tests would not provide stronger deterministic proof here.

Commands run:
- `cd /Users/markus/Projects/owlbear-dev && uv run pytest tests/test_memory_engine_lifecycle.py -q --tb=short` -> 59 passed.
- `cd /Users/markus/Projects/owlbear-dev && uv run ruff check serve/memory/src/owlbear_memory/engine.py` -> All checks passed.
- Builder challenger ran broader proof: `uv run pytest -q tests/test_memory_engine_lifecycle.py tests/test_memory_state_machine.py tests/test_confirmation_cycle.py tests/test_assess_memories.py tests/test_memory_migration.py` -> 198 passed in 1.02s.

Builder-challenger result: pass. It confirmed all public cache/index mutation paths are serialized and found no remaining blocker.

Follow-up risks: deterministic interleaving tests are not present in the existing suite; verifier should inspect the concurrency contract and confirm the lock coverage against AC-1 through AC-3.

[[2026-07-17T06:38:00+02:00]]
## Verify Notes

Verdict: PASS.

Evidence reviewed:
- Contract authority checked: `openspec/changes/purge-deleted-memories/design.md`, Decision 2 requires one instance-level re-entrant lock around mtime checks, reload/index replacement, purge, preview, and ordinary mutation paths.
- Change Module Map checked: implementation remains solely in `serve/memory/src/owlbear_memory/engine.py`, the shaped `MemoryEngine` owner. No module-map or public-interface deviation.
- Source review: `_lock` covers `load()`, `get_entries()` including the `has_changed()` plus `_load()` sequence, `preview_purge()`, `purge()`, `health()`, all public mutation methods, `save()`, and `migrate_scores()`. `_write_updated_entry()`, `_remove_from_cache()`, and `_upsert_cache()` mutate shared state only through these guarded paths. RLock re-entrancy permits composed reads safely.

Normal-path boundary exercised:
- Focused ephemeral public-engine concurrency probe (scheduling controlled below `MemoryEngine` calls) blocked `storage.delete_entry` during `purge(0)` while `get_entries()` ran, then verified both threads completed, the returned entries were empty, and `_id_to_path` was empty.
- The same probe blocked `_load()` during mtime-triggered `get_entries()` while `save()` ran, then verified both threads completed and the final public read retained the saved entry. Result: `public cache concurrency probes passed`.
- No command/workflow boundary was mocked or replaced; gates were below public engine calls solely to force the interleavings.

Checks run:
- `uv run --project . test-root serve/memory/src/owlbear_memory/engine.py` -> pytest mapping at repository root.
- `uv run pytest -q tests/test_memory_engine_lifecycle.py tests/test_memory_state_machine.py tests/test_confirmation_cycle.py tests/test_assess_memories.py tests/test_memory_migration.py` -> 198 passed in 0.94s.
- `uv run ruff check serve/memory/src/owlbear_memory/engine.py` -> All checks passed.
- `git diff --check` -> no whitespace errors.

AC findings:
- AC-1 and AC-2 pass through the forced public-engine interleavings and coherent final cache/index state.
- AC-3 is covered by the passing lifecycle suite: pending deletion physically removes the entry; non-pending deletion persists the deleted tombstone.

Patches applied: none.

Verifier-challenger result: pass; no concrete missing AC evidence, scope drift, or design deviation.

Final route: PASS -> collect.
