---
id: 1845
title: 'P2-06: Confirmation cycle — factually-wrong to contested/disputed'
status: research
priority: needed
created: 2026-05-24T19:01:24.983062+02:00
updated: 2026-05-24T19:15:17.417379+02:00
tags:
  - phase-2
  - scope:memory
  - feature
parent: 1839
depends_on:
  - 1840
  - 1841
ac:
  - '`MemoryEntry` has `contested_by_task: str | None` (default None) field. Engine
    method `record_factually_wrong(entry_id, task_id, expected_updated_at)` on first
    call sets state to contested and stores contested_by_task = task_id. Entry remains
    in recall results.'
  - Second call to `record_factually_wrong` where task_id differs from stored 
    contested_by_task transitions state from contested to disputed. Entry is 
    excluded from recall.
  - Second call with same task_id as contested_by_task is a no-op (returns entry
    unchanged, no error). Calls on entries not in voteable state (pending, 
    deleted, stale, disputed) raise TransitionError.
  - "`expected_updated_at` is a CAS guard: if provided and does not match the entry's
    current `updated_at`, raise ConflictError without mutating the entry. If None,
    the check is skipped (unconditional write)."
proof_bundle: behavioral
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
Brief: see parent #1839

## Scope

Implement the two-step confirmation cycle for factually-wrong assessments.

### In Scope
- MemoryEntry field: contested_by_task (str | None, default None)
- Engine method: record_factually_wrong(entry_id, task_id, expected_updated_at)
- First factually_wrong → contested (still recalled)
- Second from different task → disputed (excluded)
- Same-task duplicate = no-op
- Voteable state guard (approved, curated, contested)

### Out of Scope
- State enum definition (P2-01)
- Assessment tool (P2-07)
- Score computation (P2-02)

## Domain
serve/memory/