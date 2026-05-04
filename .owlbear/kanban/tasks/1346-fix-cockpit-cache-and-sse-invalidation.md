---
id: 1346
title: Fix Cockpit cache and SSE invalidation
status: backlog
priority: critical
created: 2026-05-04T17:27:34.924833+00:00
updated: 2026-05-04T17:28:16+00:00
tags:
- sync-blocker
- cockpit
- cache
- events
parent:
depends_on:
- 1344
- 1345
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Context

Cockpit task-list invalidation can miss task removals and archive moves. SSE skips deleted task paths and does not watch archive files as task-list invalidation signals; the HTTP task cache compares only the maximum file mtime in `tasks/`, so deleting a non-newest task file leaves cached board data unchanged.

Audit decision: implement robust invalidation rather than an archive-only SSE patch.

## Acceptance Criteria

1. `MtimeScanCache` uses a directory signature that changes on create, edit, delete, rename, and archive moves. The signature must not rely only on max file mtime.
2. `GET /api/tasks` reloads from `CockpitView.list_tasks()` whenever the signature changes and never returns a deleted/archived active task from cache.
3. Successful Cockpit mutation routes that change task visibility or summary fields invalidate the task-list cache deterministically, or the cache implementation detects the mutation without a race.
4. `GET /api/events` emits a task invalidation event for task deletion/archive movement even when the changed active task path no longer exists by the time it is processed.
5. Archive directory writes that affect active-board membership are treated as task-list invalidation signals, without causing archived tasks to appear in the active list.
6. Existing `activity-changed` and `decisions-changed` event behavior remains intact.
7. Durable tests cover: deletion of a non-newest task file, archive move of a non-newest task, delete-only watch batch, mixed delete/survivor watch batch, and mutation-route cache invalidation.

## Key Files

- `serve/cockpit/src/owlbear_cockpit/cache.py`
- `serve/cockpit/src/owlbear_cockpit/routes/read.py`
- `serve/cockpit/src/owlbear_cockpit/routes/events.py`
- `serve/cockpit/src/owlbear_cockpit/routes/mutation.py`
- `tests/test_cockpit_read_api.py`
- `tests/test_cockpit_events_1234.py`

## Audit Evidence

- A direct cache repro showed `has_changed()` returns `False` after deleting a non-newest task file because `scan()` still returns the newest remaining file mtime.
- `events.py` skips deleted paths via `FileNotFoundError`, so a pure delete/archive-out batch can emit no `tasks-changed` event.
- The watch filter covers direct task markdown, pending decisions, and activity log, but not archive files.

## Recommendation

Use a robust directory signature plus explicit mutation invalidation where appropriate. Disabling cache is acceptable only as a temporary correctness-first fallback.
