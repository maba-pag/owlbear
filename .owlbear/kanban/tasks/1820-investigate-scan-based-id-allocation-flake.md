---
id: 1820
title: Investigate scan based id allocation failure
status: research
priority: important
created: 2026-05-24T09:23:21+02:00
updated: 2026-05-24T09:23:21+02:00
tags:
  - scope:kanban-engine
  - concurrency
  - test-failure
  - discussion
parent: 1814
depends_on:
  - 1814
ac:
  - The `test_ac4_concurrent_creates_produce_distinct_scan_based_ids` failure is reproduced or classified as flaky.
  - Current ID allocation locking/scan behavior is traced before implementation.
  - Any fix has a repeated or stress-style verification command.
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---
## Observation
The #1814 root glob has one failure in `tests/test_engine_1443.py::TestFromAC_ScanBasedIdAllocation::test_ac4_concurrent_creates_produce_distinct_scan_based_ids`.

## Boundary
Do not change ID allocation without reproducing the failure and checking concurrent create behavior.