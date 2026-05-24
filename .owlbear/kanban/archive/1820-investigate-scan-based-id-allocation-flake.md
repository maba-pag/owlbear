---
id: 1820
title: Fix scan based id allocation race
status: archived
priority: important
created: 2026-05-24T09:23:21+02:00
updated: 2026-05-24T10:50:02.895701+02:00
tags:
  - scope:kanban-engine
  - concurrency
  - test-failure
  - discussion
parent: 1814
depends_on:
  - 1814
ac:
  - The `test_ac4_concurrent_creates_produce_distinct_scan_based_ids` failure is
    reproduced or classified as flaky.
  - Current ID allocation locking/scan behavior is traced before implementation.
  - Any fix has a repeated or stress-style verification command.
blocked: false
block_reason:
claimed_at:
archival_reason: completed
archival_refs: []
---
## Observation
The #1814 root glob has one failure in `tests/test_engine_1443.py::TestFromAC_ScanBasedIdAllocation::test_ac4_concurrent_creates_produce_distinct_scan_based_ids`.

## Boundary
Do not change ID allocation without reproducing the failure and checking concurrent create behavior.

## Decision
User approved implementing #1820. This was an observed runtime race, not a stale test:
- `allocate_next_id()` scanned active/archive files and invoked the create callback without a lock that serialized concurrent threads in the same process.
- Concurrent `create_task()` calls could scan the same max prefix and attempt duplicate IDs.

The fix wraps scan, optional `.next_id` read/write, and callback write in a narrow allocation lock. The lock uses the existing ignored `.next_id.lock` artifact and combines a per-board `threading.Lock` for same-process threads with `fcntl.flock()` for cross-process callers.

## Verification
- `uv run ruff check serve/kanban/src/owlbear_kanban/storage.py tests/test_engine_1443.py` — passed.
- `uv run pytest tests/test_engine_1443.py -q --tb=short` — 17 passed.
- `for i in {1..25}; do uv run pytest tests/test_engine_1443.py::TestFromAC_ScanBasedIdAllocation::test_ac4_concurrent_creates_produce_distinct_scan_based_ids -q --tb=short || exit 1; done` — 25/25 passed.
- `for i in {1..10}; do uv run pytest tests/test_engine_1443.py::TestFromAC_ScanBasedIdAllocation::test_ac4_concurrent_creates_produce_distinct_scan_based_ids -q --tb=short || exit 1; done` — 10/10 passed after switching to `.next_id.lock`.
- `uv run pytest serve/kanban/tests -q --tb=short` — 1358 passed.
- `uv run pytest tests/test_engine_*.py tests/test_kanban_*.py -q --tb=no` — 2 failed, 538 passed.

## Remaining
The root glob remains red due to #1821 only.