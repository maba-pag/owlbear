---
id: 1205
title: Thread cached config through read_task
status: backlog
priority: important
created: '2026-04-30 15:29:06.208450+00:00'
updated: '2026-04-30 15:32:04.123034+00:00'
tags:
- audit-kanban
- performance
parent:
depends_on:
- 1204
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

## Objective
Avoid redundant config disk reads in read_task hot path.

## Files
- storage.py (read_task function)
- engine.py (callers of read_task)

## Change
Add optional `config: BoardConfig | None = None` parameter to `read_task()`. Engine passes its cached `self._config`. Standalone callers still load from disk.

## AC
- [ ] read_task accepts optional config parameter
- [ ] Engine callers pass cached config
- [ ] Standalone callers still work without passing config
- [ ] No behavior change; performance improvement on hot path

## Finding: 5.1
