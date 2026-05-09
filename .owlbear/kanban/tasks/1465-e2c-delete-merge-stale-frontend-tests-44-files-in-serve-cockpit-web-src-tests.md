---
id: 1465
title: 'E2c: Delete/merge stale frontend tests (44 files in serve/cockpit/web/src/__tests__/)'
status: research
priority: important
created: 2026-05-09T03:32:04.287026+00:00
updated: 2026-05-09T03:32:25.854834+00:00
tags:
- pipeline
- ws-cleanup
- scope:tests
- frontend
parent: 1415
depends_on:
- 1463
blocked: false
block_reason:
claimed_at:
archival_reason:
archival_refs: []
---

Parent: #1415
Brief: .owlbear/research/1415-stale-test-cleanup.md

## Acceptance Criteria
P1: 44 task-scoped TSX test files cleaned up (delete duplicates, rename singles, merge multiples)
P2: Vitest suite passes with same or better pass count
P3: Shell_* (10 files) and KanbanBoard_* (6 files) are largest merge groups

## Scope
In scope: serve/cockpit/web/src/__tests__/*_{task_id}.test.tsx files only
Out of scope: Python tests, new test creation