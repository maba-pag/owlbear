---
id: 1402
title: Harden cache populate ordering in MtimeScanCache
status: backlog
priority: nice-to-have
created: 2026-05-06T03:40:51.447745+00:00
updated: 2026-05-06T04:10:45.516267+00:00
tags:
- cockpit
- cache
parent: 1346
depends_on: []
blocked: false
block_reason:
claimed_at: 2026-05-06T04:10:45.516267+00:00
archival_reason:
archival_refs: []
---

## Context

In `serve/cockpit/src/owlbear_cockpit/routes/read.py:92-93`, `cache.has_changed_at(mtime)` commits the new signature as a side effect before `view.list_tasks()` populates `cache.tasks` at line 95. If `view.list_tasks()` raises (e.g., engine CorruptionError on duplicate IDs), the signature is committed but the cache holds stale data. The next request with the same directory state sees no change (signature already committed) and serves stale tasks until the next real file modification.

Identified during architect re-review of #1346 as follow-up recommendation #1.

## Acceptance Criteria

1. `MtimeScanCache` signature state is not updated until `cache.tasks` is successfully populated. If `view.list_tasks()` raises after a directory-signature change is detected, the signature must remain at its previous value so the next request retries the populate.
2. A test proves that a failed `view.list_tasks()` call does not commit the signature — the subsequent request must re-detect the change and retry population.
3. Existing cockpit test suites pass without modification (154+ tests across `test_cockpit_cache_sse_1346.py`, `test_cockpit_read_api.py`, `test_cockpit_events_*`).

## Scope

- **In scope:** `cache.py` (possible API change to separate check from commit), `routes/read.py` (reorder or wrap the signature commit).
- **Out of scope:** SSE events, archive watching, mutation-route invalidation (all handled by #1346).

## Key Files

- `serve/cockpit/src/owlbear_cockpit/cache.py`
- `serve/cockpit/src/owlbear_cockpit/routes/read.py`